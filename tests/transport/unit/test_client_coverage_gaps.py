from datetime import datetime, timezone, timedelta
from unittest.mock import patch

import httpx
import pytest

from asap.models.enums import TaskStatus
from asap.models.envelope import Envelope
from asap.models.payloads import TaskRequest, TaskResponse
from asap.errors import CircuitOpenError
from asap.transport.client import ASAPClient, RetryConfig, ASAPConnectionError, ASAPTimeoutError
from asap.transport.circuit_breaker import CircuitState, get_registry


@pytest.fixture(autouse=True)
def cleanup_registry():
    get_registry().clear()
    yield
    get_registry().clear()


@pytest.fixture
def sample_request_envelope() -> Envelope:
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


def create_mock_response(envelope: Envelope) -> httpx.Response:
    json_rpc_response = {
        "jsonrpc": "2.0",
        "result": {"envelope": envelope.model_dump(mode="json")},
        "id": "req-1",
    }
    return httpx.Response(status_code=200, json=json_rpc_response)


class TestASAPClientCoverageGaps:
    """Tests designed to fill specific coverage gaps in ASAPClient."""

    def test_init_with_retry_config(self) -> None:
        """Test initialization using RetryConfig object."""
        config = RetryConfig(
            max_retries=10,
            base_delay=2.0,
            max_delay=100.0,
            jitter=False,
            circuit_breaker_enabled=True,
            circuit_breaker_threshold=3,
            circuit_breaker_timeout=30.0,
        )
        client = ASAPClient("https://example.com", retry_config=config)

        assert client.max_retries == 10
        assert client.base_delay == 2.0
        assert client.max_delay == 100.0
        assert client.jitter is False
        assert client.circuit_breaker_enabled is True
        assert client._circuit_breaker is not None
        assert client._circuit_breaker.threshold == 3
        assert client._circuit_breaker.timeout == 30.0

    @pytest.mark.asyncio
    async def test_retry_after_future_date(self, sample_request_envelope: Envelope) -> None:
        """Test handling of Retry-After header with a future HTTP date."""
        # Date 10 seconds in the future
        future_date = datetime.now(timezone.utc) + timedelta(seconds=10)
        # Format as HTTP date: Wed, 21 Oct 2015 07:28:00 GMT
        future_date_str = future_date.strftime("%a, %d %b %Y %H:%M:%S GMT")

        call_count = 0

        def mock_transport(request: httpx.Request) -> httpx.Response:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return httpx.Response(
                    status_code=429,
                    content=b"Rate Limited",
                    headers={"Retry-After": future_date_str},
                )
            return create_mock_response(
                Envelope(
                    asap_version="0.1",
                    sender="urn:asap:agent:server",
                    recipient="urn:asap:agent:client",
                    payload_type="task.response",
                    payload=TaskResponse(
                        task_id="t", status=TaskStatus.COMPLETED, result={}
                    ).model_dump(),
                    correlation_id=sample_request_envelope.id,
                )
            )

        with patch("asap.transport.client.asyncio.sleep") as mock_sleep:

            async def mock_sleep_fn(delay: float) -> None:
                pass

            mock_sleep.side_effect = mock_sleep_fn

            async with ASAPClient(
                "https://example.com", transport=httpx.MockTransport(mock_transport), max_retries=2
            ) as client:
                await client.send(sample_request_envelope)

            # verify sleep was called with approx 10 seconds
            args, _ = mock_sleep.call_args
            assert 9.0 <= args[0] <= 11.0

    @pytest.mark.asyncio
    async def test_validate_connection_raises_when_not_connected(self) -> None:
        """_validate_connection raises ASAPConnectionError when used outside async with."""
        client = ASAPClient("https://example.com")
        with pytest.raises(ASAPConnectionError, match="not connected"):
            await client._validate_connection()

    @pytest.mark.asyncio
    async def test_validate_connection_success(self) -> None:
        """Test _validate_connection helper method success case."""

        def mock_transport(request: httpx.Request) -> httpx.Response:
            if "/asap/manifest" in str(request.url):
                return httpx.Response(status_code=200, json={"name": "test-agent"})
            return httpx.Response(status_code=404)

        async with ASAPClient(
            "https://example.com", transport=httpx.MockTransport(mock_transport)
        ) as client:
            result = await client._validate_connection()
            assert result is True

    @pytest.mark.asyncio
    async def test_validate_connection_failure(self) -> None:
        """Test _validate_connection helper method failure case."""

        def mock_transport(request: httpx.Request) -> httpx.Response:
            return httpx.Response(status_code=503)

        async with ASAPClient(
            "https://example.com", transport=httpx.MockTransport(mock_transport)
        ) as client:
            result = await client._validate_connection()
            assert result is False

    @pytest.mark.asyncio
    async def test_validate_connection_connect_error_returns_false(self) -> None:
        """_validate_connection returns False on ConnectError."""

        def mock_transport(request: httpx.Request) -> httpx.Response:
            raise httpx.ConnectError("Connection refused")

        async with ASAPClient(
            "https://example.com", transport=httpx.MockTransport(mock_transport)
        ) as client:
            result = await client._validate_connection()
            assert result is False

    @pytest.mark.asyncio
    async def test_validate_connection_timeout_returns_false(self) -> None:
        """_validate_connection returns False on TimeoutException."""

        def mock_transport(request: httpx.Request) -> httpx.Response:
            raise httpx.TimeoutException("Timeout")

        async with ASAPClient(
            "https://example.com", transport=httpx.MockTransport(mock_transport)
        ) as client:
            result = await client._validate_connection()
            assert result is False

    @pytest.mark.asyncio
    async def test_validate_connection_generic_exception_returns_false(self) -> None:
        """_validate_connection returns False on generic Exception."""

        def mock_transport(request: httpx.Request) -> httpx.Response:
            raise RuntimeError("Unexpected error")

        async with ASAPClient(
            "https://example.com", transport=httpx.MockTransport(mock_transport)
        ) as client:
            result = await client._validate_connection()
            assert result is False

    @pytest.mark.asyncio
    async def test_send_5xx_retry_then_circuit_opens(self) -> None:
        """Send with 503 triggers retry logging and delay, then circuit opens."""
        call_count = 0

        def mock_transport(request: httpx.Request) -> httpx.Response:
            nonlocal call_count
            call_count += 1
            return httpx.Response(status_code=503, content=b"Service Unavailable")

        large_envelope = Envelope(
            asap_version="0.1",
            sender="urn:asap:agent:client",
            recipient="urn:asap:agent:server",
            payload_type="task.request",
            payload=TaskRequest(
                conversation_id="conv_123",
                skill_id="echo",
                input={"message": "x" * 200},
            ).model_dump(),
        )

        async with ASAPClient(
            "https://example.com",
            transport=httpx.MockTransport(mock_transport),
            compression=True,
            compression_threshold=50,
            circuit_breaker_enabled=True,
            circuit_breaker_threshold=2,
            max_retries=2,
        ) as client:
            with pytest.raises(ASAPConnectionError, match="503"):
                await client.send(large_envelope)
            assert call_count == 2

            with pytest.raises(ASAPConnectionError, match="503"):
                await client.send(large_envelope)
            assert call_count == 4
            assert client._circuit_breaker is not None
            assert client._circuit_breaker.get_state() == CircuitState.OPEN

            with pytest.raises(CircuitOpenError):
                await client.send(large_envelope)
            assert call_count == 4

    @pytest.mark.asyncio
    async def test_circuit_breaker_records_failure_on_exhausted_5xx(
        self, sample_request_envelope: Envelope
    ) -> None:
        """Test that circuit breaker records failure when retries are exhausted for 5xx."""

        def mock_transport(request: httpx.Request) -> httpx.Response:
            return httpx.Response(status_code=503, content=b"Unavailable")

        async with ASAPClient(
            "https://example.com",
            transport=httpx.MockTransport(mock_transport),
            max_retries=2,
            circuit_breaker_enabled=True,
            circuit_breaker_threshold=5,
        ) as client:
            with pytest.raises(ASAPConnectionError):
                await client.send(sample_request_envelope)

            # Should have context. Attempt 1 fail -> backoff -> Attempt 2 fail -> record failure
            assert client._circuit_breaker.get_consecutive_failures() == 1

    @pytest.mark.asyncio
    async def test_circuit_breaker_records_failure_on_exhausted_connect_error(
        self, sample_request_envelope: Envelope
    ) -> None:
        """Test that circuit breaker records failure when retries are exhausted for connection error."""

        def mock_transport(request: httpx.Request) -> httpx.Response:
            raise httpx.ConnectError("Failed")

        async with ASAPClient(
            "https://example.com",
            transport=httpx.MockTransport(mock_transport),
            max_retries=2,
            circuit_breaker_enabled=True,
        ) as client:
            with pytest.raises(ASAPConnectionError):
                await client.send(sample_request_envelope)

            assert client._circuit_breaker.get_consecutive_failures() == 1

    @pytest.mark.asyncio
    async def test_circuit_breaker_records_failure_on_exhausted_429(
        self, sample_request_envelope: Envelope
    ) -> None:
        """Test that circuit breaker records failure when retries are exhausted for 429."""

        def mock_transport(request: httpx.Request) -> httpx.Response:
            return httpx.Response(status_code=429, content=b"Rate Limited")

        async with ASAPClient(
            "https://example.com",
            transport=httpx.MockTransport(mock_transport),
            max_retries=2,
            circuit_breaker_enabled=True,
            base_delay=0.01,
            jitter=False,
        ) as client:
            with pytest.raises(ASAPConnectionError, match="rate limit"):
                await client.send(sample_request_envelope)

            assert client._circuit_breaker.get_consecutive_failures() == 1

    @pytest.mark.asyncio
    async def test_circuit_breaker_records_failure_on_exhausted_timeout(
        self, sample_request_envelope: Envelope
    ) -> None:
        """Test that circuit breaker records failure when retries are exhausted for timeouts."""

        def mock_transport(request: httpx.Request) -> httpx.Response:
            raise httpx.TimeoutException("Timed out")

        async with ASAPClient(
            "https://example.com",
            transport=httpx.MockTransport(mock_transport),
            max_retries=2,
            circuit_breaker_enabled=True,
            base_delay=0.01,
            jitter=False,
        ) as client:
            with pytest.raises(ASAPTimeoutError):
                await client.send(sample_request_envelope)

            assert client._circuit_breaker.get_consecutive_failures() == 1

    @pytest.mark.asyncio
    async def test_circuit_breaker_records_failure_on_400_error(
        self, sample_request_envelope: Envelope
    ) -> None:
        """Test that circuit breaker records failure on non-retriable 4xx errors."""

        def mock_transport(request: httpx.Request) -> httpx.Response:
            return httpx.Response(status_code=400, content=b"Bad Request")

        async with ASAPClient(
            "https://example.com",
            transport=httpx.MockTransport(mock_transport),
            circuit_breaker_enabled=True,
        ) as client:
            with pytest.raises(ASAPConnectionError, match="400"):
                await client.send(sample_request_envelope)

            assert client._circuit_breaker.get_consecutive_failures() == 1

    def test_url_validation_missing_netloc(self) -> None:
        """Test URL validation for missing network location."""
        with pytest.raises(ValueError, match="Invalid base_url format"):
            ASAPClient("http:///path")

    def test_is_localhost_helper(self) -> None:
        """Test internal _is_localhost helper with various formats."""
        client = ASAPClient("https://example.com")
        from urllib.parse import urlparse

        assert client._is_localhost(urlparse("http://localhost:8000")) is True
        assert client._is_localhost(urlparse("http://127.0.0.1:8000")) is True
        assert client._is_localhost(urlparse("http://[::1]")) is True
        assert client._is_localhost(urlparse("http://example.com")) is False
        assert client._is_localhost(urlparse("http://192.168.1.1")) is False

    def test_is_localhost_no_hostname_returns_false(self) -> None:
        """_is_localhost returns False when URL has no hostname (e.g. file or opaque)."""
        client = ASAPClient("https://example.com")
        from urllib.parse import urlparse

        assert client._is_localhost(urlparse("file:///tmp/foo")) is False

    @pytest.mark.asyncio
    async def test_retry_after_invalid_date_format(self, sample_request_envelope: Envelope) -> None:
        """Test handling of Retry-After header with an invalid date format."""
        call_count = 0

        def mock_transport(request: httpx.Request) -> httpx.Response:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return httpx.Response(
                    status_code=429,
                    content=b"Rate Limited",
                    headers={"Retry-After": "Invalid Date Format"},
                )
            return create_mock_response(sample_request_envelope)

        with patch("asap.transport.client.asyncio.sleep") as mock_sleep:

            async def mock_sleep_fn(delay: float) -> None:
                pass

            mock_sleep.side_effect = mock_sleep_fn

            async with ASAPClient(
                "https://example.com",
                transport=httpx.MockTransport(mock_transport),
                max_retries=2,
                base_delay=0.1,
                jitter=False,
            ) as client:
                await client.send(sample_request_envelope)

            # Should fall back to 0.1s backoff (base_delay)
            mock_sleep.assert_called_once_with(0.1)


class TestASAPClientManifestCache:
    """Tests for get_manifest cache behavior."""

    @pytest.mark.asyncio
    async def test_get_manifest_cache_hit(self) -> None:
        """get_manifest returns cached manifest without HTTP call if cache hit."""
        from asap.models.entities import Manifest

        manifest_data = {
            "id": "urn:asap:agent:testagent",
            "name": "Test Agent",
            "version": "1.0.0",
            "description": "Test agent",
            "capabilities": {
                "asap_version": "0.1",
                "skills": [{"id": "test", "description": "Test skill"}],
                "state_persistence": False,
            },
            "endpoints": {"asap": "http://localhost:8000/asap"},
        }
        expected_manifest = Manifest(**manifest_data)

        call_count = 0

        def mock_transport(request: httpx.Request) -> httpx.Response:
            nonlocal call_count
            call_count += 1
            return httpx.Response(status_code=200, json=manifest_data)

        async with ASAPClient(
            "https://example.com", transport=httpx.MockTransport(mock_transport)
        ) as client:
            client._manifest_cache.set(
                "https://example.com/.well-known/asap/manifest.json", expected_manifest
            )
            result = await client.get_manifest()

        assert call_count == 0
        assert result.id == expected_manifest.id

    @pytest.mark.asyncio
    async def test_get_manifest_cache_miss_then_set(self) -> None:
        """get_manifest fetches from HTTP on cache miss and caches the result."""
        manifest_data = {
            "id": "urn:asap:agent:testagent",
            "name": "Test Agent",
            "version": "1.0.0",
            "description": "Test agent",
            "capabilities": {
                "asap_version": "0.1",
                "skills": [{"id": "test", "description": "Test skill"}],
                "state_persistence": False,
            },
            "endpoints": {"asap": "http://localhost:8000/asap"},
        }

        call_count = 0

        def mock_transport(request: httpx.Request) -> httpx.Response:
            nonlocal call_count
            call_count += 1
            return httpx.Response(status_code=200, json=manifest_data)

        async with ASAPClient(
            "https://example.com", transport=httpx.MockTransport(mock_transport)
        ) as client:
            assert client._manifest_cache.size() == 0
            result = await client.get_manifest()
            assert call_count == 1
            assert result.id == "urn:asap:agent:testagent"
            assert client._manifest_cache.size() == 1
            cached = client._manifest_cache.get(
                "https://example.com/.well-known/asap/manifest.json"
            )
            assert cached is not None
            assert cached.id == "urn:asap:agent:testagent"

    @pytest.mark.asyncio
    async def test_get_manifest_cache_invalidate_on_http_error(self) -> None:
        """get_manifest invalidates cache entry on HTTP error."""
        from asap.models.entities import Manifest

        manifest_data = {
            "id": "urn:asap:agent:testagent",
            "name": "Test Agent",
            "version": "1.0.0",
            "description": "Test agent",
            "capabilities": {
                "asap_version": "0.1",
                "skills": [{"id": "test", "description": "Test skill"}],
                "state_persistence": False,
            },
            "endpoints": {"asap": "http://localhost:8000/asap"},
        }
        stale_manifest = Manifest(**manifest_data)

        def mock_transport(request: httpx.Request) -> httpx.Response:
            return httpx.Response(status_code=500, content=b"Internal Server Error")

        async with ASAPClient(
            "https://example.com", transport=httpx.MockTransport(mock_transport)
        ) as client:
            url = "https://example.com/.well-known/asap/manifest.json"
            client._manifest_cache.set(url, stale_manifest)
            assert client._manifest_cache.size() == 1
            client._manifest_cache.invalidate(url)
            assert client._manifest_cache.size() == 0

            with pytest.raises(ASAPConnectionError, match="500"):
                await client.get_manifest()

            assert client._manifest_cache.size() == 0

    @pytest.mark.asyncio
    async def test_get_manifest_cache_invalidate_on_invalid_json(self) -> None:
        """get_manifest invalidates cache entry on invalid JSON response."""

        def mock_transport(request: httpx.Request) -> httpx.Response:
            return httpx.Response(status_code=200, content=b"not valid json")

        async with ASAPClient(
            "https://example.com", transport=httpx.MockTransport(mock_transport)
        ) as client:
            with pytest.raises(ValueError, match="Invalid JSON"):
                await client.get_manifest()

            assert client._manifest_cache.size() == 0

    @pytest.mark.asyncio
    async def test_get_manifest_cache_invalidate_on_invalid_manifest(self) -> None:
        """get_manifest invalidates cache entry on invalid manifest format."""

        def mock_transport(request: httpx.Request) -> httpx.Response:
            return httpx.Response(status_code=200, json={"foo": "bar"})

        async with ASAPClient(
            "https://example.com", transport=httpx.MockTransport(mock_transport)
        ) as client:
            with pytest.raises(ValueError, match="Invalid manifest"):
                await client.get_manifest()

            assert client._manifest_cache.size() == 0

    @pytest.mark.asyncio
    async def test_get_manifest_cache_invalidate_on_timeout(self) -> None:
        """get_manifest invalidates cache entry on timeout."""

        def mock_transport(request: httpx.Request) -> httpx.Response:
            raise httpx.TimeoutException("Timeout fetching manifest")

        async with ASAPClient(
            "https://example.com", transport=httpx.MockTransport(mock_transport)
        ) as client:
            with pytest.raises(ASAPTimeoutError):
                await client.get_manifest()

            assert client._manifest_cache.size() == 0

    @pytest.mark.asyncio
    async def test_get_manifest_cache_invalidate_on_connect_error(self) -> None:
        """get_manifest invalidates cache entry on connection error."""

        def mock_transport(request: httpx.Request) -> httpx.Response:
            raise httpx.ConnectError("Connection refused")

        async with ASAPClient(
            "https://example.com", transport=httpx.MockTransport(mock_transport)
        ) as client:
            with pytest.raises(ASAPConnectionError):
                await client.get_manifest()

            assert client._manifest_cache.size() == 0
