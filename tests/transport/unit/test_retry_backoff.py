"""Unit tests for exponential backoff retry logic in ASAP client.

This module tests the exponential backoff implementation in isolation,
verifying delay calculations, jitter application, and max delay capping.
"""

import asyncio
from typing import TYPE_CHECKING
from unittest.mock import patch

import httpx
import pytest

from asap.models.constants import DEFAULT_BASE_DELAY, DEFAULT_MAX_DELAY
from asap.models.envelope import Envelope
from asap.models.payloads import TaskRequest, TaskResponse
from asap.models.enums import TaskStatus
from asap.transport.client import ASAPClient

if TYPE_CHECKING:
    pass


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


class TestBackoffCalculation:
    """Tests for backoff delay calculation."""

    def test_backoff_increases_exponentially(self) -> None:
        """Test that backoff delays increase exponentially (1s, 2s, 4s, 8s...)."""
        client = ASAPClient("http://localhost:8000", base_delay=1.0, jitter=False)

        # Test exponential progression: base_delay * (2 ** attempt)
        assert client._calculate_backoff(0) == 1.0  # 1 * 2^0 = 1
        assert client._calculate_backoff(1) == 2.0  # 1 * 2^1 = 2
        assert client._calculate_backoff(2) == 4.0  # 1 * 2^2 = 4
        assert client._calculate_backoff(3) == 8.0  # 1 * 2^3 = 8
        assert client._calculate_backoff(4) == 16.0  # 1 * 2^4 = 16

    def test_backoff_respects_max_delay(self) -> None:
        """Test that backoff delays are capped at max_delay."""
        client = ASAPClient("http://localhost:8000", base_delay=1.0, max_delay=60.0, jitter=False)

        # Test that delays beyond max_delay are capped
        assert client._calculate_backoff(0) == 1.0  # 1 * 2^0 = 1
        assert client._calculate_backoff(5) == 32.0  # 1 * 2^5 = 32
        assert client._calculate_backoff(6) == 60.0  # 1 * 2^6 = 64, capped at 60
        assert client._calculate_backoff(10) == 60.0  # Still capped at 60

    def test_backoff_with_custom_base_delay(self) -> None:
        """Test backoff calculation with custom base_delay."""
        client = ASAPClient("http://localhost:8000", base_delay=0.5, jitter=False)

        assert client._calculate_backoff(0) == 0.5  # 0.5 * 2^0 = 0.5
        assert client._calculate_backoff(1) == 1.0  # 0.5 * 2^1 = 1.0
        assert client._calculate_backoff(2) == 2.0  # 0.5 * 2^2 = 2.0

    def test_backoff_with_jitter(self) -> None:
        """Test that jitter is applied correctly (random component)."""
        client = ASAPClient("http://localhost:8000", base_delay=1.0, jitter=True)

        # Calculate backoff multiple times and verify jitter is applied
        delays = [client._calculate_backoff(1) for _ in range(100)]

        # All delays should be >= base delay (2.0) and <= base delay + 10% jitter
        base_delay = 2.0
        max_jitter = base_delay * 0.1
        for delay in delays:
            assert base_delay <= delay <= base_delay + max_jitter

        # Verify that delays vary (not all the same)
        assert len(set(delays)) > 1, "Jitter should produce varying delays"

    def test_backoff_without_jitter(self) -> None:
        """Test that backoff without jitter produces deterministic delays."""
        client = ASAPClient("http://localhost:8000", base_delay=1.0, jitter=False)

        # Calculate backoff multiple times - should be identical
        delays = [client._calculate_backoff(2) for _ in range(10)]
        assert all(delay == 4.0 for delay in delays), "Without jitter, delays should be identical"


class TestBackoffInRetryLoop:
    """Tests for backoff behavior in actual retry scenarios."""

    @pytest.fixture
    def sample_request_envelope(self) -> Envelope:
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
    def sample_response_envelope(self, sample_request_envelope: Envelope) -> Envelope:
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

    async def test_backoff_applied_for_5xx_errors(
        self, sample_request_envelope: Envelope
    ) -> None:
        """Test that backoff is applied when retrying 5xx server errors."""
        call_count = 0
        delays: list[float] = []

        def mock_transport(request: httpx.Request) -> httpx.Response:
            nonlocal call_count
            call_count += 1
            # Return 503 for first 2 attempts, then success
            if call_count <= 2:
                return httpx.Response(status_code=503, content=b"Service Unavailable")
            return create_mock_response(
                Envelope(
                    asap_version="0.1",
                    sender="urn:asap:agent:server",
                    recipient="urn:asap:agent:client",
                    payload_type="task.response",
                    payload=TaskResponse(
                        task_id="task_456",
                        status=TaskStatus.COMPLETED,
                        result={},
                    ).model_dump(),
                    correlation_id=sample_request_envelope.id,
                )
            )

        # Mock asyncio.sleep to capture delays
        with patch("asap.transport.client.asyncio.sleep") as mock_sleep:
            async def sleep_capture(delay: float) -> None:
                delays.append(delay)
                # Don't actually sleep, just capture the delay

            mock_sleep.side_effect = sleep_capture

            async with ASAPClient(
                "http://localhost:8000",
                transport=httpx.MockTransport(mock_transport),
                base_delay=0.1,  # Short delay for testing
                max_delay=1.0,
                jitter=False,
                max_retries=3,
            ) as client:
                response = await client.send(sample_request_envelope)
                assert response.payload_type == "task.response"

        # Should have retried twice (attempts 0 and 1)
        assert call_count == 3  # 2 failures + 1 success
        assert len(delays) == 2  # Backoff applied twice
        # First retry: base_delay * 2^0 = 0.1
        # Second retry: base_delay * 2^1 = 0.2
        assert delays[0] == pytest.approx(0.1, abs=0.01)
        assert delays[1] == pytest.approx(0.2, abs=0.01)

    async def test_no_backoff_for_4xx_errors(
        self, sample_request_envelope: Envelope
    ) -> None:
        """Test that backoff is NOT applied for 4xx client errors."""
        call_count = 0

        def mock_transport(request: httpx.Request) -> httpx.Response:
            nonlocal call_count
            call_count += 1
            # Always return 400 Bad Request
            return httpx.Response(status_code=400, content=b"Bad Request")

        delays: list[float] = []

        # Mock asyncio.sleep to capture delays
        with patch("asyncio.sleep") as mock_sleep:
            async def sleep_capture(delay: float) -> None:
                delays.append(delay)

            mock_sleep.side_effect = sleep_capture

            async with ASAPClient(
                "http://localhost:8000",
                transport=httpx.MockTransport(mock_transport),
                base_delay=0.1,
                max_retries=3,
            ) as client:
                with pytest.raises(Exception):  # Will be ASAPConnectionError
                    await client.send(sample_request_envelope)

        # Should have attempted once (4xx errors are not retriable)
        assert call_count == 1
        # No backoff should be applied for 4xx errors
        assert len(delays) == 0

    async def test_retry_after_header_respected(
        self, sample_request_envelope: Envelope
    ) -> None:
        """Test that Retry-After header is respected for 429 responses."""
        call_count = 0
        delays: list[float] = []

        def mock_transport(request: httpx.Request) -> httpx.Response:
            nonlocal call_count
            call_count += 1
            # Return 429 with Retry-After header for first attempt, then success
            if call_count == 1:
                return httpx.Response(
                    status_code=429,
                    content=b"Rate Limited",
                    headers={"Retry-After": "2.5"},
                )
            return create_mock_response(
                Envelope(
                    asap_version="0.1",
                    sender="urn:asap:agent:server",
                    recipient="urn:asap:agent:client",
                    payload_type="task.response",
                    payload=TaskResponse(
                        task_id="task_456",
                        status=TaskStatus.COMPLETED,
                        result={},
                    ).model_dump(),
                    correlation_id=sample_request_envelope.id,
                )
            )

        # Mock asyncio.sleep to capture delays
        with patch("asap.transport.client.asyncio.sleep") as mock_sleep:
            async def sleep_capture(delay: float) -> None:
                delays.append(delay)
                # Don't actually sleep, just capture the delay

            mock_sleep.side_effect = sleep_capture

            async with ASAPClient(
                "http://localhost:8000",
                transport=httpx.MockTransport(mock_transport),
                base_delay=1.0,  # This would normally be used, but Retry-After should override
                max_delay=60.0,
                jitter=False,
                max_retries=3,
            ) as client:
                response = await client.send(sample_request_envelope)
                assert response.payload_type == "task.response"

        # Should have retried once
        assert call_count == 2  # 1 failure + 1 success
        assert len(delays) == 1
        # Should use Retry-After value (2.5) instead of calculated backoff
        assert delays[0] == pytest.approx(2.5, abs=0.01)

    async def test_retry_after_header_invalid_falls_back_to_backoff(
        self, sample_request_envelope: Envelope
    ) -> None:
        """Test that invalid Retry-After header falls back to calculated backoff."""
        call_count = 0
        delays: list[float] = []

        def mock_transport(request: httpx.Request) -> httpx.Response:
            nonlocal call_count
            call_count += 1
            # Return 429 with invalid Retry-After header (HTTP date format)
            if call_count == 1:
                return httpx.Response(
                    status_code=429,
                    content=b"Rate Limited",
                    headers={"Retry-After": "Wed, 21 Oct 2015 07:28:00 GMT"},  # HTTP date
                )
            return create_mock_response(
                Envelope(
                    asap_version="0.1",
                    sender="urn:asap:agent:server",
                    recipient="urn:asap:agent:client",
                    payload_type="task.response",
                    payload=TaskResponse(
                        task_id="task_456",
                        status=TaskStatus.COMPLETED,
                        result={},
                    ).model_dump(),
                    correlation_id=sample_request_envelope.id,
                )
            )

        # Mock asyncio.sleep to capture delays
        with patch("asap.transport.client.asyncio.sleep") as mock_sleep:
            async def sleep_capture(delay: float) -> None:
                delays.append(delay)
                # Don't actually sleep, just capture the delay

            mock_sleep.side_effect = sleep_capture

            async with ASAPClient(
                "http://localhost:8000",
                transport=httpx.MockTransport(mock_transport),
                base_delay=0.5,
                max_delay=60.0,
                jitter=False,
                max_retries=3,
            ) as client:
                response = await client.send(sample_request_envelope)
                assert response.payload_type == "task.response"

        # Should have retried once
        assert call_count == 2  # 1 failure + 1 success
        assert len(delays) == 1
        # Should fall back to calculated backoff (0.5 * 2^0 = 0.5)
        assert delays[0] == pytest.approx(0.5, abs=0.01)

    async def test_backoff_for_connection_errors(
        self, sample_request_envelope: Envelope
    ) -> None:
        """Test that backoff is applied when retrying connection errors."""
        call_count = 0
        delays: list[float] = []

        def mock_transport(request: httpx.Request) -> httpx.Response:
            nonlocal call_count
            call_count += 1
            # Raise connection error for first 2 attempts, then success
            if call_count <= 2:
                raise httpx.ConnectError("Connection failed")
            return create_mock_response(
                Envelope(
                    asap_version="0.1",
                    sender="urn:asap:agent:server",
                    recipient="urn:asap:agent:client",
                    payload_type="task.response",
                    payload=TaskResponse(
                        task_id="task_456",
                        status=TaskStatus.COMPLETED,
                        result={},
                    ).model_dump(),
                    correlation_id=sample_request_envelope.id,
                )
            )

        # Mock asyncio.sleep to capture delays
        with patch("asap.transport.client.asyncio.sleep") as mock_sleep:
            async def sleep_capture(delay: float) -> None:
                delays.append(delay)
                # Don't actually sleep, just capture the delay

            mock_sleep.side_effect = sleep_capture

            async with ASAPClient(
                "http://localhost:8000",
                transport=httpx.MockTransport(mock_transport),
                base_delay=0.1,
                max_delay=1.0,
                jitter=False,
                max_retries=3,
            ) as client:
                response = await client.send(sample_request_envelope)
                assert response.payload_type == "task.response"

        # Should have retried twice
        assert call_count == 3  # 2 failures + 1 success
        assert len(delays) == 2
        # First retry: base_delay * 2^0 = 0.1
        # Second retry: base_delay * 2^1 = 0.2
        assert delays[0] == pytest.approx(0.1, abs=0.01)
        assert delays[1] == pytest.approx(0.2, abs=0.01)

    async def test_backoff_pattern_1s_2s_4s_8s_with_jitter(
        self, sample_request_envelope: Envelope
    ) -> None:
        """Test local backoff pattern: 1s, 2s, 4s, 8s with jitter (Task 4.1.4).

        This test mocks a server that returns 503, sends a request, observes delays,
        and verifies the exponential pattern (1s, 2s, 4s, 8s) with jitter applied.
        """
        call_count = 0
        delays: list[float] = []

        def mock_transport(request: httpx.Request) -> httpx.Response:
            nonlocal call_count
            call_count += 1
            # Return 503 for first 4 attempts, then success
            if call_count <= 4:
                return httpx.Response(status_code=503, content=b"Service Unavailable")
            return create_mock_response(
                Envelope(
                    asap_version="0.1",
                    sender="urn:asap:agent:server",
                    recipient="urn:asap:agent:client",
                    payload_type="task.response",
                    payload=TaskResponse(
                        task_id="task_456",
                        status=TaskStatus.COMPLETED,
                        result={},
                    ).model_dump(),
                    correlation_id=sample_request_envelope.id,
                )
            )

        # Mock asyncio.sleep to capture delays
        with patch("asap.transport.client.asyncio.sleep") as mock_sleep:
            async def sleep_capture(delay: float) -> None:
                delays.append(delay)
                # Don't actually sleep, just capture the delay

            mock_sleep.side_effect = sleep_capture

            async with ASAPClient(
                "http://localhost:8000",
                transport=httpx.MockTransport(mock_transport),
                base_delay=1.0,  # 1 second base delay
                max_delay=60.0,
                jitter=True,  # Enable jitter
                max_retries=5,  # Allow 4 retries (attempts 0-3)
            ) as client:
                response = await client.send(sample_request_envelope)
                assert response.payload_type == "task.response"

        # Should have retried 4 times (attempts 0, 1, 2, 3)
        assert call_count == 5  # 4 failures + 1 success
        assert len(delays) == 4  # Backoff applied 4 times

        # Verify exponential pattern: 1s, 2s, 4s, 8s (with jitter)
        # Base delays: 1.0 * 2^0 = 1.0, 1.0 * 2^1 = 2.0, 1.0 * 2^2 = 4.0, 1.0 * 2^3 = 8.0
        # With jitter: each delay should be base + (0 to 10% of base)
        base_delays = [1.0, 2.0, 4.0, 8.0]

        for i, delay in enumerate(delays):
            base = base_delays[i]
            max_jitter = base * 0.1
            # Delay should be between base and base + max_jitter
            assert base <= delay <= base + max_jitter, (
                f"Delay {delay} for attempt {i} should be between {base} and {base + max_jitter}"
            )
            # Verify it's close to expected base (within jitter range)
            assert delay == pytest.approx(base, abs=max_jitter + 0.01), (
                f"Delay {delay} for attempt {i} should be approximately {base} (with jitter)"
            )

    async def test_backoff_pattern_1s_2s_4s_8s_without_jitter(
        self, sample_request_envelope: Envelope
    ) -> None:
        """Test local backoff pattern: 1s, 2s, 4s, 8s without jitter (Task 4.1.4).

        This test verifies the exact exponential pattern without jitter for precise timing.
        """
        call_count = 0
        delays: list[float] = []

        def mock_transport(request: httpx.Request) -> httpx.Response:
            nonlocal call_count
            call_count += 1
            # Return 503 for first 4 attempts, then success
            if call_count <= 4:
                return httpx.Response(status_code=503, content=b"Service Unavailable")
            return create_mock_response(
                Envelope(
                    asap_version="0.1",
                    sender="urn:asap:agent:server",
                    recipient="urn:asap:agent:client",
                    payload_type="task.response",
                    payload=TaskResponse(
                        task_id="task_456",
                        status=TaskStatus.COMPLETED,
                        result={},
                    ).model_dump(),
                    correlation_id=sample_request_envelope.id,
                )
            )

        # Mock asyncio.sleep to capture delays
        with patch("asap.transport.client.asyncio.sleep") as mock_sleep:
            async def sleep_capture(delay: float) -> None:
                delays.append(delay)

            mock_sleep.side_effect = sleep_capture

            async with ASAPClient(
                "http://localhost:8000",
                transport=httpx.MockTransport(mock_transport),
                base_delay=1.0,  # 1 second base delay
                max_delay=60.0,
                jitter=False,  # Disable jitter for exact pattern
                max_retries=5,  # Allow 4 retries (attempts 0-3)
            ) as client:
                response = await client.send(sample_request_envelope)
                assert response.payload_type == "task.response"

        # Should have retried 4 times
        assert call_count == 5  # 4 failures + 1 success
        assert len(delays) == 4

        # Verify exact exponential pattern: 1s, 2s, 4s, 8s
        expected_delays = [1.0, 2.0, 4.0, 8.0]
        for i, delay in enumerate(delays):
            assert delay == pytest.approx(expected_delays[i], abs=0.01), (
                f"Delay {delay} for attempt {i} should be exactly {expected_delays[i]}s"
            )
