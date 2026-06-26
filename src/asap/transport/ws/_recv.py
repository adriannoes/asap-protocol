"""Receive-loop frame dispatch for :class:`asap.transport.ws.client.WebSocketTransport`.

Split out of ``ws/client.py`` so the transport module stays under the 400-LOC
ceiling mandated by the v2.5.1 thermo-nuclear patch. Exposed as a mixin
(:class:`_RecvDispatch`) that :class:`WebSocketTransport` inherits; it owns the
inbound frame loop and per-frame routing (heartbeat, ``asap.ack``, error,
result, on_message callback) with B6/BUG #6 correlation binding enforcement.
"""

from __future__ import annotations

import asyncio
import json
from typing import Any

from asap.models.envelope import Envelope
from asap.models.payloads import MessageAck
from asap.observability import get_logger
from asap.transport.errors import ProtocolCorrelationError, assert_correlation_binds
from asap.transport.ws._errors import WebSocketRemoteError
from asap.transport.ws.codecs import (
    ASAP_ACK_METHOD,
    HEARTBEAT_FRAME_TYPE_PING,
    HEARTBEAT_FRAME_TYPE_PONG,
    decode_frame_to_json,
)

logger = get_logger(__name__)


class _RecvDispatch:
    """Mixin: inbound WS frame loop and per-frame routing for the client transport.

    The host class must initialize ``_ws``, ``_pending``, ``_pending_request_ids``,
    ``_pending_acks`` and ``_on_message`` before calling :meth:`_recv_loop`.
    """

    _ws: Any
    _pending: dict[str, asyncio.Future[Envelope]]
    _pending_request_ids: dict[str, str]
    _pending_acks: dict[str, Any]
    _on_message: Any

    async def _recv_loop(self) -> None:
        """Receive frames until the connection drops; route each by frame shape."""
        if self._ws is None:
            return
        try:
            while self._ws is not None:
                raw = await self._ws.recv()
                if isinstance(raw, bytes):
                    raw = raw.decode("utf-8")
                try:
                    data = decode_frame_to_json(raw)
                except ValueError as e:
                    logger.warning("asap.websocket.recv_loop_parse_error", error=str(e))
                    continue
                if self._is_client_heartbeat_ping(data):
                    if self._ws is not None:
                        await self._ws.send(json.dumps({"type": HEARTBEAT_FRAME_TYPE_PONG}))
                    continue
                if data.get("method") == ASAP_ACK_METHOD and "params" in data:
                    self._consume_ack_frame(data)
                    continue
                request_id = data.get("id")
                if "error" in data:
                    self._resolve_error_frame(data, request_id)
                    continue
                result = data.get("result")
                if not result or "envelope" not in result:
                    self._resolve_missing_result(data, request_id)
                    continue
                await self._resolve_result_frame(data, request_id, result)
        except asyncio.CancelledError:
            pass
        except (SystemExit, KeyboardInterrupt):
            raise
        except Exception as e:
            logger.warning("asap.websocket.recv_loop_error", error=str(e))
            for future in self._pending.values():
                if not future.done():
                    future.set_exception(WebSocketRemoteError(-32603, str(e)))
            self._pending.clear()
            self._pending_request_ids.clear()

    @staticmethod
    def _is_client_heartbeat_ping(data: dict[str, Any]) -> bool:
        """True when *data* is a server-initiated heartbeat ping (no JSON-RPC method)."""
        return data.get("type") == HEARTBEAT_FRAME_TYPE_PING and "method" not in data

    def _consume_ack_frame(self, data: dict[str, Any]) -> None:
        """Pop a pending ack when a valid ``asap.ack`` MessageAck frame arrives."""
        params = data.get("params") or {}
        env_dict = params.get("envelope") if isinstance(params, dict) else None
        if not isinstance(env_dict, dict):
            return
        try:
            ack_env = Envelope.model_validate(env_dict)
            if ack_env.payload_type == "MessageAck":
                ack = MessageAck.model_validate(ack_env.payload_dict)
                self._pending_acks.pop(ack.original_envelope_id, None)
        except Exception as e:  # noqa: BLE001 — ack parse must not kill the recv loop
            logger.warning(
                "asap.websocket.ack_validation_failed",
                error=str(e),
                envelope_id=env_dict.get("id"),
            )

    def _resolve_error_frame(self, data: dict[str, Any], request_id: Any) -> None:
        """Set the exception on the pending future matching *request_id*, if any."""
        err = data["error"]
        # Defend against malformed frames where ``error`` is not a dict (e.g. a
        # non-JSON-RPC HTTP body forwarded over WS) so the recv loop keeps running
        # instead of crashing with ``AttributeError`` (CR#2 defensive guard).
        if not isinstance(err, dict):
            exc = WebSocketRemoteError(-32603, str(err) if err else "Unknown error")
            if request_id is not None and request_id in self._pending:
                future = self._pending.pop(request_id, None)
                self._pending_request_ids.pop(request_id, None)
                if future is not None and not future.done():
                    future.set_exception(exc)
            else:
                logger.warning("asap.websocket.recv_loop_malformed_error_frame", error=str(err))
            return
        code = err.get("code", -32603)
        msg = err.get("message", "Unknown error")
        exc = WebSocketRemoteError(code, msg, err.get("data"))
        if request_id is not None and request_id in self._pending:
            future = self._pending.pop(request_id, None)
            # Keep _pending_request_ids in lockstep with _pending so no stale id
            # entries leak if other callers ever read this map (B6 follow-up).
            self._pending_request_ids.pop(request_id, None)
            if future is not None and not future.done():
                future.set_exception(exc)
        else:
            logger.warning("asap.websocket.recv_loop_error_frame", code=code, message=msg)

    def _resolve_missing_result(self, data: dict[str, Any], request_id: Any) -> None:
        """Fail the pending future when a response lacks ``result.envelope``."""
        if request_id is None or request_id not in self._pending:
            return
        future = self._pending.pop(request_id, None)
        self._pending_request_ids.pop(request_id, None)
        if future is not None and not future.done():
            future.set_exception(
                WebSocketRemoteError(-32603, "Missing result.envelope in response", data=data)
            )

    async def _resolve_result_frame(
        self, data: dict[str, Any], request_id: Any, result: dict[str, Any]
    ) -> None:
        """Resolve a response envelope to its pending future or the on_message callback."""
        envelope = Envelope.model_validate(result["envelope"])
        if request_id is not None and request_id in self._pending:
            await self._resolve_bound_future(envelope, request_id)
            return
        if self._on_message is not None:
            await self._invoke_on_message(envelope)

    async def _resolve_bound_future(self, envelope: Envelope, request_id: Any) -> None:
        """Bind a response envelope to its pending future with correlation enforcement."""
        future = self._pending.pop(request_id, None)
        request_envelope_id = self._pending_request_ids.pop(request_id, None)
        if future is None or future.done():
            return
        # BINDING: the response must correlate to the request we sent, else a
        # buggy/malicious server could pair a response with the wrong request
        # under concurrency (B6/BUG #6).
        try:
            assert_correlation_binds(str(request_envelope_id), envelope)
        except ProtocolCorrelationError as corr_err:
            future.set_exception(corr_err)
            return
        future.set_result(envelope)

    async def _invoke_on_message(self, envelope: Envelope) -> None:
        """Dispatch a server-push envelope to the on_message callback if set."""
        try:
            cb = self._on_message(envelope)
            if asyncio.iscoroutine(cb):
                await cb
        except Exception as e:  # noqa: BLE001 — callback errors must not kill recv
            logger.warning("asap.websocket.on_message_error", error=str(e))


__all__ = ["_RecvDispatch"]
