"""Envelope dispatch layer for the WS server handler.

Split out of :mod:`asap.transport.ws.server` so the server module stays under
the 400-LOC ceiling mandated by the v2.5.1 thermo-nuclear patch. Owns the 3.2
change: envelopes are dispatched directly via
:meth:`ASAPRequestHandler._prepare_request` + ``registry.dispatch_async`` /
``dispatch_stream_async`` (no fake-request synthesis, no HTTP ``handle_message``).
"""

from __future__ import annotations

import json
import time
from typing import TYPE_CHECKING, Any, cast

from fastapi import WebSocket
from fastapi.responses import Response
from pydantic import ValidationError
from starlette.requests import Request

from asap.models.envelope import Envelope
from asap.observability import get_logger
from asap.observability.tracing import inject_envelope_trace_context
from asap.transport.jsonrpc import INTERNAL_ERROR, JsonRpcResponse
from asap.transport.rate_limit import WebSocketTokenBucket
from asap.transport.ws._actions import WSCloseAction
from asap.transport.ws.codecs import _build_ack_notification_frame
from opentelemetry import context

if TYPE_CHECKING:
    from asap.transport.server import ASAPRequestHandler, PreparedRequest

logger = get_logger(__name__)


def _is_prepared_request(prepared: Any) -> bool:
    """Structural check distinguishing a ``PreparedRequest`` from an error ``Response``.

    ``_prepare_request`` returns either a :class:`PreparedRequest` (has
    ``envelope``/``ctx``/``trace_token``) or a JSON-RPC error
    :class:`fastapi.responses.Response` (has ``body``, no ``envelope``). We avoid
    importing ``PreparedRequest`` at module top to break a circular import
    (``asap.transport.server`` → ``routes`` → ``asap.transport.websocket`` →
    ``asap.transport.ws`` → this module), so the check is structural.
    """
    return hasattr(prepared, "envelope") and hasattr(prepared, "ctx")


def _registry_has_streaming_for_payload(registry: Any, payload_type: str) -> bool:
    """True only when registry reports streaming with a real bool (not e.g. MagicMock)."""
    fn = getattr(registry, "has_streaming_handler", None)
    if not callable(fn):
        return False
    return fn(payload_type) is True


async def _synthesize_ws_request(body: str, websocket: WebSocket) -> Request:
    """Build a minimal Starlette ``Request`` carrying *body* for the shared pipeline.

    Replaces the deleted fake-request synthesis. The shared
    :meth:`ASAPRequestHandler._prepare_request` pipeline reads the JSON-RPC body
    via ``request.stream()``, so the WS path must hand it a ``Request``. The
    scope mirrors the WS handshake (headers, path, server) so auth and
    content-length checks behave like the HTTP path.
    """
    body_bytes = body.encode("utf-8")
    headers = list(websocket.scope.get("headers", []))
    headers.append((b"content-length", str(len(body_bytes)).encode()))
    scope: dict[str, Any] = {
        "type": "http",
        "method": "POST",
        "headers": headers,
        "path": websocket.scope.get("path", "/asap"),
        "root_path": "",
        "query_string": b"",
        "server": websocket.scope.get("server", ("localhost", 8000)),
    }
    first_receive = True

    async def receive() -> dict[str, Any]:
        nonlocal first_receive
        if first_receive:
            first_receive = False
            return {"type": "http.request", "body": body_bytes, "more_body": False}
        return {"type": "http.disconnect"}

    async def send(_: Any) -> None:
        pass

    return Request(scope, receive, send)


async def _send_rate_limit_error(
    websocket: WebSocket, bucket: WebSocketTokenBucket, data: dict[str, Any]
) -> None:
    """Send the JSON-RPC rate-limit error frame and log the exceeded event."""
    logger.warning(
        "asap.websocket.rate_limit_exceeded",
        client=websocket.client,
        limit_per_sec=bucket.rate,
    )
    await websocket.send_text(
        json.dumps(
            {
                "jsonrpc": "2.0",
                "error": {
                    "code": -32001,
                    "message": "Rate limit exceeded; too many messages per second",
                },
                "id": data.get("id"),
            }
        )
    )


def _extract_envelope_for_ack(data: dict[str, Any]) -> Envelope | None:
    """Validate the envelope in *data*'s params for ack routing; None if absent/invalid."""
    params = data.get("params")
    envelope_dict = params.get("envelope") if isinstance(params, dict) else None
    if not isinstance(envelope_dict, dict):
        return None
    try:
        return Envelope.model_validate(envelope_dict)
    except ValidationError as e:
        logger.warning("asap.websocket.envelope_validation_failed", error=str(e))
        return None


async def _maybe_send_received_ack(websocket: WebSocket, envelope_for_ack: Envelope | None) -> None:
    """Send a ``received`` ack frame when *envelope_for_ack* requires one."""
    if envelope_for_ack is None or not envelope_for_ack.requires_ack or not envelope_for_ack.id:
        return
    ack_frame = _build_ack_notification_frame(
        original_envelope_id=envelope_for_ack.id,
        status="received",
        sender=envelope_for_ack.recipient,
        recipient=envelope_for_ack.sender,
        asap_version=envelope_for_ack.asap_version,
    )
    await websocket.send_text(ack_frame)


async def _dispatch_ws_envelope(
    websocket: WebSocket,
    request_handler: "ASAPRequestHandler",
    raw: str,
    data: dict[str, Any],
    envelope_for_ack: Envelope | None,
) -> WSCloseAction:
    """Prepare the request and dispatch its envelope directly (3.2).

    Uses :meth:`ASAPRequestHandler._prepare_request` to run the shared
    parse→auth→envelope→timestamp→nonce gate, then hands the validated envelope
    to ``registry.dispatch_async`` or ``dispatch_stream_async`` instead of the
    HTTP ``handle_message``/``iter_websocket_stream``. Sends a ``rejected`` ack
    and a JSON-RPC error frame on failure. Returns ``CLOSE_FATAL`` if the
    internal-error frame itself cannot be sent (connection broken), else
    ``CONTINUE``.
    """
    jsonrpc_id = data.get("id")
    response_id: str | int = jsonrpc_id if jsonrpc_id is not None else ""
    prepared: Any = None
    try:
        request = await _synthesize_ws_request(raw, websocket)
        prepared = await request_handler._prepare_request(  # noqa: SLF001 — public dispatch seam
            request, time.perf_counter(), received_log_event="asap.request.ws_received"
        )
        if _is_prepared_request(prepared):
            await _run_ws_dispatch(
                websocket, request_handler, cast("PreparedRequest", prepared), response_id
            )
            return WSCloseAction.CONTINUE
        # Preparation failed: forward the JSON-RPC error response body over WS.
        body = cast("Response", prepared).body
        await websocket.send_text(body.decode("utf-8") if isinstance(body, bytes) else str(body))
        return WSCloseAction.CONTINUE
    except Exception as e:
        logger.warning("asap.websocket.message_error", error=str(e))
        await _send_ws_dispatch_failure(websocket, envelope_for_ack, e)
        return await _send_internal_error_frame(websocket, e)
    finally:
        if _is_prepared_request(prepared):
            context.detach(cast("PreparedRequest", prepared).trace_token)


async def _run_ws_dispatch(
    websocket: WebSocket,
    request_handler: "ASAPRequestHandler",
    prepared: PreparedRequest,
    response_id: str | int,
) -> None:
    """Dispatch the prepared envelope via the registry and stream frames back over WS."""
    envelope = prepared.envelope
    manifest = request_handler.manifest
    registry = request_handler.registry_holder.registry
    if _registry_has_streaming_for_payload(registry, envelope.payload_type):
        async for response_envelope in registry.dispatch_stream_async(envelope, manifest):
            await _send_ws_result_frame(websocket, response_envelope, response_id)
        return
    response_envelope = await registry.dispatch_async(envelope, manifest)
    await _send_ws_result_frame(websocket, response_envelope, response_id)


async def _send_ws_result_frame(
    websocket: WebSocket, response_envelope: Envelope, response_id: str | int
) -> None:
    """Wrap *response_envelope* in a JSON-RPC result frame and send it over WS."""
    injected = inject_envelope_trace_context(response_envelope)
    frame = JsonRpcResponse(result={"envelope": injected.model_dump(mode="json")}, id=response_id)
    await websocket.send_text(json.dumps(frame.model_dump()))


async def _send_ws_dispatch_failure(
    websocket: WebSocket, envelope_for_ack: Envelope | None, error: Exception
) -> None:
    """Send a ``rejected`` ack frame when WS dispatch raises, if ack is required."""
    if envelope_for_ack is None or not envelope_for_ack.requires_ack or not envelope_for_ack.id:
        return
    reject_frame = _build_ack_notification_frame(
        original_envelope_id=envelope_for_ack.id,
        status="rejected",
        sender=envelope_for_ack.recipient,
        recipient=envelope_for_ack.sender,
        asap_version=envelope_for_ack.asap_version,
        error=str(error),
    )
    await websocket.send_text(reject_frame)


async def _send_internal_error_frame(websocket: WebSocket, error: Exception) -> WSCloseAction:
    """Best-effort emit a JSON-RPC internal-error frame; ``CLOSE_FATAL`` if send fails."""
    error_payload = {
        "jsonrpc": "2.0",
        "error": {
            "code": INTERNAL_ERROR,
            "message": "Internal error",
            "data": {"error": str(error)},
        },
        "id": None,
    }
    try:
        await websocket.send_text(json.dumps(error_payload))
    except Exception as send_error:  # noqa: BLE001 — send failure breaks the loop
        logger.debug("asap.websocket.error_payload_failed", error=str(send_error))
        return WSCloseAction.CLOSE_FATAL
    return WSCloseAction.CONTINUE


__all__ = [
    "_dispatch_ws_envelope",
    "_extract_envelope_for_ack",
    "_maybe_send_received_ack",
    "_registry_has_streaming_for_payload",
    "_send_rate_limit_error",
    "_synthesize_ws_request",
]
