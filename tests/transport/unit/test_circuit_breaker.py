"""Unit tests for circuit breaker pattern in ASAP client.

This module tests the circuit breaker implementation in isolation,
verifying state transitions, failure tracking, and thread-safety.
"""

import time
from typing import TYPE_CHECKING
from unittest.mock import patch

import httpx
import pytest

from asap.errors import CircuitOpenError
from asap.models.envelope import Envelope
from asap.models.payloads import TaskRequest, TaskResponse
from asap.models.enums import TaskStatus
from asap.transport.client import ASAPClient, CircuitBreaker, CircuitState

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


class TestCircuitBreakerBasic:
    """Tests for basic circuit breaker functionality."""

    def test_circuit_breaker_starts_closed(self) -> None:
        """Test circuit breaker starts in CLOSED state."""
        breaker = CircuitBreaker(threshold=5, timeout=60.0)
        assert breaker.get_state() == CircuitState.CLOSED
        assert breaker.get_consecutive_failures() == 0

    def test_circuit_breaker_opens_after_threshold_failures(self) -> None:
        """Test circuit breaker opens after threshold consecutive failures."""
        breaker = CircuitBreaker(threshold=5, timeout=60.0)

        # Record 4 failures (should still be closed)
        for _ in range(4):
            breaker.record_failure()
        assert breaker.get_state() == CircuitState.CLOSED
        assert breaker.get_consecutive_failures() == 4

        # Record 5th failure (should open)
        breaker.record_failure()
        assert breaker.get_state() == CircuitState.OPEN
        assert breaker.get_consecutive_failures() == 5

    def test_circuit_breaker_can_attempt_when_closed(self) -> None:
        """Test can_attempt() returns True when circuit is CLOSED."""
        breaker = CircuitBreaker(threshold=5, timeout=60.0)
        assert breaker.can_attempt() is True

    def test_circuit_breaker_cannot_attempt_when_open(self) -> None:
        """Test can_attempt() returns False when circuit is OPEN."""
        breaker = CircuitBreaker(threshold=5, timeout=60.0)

        # Open the circuit
        for _ in range(5):
            breaker.record_failure()

        assert breaker.get_state() == CircuitState.OPEN
        assert breaker.can_attempt() is False

    def test_circuit_breaker_resets_on_success(self) -> None:
        """Test circuit breaker resets failure count on success."""
        breaker = CircuitBreaker(threshold=5, timeout=60.0)

        # Record some failures
        for _ in range(3):
            breaker.record_failure()
        assert breaker.get_consecutive_failures() == 3

        # Record success
        breaker.record_success()
        assert breaker.get_consecutive_failures() == 0
        assert breaker.get_state() == CircuitState.CLOSED

    def test_circuit_breaker_closes_from_half_open_on_success(self) -> None:
        """Test circuit breaker closes from HALF_OPEN to CLOSED on success."""
        breaker = CircuitBreaker(threshold=5, timeout=0.1)  # Short timeout for testing

        # Open the circuit
        for _ in range(5):
            breaker.record_failure()
        assert breaker.get_state() == CircuitState.OPEN

        # Wait for timeout
        time.sleep(0.2)

        # Should transition to HALF_OPEN
        assert breaker.can_attempt() is True
        # State should be HALF_OPEN (checked via can_attempt allowing it)

        # Record success
        breaker.record_success()
        assert breaker.get_state() == CircuitState.CLOSED
        assert breaker.get_consecutive_failures() == 0


class TestCircuitBreakerTimeout:
    """Tests for circuit breaker timeout and HALF_OPEN state."""

    def test_circuit_breaker_transitions_to_half_open_after_timeout(self) -> None:
        """Test circuit breaker transitions OPEN -> HALF_OPEN after timeout."""
        breaker = CircuitBreaker(threshold=5, timeout=0.1)  # Short timeout for testing

        # Open the circuit
        for _ in range(5):
            breaker.record_failure()
        assert breaker.get_state() == CircuitState.OPEN
        assert breaker.can_attempt() is False

        # Wait for timeout
        time.sleep(0.2)

        # Should now allow attempts (HALF_OPEN state)
        assert breaker.can_attempt() is True

    def test_circuit_breaker_stays_open_before_timeout(self) -> None:
        """Test circuit breaker stays OPEN before timeout expires."""
        breaker = CircuitBreaker(threshold=5, timeout=60.0)

        # Open the circuit
        for _ in range(5):
            breaker.record_failure()
        assert breaker.get_state() == CircuitState.OPEN

        # Should not allow attempts immediately
        assert breaker.can_attempt() is False


class TestCircuitBreakerIntegration:
    """Tests for circuit breaker integration with ASAPClient."""

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

    async def test_circuit_breaker_disabled_by_default(
        self, sample_request_envelope: Envelope, sample_response_envelope: Envelope
    ) -> None:
        """Test circuit breaker is disabled by default."""
        def mock_transport(request: httpx.Request) -> httpx.Response:
            return create_mock_response(sample_response_envelope)

        async with ASAPClient(
            "http://localhost:8000", transport=httpx.MockTransport(mock_transport)
        ) as client:
            # Circuit breaker should be None when disabled
            assert client._circuit_breaker is None
            # Should work normally
            response = await client.send(sample_request_envelope)
            assert response.payload_type == "task.response"

    async def test_circuit_breaker_opens_after_5_failures(
        self, sample_request_envelope: Envelope
    ) -> None:
        """Test circuit breaker opens after 5 consecutive failures."""
        call_count = 0

        def mock_transport(request: httpx.Request) -> httpx.Response:
            nonlocal call_count
            call_count += 1
            # Always return 5xx error
            return httpx.Response(status_code=503, content=b"Service Unavailable")

        async with ASAPClient(
            "http://localhost:8000",
            transport=httpx.MockTransport(mock_transport),
            circuit_breaker_enabled=True,
            circuit_breaker_threshold=5,
            max_retries=1,  # Single attempt per request to count failures accurately
        ) as client:
            # Make 5 requests that fail
            for i in range(5):
                with pytest.raises(Exception):  # Will be ASAPConnectionError
                    await client.send(sample_request_envelope)

            # Circuit should be open
            assert client._circuit_breaker is not None
            assert client._circuit_breaker.get_state() == CircuitState.OPEN
            # Should have at least 5 consecutive failures (may be more if circuit was just opened)
            assert client._circuit_breaker.get_consecutive_failures() >= 5

            # Next request should fail immediately with CircuitOpenError
            with pytest.raises(CircuitOpenError) as exc_info:
                await client.send(sample_request_envelope)

            # consecutive_failures should be at least 5 (may be more if circuit was just opened)
            assert exc_info.value.consecutive_failures >= 5
            assert exc_info.value.base_url == "http://localhost:8000"

    async def test_circuit_breaker_allows_requests_when_closed(
        self, sample_request_envelope: Envelope, sample_response_envelope: Envelope
    ) -> None:
        """Test circuit breaker allows requests when circuit is CLOSED."""
        def mock_transport(request: httpx.Request) -> httpx.Response:
            return create_mock_response(sample_response_envelope)

        async with ASAPClient(
            "http://localhost:8000",
            transport=httpx.MockTransport(mock_transport),
            circuit_breaker_enabled=True,
            circuit_breaker_threshold=5,
        ) as client:
            # Should work normally
            response = await client.send(sample_request_envelope)
            assert response.payload_type == "task.response"

            # Circuit should still be closed
            assert client._circuit_breaker is not None
            assert client._circuit_breaker.get_state() == CircuitState.CLOSED

    async def test_circuit_breaker_closes_after_success_in_half_open(
        self, sample_request_envelope: Envelope, sample_response_envelope: Envelope
    ) -> None:
        """Test circuit breaker closes after success when in HALF_OPEN state."""
        http_call_count = 0
        should_succeed = False

        def mock_transport(request: httpx.Request) -> httpx.Response:
            nonlocal http_call_count, should_succeed
            http_call_count += 1
            # After 5 failed requests and timeout, next call should succeed
            if should_succeed:
                return create_mock_response(sample_response_envelope)
            return httpx.Response(status_code=503, content=b"Service Unavailable")

        async with ASAPClient(
            "http://localhost:8000",
            transport=httpx.MockTransport(mock_transport),
            circuit_breaker_enabled=True,
            circuit_breaker_threshold=5,
            circuit_breaker_timeout=0.1,  # Short timeout for testing
            max_retries=1,  # Single attempt per request
        ) as client:
            # Make 5 requests that fail to open circuit
            for _ in range(5):
                with pytest.raises(Exception):
                    await client.send(sample_request_envelope)

            # Circuit should be open
            assert client._circuit_breaker is not None
            assert client._circuit_breaker.get_state() == CircuitState.OPEN

            # Wait for timeout to transition to HALF_OPEN
            time.sleep(0.2)

            # Verify circuit is in HALF_OPEN (can_attempt should return True)
            assert client._circuit_breaker.can_attempt() is True

            # Enable success for next request
            should_succeed = True

            # Next request should succeed and close circuit
            response = await client.send(sample_request_envelope)
            assert response.payload_type == "task.response"
            assert client._circuit_breaker.get_state() == CircuitState.CLOSED
            assert client._circuit_breaker.get_consecutive_failures() == 0


class TestCircuitBreakerThreadSafety:
    """Tests for circuit breaker thread-safety."""

    def test_circuit_breaker_thread_safe_state_transitions(self) -> None:
        """Test circuit breaker state transitions are thread-safe."""
        import threading

        breaker = CircuitBreaker(threshold=5, timeout=60.0)
        failures_recorded = 0
        lock = threading.Lock()

        def record_failure() -> None:
            nonlocal failures_recorded
            breaker.record_failure()
            with lock:
                failures_recorded += 1

        # Create multiple threads that record failures concurrently
        threads = []
        for _ in range(10):
            thread = threading.Thread(target=record_failure)
            threads.append(thread)
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join()

        # Should have recorded all failures correctly
        assert failures_recorded == 10
        # Circuit should be open (threshold is 5)
        assert breaker.get_state() == CircuitState.OPEN
        assert breaker.get_consecutive_failures() == 10

    def test_circuit_breaker_thread_safe_concurrent_checks(self) -> None:
        """Test circuit breaker can_attempt() is thread-safe."""
        import threading

        breaker = CircuitBreaker(threshold=5, timeout=60.0)

        # Open the circuit
        for _ in range(5):
            breaker.record_failure()

        results: list[bool] = []
        lock = threading.Lock()

        def check_attempt() -> None:
            result = breaker.can_attempt()
            with lock:
                results.append(result)

        # Create multiple threads that check can_attempt concurrently
        threads = []
        for _ in range(10):
            thread = threading.Thread(target=check_attempt)
            threads.append(thread)
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join()

        # All results should be False (circuit is open)
        assert len(results) == 10
        assert all(result is False for result in results)
