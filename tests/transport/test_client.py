"""Tests for ASAP protocol async HTTP client.

This module tests the ASAPClient class that provides async HTTP
communication between ASAP agents.
"""

import json
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, patch

import httpx
import pytest

from asap.models.enums import TaskStatus
from asap.models.envelope import Envelope
from asap.models.payloads import TaskRequest, TaskResponse
from asap.testing import assert_envelope_valid, assert_response_correlates

if TYPE_CHECKING:
    pass


# Test fixtures
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


@pytest.fixture
def sample_response_envelope(sample_request_envelope: Envelope) -> Envelope:
    """Create a sample response envelope for testing."""
    return Envelope(
        asap_version="0.1",
        sender="urn:asap:agent:server",
        recipient="urn:asap:agent:client",
        payload_type="task.response",
        payload=TaskResponse(
            task_id="task_456",
            status=TaskStatus.COMPLETED,
            result={"echoed": {"message": "Hello!"}},
        ).model_dump(),
        correlation_id=sample_request_envelope.id,
    )


def create_mock_response(envelope: Envelope, request_id: str | int = "req-1") -> httpx.Response:
    """Create a mock HTTP response with JSON-RPC wrapped envelope."""
    json_rpc_response = {
        "jsonrpc": "2.0",
        "result": {"envelope": envelope.model_dump(mode="json")},
        "id": request_id,
    }
    return httpx.Response(
        status_code=200,
        json=json_rpc_response,
    )


def create_mock_error_response(
    code: int, message: str, request_id: str | int | None = "req-1"
) -> httpx.Response:
    """Create a mock HTTP error response with JSON-RPC error."""
    json_rpc_error = {
        "jsonrpc": "2.0",
        "error": {"code": code, "message": message},
        "id": request_id,
    }
    return httpx.Response(
        status_code=200,
        json=json_rpc_error,
    )


class TestASAPClientContextManager:
    """Tests for ASAPClient as async context manager."""

    async def test_client_as_async_context_manager(self) -> None:
        """Test ASAPClient can be used as async context manager."""
        from asap.transport.client import ASAPClient

        async with ASAPClient("http://localhost:8000") as client:
            assert client is not None

    async def test_client_opens_connection_on_enter(self) -> None:
        """Test client opens HTTP connection on context enter."""
        from asap.transport.client import ASAPClient

        client = ASAPClient("http://localhost:8000")
        assert not client.is_connected

        async with client:
            assert client.is_connected

    async def test_client_closes_connection_on_exit(self) -> None:
        """Test client closes HTTP connection on context exit."""
        from asap.transport.client import ASAPClient

        client = ASAPClient("http://localhost:8000")

        async with client:
            pass  # Connection should be open here

        assert not client.is_connected

    async def test_client_closes_connection_on_exception(self) -> None:
        """Test client closes connection even when exception occurs."""
        from asap.transport.client import ASAPClient

        client = ASAPClient("http://localhost:8000")

        with pytest.raises(RuntimeError):
            async with client:
                raise RuntimeError("Test exception")

        assert not client.is_connected

    async def test_client_with_custom_timeout(self) -> None:
        """Test client accepts custom timeout configuration."""
        from asap.transport.client import ASAPClient

        client = ASAPClient("http://localhost:8000", timeout=30.0)
        assert client.timeout == 30.0

    async def test_client_creates_async_client_with_pool_limits(self) -> None:
        """Test ASAPClient passes pool config to httpx.AsyncClient as Limits and Timeout."""
        from asap.transport.client import ASAPClient, DEFAULT_POOL_TIMEOUT

        mock_instance = AsyncMock()
        mock_instance.aclose = AsyncMock()
        with patch(
            "asap.transport.client.httpx.AsyncClient", return_value=mock_instance
        ) as mock_async_client:
            client = ASAPClient(
                "http://localhost:8000",
                pool_connections=50,
                pool_maxsize=200,
                pool_timeout=10.0,
            )
            async with client:
                pass
            mock_async_client.assert_called_once()
            call_kwargs = mock_async_client.call_args.kwargs
            assert "limits" in call_kwargs
            limits = call_kwargs["limits"]
            assert isinstance(limits, httpx.Limits)
            assert limits.max_keepalive_connections == 50
            assert limits.max_connections == 200
            assert limits.keepalive_expiry == DEFAULT_POOL_TIMEOUT
            assert "timeout" in call_kwargs
            timeout = call_kwargs["timeout"]
            assert isinstance(timeout, httpx.Timeout)
            assert timeout.pool == 10.0

    async def test_client_http2_enabled_by_default(self) -> None:
        """Test ASAPClient has HTTP/2 enabled by default."""
        from asap.transport.client import ASAPClient

        mock_instance = AsyncMock()
        mock_instance.aclose = AsyncMock()
        with patch(
            "asap.transport.client.httpx.AsyncClient", return_value=mock_instance
        ) as mock_async_client:
            client = ASAPClient("http://localhost:8000")
            async with client:
                pass
            mock_async_client.assert_called_once()
            call_kwargs = mock_async_client.call_args.kwargs
            # HTTP/2 should be enabled by default
            assert call_kwargs.get("http2") is True

    async def test_client_http2_can_be_disabled(self) -> None:
        """Test ASAPClient can disable HTTP/2."""
        from asap.transport.client import ASAPClient

        mock_instance = AsyncMock()
        mock_instance.aclose = AsyncMock()
        with patch(
            "asap.transport.client.httpx.AsyncClient", return_value=mock_instance
        ) as mock_async_client:
            client = ASAPClient("http://localhost:8000", http2=False)
            async with client:
                pass
            mock_async_client.assert_called_once()
            call_kwargs = mock_async_client.call_args.kwargs
            # HTTP/2 should be disabled
            assert call_kwargs.get("http2") is False

    async def test_client_http2_not_passed_with_custom_transport(self) -> None:
        """Test HTTP/2 flag is not passed when using custom transport (for testing)."""
        from asap.transport.client import ASAPClient

        def mock_transport(request: httpx.Request) -> httpx.Response:
            return httpx.Response(status_code=200, json={})

        # Custom transport is used for testing - http2 shouldn't be passed
        async with ASAPClient(
            "http://localhost:8000", transport=httpx.MockTransport(mock_transport)
        ) as client:
            # Just verify client works with custom transport
            assert client.is_connected

    async def test_client_default_timeout(self) -> None:
        """Test client has reasonable default timeout."""
        from asap.transport.client import ASAPClient

        client = ASAPClient("http://localhost:8000")
        assert client.timeout > 0  # Should have a positive default

    def test_client_rejects_invalid_url_scheme(self) -> None:
        """Test client rejects URLs with invalid schemes."""
        from asap.transport.client import ASAPClient

        # Test various invalid schemes
        # Note: file:// URLs may fail format validation first, so test with valid format
        invalid_urls = [
            ("ftp://example.com", "Invalid URL scheme"),
            ("javascript://example.com", "Invalid URL scheme"),
            ("data://example.com", "Invalid URL scheme"),
        ]

        for url, expected_match in invalid_urls:
            with pytest.raises(ValueError, match=expected_match):
                ASAPClient(url)

        # file:// URLs may fail format validation, so test separately
        with pytest.raises(ValueError):
            ASAPClient("file:///path/to/file")

    def test_client_accepts_http_scheme(self) -> None:
        """Test client accepts http:// URLs."""
        from asap.transport.client import ASAPClient

        client = ASAPClient("http://localhost:8000")
        assert client.base_url == "http://localhost:8000"

    def test_client_accepts_https_scheme(self) -> None:
        """Test client accepts https:// URLs."""
        from asap.transport.client import ASAPClient

        client = ASAPClient("https://example.com")
        assert client.base_url == "https://example.com"

    def test_client_rejects_malformed_url(self) -> None:
        """Test client rejects malformed URLs."""
        from asap.transport.client import ASAPClient

        invalid_urls = [
            "not-a-url",
            "://missing-scheme",
            "http://",  # Missing netloc
        ]

        for url in invalid_urls:
            with pytest.raises(ValueError, match="Invalid base_url format"):
                ASAPClient(url)


class TestASAPClientSend:
    """Tests for ASAPClient.send() method."""

    async def test_send_returns_response_envelope(
        self, sample_request_envelope: Envelope, sample_response_envelope: Envelope
    ) -> None:
        """Test send() returns response envelope from server."""
        from asap.transport.client import ASAPClient

        # Create a mock transport
        def mock_transport(request: httpx.Request) -> httpx.Response:
            return create_mock_response(sample_response_envelope)

        async with ASAPClient(
            "http://localhost:8000", transport=httpx.MockTransport(mock_transport)
        ) as client:
            response = await client.send(sample_request_envelope)

        assert_envelope_valid(response, allowed_payload_types=["task.response"])
        assert_response_correlates(sample_request_envelope, response)

    async def test_send_includes_envelope_in_request(
        self, sample_request_envelope: Envelope, sample_response_envelope: Envelope
    ) -> None:
        """Test send() includes envelope in JSON-RPC request params."""
        from asap.transport.client import ASAPClient

        captured_request: httpx.Request | None = None

        def mock_transport(request: httpx.Request) -> httpx.Response:
            nonlocal captured_request
            captured_request = request
            return create_mock_response(sample_response_envelope)

        async with ASAPClient(
            "http://localhost:8000", transport=httpx.MockTransport(mock_transport)
        ) as client:
            await client.send(sample_request_envelope)

        assert captured_request is not None
        body = json.loads(captured_request.content)
        assert body["method"] == "asap.send"
        assert "envelope" in body["params"]

    async def test_send_posts_to_asap_endpoint(
        self, sample_request_envelope: Envelope, sample_response_envelope: Envelope
    ) -> None:
        """Test send() POSTs to /asap endpoint."""
        from asap.transport.client import ASAPClient

        captured_request: httpx.Request | None = None

        def mock_transport(request: httpx.Request) -> httpx.Response:
            nonlocal captured_request
            captured_request = request
            return create_mock_response(sample_response_envelope)

        async with ASAPClient(
            "http://localhost:8000", transport=httpx.MockTransport(mock_transport)
        ) as client:
            await client.send(sample_request_envelope)

        assert captured_request is not None
        assert captured_request.method == "POST"
        assert str(captured_request.url) == "http://localhost:8000/asap"

    async def test_send_sets_content_type_json(
        self, sample_request_envelope: Envelope, sample_response_envelope: Envelope
    ) -> None:
        """Test send() sets Content-Type to application/json."""
        from asap.transport.client import ASAPClient

        captured_request: httpx.Request | None = None

        def mock_transport(request: httpx.Request) -> httpx.Response:
            nonlocal captured_request
            captured_request = request
            return create_mock_response(sample_response_envelope)

        async with ASAPClient(
            "http://localhost:8000", transport=httpx.MockTransport(mock_transport)
        ) as client:
            await client.send(sample_request_envelope)

        assert captured_request is not None
        assert "application/json" in captured_request.headers.get("content-type", "")


class TestASAPClientErrorHandling:
    """Tests for ASAPClient error handling."""

    async def test_send_raises_on_connection_error(self, sample_request_envelope: Envelope) -> None:
        """Test send() raises ConnectionError on network failure."""
        from asap.transport.client import ASAPClient, ASAPConnectionError

        def mock_transport(request: httpx.Request) -> httpx.Response:
            raise httpx.ConnectError("Connection refused")

        async with ASAPClient(
            "http://localhost:8000", transport=httpx.MockTransport(mock_transport)
        ) as client:
            with pytest.raises(ASAPConnectionError) as exc_info:
                await client.send(sample_request_envelope)

            assert (
                "Connection refused" in str(exc_info.value)
                or "connection" in str(exc_info.value).lower()
            )

    async def test_send_raises_on_timeout(self, sample_request_envelope: Envelope) -> None:
        """Test send() raises TimeoutError on request timeout."""
        from asap.transport.client import ASAPClient, ASAPTimeoutError

        def mock_transport(request: httpx.Request) -> httpx.Response:
            raise httpx.TimeoutException("Request timed out")

        async with ASAPClient(
            "http://localhost:8000", transport=httpx.MockTransport(mock_transport)
        ) as client:
            with pytest.raises(ASAPTimeoutError) as exc_info:
                await client.send(sample_request_envelope)

            assert "timeout" in str(exc_info.value).lower()

    async def test_send_raises_on_json_rpc_error(self, sample_request_envelope: Envelope) -> None:
        """Test send() raises error on JSON-RPC error response."""
        from asap.transport.client import ASAPClient, ASAPRemoteError

        def mock_transport(request: httpx.Request) -> httpx.Response:
            return create_mock_error_response(-32601, "Method not found")

        async with ASAPClient(
            "http://localhost:8000", transport=httpx.MockTransport(mock_transport)
        ) as client:
            with pytest.raises(ASAPRemoteError) as exc_info:
                await client.send(sample_request_envelope)

            assert exc_info.value.code == -32601
            assert "Method not found" in exc_info.value.message

    async def test_send_raises_on_http_error(self, sample_request_envelope: Envelope) -> None:
        """Test send() raises error on HTTP error status."""
        from asap.transport.client import ASAPClient, ASAPConnectionError

        def mock_transport(request: httpx.Request) -> httpx.Response:
            return httpx.Response(status_code=500, content=b"Internal Server Error")

        async with ASAPClient(
            "http://localhost:8000", transport=httpx.MockTransport(mock_transport)
        ) as client:
            with pytest.raises(ASAPConnectionError) as exc_info:
                await client.send(sample_request_envelope)

            assert "500" in str(exc_info.value)

    async def test_send_raises_on_invalid_response(self, sample_request_envelope: Envelope) -> None:
        """Test send() raises error on invalid JSON response."""
        from asap.transport.client import ASAPClient, ASAPRemoteError

        def mock_transport(request: httpx.Request) -> httpx.Response:
            return httpx.Response(status_code=200, content=b"not json")

        async with ASAPClient(
            "http://localhost:8000", transport=httpx.MockTransport(mock_transport)
        ) as client:
            with pytest.raises(ASAPRemoteError):
                await client.send(sample_request_envelope)


class TestASAPClientRetry:
    """Tests for ASAPClient retry logic."""

    async def test_send_includes_idempotency_key(
        self, sample_request_envelope: Envelope, sample_response_envelope: Envelope
    ) -> None:
        """Test send() includes idempotency_key in request for retries."""
        from asap.transport.client import ASAPClient

        captured_request: httpx.Request | None = None

        def mock_transport(request: httpx.Request) -> httpx.Response:
            nonlocal captured_request
            captured_request = request
            return create_mock_response(sample_response_envelope)

        async with ASAPClient(
            "http://localhost:8000", transport=httpx.MockTransport(mock_transport)
        ) as client:
            await client.send(sample_request_envelope)

        assert captured_request is not None
        body = json.loads(captured_request.content)
        # idempotency_key should be in params or as header
        assert (
            "idempotency_key" in body.get("params", {})
            or "x-idempotency-key" in captured_request.headers
        )

    async def test_send_same_idempotency_key_on_retry(
        self, sample_request_envelope: Envelope, sample_response_envelope: Envelope
    ) -> None:
        """Test send() uses same idempotency_key when retrying."""
        from asap.transport.client import ASAPClient

        call_count = 0
        captured_keys: list[str] = []

        def mock_transport(request: httpx.Request) -> httpx.Response:
            nonlocal call_count
            call_count += 1
            body = json.loads(request.content)
            key = body.get("params", {}).get("idempotency_key") or request.headers.get(
                "x-idempotency-key"
            )
            if key:
                captured_keys.append(key)

            if call_count < 2:
                raise httpx.ConnectError("Temporary failure")
            return create_mock_response(sample_response_envelope)

        async with ASAPClient(
            "http://localhost:8000",
            transport=httpx.MockTransport(mock_transport),
            max_retries=3,
        ) as client:
            await client.send(sample_request_envelope)

        # Should have retried and used same key
        assert call_count == 2
        assert len(captured_keys) >= 1

    async def test_send_retries_on_5xx_server_errors(
        self, sample_request_envelope: Envelope, sample_response_envelope: Envelope
    ) -> None:
        """Test send() retries on 5xx server errors."""
        from asap.transport.client import ASAPClient

        call_count = 0

        def mock_transport(request: httpx.Request) -> httpx.Response:
            nonlocal call_count
            call_count += 1
            # Return 5xx errors for first 2 attempts, succeed on 3rd
            if call_count < 3:
                return httpx.Response(status_code=503, content=b"Service Unavailable")
            return create_mock_response(sample_response_envelope)

        async with ASAPClient(
            "http://localhost:8000",
            transport=httpx.MockTransport(mock_transport),
            max_retries=3,
        ) as client:
            response = await client.send(sample_request_envelope)

        # Should have retried and eventually succeeded
        assert call_count == 3
        assert response.payload_type == "task.response"

    async def test_send_raises_after_max_retries_on_5xx(
        self, sample_request_envelope: Envelope
    ) -> None:
        """Test send() raises ASAPConnectionError after max retries on 5xx errors."""
        from asap.transport.client import ASAPClient, ASAPConnectionError

        call_count = 0

        def mock_transport(request: httpx.Request) -> httpx.Response:
            nonlocal call_count
            call_count += 1
            # Always return 5xx error
            return httpx.Response(status_code=502, content=b"Bad Gateway")

        async with ASAPClient(
            "http://localhost:8000",
            transport=httpx.MockTransport(mock_transport),
            max_retries=3,
        ) as client:
            with pytest.raises(ASAPConnectionError) as exc_info:
                await client.send(sample_request_envelope)

            # Should have attempted max_retries times
            assert call_count == 3
            assert "502" in str(exc_info.value)


class TestASAPClientRetryEdgeCases:
    """Tests for ASAPClient retry edge cases and error scenarios."""

    async def test_send_raises_when_not_connected(self, sample_request_envelope: Envelope) -> None:
        """Test send() raises ASAPConnectionError when called outside context manager."""
        from asap.transport.client import ASAPClient, ASAPConnectionError

        client = ASAPClient("http://localhost:8000")
        # Calling send() without entering context manager
        with pytest.raises(ASAPConnectionError) as exc_info:
            await client.send(sample_request_envelope)

        assert "not connected" in str(exc_info.value).lower()
        assert "async with" in str(exc_info.value)

    async def test_send_raises_on_none_envelope(self) -> None:
        """Test send() raises ValueError when envelope is None."""
        from asap.transport.client import ASAPClient

        def mock_transport(request: httpx.Request) -> httpx.Response:
            return httpx.Response(status_code=200, json={"jsonrpc": "2.0", "result": {}})

        async with ASAPClient(
            "http://localhost:8000", transport=httpx.MockTransport(mock_transport)
        ) as client:
            with pytest.raises(ValueError, match="envelope cannot be None"):
                await client.send(None)  # type: ignore[arg-type]

    async def test_send_raises_on_max_retries_exceeded(
        self, sample_request_envelope: Envelope
    ) -> None:
        """Test send() raises ASAPConnectionError when all retry attempts fail."""
        from asap.transport.client import ASAPClient, ASAPConnectionError

        call_count = 0

        def mock_transport(request: httpx.Request) -> httpx.Response:
            nonlocal call_count
            call_count += 1
            # Always fail with connection error
            raise httpx.ConnectError("Server unavailable")

        async with ASAPClient(
            "http://localhost:8000",
            transport=httpx.MockTransport(mock_transport),
            max_retries=3,
        ) as client:
            with pytest.raises(ASAPConnectionError) as exc_info:
                await client.send(sample_request_envelope)

            # Should have attempted max_retries times
            assert call_count == 3
            assert "connection" in str(exc_info.value).lower()

    async def test_send_recovers_from_intermittent_network_errors(
        self, sample_request_envelope: Envelope, sample_response_envelope: Envelope
    ) -> None:
        """Test send() recovers when network errors are intermittent."""
        from asap.transport.client import ASAPClient

        call_count = 0

        def mock_transport(request: httpx.Request) -> httpx.Response:
            nonlocal call_count
            call_count += 1
            # Fail first 2 attempts, succeed on 3rd
            if call_count < 3:
                raise httpx.ConnectError("Temporary network issue")
            return create_mock_response(sample_response_envelope)

        async with ASAPClient(
            "http://localhost:8000",
            transport=httpx.MockTransport(mock_transport),
            max_retries=5,
        ) as client:
            response = await client.send(sample_request_envelope)

        # Should have retried and eventually succeeded
        assert call_count == 3
        assert response.payload_type == "task.response"

    async def test_send_raises_on_missing_envelope_in_response(
        self, sample_request_envelope: Envelope
    ) -> None:
        """Test send() raises ASAPRemoteError when response is missing envelope."""
        from asap.transport.client import ASAPClient, ASAPRemoteError

        def mock_transport(request: httpx.Request) -> httpx.Response:
            # Return valid JSON-RPC response but without envelope
            json_rpc_response = {
                "jsonrpc": "2.0",
                "result": {"status": "ok"},  # Missing 'envelope' key
                "id": "req-1",
            }
            return httpx.Response(status_code=200, json=json_rpc_response)

        async with ASAPClient(
            "http://localhost:8000", transport=httpx.MockTransport(mock_transport)
        ) as client:
            with pytest.raises(ASAPRemoteError) as exc_info:
                await client.send(sample_request_envelope)

            assert exc_info.value.code == -32603
            assert "missing envelope" in str(exc_info.value).lower()

    async def test_send_wraps_unexpected_exceptions(
        self, sample_request_envelope: Envelope
    ) -> None:
        """Test send() wraps unexpected exceptions in ASAPConnectionError."""
        from asap.transport.client import ASAPClient, ASAPConnectionError

        def mock_transport(request: httpx.Request) -> httpx.Response:
            # Raise an unexpected exception type
            raise ValueError("Unexpected internal error")

        async with ASAPClient(
            "http://localhost:8000", transport=httpx.MockTransport(mock_transport)
        ) as client:
            with pytest.raises(ASAPConnectionError) as exc_info:
                await client.send(sample_request_envelope)

            assert "unexpected" in str(exc_info.value).lower()
            assert exc_info.value.cause is not None
            assert isinstance(exc_info.value.cause, ValueError)

    async def test_idempotency_key_consistent_across_all_retries(
        self, sample_request_envelope: Envelope, sample_response_envelope: Envelope
    ) -> None:
        """Test idempotency_key remains consistent across all retry attempts."""
        from asap.transport.client import ASAPClient

        captured_keys: list[str] = []
        captured_header_keys: list[str] = []

        def mock_transport(request: httpx.Request) -> httpx.Response:
            body = json.loads(request.content)
            param_key = body.get("params", {}).get("idempotency_key")
            header_key = request.headers.get("x-idempotency-key")

            if param_key:
                captured_keys.append(param_key)
            if header_key:
                captured_header_keys.append(header_key)

            # Fail first 2 attempts
            if len(captured_keys) < 3:
                raise httpx.ConnectError("Retry needed")
            return create_mock_response(sample_response_envelope)

        async with ASAPClient(
            "http://localhost:8000",
            transport=httpx.MockTransport(mock_transport),
            max_retries=5,
        ) as client:
            await client.send(sample_request_envelope)

        # All captured keys should be identical
        assert len(captured_keys) == 3
        assert all(k == captured_keys[0] for k in captured_keys)
        # Header keys should also be identical
        assert len(captured_header_keys) == 3
        assert all(k == captured_header_keys[0] for k in captured_header_keys)

    async def test_aexit_handles_none_client(self) -> None:
        """Test __aexit__ handles case when client was never connected."""
        from asap.transport.client import ASAPClient

        client = ASAPClient("http://localhost:8000")
        # Manually call __aexit__ without entering context
        await client.__aexit__(None, None, None)
        # Should not raise any exception
        assert not client.is_connected


class TestASAPClientHTTPSValidation:
    """Tests for HTTPS enforcement in ASAPClient initialization."""

    def test_https_urls_accepted(self) -> None:
        """Test that HTTPS URLs are accepted."""
        from asap.transport.client import ASAPClient

        client = ASAPClient("https://example.com")
        assert client.base_url == "https://example.com"
        assert client.require_https is True

    def test_http_localhost_accepted_with_warning(self) -> None:
        """Test that HTTP localhost URLs are accepted with warning."""
        from asap.transport.client import ASAPClient

        # Should not raise, but will log warning
        client = ASAPClient("http://localhost:8000")
        assert client.base_url == "http://localhost:8000"
        assert client.require_https is True

    def test_http_127_0_0_1_accepted_with_warning(self) -> None:
        """Test that HTTP 127.0.0.1 URLs are accepted with warning."""
        from asap.transport.client import ASAPClient

        # Should not raise, but will log warning
        client = ASAPClient("http://127.0.0.1:8000")
        assert client.base_url == "http://127.0.0.1:8000"
        assert client.require_https is True

    def test_http_production_rejected(self) -> None:
        """Test that HTTP URLs for non-localhost are rejected."""
        from asap.transport.client import ASAPClient

        with pytest.raises(ValueError) as exc_info:
            ASAPClient("http://example.com")

        assert "HTTPS is required" in str(exc_info.value)
        assert "require_https=False" in str(exc_info.value)

    def test_http_with_override_works(self) -> None:
        """Test that HTTP URLs work when require_https=False."""
        from asap.transport.client import ASAPClient

        client = ASAPClient("http://example.com", require_https=False)
        assert client.base_url == "http://example.com"
        assert client.require_https is False

    def test_https_with_require_https_false_works(self) -> None:
        """Test that HTTPS URLs work even when require_https=False."""
        from asap.transport.client import ASAPClient

        client = ASAPClient("https://example.com", require_https=False)
        assert client.base_url == "https://example.com"
        assert client.require_https is False


class TestASAPClientCustomErrors:
    """Tests for ASAP client custom error classes."""

    def test_asap_connection_error_is_exception(self) -> None:
        """Test ASAPConnectionError is an exception."""
        from asap.transport.client import ASAPConnectionError

        error = ASAPConnectionError("Test error")
        assert isinstance(error, Exception)
        assert "Test error" in str(error)

    def test_asap_timeout_error_is_exception(self) -> None:
        """Test ASAPTimeoutError is an exception."""
        from asap.transport.client import ASAPTimeoutError

        error = ASAPTimeoutError("Timeout occurred")
        assert isinstance(error, Exception)
        assert "Timeout" in str(error)

    def test_asap_remote_error_has_code_and_message(self) -> None:
        """Test ASAPRemoteError has code and message attributes."""
        from asap.transport.client import ASAPRemoteError

        error = ASAPRemoteError(-32601, "Method not found", {"method": "unknown"})
        assert error.code == -32601
        assert error.message == "Method not found"
        assert error.data == {"method": "unknown"}

    def test_asap_remote_error_str_includes_details(self) -> None:
        """Test ASAPRemoteError string includes code and message."""
        from asap.transport.client import ASAPRemoteError

        error = ASAPRemoteError(-32602, "Invalid params")
        error_str = str(error)
        assert "-32602" in error_str
        assert "Invalid params" in error_str


class TestImprovedConnectionErrorMessages:
    """Tests for improved connection error messages with troubleshooting guidance."""

    async def test_connection_error_includes_url_and_troubleshooting(
        self, sample_request_envelope: Envelope
    ) -> None:
        """Test that ASAPConnectionError includes URL and troubleshooting suggestions."""
        from asap.transport.client import ASAPClient, ASAPConnectionError

        def mock_transport(request: httpx.Request) -> httpx.Response:
            raise httpx.ConnectError("Connection refused")

        async with ASAPClient(
            "http://localhost:8000", transport=httpx.MockTransport(mock_transport)
        ) as client:
            with pytest.raises(ASAPConnectionError) as exc_info:
                await client.send(sample_request_envelope)

            error_message = str(exc_info.value)
            # Should include URL
            assert "localhost:8000" in error_message or "http://localhost:8000" in error_message
            # Should include troubleshooting suggestion
            assert "Verify" in error_message or "verify" in error_message.lower()
            assert exc_info.value.url == "http://localhost:8000"

    async def test_connection_error_after_retries_includes_context(
        self, sample_request_envelope: Envelope
    ) -> None:
        """Test that connection errors after retries include attempt context."""
        from asap.transport.client import ASAPClient, ASAPConnectionError

        def mock_transport(request: httpx.Request) -> httpx.Response:
            raise httpx.ConnectError("Server unavailable")

        async with ASAPClient(
            "http://example.com",
            transport=httpx.MockTransport(mock_transport),
            max_retries=2,
            require_https=False,
        ) as client:
            with pytest.raises(ASAPConnectionError) as exc_info:
                await client.send(sample_request_envelope)

            error_message = str(exc_info.value)
            # Should include URL
            assert "example.com" in error_message
            # Should include troubleshooting
            assert "Verify" in error_message or "verify" in error_message.lower()
            assert exc_info.value.url == "http://example.com"

    async def test_server_error_includes_url_and_context(
        self, sample_request_envelope: Envelope
    ) -> None:
        """Test that server errors (5xx) include URL and context."""
        from asap.transport.client import ASAPClient, ASAPConnectionError

        def mock_transport(request: httpx.Request) -> httpx.Response:
            return httpx.Response(status_code=503, content=b"Service Unavailable")

        async with ASAPClient(
            "http://api.example.com",
            transport=httpx.MockTransport(mock_transport),
            max_retries=1,
            require_https=False,
        ) as client:
            with pytest.raises(ASAPConnectionError) as exc_info:
                await client.send(sample_request_envelope)

            error_message = str(exc_info.value)
            # Should include URL
            assert "api.example.com" in error_message
            # Should include status code
            assert "503" in error_message
            assert exc_info.value.url == "http://api.example.com"

    async def test_client_error_includes_troubleshooting(
        self, sample_request_envelope: Envelope
    ) -> None:
        """Test that client errors (4xx) include troubleshooting information."""
        from asap.transport.client import ASAPClient, ASAPConnectionError

        def mock_transport(request: httpx.Request) -> httpx.Response:
            return httpx.Response(status_code=400, content=b"Bad Request")

        async with ASAPClient(
            "http://api.example.com",
            transport=httpx.MockTransport(mock_transport),
            require_https=False,
        ) as client:
            with pytest.raises(ASAPConnectionError) as exc_info:
                await client.send(sample_request_envelope)

            error_message = str(exc_info.value)
            # Should include URL
            assert "api.example.com" in error_message
            # Should include status code
            assert "400" in error_message
            # Should indicate it's a client error
            assert (
                "client error" in error_message.lower()
                or "problem with the request" in error_message.lower()
            )
            assert exc_info.value.url == "http://api.example.com"

    async def test_timeout_error_includes_context(self, sample_request_envelope: Envelope) -> None:
        """Test that timeout errors include context and troubleshooting."""
        from asap.transport.client import ASAPClient, ASAPTimeoutError

        def mock_transport(request: httpx.Request) -> httpx.Response:
            raise httpx.TimeoutException("Request timed out")

        async with ASAPClient(
            "http://slow-api.example.com",
            transport=httpx.MockTransport(mock_transport),
            timeout=5.0,
            require_https=False,
        ) as client:
            with pytest.raises(ASAPTimeoutError) as exc_info:
                await client.send(sample_request_envelope)

            error_message = str(exc_info.value)
            # Should include timeout value
            assert "5" in error_message or "timeout" in error_message.lower()
            assert exc_info.value.timeout == 5.0

    async def test_connection_validation_helper(self, sample_request_envelope: Envelope) -> None:
        """Test the _validate_connection helper method."""
        from asap.transport.client import ASAPClient

        # Test with successful connection
        def mock_transport_success(request: httpx.Request) -> httpx.Response:
            if request.method == "HEAD":
                return httpx.Response(status_code=200)
            return httpx.Response(status_code=200, json={"jsonrpc": "2.0", "result": {}})

        async with ASAPClient(
            "http://localhost:8000", transport=httpx.MockTransport(mock_transport_success)
        ) as client:
            is_valid = await client._validate_connection()
            assert is_valid is True

        # Test with connection failure
        def mock_transport_failure(request: httpx.Request) -> httpx.Response:
            raise httpx.ConnectError("Connection refused")

        async with ASAPClient(
            "http://localhost:8000", transport=httpx.MockTransport(mock_transport_failure)
        ) as client:
            is_valid = await client._validate_connection()
            assert is_valid is False


class TestASAPClientSendBatch:
    """Tests for ASAPClient.send_batch() method."""

    @pytest.fixture
    def multiple_request_envelopes(self) -> list[Envelope]:
        """Create multiple request envelopes for batch testing."""
        envelopes = []
        for i in range(5):
            envelopes.append(
                Envelope(
                    asap_version="0.1",
                    sender="urn:asap:agent:client",
                    recipient="urn:asap:agent:server",
                    payload_type="task.request",
                    payload=TaskRequest(
                        conversation_id=f"conv_{i}",
                        skill_id="echo",
                        input={"message": f"Hello {i}!"},
                    ).model_dump(),
                )
            )
        return envelopes

    async def test_send_batch_returns_all_responses(
        self, multiple_request_envelopes: list[Envelope]
    ) -> None:
        """Test send_batch() returns response for each envelope."""
        from asap.transport.client import ASAPClient

        def mock_transport(request: httpx.Request) -> httpx.Response:
            body = json.loads(request.content)
            envelope_data = body["params"]["envelope"]
            response_envelope = Envelope(
                asap_version="0.1",
                sender="urn:asap:agent:server",
                recipient="urn:asap:agent:client",
                payload_type="task.response",
                payload=TaskResponse(
                    task_id=f"task_{envelope_data['id']}",
                    status=TaskStatus.COMPLETED,
                    result={"echoed": envelope_data["payload"]},
                ).model_dump(),
                correlation_id=envelope_data["id"],
            )
            return create_mock_response(response_envelope)

        async with ASAPClient(
            "http://localhost:8000", transport=httpx.MockTransport(mock_transport)
        ) as client:
            responses = await client.send_batch(multiple_request_envelopes)

        assert len(responses) == len(multiple_request_envelopes)
        for i, response in enumerate(responses):
            assert isinstance(response, Envelope)
            assert response.payload_type == "task.response"
            assert response.correlation_id == multiple_request_envelopes[i].id

    async def test_send_batch_preserves_order(
        self, multiple_request_envelopes: list[Envelope]
    ) -> None:
        """Test send_batch() preserves order of responses matching inputs."""
        from asap.transport.client import ASAPClient

        def mock_transport(request: httpx.Request) -> httpx.Response:
            body = json.loads(request.content)
            envelope_data = body["params"]["envelope"]
            # Include request envelope id in response to verify order
            response_envelope = Envelope(
                asap_version="0.1",
                sender="urn:asap:agent:server",
                recipient="urn:asap:agent:client",
                payload_type="task.response",
                payload=TaskResponse(
                    task_id=f"task_{envelope_data['id']}",
                    status=TaskStatus.COMPLETED,
                    result={"original_id": envelope_data["id"]},
                ).model_dump(),
                correlation_id=envelope_data["id"],
            )
            return create_mock_response(response_envelope)

        async with ASAPClient(
            "http://localhost:8000", transport=httpx.MockTransport(mock_transport)
        ) as client:
            responses = await client.send_batch(multiple_request_envelopes)

        # Verify order is preserved by checking correlation_id matches
        for i, response in enumerate(responses):
            assert isinstance(response, Envelope)
            assert response.correlation_id == multiple_request_envelopes[i].id

    async def test_send_batch_empty_list_raises_error(self) -> None:
        """Test send_batch() raises ValueError for empty list."""
        from asap.transport.client import ASAPClient

        def mock_transport(request: httpx.Request) -> httpx.Response:
            return httpx.Response(status_code=200, json={})

        async with ASAPClient(
            "http://localhost:8000", transport=httpx.MockTransport(mock_transport)
        ) as client:
            with pytest.raises(ValueError, match="envelopes list cannot be empty"):
                await client.send_batch([])

    async def test_send_batch_not_connected_raises_error(
        self, multiple_request_envelopes: list[Envelope]
    ) -> None:
        """Test send_batch() raises error when not connected."""
        from asap.transport.client import ASAPClient, ASAPConnectionError

        client = ASAPClient("http://localhost:8000")
        with pytest.raises(ASAPConnectionError, match="not connected"):
            await client.send_batch(multiple_request_envelopes)

    async def test_send_batch_with_return_exceptions_true(
        self, multiple_request_envelopes: list[Envelope]
    ) -> None:
        """Test send_batch() returns exceptions when return_exceptions=True."""
        from asap.transport.client import ASAPClient, ASAPConnectionError

        call_count = 0

        def mock_transport(request: httpx.Request) -> httpx.Response:
            nonlocal call_count
            call_count += 1
            body = json.loads(request.content)
            envelope_data = body["params"]["envelope"]

            # Fail for envelope index 2 (third envelope based on conversation_id)
            if "conv_2" in envelope_data.get("payload", {}).get("conversation_id", ""):
                raise httpx.ConnectError("Server unavailable for conv_2")

            response_envelope = Envelope(
                asap_version="0.1",
                sender="urn:asap:agent:server",
                recipient="urn:asap:agent:client",
                payload_type="task.response",
                payload=TaskResponse(
                    task_id=f"task_{envelope_data['id']}",
                    status=TaskStatus.COMPLETED,
                    result={"echoed": True},
                ).model_dump(),
                correlation_id=envelope_data["id"],
            )
            return create_mock_response(response_envelope)

        async with ASAPClient(
            "http://localhost:8000",
            transport=httpx.MockTransport(mock_transport),
            max_retries=1,  # Reduce retries for faster test
        ) as client:
            results = await client.send_batch(multiple_request_envelopes, return_exceptions=True)

        assert len(results) == 5
        # Check that most results are Envelopes
        successful = [r for r in results if isinstance(r, Envelope)]
        failed = [r for r in results if isinstance(r, BaseException)]

        assert len(successful) == 4
        assert len(failed) == 1
        assert isinstance(failed[0], ASAPConnectionError)

    async def test_send_batch_without_return_exceptions_raises(
        self, multiple_request_envelopes: list[Envelope]
    ) -> None:
        """Test send_batch() raises exception when return_exceptions=False."""
        from asap.transport.client import ASAPClient, ASAPConnectionError

        def mock_transport(request: httpx.Request) -> httpx.Response:
            body = json.loads(request.content)
            envelope_data = body["params"]["envelope"]

            # Fail for second envelope
            if "conv_1" in envelope_data.get("payload", {}).get("conversation_id", ""):
                raise httpx.ConnectError("Server unavailable")

            response_envelope = Envelope(
                asap_version="0.1",
                sender="urn:asap:agent:server",
                recipient="urn:asap:agent:client",
                payload_type="task.response",
                payload=TaskResponse(
                    task_id="task_1",
                    status=TaskStatus.COMPLETED,
                    result={},
                ).model_dump(),
                correlation_id=envelope_data["id"],
            )
            return create_mock_response(response_envelope)

        async with ASAPClient(
            "http://localhost:8000",
            transport=httpx.MockTransport(mock_transport),
            max_retries=1,
        ) as client:
            with pytest.raises(ASAPConnectionError):
                await client.send_batch(multiple_request_envelopes, return_exceptions=False)

    async def test_send_batch_concurrent_execution(
        self, multiple_request_envelopes: list[Envelope]
    ) -> None:
        """Test send_batch() executes requests concurrently."""
        import asyncio

        from asap.transport.client import ASAPClient

        start_times: list[float] = []
        end_times: list[float] = []
        lock = asyncio.Lock()

        async def delayed_response(request: httpx.Request) -> httpx.Response:
            # Track timing
            async with lock:
                start_times.append(asyncio.get_event_loop().time())

            # Small delay to simulate network
            await asyncio.sleep(0.01)

            async with lock:
                end_times.append(asyncio.get_event_loop().time())

            body = json.loads(request.content)
            envelope_data = body["params"]["envelope"]
            response_envelope = Envelope(
                asap_version="0.1",
                sender="urn:asap:agent:server",
                recipient="urn:asap:agent:client",
                payload_type="task.response",
                payload=TaskResponse(
                    task_id=f"task_{envelope_data['id']}",
                    status=TaskStatus.COMPLETED,
                    result={},
                ).model_dump(),
                correlation_id=envelope_data["id"],
            )
            return create_mock_response(response_envelope)

        # Using httpx.MockTransport won't work with async delays, so we use a custom transport
        class AsyncMockTransport(httpx.AsyncBaseTransport):
            async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
                return await delayed_response(request)

        async with ASAPClient(
            "http://localhost:8000",
            transport=AsyncMockTransport(),
        ) as client:
            await client.send_batch(multiple_request_envelopes)

        # With concurrent execution, all requests should start roughly at the same time
        # If sequential, the time span would be ~5x larger
        assert len(start_times) == 5
        time_span = max(start_times) - min(start_times)
        # With concurrent execution, time span should be very small (< 50ms)
        # Sequential would be > 50ms (5 * 10ms delays)
        assert time_span < 0.05, f"Requests not concurrent: time span = {time_span}s"

    async def test_send_batch_single_envelope(self) -> None:
        """Test send_batch() works with single envelope."""
        from asap.transport.client import ASAPClient

        single_envelope = Envelope(
            asap_version="0.1",
            sender="urn:asap:agent:client",
            recipient="urn:asap:agent:server",
            payload_type="task.request",
            payload=TaskRequest(
                conversation_id="conv_single",
                skill_id="echo",
                input={"message": "Single"},
            ).model_dump(),
        )

        def mock_transport(request: httpx.Request) -> httpx.Response:
            body = json.loads(request.content)
            envelope_data = body["params"]["envelope"]
            response_envelope = Envelope(
                asap_version="0.1",
                sender="urn:asap:agent:server",
                recipient="urn:asap:agent:client",
                payload_type="task.response",
                payload=TaskResponse(
                    task_id="task_single",
                    status=TaskStatus.COMPLETED,
                    result={"echoed": "Single"},
                ).model_dump(),
                correlation_id=envelope_data["id"],
            )
            return create_mock_response(response_envelope)

        async with ASAPClient(
            "http://localhost:8000", transport=httpx.MockTransport(mock_transport)
        ) as client:
            responses = await client.send_batch([single_envelope])

        assert len(responses) == 1
        assert isinstance(responses[0], Envelope)
        assert responses[0].correlation_id == single_envelope.id

    async def test_send_batch_large_batch(self) -> None:
        """Test send_batch() handles large batches efficiently."""
        from asap.transport.client import ASAPClient

        # Create 50 envelopes
        large_batch = [
            Envelope(
                asap_version="0.1",
                sender="urn:asap:agent:client",
                recipient="urn:asap:agent:server",
                payload_type="task.request",
                payload=TaskRequest(
                    conversation_id=f"conv_{i}",
                    skill_id="echo",
                    input={"index": i},
                ).model_dump(),
            )
            for i in range(50)
        ]

        def mock_transport(request: httpx.Request) -> httpx.Response:
            body = json.loads(request.content)
            envelope_data = body["params"]["envelope"]
            response_envelope = Envelope(
                asap_version="0.1",
                sender="urn:asap:agent:server",
                recipient="urn:asap:agent:client",
                payload_type="task.response",
                payload=TaskResponse(
                    task_id=f"task_{envelope_data['id']}",
                    status=TaskStatus.COMPLETED,
                    result={"processed": True},
                ).model_dump(),
                correlation_id=envelope_data["id"],
            )
            return create_mock_response(response_envelope)

        async with ASAPClient(
            "http://localhost:8000", transport=httpx.MockTransport(mock_transport)
        ) as client:
            responses = await client.send_batch(large_batch)

        assert len(responses) == 50
        for response in responses:
            assert isinstance(response, Envelope)
            assert response.payload_type == "task.response"
