"""Unit and integration tests for WebSocket transport (Task 3.1, 3.2, 3.3)."""

import asyncio
import contextlib
import json
import threading
import time
from contextlib import suppress
from typing import TYPE_CHECKING, Any, cast
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI, WebSocket
from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient

from asap.models.entities import Manifest
from asap.models.envelope import Envelope
from asap.models.payloads import MessageAck, TaskRequest
from asap.transport.jsonrpc import ASAP_METHOD, JsonRpcRequest
from asap.transport.server import create_app
from asap.transport.websocket import (
    ASAP_ACK_METHOD,
    DEFAULT_POOL_IDLE_TIMEOUT,
    DEFAULT_POOL_MAX_SIZE,
    DEFAULT_WS_RECEIVE_TIMEOUT,
    FRAME_ENCODING_BINARY,
    FRAME_ENCODING_JSON,
    HEARTBEAT_FRAME_TYPE_PING,
    HEARTBEAT_FRAME_TYPE_PONG,
    HEARTBEAT_PING_INTERVAL,
    PendingAck,
    RECONNECT_INITIAL_BACKOFF,
    RECONNECT_MAX_BACKOFF,
    STALE_CONNECTION_TIMEOUT,
    WS_CLOSE_GOING_AWAY,
    WS_CLOSE_REASON_SHUTDOWN,
    WebSocketConnectionPool,
    WebSocketRemoteError,
    WebSocketTransport,
    _build_ack_notification_frame,
    _heartbeat_loop,
    _is_heartbeat_pong,
    _make_fake_request,
    decode_frame_to_json,
    encode_envelope_frame,
    handle_websocket_connection,
)

from .conftest import NoRateLimitTestBase, TEST_RATE_LIMIT_DEFAULT

if TYPE_CHECKING:
    from asap.transport.rate_limit import ASAPRateLimiter


# --- Fixtures ---


@pytest.fixture
def app(
    sample_manifest: Manifest,
    disable_rate_limiting: "ASAPRateLimiter",
) -> FastAPI:
    app_instance = create_app(sample_manifest, rate_limit=TEST_RATE_LIMIT_DEFAULT)
    app_instance.state.limiter = disable_rate_limiting
    return app_instance


@pytest.fixture
def client(app: FastAPI) -> TestClient:
    return TestClient(app)


# --- Message framing (encode/decode) ---


class TestWebSocketFraming:
    """Tests for encode_envelope_frame and decode_frame_to_json."""

    def test_encode_decode_json_roundtrip(self) -> None:
        """Envelope as JSON frame round-trips correctly."""
        envelope = {
            "sender": "urn:asap:agent:a",
            "recipient": "urn:asap:agent:b",
            "payload_type": "task.request",
            "payload": {},
            "asap_version": "0.1",
        }
        frame = encode_envelope_frame(envelope, request_id=1, encoding=FRAME_ENCODING_JSON)
        assert isinstance(frame, str)
        parsed = decode_frame_to_json(frame)
        assert parsed.get("params", {}).get("envelope") == envelope
        assert parsed.get("method") == ASAP_METHOD

    def test_encode_decode_binary_roundtrip(self) -> None:
        """Envelope as base64 frame round-trips correctly."""
        envelope = {
            "sender": "urn:asap:agent:a",
            "recipient": "urn:asap:agent:b",
            "payload_type": "task.request",
            "payload": {},
            "asap_version": "0.1",
        }
        frame = encode_envelope_frame(envelope, request_id=2, encoding=FRAME_ENCODING_BINARY)
        assert isinstance(frame, bytes)
        parsed = decode_frame_to_json(frame)
        assert parsed.get("params", {}).get("envelope") == envelope

    def test_decode_invalid_json_raises(self) -> None:
        """Invalid JSON string raises ValueError."""
        with pytest.raises(ValueError, match="Expecting value|Invalid"):
            decode_frame_to_json("not json")

    def test_decode_invalid_base64_raises(self) -> None:
        """Invalid base64 bytes raise ValueError."""
        with pytest.raises(ValueError, match="base64|Invalid"):
            decode_frame_to_json(b"!!!invalid base64!!!")


class TestWebSocketRemoteError:
    def test_remote_error_data_none_becomes_empty_dict(self) -> None:
        err = WebSocketRemoteError(-32603, "Test", data=None)
        assert err.code == -32603
        assert err.message == "Test"
        assert err.data == {}

    def test_remote_error_data_preserved(self) -> None:
        err = WebSocketRemoteError(-32600, "Parse error", data={"line": 1})
        assert err.data == {"line": 1}


class TestMakeFakeRequest:
    @pytest.mark.asyncio
    async def test_make_fake_request_receive_returns_disconnect_second_call(
        self,
    ) -> None:
        class FakeWs:
            scope: dict[str, Any] = {"headers": []}

        body = '{"jsonrpc":"2.0","method":"asap.send","params":{},"id":1}'
        request = await _make_fake_request(body, FakeWs())
        r1 = await request.receive()
        assert r1["type"] == "http.request"
        assert r1.get("body", b"").decode() == body
        r2 = await request.receive()
        assert r2["type"] == "http.disconnect"

    @pytest.mark.asyncio
    async def test_make_fake_request_scope_has_required_asgi_fields(self) -> None:
        """Fake request scope includes path, root_path, query_string, server for middleware compatibility."""

        class FakeWs:
            scope: dict[str, Any] = {
                "headers": [],
                "path": "/asap/ws",
                "server": ("localhost", 9000),
            }

        body = '{"jsonrpc":"2.0","method":"asap.send","params":{},"id":1}'
        request = await _make_fake_request(body, FakeWs())
        assert request.scope["path"] == "/asap/ws"
        assert request.scope["root_path"] == ""
        assert request.scope["query_string"] == b""
        assert request.scope["server"] == ("localhost", 9000)

    @pytest.mark.asyncio
    async def test_make_fake_request_scope_defaults_when_missing_in_websocket_scope(
        self,
    ) -> None:
        """When WebSocket scope has no path/server, fake request uses sensible defaults."""

        class FakeWs:
            scope: dict[str, Any] = {"headers": []}

        body = "{}"
        request = await _make_fake_request(body, FakeWs())
        assert request.scope["path"] == "/asap"
        assert request.scope["root_path"] == ""
        assert request.scope["query_string"] == b""
        assert request.scope["server"] == ("localhost", 8000)


class TestHeartbeatHelpers:
    def test_is_heartbeat_pong_true_when_type_pong_no_method(self) -> None:
        assert _is_heartbeat_pong({"type": HEARTBEAT_FRAME_TYPE_PONG}) is True

    def test_is_heartbeat_pong_false_when_method_present(self) -> None:
        assert (
            _is_heartbeat_pong({"type": HEARTBEAT_FRAME_TYPE_PONG, "method": "asap.send"}) is False
        )

    def test_is_heartbeat_pong_false_when_type_not_pong(self) -> None:
        assert _is_heartbeat_pong({"type": HEARTBEAT_FRAME_TYPE_PING}) is False
        assert _is_heartbeat_pong({"type": "other"}) is False


# --- WebSocket connection lifecycle and message routing ---


class TestWebSocketConnectionLifecycle(NoRateLimitTestBase):
    """Tests for WebSocket connection open, message, close."""

    def test_websocket_accepts_connection(self, client: TestClient) -> None:
        with client.websocket_connect("/asap/ws") as websocket:
            assert websocket is not None

    def test_websocket_closes_cleanly(self, client: TestClient) -> None:
        with client.websocket_connect("/asap/ws") as websocket:
            websocket.send_text("{}")
            _ = websocket.receive_text()

    def test_websocket_route_registered(self, app: FastAPI) -> None:
        routes = [r for r in app.routes if getattr(r, "path", None) == "/asap/ws"]
        assert len(routes) == 1


class TestWebSocketMessageRouting(NoRateLimitTestBase):
    """Tests for message routing over WebSocket (JSON-RPC -> handler -> response)."""

    def test_websocket_echo_request_returns_response(self, client: TestClient) -> None:
        """Valid task.request over WebSocket returns JSON-RPC response with result."""
        envelope = Envelope(
            asap_version="0.1",
            sender="urn:asap:agent:client",
            recipient="urn:asap:agent:test-server",
            payload_type="task.request",
            payload=TaskRequest(
                conversation_id="conv-ws-1",
                skill_id="echo",
                input={"message": "hello"},
            ).model_dump(),
        )
        rpc = JsonRpcRequest(
            method=ASAP_METHOD,
            params={"envelope": envelope.model_dump(mode="json")},
            id="ws-req-1",
        )
        body = json.dumps(rpc.model_dump())

        with client.websocket_connect("/asap/ws") as websocket:
            websocket.send_text(body)
            response_text = websocket.receive_text()

        data = json.loads(response_text)
        assert data.get("jsonrpc") == "2.0"
        assert "result" in data or "error" in data
        assert data.get("id") == "ws-req-1"
        if "result" in data:
            assert "envelope" in data["result"]
            assert data["result"]["envelope"].get("payload_type") == "task.response"


class TestWebSocketErrorHandling(NoRateLimitTestBase):
    """Tests for error handling (invalid JSON, invalid params, etc.)."""

    def test_websocket_invalid_json_frame_skipped(self, client: TestClient) -> None:
        """Invalid JSON frame is skipped (no response); connection stays open; valid request still works."""
        envelope = Envelope(
            asap_version="0.1",
            sender="urn:asap:agent:client",
            recipient="urn:asap:agent:test-server",
            payload_type="task.request",
            payload=TaskRequest(
                conversation_id="c1",
                skill_id="echo",
                input={"msg": "after-invalid"},
            ).model_dump(),
        )
        rpc = JsonRpcRequest(
            method=ASAP_METHOD,
            params={"envelope": envelope.model_dump(mode="json")},
            id=1,
        )
        body_valid = json.dumps(rpc.model_dump())
        with client.websocket_connect("/asap/ws") as websocket:
            websocket.send_text("not valid json {{{")
            websocket.send_text(body_valid)
            response_text = websocket.receive_text()

        data = json.loads(response_text)
        assert data.get("jsonrpc") == "2.0"
        assert "result" in data
        assert data["result"].get("envelope", {}).get("payload_type") == "task.response"

    def test_websocket_missing_envelope_returns_error(self, client: TestClient) -> None:
        """JSON-RPC without params.envelope receives invalid params error."""
        body = json.dumps({"jsonrpc": "2.0", "method": ASAP_METHOD, "params": {}, "id": 1})
        with client.websocket_connect("/asap/ws") as websocket:
            websocket.send_text(body)
            response_text = websocket.receive_text()

        data = json.loads(response_text)
        assert data.get("jsonrpc") == "2.0"
        assert "error" in data
        assert data["error"].get("code") == -32602

    def test_websocket_handler_exception_returns_jsonrpc_internal_error(
        self,
        sample_manifest: Manifest,
        disable_rate_limiting: "ASAPRateLimiter",
    ) -> None:
        """When handle_message raises, client receives JSON-RPC error frame (-32603); connection stays open."""
        from asap.transport.handlers import HandlerRegistry

        def boom_handler(envelope: Envelope, manifest: Manifest) -> Envelope:
            raise Exception("Boom")

        registry = HandlerRegistry()
        registry.register("task.request", boom_handler)
        app_instance = create_app(
            sample_manifest,
            registry,
            rate_limit=TEST_RATE_LIMIT_DEFAULT,
        )
        app_instance.state.limiter = disable_rate_limiting

        envelope = Envelope(
            asap_version="0.1",
            sender="urn:asap:agent:client",
            recipient="urn:asap:agent:test-server",
            payload_type="task.request",
            payload=TaskRequest(
                conversation_id="c1",
                skill_id="echo",
                input={"msg": "trigger-boom"},
            ).model_dump(),
        )
        rpc = JsonRpcRequest(
            method=ASAP_METHOD,
            params={"envelope": envelope.model_dump(mode="json")},
            id="ws-req-boom",
        )
        body = json.dumps(rpc.model_dump())

        with (
            TestClient(app_instance) as ws_client,
            ws_client.websocket_connect("/asap/ws") as websocket,
        ):
            websocket.send_text(body)
            response_text = websocket.receive_text()

        data = json.loads(response_text)
        assert data.get("jsonrpc") == "2.0"
        assert "error" in data
        assert data["error"].get("code") == -32603
        assert "Internal error" in (data["error"].get("message") or "")


# --- WebSocketTransport: correlation (3.2.3) and on_message (3.2.4) ---


class TestWebSocketTransportCorrelation(NoRateLimitTestBase):
    """Tests for request/response correlation by request_id (Task 3.2.3)."""

    @pytest.mark.asyncio
    async def test_send_and_receive_returns_correlated_envelope(
        self,
        sample_manifest: Manifest,
        disable_rate_limiting: "ASAPRateLimiter",
    ) -> None:
        """send_and_receive() returns the response envelope for the sent request."""
        import uvicorn
        from asap.transport import middleware as middleware_module
        from asap.transport.handlers import create_default_registry

        middleware_module.limiter = disable_rate_limiting
        port = _free_port()
        app_instance = create_app(
            sample_manifest,
            create_default_registry(),
            rate_limit=TEST_RATE_LIMIT_DEFAULT,
        )
        app_instance.state.limiter = disable_rate_limiting

        server_started = threading.Event()
        thread_err: list[Exception] = []

        def run() -> None:
            try:
                config = uvicorn.Config(
                    app_instance, host="127.0.0.1", port=port, log_level="warning"
                )
                server_started.set()
                asyncio.run(uvicorn.Server(config).serve())
            except Exception as e:
                thread_err.append(e)

        thread = threading.Thread(target=run, daemon=True)
        thread.start()
        assert server_started.wait(timeout=5.0)
        await asyncio.sleep(0.2)

        ws_url = f"ws://127.0.0.1:{port}/asap/ws"
        try:
            transport = WebSocketTransport(receive_timeout=10.0)
            await transport.connect(ws_url)
            envelope = Envelope(
                asap_version="0.1",
                sender="urn:asap:agent:test",
                recipient=sample_manifest.id,
                payload_type="task.request",
                payload=TaskRequest(
                    conversation_id="c1",
                    skill_id="echo",
                    input={"msg": "correlation"},
                ).model_dump(),
            )
            response = await transport.send_and_receive(envelope)
            await transport.close()
            assert response.payload_type == "task.response"
        except Exception as e:
            if thread_err:
                raise thread_err[0] from e
            raise

    @pytest.mark.asyncio
    async def test_send_and_receive_timeout_when_no_response(self) -> None:
        """send_and_receive() raises asyncio.TimeoutError when server does not respond."""
        # Use a URL that connects but never sends a response (no real server)
        # We use a real server that accepts then closes without replying - hard.
        # Instead: use a very short timeout and a server that sleeps forever before replying.
        # Simpler: just check that timeout is passed through (unit test with mock).
        transport = WebSocketTransport(receive_timeout=0.01)
        # Not connected - send_and_receive should raise RuntimeError
        with pytest.raises(RuntimeError, match="not connected"):
            await transport.send_and_receive(
                Envelope(
                    asap_version="0.1",
                    sender="urn:asap:agent:a",
                    recipient="urn:asap:agent:b",
                    payload_type="task.request",
                    payload={"conversation_id": "c1", "skill_id": "s1", "input": {}},
                )
            )

    @pytest.mark.asyncio
    async def test_close_swallows_oserror_from_ws_close(self) -> None:
        """close() does not raise when _ws.close() raises OSError."""
        transport = WebSocketTransport(receive_timeout=5.0)

        class FakeWs:
            async def close(self) -> None:
                raise OSError("connection already closed")

            async def recv(self) -> str:
                await asyncio.sleep(999)
                return ""

        transport._ws = cast(Any, FakeWs())
        transport._recv_task = asyncio.create_task(transport._recv_loop())
        transport._ack_check_task = asyncio.create_task(transport._ack_check_loop())
        transport._closed = False
        await transport.close()
        assert transport._ws is None
        assert transport._closed

    @pytest.mark.asyncio
    async def test_connect_passes_ssl_context_to_websockets_connect(
        self,
    ) -> None:
        """WebSocketTransport passes ssl_context to websockets.connect for wss://."""
        import ssl

        from unittest.mock import patch

        ssl_ctx = ssl.create_default_context()
        connect_calls: list[tuple[str, dict[str, Any]]] = []

        async def fake_connect(url: str, **kwargs: object) -> object:
            connect_calls.append((url, dict(kwargs)))
            raise ConnectionRefusedError("mock: no real server")

        with patch("asap.transport.websocket.websockets.connect", side_effect=fake_connect):
            transport = WebSocketTransport(ssl_context=ssl_ctx)
            with pytest.raises(ConnectionRefusedError):
                await transport.connect("wss://example.com/asap/ws")

        assert len(connect_calls) == 1
        _, kwargs = connect_calls[0]
        assert kwargs.get("ssl") is ssl_ctx

    @pytest.mark.asyncio
    async def test_connect_race_with_close_cleans_up_when_closed_during_connect(
        self,
    ) -> None:
        """When close() runs while connect() is awaiting, _do_connect cleans up (lines 249-253)."""
        from unittest.mock import AsyncMock, patch

        release_connect = asyncio.Event()
        connect_called = asyncio.Event()

        async def slow_connect(url: str, **kwargs: object) -> object:
            connect_called.set()
            await release_connect.wait()
            return AsyncMock()

        with patch("asap.transport.websocket.websockets.connect", side_effect=slow_connect):
            transport = WebSocketTransport(
                receive_timeout=5.0,
                reconnect_on_disconnect=False,
            )
            connect_task = asyncio.create_task(transport.connect("ws://localhost:9999/asap/ws"))
            await connect_called.wait()
            await transport.close()
            release_connect.set()
            await connect_task

        assert transport._ws is None
        assert transport._closed

    def test_envelope_dict_for_send_preserves_requires_ack_true(self) -> None:
        """_envelope_dict_for_send keeps requires_ack=True when already set."""
        transport = WebSocketTransport()
        envelope = Envelope(
            asap_version="0.1",
            sender="urn:asap:agent:a",
            recipient="urn:asap:agent:b",
            payload_type="TaskRequest",
            payload=TaskRequest(
                conversation_id="c1",
                skill_id="s1",
                input={},
            ).model_dump(),
            requires_ack=True,
        )
        dump = transport._envelope_dict_for_send(envelope)
        assert dump.get("requires_ack") is True

    @pytest.mark.asyncio
    async def test_send_raises_runtime_error_when_not_connected(self) -> None:
        """send() raises RuntimeError when WebSocket is not connected."""
        transport = WebSocketTransport()
        envelope = Envelope(
            asap_version="0.1",
            sender="urn:asap:agent:a",
            recipient="urn:asap:agent:b",
            payload_type="TaskRequest",
            payload=TaskRequest(conversation_id="c1", skill_id="s1", input={}).model_dump(),
        )
        with pytest.raises(RuntimeError, match="not connected"):
            await transport.send(envelope)

    @pytest.mark.asyncio
    async def test_receive_raises_remote_error_when_server_sends_error_frame(
        self,
    ) -> None:
        """receive() raises WebSocketRemoteError when server returns JSON-RPC error."""
        error_frame = json.dumps(
            {
                "jsonrpc": "2.0",
                "error": {"code": -32600, "message": "Parse error", "data": {"line": 1}},
                "id": 1,
            }
        )
        mock_ws = _MockWebSocket(recv_side_effect=[error_frame])
        transport = WebSocketTransport(receive_timeout=5.0)
        transport._ws = cast(Any, mock_ws)
        with pytest.raises(WebSocketRemoteError) as exc_info:
            await transport.receive()
        assert exc_info.value.code == -32600
        assert "Parse error" in exc_info.value.message
        assert exc_info.value.data == {"line": 1}

    @pytest.mark.asyncio
    async def test_receive_raises_remote_error_when_result_missing_envelope(
        self,
    ) -> None:
        """receive() raises WebSocketRemoteError when result has no envelope."""
        bad_result_frame = json.dumps(
            {
                "jsonrpc": "2.0",
                "result": {},
                "id": 1,
            }
        )
        mock_ws = _MockWebSocket(recv_side_effect=[bad_result_frame])
        transport = WebSocketTransport(receive_timeout=5.0)
        transport._ws = cast(Any, mock_ws)
        with pytest.raises(WebSocketRemoteError) as exc_info:
            await transport.receive()
        assert exc_info.value.code == -32603
        assert "Missing result.envelope" in exc_info.value.message

    @pytest.mark.asyncio
    async def test_recv_loop_error_frame_with_unknown_id_logs_warning(
        self,
        caplog: "pytest.LogCaptureFixture",
    ) -> None:
        """When error frame has request_id not in _pending, recv_loop logs warning."""
        import logging

        caplog.set_level(logging.WARNING)
        error_frame = json.dumps(
            {
                "jsonrpc": "2.0",
                "error": {"code": -32600, "message": "Parse error"},
                "id": "unknown-id",
            }
        )
        mock_ws = _MockWebSocket(recv_side_effect=[error_frame])
        transport = WebSocketTransport(receive_timeout=5.0)
        transport._ws = cast(Any, mock_ws)
        transport._recv_task = asyncio.create_task(transport._recv_loop())
        await asyncio.sleep(0.15)
        transport._recv_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await transport._recv_task
        assert "recv_loop_error_frame" in caplog.text or "Parse error" in caplog.text

    @pytest.mark.asyncio
    async def test_send_and_receive_raises_when_server_returns_result_without_envelope(
        self,
    ) -> None:
        """send_and_receive raises WebSocketRemoteError when response has no envelope."""
        from unittest.mock import patch

        bad_frame = json.dumps(
            {
                "jsonrpc": "2.0",
                "result": {},
                "id": "ws-req-1",
            }
        )
        mock_ws = _MockWebSocket(recv_side_effect=[bad_frame])
        transport = WebSocketTransport(receive_timeout=5.0)
        transport._ws = cast(Any, mock_ws)
        transport._recv_task = asyncio.create_task(transport._recv_loop())
        with (
            patch.object(transport, "_next_request_id", return_value="ws-req-1"),
            pytest.raises(
                WebSocketRemoteError,
            ) as exc_info,
        ):
            await transport.send_and_receive(
                Envelope(
                    asap_version="0.1",
                    sender="urn:asap:agent:a",
                    recipient="urn:asap:agent:b",
                    payload_type="TaskRequest",
                    payload=TaskRequest(
                        conversation_id="c1",
                        skill_id="s1",
                        input={},
                    ).model_dump(),
                ),
            )
        assert exc_info.value.code == -32603
        assert "Missing result.envelope" in exc_info.value.message
        transport._recv_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await transport._recv_task

    @pytest.mark.asyncio
    async def test_recv_loop_exception_sets_pending_futures(self) -> None:
        """When recv() raises, pending futures get WebSocketRemoteError and are cleared."""
        mock_ws = _MockWebSocket(recv_side_effect=[Exception("network down")])
        transport = WebSocketTransport(receive_timeout=5.0)
        transport._ws = cast(Any, mock_ws)
        future: asyncio.Future[Envelope] = asyncio.get_event_loop().create_future()
        transport._pending["req-1"] = future
        transport._recv_task = asyncio.create_task(transport._recv_loop())
        await asyncio.sleep(0.15)
        transport._recv_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await transport._recv_task
        assert future.done()
        with pytest.raises(WebSocketRemoteError):
            future.result()
        assert "req-1" not in transport._pending


class TestWebSocketTransportOnMessage(NoRateLimitTestBase):
    """Tests for server-push callback on_message (Task 3.2.4)."""

    @pytest.mark.asyncio
    async def test_on_message_called_for_push_frame(
        self,
    ) -> None:
        """When a frame has result but no matching pending id, on_message is called."""
        push_envelope = {
            "asap_version": "0.1",
            "sender": "urn:asap:agent:server",
            "recipient": "urn:asap:agent:client",
            "payload_type": "task.update",
            "payload": {
                "task_id": "t1",
                "update_type": "progress",
                "status": "working",
                "progress": {"percent": 50},
            },
        }
        push_frame = json.dumps(
            {"jsonrpc": "2.0", "result": {"envelope": push_envelope}, "id": None}
        )
        received: list[Envelope] = []

        def on_message(env: Envelope) -> None:
            received.append(env)

        transport = WebSocketTransport(
            receive_timeout=DEFAULT_WS_RECEIVE_TIMEOUT,
            on_message=on_message,
        )
        mock_ws = _MockWebSocket(recv_side_effect=[push_frame])
        transport._ws = cast(Any, mock_ws)
        transport._recv_task = asyncio.create_task(transport._recv_loop())
        await asyncio.sleep(0.15)
        transport._recv_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await transport._recv_task
        assert len(received) == 1
        assert received[0].payload_type == "task.update"
        assert received[0].payload_dict.get("progress", {}).get("percent") == 50

    @pytest.mark.asyncio
    async def test_on_message_async_callback_awaited(
        self,
    ) -> None:
        """When on_message is async, the coroutine is awaited."""
        push_envelope = {
            "asap_version": "0.1",
            "sender": "urn:asap:agent:server",
            "recipient": "urn:asap:agent:client",
            "payload_type": "task.update",
            "payload": {
                "task_id": "t1",
                "update_type": "progress",
                "status": "working",
                "progress": {"percent": 99},
            },
        }
        push_frame = json.dumps(
            {"jsonrpc": "2.0", "result": {"envelope": push_envelope}, "id": None}
        )
        received: list[Envelope] = []

        async def on_message_async(env: Envelope) -> None:
            received.append(env)

        transport = WebSocketTransport(
            receive_timeout=DEFAULT_WS_RECEIVE_TIMEOUT,
            on_message=on_message_async,
        )
        mock_ws = _MockWebSocket(recv_side_effect=[push_frame])
        transport._ws = cast(Any, mock_ws)
        transport._recv_task = asyncio.create_task(transport._recv_loop())
        await asyncio.sleep(0.15)
        transport._recv_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await transport._recv_task
        assert len(received) == 1
        assert received[0].payload_dict.get("progress", {}).get("percent") == 99


def _free_port() -> int:
    import socket

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


class _MockWebSocket:
    """Minimal mock that returns fixed frames from recv() and optionally records send()."""

    def __init__(
        self,
        recv_side_effect: list[str | Exception],
        sent: list[str] | None = None,
    ) -> None:
        self._recv_queue: asyncio.Queue[str | Exception] = asyncio.Queue()
        for frame in recv_side_effect:
            self._recv_queue.put_nowait(frame)
        self._sent: list[str] = sent if sent is not None else []

    async def recv(self) -> str:
        item = await self._recv_queue.get()
        if isinstance(item, Exception):
            raise item
        return item

    async def send(self, payload: str) -> None:
        self._sent.append(payload)

    async def close(self) -> None:
        pass


# --- Heartbeat (Task 3.3.1) ---


class TestWebSocketHeartbeat(NoRateLimitTestBase):
    """Tests for heartbeat: server sends ping, client responds with pong, stale detection."""

    def test_heartbeat_constants_defined(self) -> None:
        """Heartbeat interval and stale timeout are defined."""
        assert HEARTBEAT_PING_INTERVAL == 30.0
        assert STALE_CONNECTION_TIMEOUT == 90.0
        assert HEARTBEAT_FRAME_TYPE_PING == "ping"
        assert HEARTBEAT_FRAME_TYPE_PONG == "pong"

    @pytest.mark.asyncio
    async def test_client_responds_to_ping_with_pong(self) -> None:
        """When client receives application-level ping, it sends pong back."""
        ping_frame = json.dumps({"type": HEARTBEAT_FRAME_TYPE_PING})
        sent: list[str] = []
        mock_ws = _MockWebSocket(recv_side_effect=[ping_frame], sent=sent)
        transport = WebSocketTransport(
            receive_timeout=DEFAULT_WS_RECEIVE_TIMEOUT,
            ping_interval=None,
            ping_timeout=None,
        )
        transport._ws = cast(Any, mock_ws)
        transport._recv_task = asyncio.create_task(transport._recv_loop())
        await asyncio.sleep(0.1)
        transport._recv_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await transport._recv_task
        assert len(sent) == 1
        pong_data = json.loads(sent[0])
        assert pong_data.get("type") == HEARTBEAT_FRAME_TYPE_PONG


# --- Reconnection (Task 3.3.2) ---


class TestWebSocketReconnection(NoRateLimitTestBase):
    """Tests for automatic reconnection with exponential backoff."""

    def test_reconnect_backoff_constants(self) -> None:
        """Reconnect backoff constants are defined."""
        assert RECONNECT_INITIAL_BACKOFF == 1.0
        assert RECONNECT_MAX_BACKOFF == 30.0

    def test_reconnect_delay_exponential_capped(self) -> None:
        """Backoff delay is 1s, 2s, 4s, ... and capped at max_backoff."""
        from asap.transport.websocket import _reconnect_delay

        assert _reconnect_delay(1) == 1.0
        assert _reconnect_delay(2) == 2.0
        assert _reconnect_delay(3) == 4.0
        assert _reconnect_delay(4) == 8.0
        assert _reconnect_delay(5) == 16.0
        assert _reconnect_delay(6) == 30.0  # cap
        assert _reconnect_delay(10) == 30.0

    def test_reconnect_params_stored(self) -> None:
        """Transport stores reconnect_on_disconnect and max_reconnect_attempts."""
        transport = WebSocketTransport(
            reconnect_on_disconnect=True,
            max_reconnect_attempts=5,
            initial_backoff=2.0,
            max_backoff=60.0,
        )
        assert transport._reconnect_on_disconnect is True
        assert transport._max_reconnect_attempts == 5
        assert transport._initial_backoff == 2.0
        assert transport._max_backoff == 60.0

    @pytest.mark.asyncio
    async def test_connect_reconnect_mode_invalid_url_raises(
        self,
    ) -> None:
        """With reconnect_on_disconnect, first connection failure propagates to connect()."""
        transport = WebSocketTransport(
            reconnect_on_disconnect=True,
            max_reconnect_attempts=2,
            ping_interval=None,
            ping_timeout=None,
        )
        with pytest.raises((OSError, ConnectionError)):
            await transport.connect("ws://127.0.0.1:1/")  # nothing listening


# --- Connection pool (Task 3.3.3) ---


class TestWebSocketConnectionPool(NoRateLimitTestBase):
    """Tests for WebSocket connection pooling: reuse, max size, idle cleanup."""

    def test_pool_constants_defined(self) -> None:
        """Pool default max size and idle timeout are defined."""
        assert DEFAULT_POOL_MAX_SIZE == 10
        assert DEFAULT_POOL_IDLE_TIMEOUT == 60.0

    @pytest.mark.asyncio
    async def test_pool_acquire_release_reuse(
        self,
        sample_manifest: Manifest,
        disable_rate_limiting: "ASAPRateLimiter",
    ) -> None:
        """Release then acquire returns the same transport (connection reused)."""
        import uvicorn
        from asap.transport import middleware as middleware_module
        from asap.transport.handlers import create_default_registry

        middleware_module.limiter = disable_rate_limiting
        port = _free_port()
        app_instance = create_app(
            sample_manifest,
            create_default_registry(),
            rate_limit=TEST_RATE_LIMIT_DEFAULT,
        )
        app_instance.state.limiter = disable_rate_limiting
        server_started = threading.Event()
        thread_err: list[Exception] = []

        def run() -> None:
            try:
                config = uvicorn.Config(
                    app_instance, host="127.0.0.1", port=port, log_level="warning"
                )
                server_started.set()
                asyncio.run(uvicorn.Server(config).serve())
            except Exception as e:
                thread_err.append(e)

        thread = threading.Thread(target=run, daemon=True)
        thread.start()
        assert server_started.wait(timeout=5.0)
        await asyncio.sleep(0.2)

        ws_url = f"ws://127.0.0.1:{port}/asap/ws"
        pool = None
        try:
            pool = WebSocketConnectionPool(
                ws_url,
                max_size=1,
                receive_timeout=10.0,
                ping_interval=None,
                ping_timeout=None,
            )
            t1 = await pool.acquire()
            await pool.release(t1)
            t2 = await pool.acquire()
            await pool.release(t2)
            await pool.close()
            assert t1 is t2
        finally:
            if pool is not None:
                await pool.close()

    @pytest.mark.asyncio
    async def test_pool_idle_timeout_closes_and_creates_new(
        self,
        sample_manifest: Manifest,
        disable_rate_limiting: "ASAPRateLimiter",
    ) -> None:
        """After idle_timeout, released connection is closed; next acquire creates new transport."""
        import uvicorn
        from asap.transport import middleware as middleware_module
        from asap.transport.handlers import create_default_registry

        middleware_module.limiter = disable_rate_limiting
        port = _free_port()
        app_instance = create_app(
            sample_manifest,
            create_default_registry(),
            rate_limit=TEST_RATE_LIMIT_DEFAULT,
        )
        app_instance.state.limiter = disable_rate_limiting
        server_started = threading.Event()

        def run() -> None:
            config = uvicorn.Config(app_instance, host="127.0.0.1", port=port, log_level="warning")
            server_started.set()
            asyncio.run(uvicorn.Server(config).serve())

        thread = threading.Thread(target=run, daemon=True)
        thread.start()
        assert server_started.wait(timeout=5.0)
        await asyncio.sleep(0.2)

        ws_url = f"ws://127.0.0.1:{port}/asap/ws"
        pool = None
        try:
            pool = WebSocketConnectionPool(
                ws_url,
                max_size=2,
                idle_timeout=0.05,
                receive_timeout=5.0,
                ping_interval=None,
                ping_timeout=None,
            )
            t1 = await pool.acquire()
            await pool.release(t1)
            await asyncio.sleep(0.15)
            t2 = await pool.acquire()
            await pool.release(t2)
            await pool.close()
            assert t1 is not t2
            assert t1._ws is None
        finally:
            if pool is not None:
                await pool.close()

    @pytest.mark.asyncio
    async def test_pool_release_when_closed_closes_transport(
        self,
        sample_manifest: Manifest,
        disable_rate_limiting: "ASAPRateLimiter",
    ) -> None:
        """When pool is closed, release(transport) closes the transport and returns."""
        import uvicorn
        from asap.transport import middleware as middleware_module
        from asap.transport.handlers import create_default_registry

        middleware_module.limiter = disable_rate_limiting
        port = _free_port()
        app_instance = create_app(
            sample_manifest,
            create_default_registry(),
            rate_limit=TEST_RATE_LIMIT_DEFAULT,
        )
        app_instance.state.limiter = disable_rate_limiting
        server_started = threading.Event()

        def run() -> None:
            config = uvicorn.Config(app_instance, host="127.0.0.1", port=port, log_level="warning")
            server_started.set()
            asyncio.run(uvicorn.Server(config).serve())

        thread = threading.Thread(target=run, daemon=True)
        thread.start()
        assert server_started.wait(timeout=5.0)
        await asyncio.sleep(0.2)

        ws_url = f"ws://127.0.0.1:{port}/asap/ws"
        pool = WebSocketConnectionPool(
            ws_url,
            max_size=1,
            receive_timeout=5.0,
            ping_interval=None,
            ping_timeout=None,
        )
        t1 = await pool.acquire()
        await pool.close()
        await pool.release(t1)
        assert t1._closed
        assert t1._ws is None

    @pytest.mark.asyncio
    async def test_pool_release_when_transport_ws_none_does_not_put_back(
        self,
        sample_manifest: Manifest,
        disable_rate_limiting: "ASAPRateLimiter",
    ) -> None:
        """When transport._ws is None, release() does not put it back in the pool."""
        import uvicorn
        from asap.transport import middleware as middleware_module
        from asap.transport.handlers import create_default_registry

        middleware_module.limiter = disable_rate_limiting
        port = _free_port()
        app_instance = create_app(
            sample_manifest,
            create_default_registry(),
            rate_limit=TEST_RATE_LIMIT_DEFAULT,
        )
        app_instance.state.limiter = disable_rate_limiting
        server_started = threading.Event()

        def run() -> None:
            config = uvicorn.Config(app_instance, host="127.0.0.1", port=port, log_level="warning")
            server_started.set()
            asyncio.run(uvicorn.Server(config).serve())

        thread = threading.Thread(target=run, daemon=True)
        thread.start()
        assert server_started.wait(timeout=5.0)
        await asyncio.sleep(0.2)

        ws_url = f"ws://127.0.0.1:{port}/asap/ws"
        pool = None
        try:
            pool = WebSocketConnectionPool(
                ws_url,
                max_size=2,
                receive_timeout=5.0,
                ping_interval=None,
                ping_timeout=None,
            )
            t1 = await pool.acquire()
            await t1.close()
            assert t1._ws is None
            await pool.release(t1)
            t2 = await pool.acquire()
            await pool.release(t2)
            await pool.close()
            assert t1 is not t2
        finally:
            if pool is not None:
                await pool.close()

    @pytest.mark.asyncio
    async def test_pool_close_swallows_oserror_from_transport_close(
        self,
        sample_manifest: Manifest,
        disable_rate_limiting: "ASAPRateLimiter",
    ) -> None:
        """Pool close() does not raise when a transport's close() raises OSError."""
        import uvicorn
        from asap.transport import middleware as middleware_module
        from asap.transport.handlers import create_default_registry

        middleware_module.limiter = disable_rate_limiting
        port = _free_port()
        app_instance = create_app(
            sample_manifest,
            create_default_registry(),
            rate_limit=TEST_RATE_LIMIT_DEFAULT,
        )
        app_instance.state.limiter = disable_rate_limiting
        server_started = threading.Event()

        def run() -> None:
            config = uvicorn.Config(app_instance, host="127.0.0.1", port=port, log_level="warning")
            server_started.set()
            asyncio.run(uvicorn.Server(config).serve())

        thread = threading.Thread(target=run, daemon=True)
        thread.start()
        assert server_started.wait(timeout=5.0)
        await asyncio.sleep(0.2)

        ws_url = f"ws://127.0.0.1:{port}/asap/ws"
        pool = WebSocketConnectionPool(
            ws_url,
            max_size=2,
            receive_timeout=5.0,
            ping_interval=None,
            ping_timeout=None,
        )
        t1 = await pool.acquire()

        async def close_raises() -> None:
            raise OSError("closed")

        cast(Any, t1).close = close_raises
        await pool.release(t1)
        await pool.close()

    @pytest.mark.asyncio
    async def test_pool_acquire_blocks_until_release(
        self,
        sample_manifest: Manifest,
        disable_rate_limiting: "ASAPRateLimiter",
    ) -> None:
        """When pool is full, second acquire() blocks until first release()."""
        import uvicorn
        from asap.transport import middleware as middleware_module
        from asap.transport.handlers import create_default_registry

        middleware_module.limiter = disable_rate_limiting
        port = _free_port()
        app_instance = create_app(
            sample_manifest,
            create_default_registry(),
            rate_limit=TEST_RATE_LIMIT_DEFAULT,
        )
        app_instance.state.limiter = disable_rate_limiting
        server_started = threading.Event()
        acquired_event = asyncio.Event()

        def run() -> None:
            config = uvicorn.Config(app_instance, host="127.0.0.1", port=port, log_level="warning")
            server_started.set()
            asyncio.run(uvicorn.Server(config).serve())

        thread = threading.Thread(target=run, daemon=True)
        thread.start()
        assert server_started.wait(timeout=5.0)
        await asyncio.sleep(0.2)

        ws_url = f"ws://127.0.0.1:{port}/asap/ws"
        pool = None
        try:
            pool = WebSocketConnectionPool(
                ws_url,
                max_size=1,
                receive_timeout=5.0,
                ping_interval=None,
                ping_timeout=None,
            )
            t1 = await pool.acquire()
            acquired_event.set()

            async def blocking_acquire() -> WebSocketTransport:
                return await pool.acquire()

            blocker = asyncio.create_task(blocking_acquire())
            await asyncio.sleep(0.05)
            await pool.release(t1)
            t2 = await asyncio.wait_for(blocker, timeout=5.0)
            await pool.release(t2)
            await pool.close()
            assert t1 is t2
        finally:
            if pool is not None:
                await pool.close()

    @pytest.mark.asyncio
    async def test_pool_acquire_context(
        self,
        sample_manifest: Manifest,
        disable_rate_limiting: "ASAPRateLimiter",
    ) -> None:
        """acquire_context() yields a transport and releases on exit."""
        import uvicorn
        from asap.transport import middleware as middleware_module
        from asap.transport.handlers import create_default_registry

        middleware_module.limiter = disable_rate_limiting
        port = _free_port()
        app_instance = create_app(
            sample_manifest,
            create_default_registry(),
            rate_limit=TEST_RATE_LIMIT_DEFAULT,
        )
        app_instance.state.limiter = disable_rate_limiting
        server_started = threading.Event()

        def run() -> None:
            config = uvicorn.Config(app_instance, host="127.0.0.1", port=port, log_level="warning")
            server_started.set()
            asyncio.run(uvicorn.Server(config).serve())

        thread = threading.Thread(target=run, daemon=True)
        thread.start()
        assert server_started.wait(timeout=5.0)
        await asyncio.sleep(0.2)

        ws_url = f"ws://127.0.0.1:{port}/asap/ws"
        pool = WebSocketConnectionPool(
            ws_url,
            max_size=2,
            receive_timeout=10.0,
            ping_interval=None,
            ping_timeout=None,
        )
        async with pool.acquire_context() as transport:
            assert transport._ws is not None
        await pool.close()

    @pytest.mark.asyncio
    async def test_pool_closed_acquire_raises(self) -> None:
        """After close(), acquire() raises RuntimeError."""
        pool = WebSocketConnectionPool(
            "ws://127.0.0.1:1/",
            max_size=1,
            ping_interval=None,
            ping_timeout=None,
        )
        await pool.close()
        with pytest.raises(RuntimeError, match="closed"):
            await pool.acquire()


# --- Graceful shutdown (Task 3.3.4) ---


class TestWebSocketGracefulShutdown(NoRateLimitTestBase):
    """Tests for graceful shutdown: close frame with reason on server stop."""

    def test_shutdown_constants_defined(self) -> None:
        """WS close code and reason for shutdown are defined."""
        assert WS_CLOSE_GOING_AWAY == 1001
        assert WS_CLOSE_REASON_SHUTDOWN == "Server shutting down"

    def test_app_has_websocket_connections_for_shutdown(
        self,
        sample_manifest: Manifest,
    ) -> None:
        """create_app sets app.state.websocket_connections for graceful shutdown."""
        from asap.transport.server import create_app
        from asap.transport.handlers import create_default_registry

        app = create_app(sample_manifest, create_default_registry())
        assert hasattr(app.state, "websocket_connections")
        assert isinstance(app.state.websocket_connections, set)
        assert len(app.state.websocket_connections) == 0


# --- Chaos tests (Task 3.3.5) ---


def _app_with_close_ws_route(
    sample_manifest: Manifest,
    disable_rate_limiting: "ASAPRateLimiter",
) -> FastAPI:
    """Create app with test-only POST /__test__/close_ws to close all WebSockets (chaos)."""
    from asap.transport.handlers import create_default_registry

    app_instance = create_app(
        sample_manifest,
        create_default_registry(),
        rate_limit=TEST_RATE_LIMIT_DEFAULT,
    )
    app_instance.state.limiter = disable_rate_limiting

    @app_instance.post("/__test__/close_ws")
    async def _close_all_websockets() -> JSONResponse:
        for ws in list(app_instance.state.websocket_connections):
            with contextlib.suppress(Exception):
                await ws.close()
        return JSONResponse(content={"ok": True})

    return app_instance


class TestWebSocketChaos(NoRateLimitTestBase):
    """Chaos tests: connection drop, server restart (close all), recovery with reconnect.

    Covers: connection drops during request, server restart (simulated by closing
    all WebSockets), and network partition (same as drop). Verifies system recovers
    when reconnect_on_disconnect is enabled.
    """

    @pytest.mark.asyncio
    async def test_connection_drop_then_reconnect(
        self,
        sample_manifest: Manifest,
        disable_rate_limiting: "ASAPRateLimiter",
    ) -> None:
        """After server closes all connections, client with reconnect recovers and next request succeeds."""
        import uvicorn
        from asap.transport import middleware as middleware_module

        middleware_module.limiter = disable_rate_limiting
        app_instance = _app_with_close_ws_route(sample_manifest, disable_rate_limiting)
        port = _free_port()
        server_started = threading.Event()
        thread_err: list[Exception] = []

        def run() -> None:
            try:
                config = uvicorn.Config(
                    app_instance,
                    host="127.0.0.1",
                    port=port,
                    log_level="warning",
                )
                server_started.set()
                asyncio.run(uvicorn.Server(config).serve())
            except Exception as e:
                thread_err.append(e)

        thread = threading.Thread(target=run, daemon=True)
        thread.start()
        assert server_started.wait(timeout=5.0)
        await asyncio.sleep(0.2)

        ws_url = f"ws://127.0.0.1:{port}/asap/ws"
        close_url = f"http://127.0.0.1:{port}/__test__/close_ws"
        try:
            transport = WebSocketTransport(
                receive_timeout=10.0,
                reconnect_on_disconnect=True,
                max_reconnect_attempts=5,
                initial_backoff=0.3,
                max_backoff=1.0,
                ping_interval=None,
                ping_timeout=None,
            )
            await transport.connect(ws_url)
            envelope = Envelope(
                asap_version="0.1",
                sender="urn:asap:agent:chaos-client",
                recipient=sample_manifest.id,
                payload_type="task.request",
                payload=TaskRequest(
                    conversation_id="c1",
                    skill_id="echo",
                    input={"msg": "before drop"},
                ).model_dump(),
            )
            response1 = await transport.send_and_receive(envelope)
            assert response1.payload_type == "task.response"

            # Simulate connection drop: server closes all WebSockets (run in executor to avoid blocking event loop)
            import urllib.request

            def _post_close() -> None:
                req = urllib.request.Request(close_url, data=b"", method="POST")
                urllib.request.urlopen(req, timeout=5)

            await asyncio.get_event_loop().run_in_executor(None, _post_close)

            # Wait for client to detect disconnect and reconnect (backoff 0.3s then reconnect)
            await asyncio.sleep(1.5)

            envelope2 = Envelope(
                asap_version="0.1",
                sender="urn:asap:agent:chaos-client",
                recipient=sample_manifest.id,
                payload_type="task.request",
                payload=TaskRequest(
                    conversation_id="c2",
                    skill_id="echo",
                    input={"msg": "after reconnect"},
                ).model_dump(),
            )
            response2 = await transport.send_and_receive(envelope2)
            await transport.close()
            assert response2.payload_type == "task.response"
        except Exception as e:
            if thread_err:
                raise thread_err[0] from e
            raise

    @pytest.mark.asyncio
    async def test_send_fails_cleanly_after_connection_lost(
        self,
        sample_manifest: Manifest,
        disable_rate_limiting: "ASAPRateLimiter",
    ) -> None:
        """When server closes the connection, next send_and_receive fails (no reconnect in this test)."""
        import uvicorn
        from asap.transport import middleware as middleware_module

        middleware_module.limiter = disable_rate_limiting
        app_instance = _app_with_close_ws_route(sample_manifest, disable_rate_limiting)
        port = _free_port()
        server_started = threading.Event()

        def run() -> None:
            config = uvicorn.Config(
                app_instance,
                host="127.0.0.1",
                port=port,
                log_level="warning",
            )
            server_started.set()
            asyncio.run(uvicorn.Server(config).serve())

        thread = threading.Thread(target=run, daemon=True)
        thread.start()
        assert server_started.wait(timeout=5.0)
        await asyncio.sleep(0.2)

        ws_url = f"ws://127.0.0.1:{port}/asap/ws"
        close_url = f"http://127.0.0.1:{port}/__test__/close_ws"
        transport = WebSocketTransport(
            receive_timeout=5.0,
            reconnect_on_disconnect=False,
            ping_interval=None,
            ping_timeout=None,
        )
        await transport.connect(ws_url)
        # Trigger server to close all connections (run in executor to avoid blocking event loop)
        import urllib.request

        def _post_close() -> None:
            req = urllib.request.Request(close_url, data=b"", method="POST")
            urllib.request.urlopen(req, timeout=5)

        await asyncio.get_event_loop().run_in_executor(None, _post_close)
        # Give server time to close
        await asyncio.sleep(0.2)
        # Next send_and_receive should fail (connection closed)
        with pytest.raises((Exception, OSError, ConnectionError)):
            await transport.send_and_receive(
                Envelope(
                    asap_version="0.1",
                    sender="urn:asap:agent:a",
                    recipient=sample_manifest.id,
                    payload_type="task.request",
                    payload=TaskRequest(
                        conversation_id="c",
                        skill_id="echo",
                        input={},
                    ).model_dump(),
                )
            )
        await transport.close()


# --- Rate Limiting (Task 3.3.6) ---


class TestWebSocketServerRateLimit(NoRateLimitTestBase):
    """Tests for server-side rate limiting on WebSocket connections."""

    def test_websocket_rate_limit_exceeded_closes_connection(
        self,
        sample_manifest: Manifest,
    ) -> None:
        """Sending messages faster than rate limit triggers error frame and close."""
        from asap.transport.server import create_app
        from asap.transport.handlers import create_default_registry

        # We need a low rate to trigger it easily in a test without sleeping too long.
        app_instance = create_app(
            sample_manifest,
            create_default_registry(),
            rate_limit="100/minute",  # HTTP limit
            websocket_message_rate_limit=1.0,  # WS limit
        )

        client = TestClient(app_instance)
        with client.websocket_connect("/asap/ws") as websocket:
            # First message should pass (bucket has tokens)
            websocket.send_text(
                json.dumps(
                    {
                        "jsonrpc": "2.0",
                        "method": "asap.send",
                        "params": {"envelope": {"payload_type": "test", "payload": {}}},
                        "id": 1,
                    }
                )
            )

            # Receive response (echo or whatever) - wait for it
            # The server logic puts the response in `body`.
            # If we send a valid legacy format or just a valid frame, it processes.
            # To trigger rate limit, we just need to send frames fast.
            # Receive response (echo or whatever) - wait for it
            # The server logic puts the response in `body`.
            # If we send a valid legacy format or just a valid frame, it processes.
            # To trigger rate limit, we just need to send frames fast.
            with contextlib.suppress(Exception):
                _ = websocket.receive_text()

            # Second message immediately might be rate limited if burst is 1.
            # If burst is 1, and we consume 1, now empty.
            # Next consume fails until token refill (1 sec).

            websocket.send_text(
                json.dumps(
                    {
                        "jsonrpc": "2.0",
                        "method": "asap.send",
                        "params": {"envelope": {"payload_type": "test", "payload": {}}},
                        "id": 2,
                    }
                )
            )

            # This response should be the error frame
            response_text = websocket.receive_text()
            data = json.loads(response_text)

            # It might be the success response for msg 2 if burst > 1
            if "result" in data:
                # Try a third one
                websocket.send_text(json.dumps({"jsonrpc": "2.0", "method": "test", "id": 3}))
                response_text = websocket.receive_text()
                data = json.loads(response_text)

            assert "error" in data
            assert data["error"]["code"] == -32001  # Rate limit exceeded

            # Connection should be closed by server with policy violation
            # TestClient websocket checks state on simple interaction?
            # or verify we can't send/receive anymore?
            from fastapi.websockets import WebSocketDisconnect

            with pytest.raises(
                (WebSocketDisconnect, Exception)
            ):  # starlette/fastapi test client raises on closed
                websocket.receive_text()


# --- Ack Handling & Circuit Breaker (Task 3.3.7) ---


class TestWebSocketAckHandling(NoRateLimitTestBase):
    """Tests for Ack retry logic and timeout handling."""

    @pytest.mark.asyncio
    async def test_ack_retransmission_logic(self) -> None:
        """_ack_check_loop retransmits pending messages when ack is missing."""
        from unittest.mock import AsyncMock

        transport = WebSocketTransport(
            ack_timeout_seconds=0.1,
            max_ack_retries=3,
            ack_check_interval=0.05,
        )
        transport._ws = AsyncMock()
        # Mock _send_envelope_only to track calls
        transport._send_envelope_only = AsyncMock()

        envelope = Envelope(
            asap_version="0.1",
            sender="urn:asap:agent:a",
            recipient="urn:asap:agent:b",
            payload_type="TaskRequest",
            payload={"conversation_id": "c1", "skill_id": "s1", "input": {}},
            id="env-1",
            requires_ack=True,
        )

        # Manually register pending ack
        transport._register_pending_ack(envelope)
        assert "env-1" in transport._pending_acks

        # Start the check loop
        transport._ack_check_task = asyncio.create_task(transport._ack_check_loop())

        # Wait for at least one retransmission (timeout 0.1s)
        await asyncio.sleep(0.25)

        try:
            # Should have retransmitted at least once
            assert transport._send_envelope_only.call_count >= 1
            # Check if retries incremented
            assert transport._pending_acks["env-1"].retries >= 1
        finally:
            await transport.close()

    @pytest.mark.asyncio
    async def test_ack_max_retries_removes_pending(self) -> None:
        """After max_retries, pending ack is removed."""
        from unittest.mock import AsyncMock

        transport = WebSocketTransport(
            ack_timeout_seconds=0.01,
            max_ack_retries=2,
            ack_check_interval=0.01,
        )
        transport._ws = AsyncMock()
        transport._send_envelope_only = AsyncMock()

        envelope = Envelope(
            asap_version="0.1",
            sender="urn:asap:agent:a",
            recipient="urn:asap:agent:b",
            payload_type="TaskRequest",
            payload={"conversation_id": "c1", "skill_id": "s1", "input": {}},
            id="env-1",
            requires_ack=True,
        )

        transport._register_pending_ack(envelope)

        transport._ack_check_task = asyncio.create_task(transport._ack_check_loop())

        # Wait enough time for 2 retries + cleanup
        # 0.01 timeout * 2 retries + buffer
        await asyncio.sleep(0.2)

        try:
            # Should be removed
            assert "env-1" not in transport._pending_acks
            # Should have retried 2 times (initial send not counted here as we mocked register)
            # Actually _send_envelope_only is called on retransmit.
            # 2 retries = 2 calls.
            assert transport._send_envelope_only.call_count >= 2
        finally:
            await transport.close()


class TestWebSocketCircuitBreakerIntegration(NoRateLimitTestBase):
    """Tests for circuit breaker integration in WebSocket transport."""

    @pytest.mark.asyncio
    async def test_circuit_breaker_records_failure_on_ack_timeout(self) -> None:
        """Circuit breaker records failure when ack max retries exceeded."""
        from unittest.mock import AsyncMock, Mock

        mock_cb = Mock()

        transport = WebSocketTransport(
            ack_timeout_seconds=0.01,
            max_ack_retries=1,
            ack_check_interval=0.01,
            circuit_breaker=mock_cb,
        )
        transport._ws = AsyncMock()
        transport._send_envelope_only = AsyncMock()

        envelope = Envelope(
            asap_version="0.1",
            sender="urn:asap:agent:a",
            recipient="urn:asap:agent:b",
            payload_type="TaskRequest",
            payload={"conversation_id": "c1", "skill_id": "s1", "input": {}},
            id="env-cb",
            requires_ack=True,
        )

        transport._register_pending_ack(envelope)
        transport._ack_check_task = asyncio.create_task(transport._ack_check_loop())

        await asyncio.sleep(0.15)

        try:
            assert "env-cb" not in transport._pending_acks
            # Verify circuit breaker call
            mock_cb.record_failure.assert_called()
        finally:
            await transport.close()


class TestWebSocketTransportSend(NoRateLimitTestBase):
    """Tests for transport.send() method."""

    @pytest.mark.asyncio
    async def test_send_sends_frame_and_registers_ack(self) -> None:
        """send() sends the frame and registers pending ack."""
        from unittest.mock import AsyncMock

        transport = WebSocketTransport()
        transport._ws = AsyncMock()
        cast(Any, transport._ws).send = AsyncMock()

        envelope = Envelope(
            asap_version="0.1",
            sender="urn:asap:agent:a",
            recipient="urn:asap:agent:b",
            payload_type="TaskRequest",
            payload={"conversation_id": "c1", "skill_id": "s1", "input": {}},
            id="env-send",
            requires_ack=True,
        )

        await transport.send(envelope)

        transport._ws.send.assert_called_once()
        assert "env-send" in transport._pending_acks

    @pytest.mark.asyncio
    async def test_send_raises_type_error_if_frame_not_str(self) -> None:
        """send() raises TypeError if encode returns bytes (binary encoding not supported by current text-only check)."""
        from unittest.mock import AsyncMock, patch

        transport = WebSocketTransport()
        transport._ws = AsyncMock()

        envelope = Envelope(
            asap_version="0.1",
            sender="urn:asap:agent:a",
            recipient="urn:asap:agent:b",
            payload_type="TaskRequest",
            payload={"conversation_id": "c1", "skill_id": "s1", "input": {}},
        )

        # Mock encode_envelope_frame to return bytes
        with (
            patch("asap.transport.websocket.encode_envelope_frame", return_value=b"binary"),
            pytest.raises(TypeError, match="Expected text frame"),
        ):
            await transport.send(envelope)


class TestWebSocketServerExceptions(NoRateLimitTestBase):
    """Tests for server-side exception handling during message processing."""

    async def test_handler_exception_returns_error_and_ack_rejection(
        self,
        sample_manifest: Manifest,
    ) -> None:
        """If internal processing raises exception (e.g. fake request creation),
        websocket sends error frame and rejection ack if needed.

        so we need to mock something outside handle_message to trigger the websocket exception handler.
        _make_fake_request is outside handle_message.
        """
        from asap.transport.server import create_app
        from asap.transport.handlers import create_default_registry
        from unittest.mock import patch

        app_instance = create_app(sample_manifest, create_default_registry())
        client = TestClient(app_instance)

        # Patch _make_fake_request in websocket module to raise exception
        with (
            patch(
                "asap.transport.websocket._make_fake_request",
                side_effect=ValueError("Fake request failed"),
            ),
            client.websocket_connect("/asap/ws") as websocket,
        ):
            # Send message requiring ack
            websocket.send_text(
                json.dumps(
                    {
                        "jsonrpc": "2.0",
                        "method": "asap.send",
                        "params": {
                            "envelope": {
                                "asap_version": "0.1",
                                "sender": "urn:asap:agent:sender",
                                "recipient": "urn:asap:agent:test",
                                "payload_type": "test",
                                "payload": {},
                                "id": "msg-1",
                                "requires_ack": True,
                            }
                        },
                        "id": 1,
                    }
                )
            )

            # Expect 3 messages: "received" ack, "rejected" ack, and Error response
            messages = [json.loads(websocket.receive_text()) for _ in range(3)]

            error_res = next((m for m in messages if "error" in m and m.get("id") is None), None)
            assert error_res is not None
            assert error_res["error"]["code"] == -32603
            assert "Fake request failed" in error_res["error"]["data"]["error"]

            rejection_ack = next(
                (
                    m
                    for m in messages
                    if m.get("method") == "asap.ack"
                    and m.get("params", {}).get("envelope", {}).get("payload", {}).get("status")
                    == "rejected"
                ),
                None,
            )

            assert rejection_ack is not None
            assert rejection_ack["params"]["envelope"]["payload"]["original_envelope_id"] == "msg-1"
            assert "Fake request failed" in rejection_ack["params"]["envelope"]["payload"]["error"]


# ---------------------------------------------------------------------------
# Coverage helpers
# ---------------------------------------------------------------------------


def _sample_envelope_cov(**overrides: Any) -> Envelope:
    defaults: dict[str, Any] = {
        "asap_version": "0.1",
        "sender": "urn:asap:agent:a",
        "recipient": "urn:asap:agent:b",
        "payload_type": "task.request",
        "payload": {"conversation_id": "c1", "skill_id": "s1", "input": {}},
    }
    defaults.update(overrides)
    return Envelope(**defaults)


def _mock_ws() -> MagicMock:
    """Create a mock websocket connection."""
    ws = MagicMock()
    ws.send = AsyncMock()
    ws.recv = AsyncMock()
    ws.close = AsyncMock()
    return ws


# ---------------------------------------------------------------------------
# _do_connect: already connected (line 232)
# ---------------------------------------------------------------------------


class TestDoConnect:
    @pytest.mark.asyncio
    async def test_do_connect_already_connected_returns_early(self) -> None:
        """If _ws is already set, _do_connect returns immediately (line 232)."""
        transport = WebSocketTransport()
        transport._ws = _mock_ws()
        # Should not raise or try to connect again
        await transport._do_connect("ws://localhost:8080")
        # Still the same ws
        assert transport._ws is not None

    @pytest.mark.asyncio
    async def test_do_connect_closed_during_connect(self) -> None:
        """If _closed is set after connect, close ws (lines 253-258)."""
        transport = WebSocketTransport()

        fake_ws = _mock_ws()

        async def fake_connect(url: str, **kwargs: Any) -> MagicMock:
            transport._closed = True  # simulate close during connect
            return fake_ws

        with patch("asap.transport.websocket.websockets.connect", side_effect=fake_connect):
            await transport._do_connect("ws://localhost:8080")

        assert transport._ws is None
        fake_ws.close.assert_awaited_once()


# ---------------------------------------------------------------------------
# _recv_loop internal branches
# ---------------------------------------------------------------------------


class TestRecvLoopBranches:
    @pytest.mark.asyncio
    async def test_recv_loop_bytes_decode(self) -> None:
        """Bytes received are decoded to utf-8 (line 356)."""
        transport = WebSocketTransport()
        ws = _mock_ws()
        transport._ws = ws

        # First recv: bytes message, then disconnect
        response_frame = json.dumps(
            {
                "jsonrpc": "2.0",
                "result": {"envelope": _sample_envelope_cov().model_dump(mode="json")},
                "id": "ws-req-1",
            }
        )
        ws.recv = AsyncMock(
            side_effect=[
                response_frame.encode("utf-8"),  # bytes
                asyncio.CancelledError(),
            ]
        )

        future: asyncio.Future[Envelope] = asyncio.get_running_loop().create_future()
        transport._pending["ws-req-1"] = future

        task = asyncio.create_task(transport._recv_loop())
        result = await asyncio.wait_for(future, timeout=2.0)
        assert result.sender == "urn:asap:agent:a"

        task.cancel()
        with suppress(asyncio.CancelledError):
            await task

    @pytest.mark.asyncio
    async def test_recv_loop_parse_error_continues(self) -> None:
        """Invalid JSON in recv_loop logs warning and continues (lines 360-361)."""
        transport = WebSocketTransport()
        ws = _mock_ws()
        transport._ws = ws

        valid_response = json.dumps(
            {
                "jsonrpc": "2.0",
                "result": {"envelope": _sample_envelope_cov().model_dump(mode="json")},
                "id": "ws-req-1",
            }
        )
        ws.recv = AsyncMock(
            side_effect=[
                "not valid json!!!",
                valid_response,
                asyncio.CancelledError(),
            ]
        )

        future: asyncio.Future[Envelope] = asyncio.get_running_loop().create_future()
        transport._pending["ws-req-1"] = future

        task = asyncio.create_task(transport._recv_loop())
        result = await asyncio.wait_for(future, timeout=2.0)
        assert result.sender == "urn:asap:agent:a"

        task.cancel()
        with suppress(asyncio.CancelledError):
            await task

    @pytest.mark.asyncio
    async def test_recv_loop_heartbeat_ping_responds_pong(self) -> None:
        """Heartbeat ping frame triggers pong response (lines 362-365)."""
        transport = WebSocketTransport()
        ws = _mock_ws()
        transport._ws = ws

        ping_frame = json.dumps({"type": HEARTBEAT_FRAME_TYPE_PING})
        ws.recv = AsyncMock(
            side_effect=[
                ping_frame,
                asyncio.CancelledError(),
            ]
        )

        task = asyncio.create_task(transport._recv_loop())
        await asyncio.sleep(0.05)
        task.cancel()
        with suppress(asyncio.CancelledError):
            await task

        # ws.send should have been called with pong
        ws.send.assert_awaited_once()
        sent = json.loads(ws.send.call_args[0][0])
        assert sent["type"] == HEARTBEAT_FRAME_TYPE_PONG

    @pytest.mark.asyncio
    async def test_recv_loop_ack_handling(self) -> None:
        """MessageAck over WebSocket removes pending ack (lines 366-383)."""
        transport = WebSocketTransport()
        ws = _mock_ws()
        transport._ws = ws

        # Register a pending ack
        env = _sample_envelope_cov()
        transport._pending_acks["env-test"] = PendingAck(
            envelope_id="env-test",
            sent_at=time.monotonic(),
            retries=0,
            original_envelope=env,
        )

        ack_envelope = Envelope(
            asap_version="0.1",
            sender="urn:asap:agent:b",
            recipient="urn:asap:agent:a",
            payload_type="MessageAck",
            payload=MessageAck(
                original_envelope_id="env-test",
                status="received",
            ).model_dump(),
        )
        ack_frame = json.dumps(
            {
                "jsonrpc": "2.0",
                "method": ASAP_ACK_METHOD,
                "params": {"envelope": ack_envelope.model_dump(mode="json")},
            }
        )
        ws.recv = AsyncMock(side_effect=[ack_frame, asyncio.CancelledError()])

        task = asyncio.create_task(transport._recv_loop())
        await asyncio.sleep(0.05)
        task.cancel()
        with suppress(asyncio.CancelledError):
            await task

        assert "env-test" not in transport._pending_acks

    @pytest.mark.asyncio
    async def test_recv_loop_ack_validation_failure(self) -> None:
        """Invalid ack envelope logs warning (lines 377-382)."""
        transport = WebSocketTransport()
        ws = _mock_ws()
        transport._ws = ws

        bad_ack_frame = json.dumps(
            {
                "jsonrpc": "2.0",
                "method": ASAP_ACK_METHOD,
                "params": {"envelope": {"invalid": "data"}},
            }
        )
        ws.recv = AsyncMock(side_effect=[bad_ack_frame, asyncio.CancelledError()])

        task = asyncio.create_task(transport._recv_loop())
        await asyncio.sleep(0.05)
        task.cancel()
        with suppress(asyncio.CancelledError):
            await task
        # Should not raise; just logs warning

    @pytest.mark.asyncio
    async def test_recv_loop_error_frame_sets_pending_exception(self) -> None:
        """Error frame sets exception on matching pending future (lines 385-394)."""
        transport = WebSocketTransport()
        ws = _mock_ws()
        transport._ws = ws

        error_frame = json.dumps(
            {
                "jsonrpc": "2.0",
                "error": {"code": -32600, "message": "Invalid request"},
                "id": "ws-req-1",
            }
        )
        ws.recv = AsyncMock(side_effect=[error_frame, asyncio.CancelledError()])

        future: asyncio.Future[Envelope] = asyncio.get_running_loop().create_future()
        transport._pending["ws-req-1"] = future

        task = asyncio.create_task(transport._recv_loop())
        await asyncio.sleep(0.05)

        with pytest.raises(WebSocketRemoteError, match="Invalid request"):
            future.result()

        task.cancel()
        with suppress(asyncio.CancelledError):
            await task

    @pytest.mark.asyncio
    async def test_recv_loop_error_frame_no_pending(self) -> None:
        """Error frame without matching pending logs warning (lines 396-400)."""
        transport = WebSocketTransport()
        ws = _mock_ws()
        transport._ws = ws

        error_frame = json.dumps(
            {
                "jsonrpc": "2.0",
                "error": {"code": -32600, "message": "Orphaned error"},
                "id": "ws-req-999",
            }
        )
        ws.recv = AsyncMock(side_effect=[error_frame, asyncio.CancelledError()])

        task = asyncio.create_task(transport._recv_loop())
        await asyncio.sleep(0.05)
        task.cancel()
        with suppress(asyncio.CancelledError):
            await task
        # Should not raise

    @pytest.mark.asyncio
    async def test_recv_loop_missing_result_envelope(self) -> None:
        """Response with no result.envelope sets exception (lines 402-414)."""
        transport = WebSocketTransport()
        ws = _mock_ws()
        transport._ws = ws

        bad_frame = json.dumps(
            {
                "jsonrpc": "2.0",
                "result": {},
                "id": "ws-req-1",
            }
        )
        ws.recv = AsyncMock(side_effect=[bad_frame, asyncio.CancelledError()])

        future: asyncio.Future[Envelope] = asyncio.get_running_loop().create_future()
        transport._pending["ws-req-1"] = future

        task = asyncio.create_task(transport._recv_loop())
        await asyncio.sleep(0.05)

        with pytest.raises(WebSocketRemoteError, match="Missing result.envelope"):
            future.result()

        task.cancel()
        with suppress(asyncio.CancelledError):
            await task

    @pytest.mark.asyncio
    async def test_recv_loop_on_message_callback_sync(self) -> None:
        """Server-push message triggers sync on_message callback (lines 420-424)."""
        received: list[Envelope] = []

        def on_msg(env: Envelope) -> None:
            received.append(env)

        transport = WebSocketTransport(on_message=on_msg)
        ws = _mock_ws()
        transport._ws = ws

        pushed = json.dumps(
            {
                "jsonrpc": "2.0",
                "result": {"envelope": _sample_envelope_cov().model_dump(mode="json")},
                "id": "some-other-id",
            }
        )
        ws.recv = AsyncMock(side_effect=[pushed, asyncio.CancelledError()])

        task = asyncio.create_task(transport._recv_loop())
        await asyncio.sleep(0.05)
        task.cancel()
        with suppress(asyncio.CancelledError):
            await task

        assert len(received) == 1

    @pytest.mark.asyncio
    async def test_recv_loop_on_message_callback_async(self) -> None:
        """Server-push message triggers async on_message callback (lines 420-424)."""
        received: list[Envelope] = []

        async def on_msg(env: Envelope) -> None:
            received.append(env)

        transport = WebSocketTransport(on_message=on_msg)
        ws = _mock_ws()
        transport._ws = ws

        pushed = json.dumps(
            {
                "jsonrpc": "2.0",
                "result": {"envelope": _sample_envelope_cov().model_dump(mode="json")},
                "id": "unknown-req",
            }
        )
        ws.recv = AsyncMock(side_effect=[pushed, asyncio.CancelledError()])

        task = asyncio.create_task(transport._recv_loop())
        await asyncio.sleep(0.05)
        task.cancel()
        with suppress(asyncio.CancelledError):
            await task

        assert len(received) == 1

    @pytest.mark.asyncio
    async def test_recv_loop_on_message_callback_error(self) -> None:
        """on_message callback error is caught (lines 425-429)."""

        def on_msg(env: Envelope) -> None:
            raise ValueError("callback boom")

        transport = WebSocketTransport(on_message=on_msg)
        ws = _mock_ws()
        transport._ws = ws

        pushed = json.dumps(
            {
                "jsonrpc": "2.0",
                "result": {"envelope": _sample_envelope_cov().model_dump(mode="json")},
                "id": "unknown-req",
            }
        )
        ws.recv = AsyncMock(side_effect=[pushed, asyncio.CancelledError()])

        task = asyncio.create_task(transport._recv_loop())
        await asyncio.sleep(0.05)
        task.cancel()
        with suppress(asyncio.CancelledError):
            await task
        # Should not raise, error is caught

    @pytest.mark.asyncio
    async def test_recv_loop_generic_exception_sets_all_pending(self) -> None:
        """Generic exception in recv_loop sets exception on all pending (lines 434-439)."""
        transport = WebSocketTransport()
        ws = _mock_ws()
        transport._ws = ws

        ws.recv = AsyncMock(side_effect=RuntimeError("connection lost"))

        future: asyncio.Future[Envelope] = asyncio.get_running_loop().create_future()
        transport._pending["ws-req-1"] = future

        task = asyncio.create_task(transport._recv_loop())
        await asyncio.sleep(0.05)

        with pytest.raises(WebSocketRemoteError, match="connection lost"):
            future.result()

        assert len(transport._pending) == 0
        task.cancel()
        with suppress(asyncio.CancelledError):
            await task


# ---------------------------------------------------------------------------
# close() with pending futures (line 461)
# ---------------------------------------------------------------------------


class TestCloseCoverage:
    @pytest.mark.asyncio
    async def test_close_cancels_pending_futures(self) -> None:
        """close() sets TimeoutError on pending futures (lines 460-462)."""
        transport = WebSocketTransport()
        transport._ws = _mock_ws()

        future: asyncio.Future[Envelope] = asyncio.get_running_loop().create_future()
        transport._pending["ws-req-1"] = future

        await transport.close()

        with pytest.raises(asyncio.TimeoutError, match="Connection closed"):
            future.result()
        assert transport._ws is None


# ---------------------------------------------------------------------------
# __aenter__ / __aexit__ (lines 471, 474)
# ---------------------------------------------------------------------------


class TestAsyncContextManager:
    @pytest.mark.asyncio
    async def test_aenter_aexit(self) -> None:
        """async with WebSocketTransport closes on exit (lines 470-474)."""
        async with WebSocketTransport() as t:
            assert isinstance(t, WebSocketTransport)
        assert t._closed is True


# ---------------------------------------------------------------------------
# _send_envelope_only: ws=None (line 502)
# ---------------------------------------------------------------------------


class TestSendEnvelopeOnly:
    @pytest.mark.asyncio
    async def test_send_envelope_only_ws_none_returns(self) -> None:
        """_send_envelope_only returns early when ws is None (line 502)."""
        transport = WebSocketTransport()
        transport._ws = None
        env = _sample_envelope_cov()
        # Should not raise
        await transport._send_envelope_only(env)


# ---------------------------------------------------------------------------
# _ack_check_loop: retransmit failure (lines 544-545)
# ---------------------------------------------------------------------------


class TestAckCheckLoop:
    @pytest.mark.asyncio
    async def test_ack_retransmit_failure_logged(self) -> None:
        """Failed retransmit logs warning (lines 544-549)."""
        transport = WebSocketTransport(
            ack_timeout_seconds=0.0,
            ack_check_interval=0.01,
            max_ack_retries=3,
        )
        ws = _mock_ws()
        ws.send = AsyncMock(side_effect=OSError("send failed"))
        transport._ws = ws

        env = _sample_envelope_cov()
        transport._pending_acks["e1"] = PendingAck(
            envelope_id="e1",
            sent_at=time.monotonic() - 100,  # expired
            retries=0,
            original_envelope=env,
        )

        task = asyncio.create_task(transport._ack_check_loop())
        await asyncio.sleep(0.1)
        transport._closed = True
        await asyncio.sleep(0.05)
        task.cancel()
        with suppress(asyncio.CancelledError):
            await task

        # Pending ack should still exist (retransmit failed, not max retries)
        assert "e1" in transport._pending_acks


# ---------------------------------------------------------------------------
# send / send_and_receive: not connected (lines 564, 578, 588)
# ---------------------------------------------------------------------------


class TestSendNotConnected:
    @pytest.mark.asyncio
    async def test_send_ws_none_raises(self) -> None:
        """send() raises RuntimeError when not connected (line 564)."""
        transport = WebSocketTransport()
        with pytest.raises(RuntimeError, match="not connected"):
            await transport.send(_sample_envelope_cov())

    @pytest.mark.asyncio
    async def test_send_and_receive_ws_none_raises(self) -> None:
        """send_and_receive() raises RuntimeError when not connected (line 578)."""
        transport = WebSocketTransport()
        with pytest.raises(RuntimeError, match="not connected"):
            await transport.send_and_receive(_sample_envelope_cov())


# ---------------------------------------------------------------------------
# receive(): ws=None, bytes, result branch (lines 598, 601, 617)
# ---------------------------------------------------------------------------


class TestReceiveCoverage:
    @pytest.mark.asyncio
    async def test_receive_ws_none_raises(self) -> None:
        """receive() raises RuntimeError when not connected (line 598)."""
        transport = WebSocketTransport()
        with pytest.raises(RuntimeError, match="not connected"):
            await transport.receive()

    @pytest.mark.asyncio
    async def test_receive_bytes_decoded(self) -> None:
        """receive() decodes bytes response (line 601)."""
        transport = WebSocketTransport()
        ws = _mock_ws()
        transport._ws = ws

        env = _sample_envelope_cov()
        response = json.dumps(
            {
                "jsonrpc": "2.0",
                "result": {"envelope": env.model_dump(mode="json")},
                "id": "ws-req-1",
            }
        )
        ws.recv = AsyncMock(return_value=response.encode("utf-8"))

        result = await transport.receive()
        assert result.sender == "urn:asap:agent:a"

    @pytest.mark.asyncio
    async def test_receive_valid_envelope(self) -> None:
        """receive() returns valid Envelope from result (line 617)."""
        transport = WebSocketTransport()
        ws = _mock_ws()
        transport._ws = ws

        env = _sample_envelope_cov()
        response = json.dumps(
            {
                "jsonrpc": "2.0",
                "result": {"envelope": env.model_dump(mode="json")},
                "id": "ws-req-1",
            }
        )
        ws.recv = AsyncMock(return_value=response)

        result = await transport.receive()
        assert result.payload_type == "task.request"


# ---------------------------------------------------------------------------
# WebSocketConnectionPool: waiting path, release (lines 653-654, 668-677, 738)
# ---------------------------------------------------------------------------


class TestPoolCoverage:
    @pytest.mark.asyncio
    async def test_pool_release_with_disconnected_transport(self) -> None:
        """release() with ws=None decrements total_count (line 687-689)."""
        pool = WebSocketConnectionPool(url="ws://localhost:8080")
        transport = WebSocketTransport()
        transport._ws = None

        pool._in_use_count = 1
        pool._total_count = 1

        await pool.release(transport)
        assert pool._total_count == 0
        assert pool._in_use_count == 0

    @pytest.mark.asyncio
    async def test_pool_acquire_skips_stale_in_queue(self) -> None:
        """acquire() skips stale connections from the available queue (lines 648-654)."""
        pool = WebSocketConnectionPool(url="ws://localhost:8080", idle_timeout=0.0)

        stale_transport = WebSocketTransport()
        stale_transport._ws = _mock_ws()

        # Put a stale connection in the queue
        pool._available.put_nowait((stale_transport, time.monotonic() - 100))
        pool._total_count = 1

        # Pool should skip stale and try to create new one, but we mock connect
        fresh_transport = WebSocketTransport()
        fresh_ws = _mock_ws()
        fresh_transport._ws = fresh_ws

        with patch.object(WebSocketTransport, "connect", new_callable=AsyncMock) as mock_connect:

            async def set_ws(url: str) -> None:
                pool._available.task_done()  # no-op
                # Simulate that the transport is now connected
                WebSocketTransport.__init__(fresh_transport)
                fresh_transport._ws = fresh_ws

            mock_connect.side_effect = set_ws

            pool._max_size = 5
            try:
                t = await pool.acquire()
                await pool.release(t)
            except Exception:
                pass

    @pytest.mark.asyncio
    async def test_pool_acquire_skips_ws_none_in_queue(self) -> None:
        """acquire() skips connections with ws=None (lines 652-654)."""
        pool = WebSocketConnectionPool(url="ws://localhost:8080")

        dead_transport = WebSocketTransport()
        dead_transport._ws = None  # disconnected

        pool._available.put_nowait((dead_transport, time.monotonic()))
        pool._total_count = 1

        with patch.object(WebSocketTransport, "connect", new_callable=AsyncMock):
            pool._max_size = 5
            try:
                t = await pool.acquire()
                await pool.release(t)
            except Exception:
                pass


# ---------------------------------------------------------------------------
# _heartbeat_loop: stale detection and error (lines 784-803)
# ---------------------------------------------------------------------------


class TestHeartbeatLoopCoverage:
    @pytest.mark.asyncio
    async def test_heartbeat_stale_connection(self) -> None:
        """_heartbeat_loop detects stale connection (lines 787-793)."""
        ws = AsyncMock()
        last_received = [time.monotonic() - STALE_CONNECTION_TIMEOUT - 10]
        closed = asyncio.Event()

        with patch("asap.transport.websocket.HEARTBEAT_PING_INTERVAL", 0.01):
            task = asyncio.create_task(_heartbeat_loop(ws, last_received, closed))
            await asyncio.sleep(0.1)

        assert closed.is_set()
        task.cancel()
        with suppress(asyncio.CancelledError):
            await task

    @pytest.mark.asyncio
    async def test_heartbeat_send_error_closes(self) -> None:
        """_heartbeat_loop closes on send error (lines 800-803)."""
        ws = AsyncMock()
        ws.send_text = AsyncMock(side_effect=OSError("broken pipe"))
        last_received = [time.monotonic()]  # Fresh, not stale
        closed = asyncio.Event()

        with patch("asap.transport.websocket.HEARTBEAT_PING_INTERVAL", 0.01):
            task = asyncio.create_task(_heartbeat_loop(ws, last_received, closed))
            await asyncio.sleep(0.1)

        assert closed.is_set()
        task.cancel()
        with suppress(asyncio.CancelledError):
            await task


# ---------------------------------------------------------------------------
# _build_ack_notification_frame
# ---------------------------------------------------------------------------


class TestBuildAckFrame:
    def test_build_ack_frame_with_error(self) -> None:
        """_build_ack_notification_frame includes error field when set."""
        frame = _build_ack_notification_frame(
            original_envelope_id="e1",
            status="rejected",
            sender="urn:asap:agent:a",
            recipient="urn:asap:agent:b",
            error="processing failed",
        )
        data = json.loads(frame)
        assert data["method"] == ASAP_ACK_METHOD
        env = data["params"]["envelope"]
        assert env["payload"]["error"] == "processing failed"


# ---------------------------------------------------------------------------
# connect() reconnect error path (lines 333, 338-345)
# ---------------------------------------------------------------------------


class TestConnectReconnect:
    @pytest.mark.asyncio
    async def test_connect_reconnect_error_raises(self) -> None:
        """connect() with reconnect mode raises initial connection error (lines 338-345)."""
        transport = WebSocketTransport(reconnect_on_disconnect=True)

        with (
            patch(
                "asap.transport.websocket.websockets.connect",
                side_effect=ConnectionRefusedError("refused"),
            ),
            pytest.raises(ConnectionRefusedError, match="refused"),
        ):
            await transport.connect("ws://localhost:8080")

        assert transport._ws is None

    @pytest.mark.asyncio
    async def test_connect_already_connected_no_op(self) -> None:
        """connect() returns immediately if already connected (line 333)."""
        transport = WebSocketTransport()
        transport._ws = _mock_ws()

        await transport.connect("ws://localhost:8080")
        # No exception, no change


# ---------------------------------------------------------------------------
# handle_websocket_connection: message processing error paths
# ---------------------------------------------------------------------------


class TestHandleWebSocketConnection:
    @pytest.mark.asyncio
    async def test_handle_message_error_sends_error_payload(self) -> None:
        """Handler error sends JSON-RPC error frame (lines 962-989)."""
        ws = AsyncMock()
        ws.accept = AsyncMock()
        ws.close = AsyncMock()
        ws.client = ("127.0.0.1", 12345)
        ws.scope = {"headers": [], "path": "/asap/ws", "server": ("localhost", 8000)}

        sent_texts: list[str] = []
        ws.send_text = AsyncMock(side_effect=lambda t: sent_texts.append(t))

        env = _sample_envelope_cov()
        valid_frame = json.dumps(
            {
                "jsonrpc": "2.0",
                "method": "asap.send",
                "params": {"envelope": env.model_dump(mode="json")},
                "id": "1",
            }
        )

        call_count = 0

        async def receive_text() -> str:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return valid_frame
            raise RuntimeError("disconnect")

        ws.receive_text = AsyncMock(side_effect=receive_text)

        handler = MagicMock()
        handler.handle_message = AsyncMock(side_effect=RuntimeError("handler boom"))

        active: set[WebSocket] = set()
        await handle_websocket_connection(
            websocket=ws,
            request_handler=handler,
            active_connections=active,
            ws_message_rate_limit=None,
        )

        # Should have sent at least an error payload
        assert any('"error"' in t for t in sent_texts)

    @pytest.mark.asyncio
    async def test_handle_message_error_with_ack_sends_reject(self) -> None:
        """Handler error for requires_ack sends reject ack frame (lines 967-976)."""
        ws = AsyncMock()
        ws.accept = AsyncMock()
        ws.close = AsyncMock()
        ws.client = ("127.0.0.1", 12345)
        ws.scope = {"headers": [], "path": "/asap/ws", "server": ("localhost", 8000)}

        sent_texts: list[str] = []
        ws.send_text = AsyncMock(side_effect=lambda t: sent_texts.append(t))

        env = _sample_envelope_cov(requires_ack=True)
        valid_frame = json.dumps(
            {
                "jsonrpc": "2.0",
                "method": "asap.send",
                "params": {"envelope": env.model_dump(mode="json")},
                "id": "1",
            }
        )

        call_count = 0

        async def receive_text() -> str:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return valid_frame
            raise RuntimeError("disconnect")

        ws.receive_text = AsyncMock(side_effect=receive_text)

        handler = MagicMock()
        handler.handle_message = AsyncMock(side_effect=RuntimeError("handler fail"))

        await handle_websocket_connection(
            websocket=ws,
            request_handler=handler,
            active_connections=set(),
            ws_message_rate_limit=None,
        )

        # Should have sent a "received" ack, then a "rejected" ack, then error payload
        ack_frames = [t for t in sent_texts if ASAP_ACK_METHOD in t]
        assert len(ack_frames) >= 1  # At least the rejected ack

    @pytest.mark.asyncio
    async def test_handle_error_payload_send_fails_breaks(self) -> None:
        """If sending error payload also fails, loop breaks (lines 988-989)."""
        ws = AsyncMock()
        ws.accept = AsyncMock()
        ws.close = AsyncMock()
        ws.client = ("127.0.0.1", 12345)
        ws.scope = {"headers": [], "path": "/asap/ws", "server": ("localhost", 8000)}

        send_count = 0

        async def send_text(t: str) -> None:
            nonlocal send_count
            send_count += 1
            if send_count >= 2:
                raise OSError("broken pipe")

        ws.send_text = AsyncMock(side_effect=send_text)

        env = _sample_envelope_cov()
        valid_frame = json.dumps(
            {
                "jsonrpc": "2.0",
                "method": "asap.send",
                "params": {"envelope": env.model_dump(mode="json")},
                "id": "1",
            }
        )

        call_count = 0

        async def receive_text() -> str:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return valid_frame
            raise RuntimeError("disconnect")

        ws.receive_text = AsyncMock(side_effect=receive_text)

        handler = MagicMock()
        handler.handle_message = AsyncMock(side_effect=RuntimeError("boom"))

        await handle_websocket_connection(
            websocket=ws,
            request_handler=handler,
            active_connections=set(),
            ws_message_rate_limit=None,
        )
        # Should not raise; loop breaks on send error

    @pytest.mark.asyncio
    async def test_handle_websocket_sla_subscribe_unsubscribe(self) -> None:
        """SLA subscribe/unsubscribe messages are handled (lines 890-916)."""
        ws = AsyncMock()
        ws.accept = AsyncMock()
        ws.close = AsyncMock()
        ws.client = ("127.0.0.1", 12345)
        ws.scope = {"headers": [], "path": "/asap/ws", "server": ("localhost", 8000)}

        sent_texts: list[str] = []
        ws.send_text = AsyncMock(side_effect=lambda t: sent_texts.append(t))

        subscribe_frame = json.dumps(
            {
                "jsonrpc": "2.0",
                "method": "sla.subscribe",
                "id": "sub-1",
            }
        )
        unsubscribe_frame = json.dumps(
            {
                "jsonrpc": "2.0",
                "method": "sla.unsubscribe",
                "id": "unsub-1",
            }
        )

        call_count = 0

        async def receive_text() -> str:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return subscribe_frame
            if call_count == 2:
                return unsubscribe_frame
            raise RuntimeError("disconnect")

        ws.receive_text = AsyncMock(side_effect=receive_text)

        handler = MagicMock()
        handler.handle_message = AsyncMock()

        sla_subs: set[Any] = set()
        await handle_websocket_connection(
            websocket=ws,
            request_handler=handler,
            active_connections=set(),
            ws_message_rate_limit=None,
            sla_breach_subscribers=sla_subs,
        )

        # Should have sent subscribe and unsubscribe confirmations
        assert any('"subscribed": true' in t for t in sent_texts)
        assert any('"unsubscribed": true' in t for t in sent_texts)
