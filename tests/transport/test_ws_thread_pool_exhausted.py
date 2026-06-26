"""WS dispatch must not forward the non-JSON-RPC HTTP 503 body verbatim (CR#2).

``ASAPRequestHandler._dispatch_to_handler`` returns a non-JSON-RPC HTTP 503 body
(``error`` as a string) for ``ThreadPoolExhaustedError``. Forwarding that verbatim
over WS crashes the client recv loop, which calls ``data["error"].get("code")``.
The WS path must re-frame it as a canonical JSON-RPC error preserving ``rpc_code``,
``retry_after_ms``, and the request ``id``.
"""

from __future__ import annotations

import json
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import WebSocket
from fastapi.responses import JSONResponse

from asap.errors import RPC_THREAD_POOL_EXHAUSTED
from asap.transport.ws._dispatch import _run_ws_dispatch


def _thread_pool_503_response() -> JSONResponse:
    """The non-JSON-RPC 503 body `_dispatch_to_handler` returns on pool exhaustion."""
    return JSONResponse(
        status_code=503,
        content={
            "error": "Service Temporarily Unavailable",
            "code": 503,
            "rpc_code": RPC_THREAD_POOL_EXHAUSTED,
            "message": "Thread pool exhausted",
            "details": {},
            "recoverable": True,
            "retry_after_ms": 1000,
            "fallback_action": "retry",
        },
    )


def _prepared_stub() -> Any:
    """Minimal PreparedRequest-like stub with ``envelope`` and ``ctx`` attributes."""
    prepared = MagicMock()
    prepared.envelope.payload_type = "task.request"
    prepared.envelope.id = "env-1"
    prepared.envelope.sender = "urn:asap:agent:client"
    prepared.ctx = MagicMock()
    prepared.ctx.request_id = "req-1"
    prepared.ctx.start_time = 0.0
    prepared.ctx.metrics = MagicMock()
    return prepared


class TestWSThreadPoolExhaustedFraming:
    """CR#2: the 503 body is re-framed as a JSON-RPC error, not forwarded verbatim."""

    @pytest.mark.asyncio
    async def test_503_is_reframed_as_jsonrpc_error_with_id_and_retry(self) -> None:
        """The WS frame is a JSON-RPC error dict with rpc_code, retry_after_ms, and id."""
        ws = MagicMock(spec=WebSocket)
        sent: list[str] = []
        ws.send_text = AsyncMock(side_effect=lambda t: sent.append(t))

        request_handler = MagicMock()
        request_handler._dispatch_to_handler = AsyncMock(  # noqa: SLF001
            return_value=_thread_pool_503_response()
        )
        request_handler.registry_holder.registry = MagicMock()
        request_handler.registry_holder.registry.has_streaming_handler = MagicMock(
            return_value=False
        )

        await _run_ws_dispatch(ws, request_handler, _prepared_stub(), response_id="req-42")

        assert len(sent) == 1, f"expected one frame, got {sent}"
        frame = json.loads(sent[0])
        # JSON-RPC error shape — `error` MUST be a dict, not the 503 string.
        assert frame["jsonrpc"] == "2.0"
        assert frame["id"] == "req-42"
        assert isinstance(frame["error"], dict)
        assert frame["error"]["code"] == RPC_THREAD_POOL_EXHAUSTED
        assert frame["error"]["message"] == "Thread pool exhausted"
        data = frame["error"]["data"]
        assert data["recoverable"] is True
        assert data["retry_after_ms"] == 1000
        assert data["fallback_action"] == "retry"

    @pytest.mark.asyncio
    async def test_non_503_jsonresponse_is_still_forwarded_verbatim(self) -> None:
        """A non-503 JSONResponse (e.g. a JSON-RPC error from HandlerNotFoundError) is untouched."""
        ws = MagicMock(spec=WebSocket)
        sent: list[str] = []
        ws.send_text = AsyncMock(side_effect=lambda t: sent.append(t))

        jsonrpc_error_body = {
            "jsonrpc": "2.0",
            "error": {"code": -32012, "message": "handler not found"},
            "id": "req-42",
        }
        request_handler = MagicMock()
        request_handler._dispatch_to_handler = AsyncMock(  # noqa: SLF001
            return_value=JSONResponse(status_code=200, content=jsonrpc_error_body)
        )
        request_handler.registry_holder.registry = MagicMock()
        request_handler.registry_holder.registry.has_streaming_handler = MagicMock(
            return_value=False
        )

        await _run_ws_dispatch(ws, request_handler, _prepared_stub(), response_id="req-42")

        assert len(sent) == 1
        assert json.loads(sent[0]) == jsonrpc_error_body
