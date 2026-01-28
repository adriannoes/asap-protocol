from datetime import datetime, timezone, timedelta
from unittest.mock import patch

import httpx
import pytest

from asap.models.enums import TaskStatus
from asap.models.envelope import Envelope
from asap.models.payloads import TaskRequest, TaskResponse
from asap.transport.client import ASAPClient, RetryConfig, ASAPConnectionError, ASAPTimeoutError
from asap.transport.circuit_breaker import get_registry


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
