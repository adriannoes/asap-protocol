"""Edge case tests for ASAPClient error paths.

Covers retry behavior, connection errors, and error paths in:
- send() with 5xx server errors (retries)
- send() with connection refused
- discover() error paths (HTTP errors, invalid JSON, connection errors)
- health_check() error paths
- _parse_max_age_from_cache_control edge cases
"""

from __future__ import annotations

from unittest.mock import AsyncMock

import httpx
import pytest

from asap.models.enums import TaskStatus
from asap.models.envelope import Envelope
from asap.models.payloads import TaskRequest, TaskResponse
from asap.transport.client import (
    ASAPClient,
    ASAPConnectionError,
    ASAPTimeoutError,
    _parse_max_age_from_cache_control,
)


@pytest.fixture
def sample_request_envelope() -> Envelope:
    """Create a sample request envelope for testing."""
    return Envelope(
        asap_version="0.1",
        sender="urn:asap:agent:client",
        recipient="urn:asap:agent:server",
        payload_type="task.request",
        payload=TaskRequest(
            conversation_id="conv_123",
            skill_id="echo",
            input={"message": "Hello!"},
        ).model_dump(),
    )


def _make_success_response(envelope: Envelope) -> httpx.Response:
    """Create a mock httpx.Response with valid JSON-RPC success."""
    response_envelope = Envelope(
        asap_version="0.1",
        sender="urn:asap:agent:server",
        recipient="urn:asap:agent:client",
        payload_type="task.response",
        payload=TaskResponse(
            task_id="task_1",
            status=TaskStatus.COMPLETED,
        ).model_dump(),
        correlation_id="req_1",
    )
    body = {
        "jsonrpc": "2.0",
        "result": {"envelope": response_envelope.model_dump(mode="json")},
        "id": "1",
    }
    return httpx.Response(200, json=body)


class TestParseMaxAge:
    """Tests for _parse_max_age_from_cache_control helper."""

    def test_none_input(self) -> None:
        """None Cache-Control returns None."""
        assert _parse_max_age_from_cache_control(None) is None

    def test_empty_string(self) -> None:
        """Empty Cache-Control returns None."""
        assert _parse_max_age_from_cache_control("") is None

    def test_no_max_age(self) -> None:
        """Cache-Control without max-age returns None."""
        assert _parse_max_age_from_cache_control("no-cache") is None

    def test_valid_max_age(self) -> None:
        """Cache-Control with valid max-age returns seconds."""
        result = _parse_max_age_from_cache_control("max-age=300")
        assert result == 300

    def test_zero_max_age(self) -> None:
        """Cache-Control with max-age=0 returns None."""
        assert _parse_max_age_from_cache_control("max-age=0") is None


class TestSendRetryOnServerError:
    """Tests for send() retry behavior on server errors."""

    @pytest.mark.asyncio
    async def test_send_retries_on_503(self, sample_request_envelope: Envelope) -> None:
        """send() retries on 503 and succeeds on retry."""
        error_response = httpx.Response(503, text="Service Unavailable")
        success_response = _make_success_response(sample_request_envelope)

        mock_transport = AsyncMock()
        mock_transport.handle_async_request.side_effect = [
            error_response,
            success_response,
        ]

        async with ASAPClient(
            "http://localhost:8000",
            max_retries=3,
            timeout=5.0,
        ) as client:
            client._client = httpx.AsyncClient(transport=mock_transport)
            result = await client.send(sample_request_envelope)
            assert result is not None
            assert result.payload_type == "task.response"

    @pytest.mark.asyncio
    async def test_send_raises_after_max_retries_on_5xx(
        self, sample_request_envelope: Envelope
    ) -> None:
        """send() raises ASAPConnectionError after exhausting retries on 5xx."""
        error_response = httpx.Response(500, text="Internal Server Error")

        mock_transport = AsyncMock()
        mock_transport.handle_async_request.return_value = error_response

        async with ASAPClient(
            "http://localhost:8000",
            max_retries=2,
            timeout=5.0,
            base_delay=0.01,
        ) as client:
            client._client = httpx.AsyncClient(transport=mock_transport)
            with pytest.raises(ASAPConnectionError):
                await client.send(sample_request_envelope)

    @pytest.mark.asyncio
    async def test_send_raises_on_connection_refused(
        self, sample_request_envelope: Envelope
    ) -> None:
        """send() raises ASAPConnectionError on connection refused."""
        mock_transport = AsyncMock()
        mock_transport.handle_async_request.side_effect = httpx.ConnectError("Connection refused")

        async with ASAPClient(
            "http://localhost:8000",
            max_retries=2,
            timeout=5.0,
            base_delay=0.01,
        ) as client:
            client._client = httpx.AsyncClient(transport=mock_transport)
            with pytest.raises(ASAPConnectionError, match="Connection refused"):
                await client.send(sample_request_envelope)

    @pytest.mark.asyncio
    async def test_send_raises_on_timeout(self, sample_request_envelope: Envelope) -> None:
        """send() raises ASAPTimeoutError on timeout."""
        mock_transport = AsyncMock()
        mock_transport.handle_async_request.side_effect = httpx.TimeoutException("timed out")

        async with ASAPClient(
            "http://localhost:8000",
            max_retries=1,
            timeout=1.0,
        ) as client:
            client._client = httpx.AsyncClient(transport=mock_transport)
            with pytest.raises(ASAPTimeoutError):
                await client.send(sample_request_envelope)


class TestDiscoverErrorPaths:
    """Tests for discover() error paths."""

    @pytest.mark.asyncio
    async def test_discover_http_error_raises(self) -> None:
        """discover() raises ASAPConnectionError on HTTP 404."""
        mock_transport = AsyncMock()
        mock_transport.handle_async_request.return_value = httpx.Response(404, text="Not Found")

        async with ASAPClient("http://localhost:8000") as client:
            client._client = httpx.AsyncClient(transport=mock_transport)
            with pytest.raises(ASAPConnectionError, match="HTTP error 404"):
                await client.discover("http://localhost:8000")

    @pytest.mark.asyncio
    async def test_discover_invalid_json_raises(self) -> None:
        """discover() raises ValueError on invalid JSON."""
        mock_transport = AsyncMock()
        mock_transport.handle_async_request.return_value = httpx.Response(
            200, content=b"not json at all", headers={"content-type": "text/plain"}
        )

        async with ASAPClient("http://localhost:8000") as client:
            client._client = httpx.AsyncClient(transport=mock_transport)
            with pytest.raises(ValueError, match="Invalid JSON"):
                await client.discover("http://localhost:8000")

    @pytest.mark.asyncio
    async def test_discover_connection_error_raises(self) -> None:
        """discover() raises ASAPConnectionError on connection error."""
        mock_transport = AsyncMock()
        mock_transport.handle_async_request.side_effect = httpx.ConnectError("Connection refused")

        async with ASAPClient("http://localhost:8000") as client:
            client._client = httpx.AsyncClient(transport=mock_transport)
            with pytest.raises(ASAPConnectionError, match="Connection error"):
                await client.discover("http://localhost:8000")

    @pytest.mark.asyncio
    async def test_discover_timeout_raises(self) -> None:
        """discover() raises ASAPTimeoutError on timeout."""
        mock_transport = AsyncMock()
        mock_transport.handle_async_request.side_effect = httpx.TimeoutException("timed out")

        async with ASAPClient("http://localhost:8000") as client:
            client._client = httpx.AsyncClient(transport=mock_transport)
            with pytest.raises(ASAPTimeoutError):
                await client.discover("http://localhost:8000")

    @pytest.mark.asyncio
    async def test_discover_unexpected_error_raises(self) -> None:
        """discover() wraps unexpected errors in ASAPConnectionError."""
        mock_transport = AsyncMock()
        mock_transport.handle_async_request.side_effect = RuntimeError("unexpected")

        async with ASAPClient("http://localhost:8000") as client:
            client._client = httpx.AsyncClient(transport=mock_transport)
            with pytest.raises(ASAPConnectionError, match="Unexpected error"):
                await client.discover("http://localhost:8000")

    @pytest.mark.asyncio
    async def test_discover_not_connected_raises(self) -> None:
        """discover() raises ASAPConnectionError when client not connected."""
        client = ASAPClient("http://localhost:8000")
        with pytest.raises(ASAPConnectionError, match="Client not connected"):
            await client.discover("http://localhost:8000")


class TestHealthCheckErrorPaths:
    """Tests for health_check() error paths."""

    @pytest.mark.asyncio
    async def test_health_check_http_error_raises(self) -> None:
        """health_check() raises ASAPConnectionError on HTTP error."""
        mock_transport = AsyncMock()
        mock_transport.handle_async_request.return_value = httpx.Response(
            500, text="Internal Server Error"
        )

        async with ASAPClient("http://localhost:8000") as client:
            client._client = httpx.AsyncClient(transport=mock_transport)
            with pytest.raises(ASAPConnectionError, match="HTTP error 500"):
                await client.health_check("http://localhost:8000")

    @pytest.mark.asyncio
    async def test_health_check_invalid_json_raises(self) -> None:
        """health_check() raises ValueError on invalid JSON."""
        mock_transport = AsyncMock()
        mock_transport.handle_async_request.return_value = httpx.Response(
            200, content=b"not json", headers={"content-type": "text/plain"}
        )

        async with ASAPClient("http://localhost:8000") as client:
            client._client = httpx.AsyncClient(transport=mock_transport)
            with pytest.raises(ValueError, match="Invalid JSON"):
                await client.health_check("http://localhost:8000")

    @pytest.mark.asyncio
    async def test_health_check_invalid_schema_raises(self) -> None:
        """health_check() raises ValueError on invalid schema."""
        mock_transport = AsyncMock()
        mock_transport.handle_async_request.return_value = httpx.Response(
            200, json={"unknown_field": "value"}
        )

        async with ASAPClient("http://localhost:8000") as client:
            client._client = httpx.AsyncClient(transport=mock_transport)
            with pytest.raises(ValueError, match="Invalid health response schema"):
                await client.health_check("http://localhost:8000")

    @pytest.mark.asyncio
    async def test_health_check_connection_error_raises(self) -> None:
        """health_check() raises ASAPConnectionError on connection error."""
        mock_transport = AsyncMock()
        mock_transport.handle_async_request.side_effect = httpx.ConnectError("refused")

        async with ASAPClient("http://localhost:8000") as client:
            client._client = httpx.AsyncClient(transport=mock_transport)
            with pytest.raises(ASAPConnectionError, match="Connection error"):
                await client.health_check("http://localhost:8000")

    @pytest.mark.asyncio
    async def test_health_check_timeout_raises(self) -> None:
        """health_check() raises ASAPTimeoutError on timeout."""
        mock_transport = AsyncMock()
        mock_transport.handle_async_request.side_effect = httpx.TimeoutException("timed out")

        async with ASAPClient("http://localhost:8000") as client:
            client._client = httpx.AsyncClient(transport=mock_transport)
            with pytest.raises(ASAPTimeoutError):
                await client.health_check("http://localhost:8000")

    @pytest.mark.asyncio
    async def test_health_check_unexpected_error_raises(self) -> None:
        """health_check() wraps unexpected errors in ASAPConnectionError."""
        mock_transport = AsyncMock()
        mock_transport.handle_async_request.side_effect = RuntimeError("unexpected")

        async with ASAPClient("http://localhost:8000") as client:
            client._client = httpx.AsyncClient(transport=mock_transport)
            with pytest.raises(ASAPConnectionError, match="Unexpected error"):
                await client.health_check("http://localhost:8000")

    @pytest.mark.asyncio
    async def test_health_check_not_connected_raises(self) -> None:
        """health_check() raises ASAPConnectionError when client not connected."""
        client = ASAPClient("http://localhost:8000")
        with pytest.raises(ASAPConnectionError, match="Client not connected"):
            await client.health_check("http://localhost:8000")
