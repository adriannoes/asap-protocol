"""E2E tests: ASAPClient over WebSocket with real server (Task 3.2)."""

import socket
import threading
from typing import TYPE_CHECKING

import pytest

from asap.models.entities import Manifest
from asap.models.envelope import Envelope
from asap.models.payloads import TaskRequest
from asap.transport.client import ASAPClient
from asap.transport.handlers import create_default_registry
from asap.transport.server import create_app

from ..conftest import NoRateLimitTestBase, TEST_RATE_LIMIT_DEFAULT

if TYPE_CHECKING:
    from asap.transport.rate_limit import ASAPRateLimiter


def _free_port() -> int:
    """Return a free port for binding."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


class TestWebSocketClientE2E(NoRateLimitTestBase):
    """E2E: ASAPClient with transport_mode=websocket against live server."""

    @pytest.mark.asyncio
    async def test_client_websocket_send_receive(
        self,
        sample_manifest: Manifest,
        disable_rate_limiting: "ASAPRateLimiter",
    ) -> None:
        """ASAPClient(transport_mode=websocket) sends TaskRequest and receives TaskResponse."""
        import asyncio

        import uvicorn
        from asap.transport import middleware as middleware_module

        middleware_module.limiter = disable_rate_limiting

        port = _free_port()
        app_instance = create_app(
            sample_manifest,
            create_default_registry(),
            rate_limit=TEST_RATE_LIMIT_DEFAULT,
        )
        app_instance.state.limiter = disable_rate_limiting

        server_started = threading.Event()
        server_error: list[Exception] = []

        def run_server() -> None:
            try:
                config = uvicorn.Config(
                    app_instance,
                    host="127.0.0.1",
                    port=port,
                    log_level="warning",
                )
                server = uvicorn.Server(config)
                server_started.set()
                asyncio.run(server.serve())
            except Exception as e:
                server_error.append(e)

        thread = threading.Thread(target=run_server, daemon=True)
        thread.start()
        if not server_started.wait(timeout=5.0):
            pytest.fail("Server did not start in time")
        await asyncio.sleep(0.3)

        ws_url = f"ws://127.0.0.1:{port}/asap/ws"
        try:
            async with ASAPClient(
                ws_url,
                transport_mode="websocket",
                timeout=10.0,
                require_https=False,
            ) as client:
                envelope = Envelope(
                    asap_version="0.1",
                    sender="urn:asap:agent:e2e-client",
                    recipient=sample_manifest.id,
                    payload_type="task.request",
                    payload=TaskRequest(
                        conversation_id="e2e-conv-1",
                        skill_id="echo",
                        input={"message": "hello e2e"},
                    ).model_dump(),
                )
                response = await client.send(envelope)
            assert response is not None
            assert response.payload_type == "task.response"
        except Exception as e:
            if server_error:
                raise server_error[0] from e
            raise


class TestWebSocketClientWithTestClient(NoRateLimitTestBase):
    """Integration tests using TestClient (in-process) to verify client path."""

    def test_websocket_client_connect_url_construction(
        self,
        sample_manifest: Manifest,
    ) -> None:
        """ASAPClient with http base_url and transport_mode=websocket builds ws URL."""
        client = ASAPClient(
            "http://localhost:8000",
            transport_mode="websocket",
            require_https=False,
        )
        assert client._use_websocket is True
        assert client._ws_url == "ws://localhost:8000/asap/ws"

    def test_websocket_client_auto_detect_ws_url(
        self,
        sample_manifest: Manifest,
    ) -> None:
        """ASAPClient with ws:// URL and transport_mode=auto uses WebSocket."""
        client = ASAPClient(
            "ws://localhost:8000/asap/ws",
            transport_mode="auto",
            require_https=False,
        )
        assert client._use_websocket is True
        assert client._ws_url == "ws://localhost:8000/asap/ws"

    def test_websocket_client_http_url_auto_uses_http(
        self,
        sample_manifest: Manifest,
    ) -> None:
        """ASAPClient with http URL and transport_mode=auto uses HTTP."""
        client = ASAPClient(
            "http://localhost:8000",
            transport_mode="auto",
            require_https=False,
        )
        assert client._use_websocket is False
