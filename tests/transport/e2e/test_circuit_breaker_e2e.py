"""End-to-end tests for circuit breaker in ASAP client.

This module tests the circuit breaker behavior when a remote agent
becomes unavailable and then recovers.
"""

import asyncio

import httpx
import pytest

from asap.errors import CircuitOpenError
from asap.models.envelope import Envelope
from asap.models.payloads import TaskRequest
from asap.transport.circuit_breaker import CircuitState, get_registry
from asap.transport.client import ASAPClient, ASAPConnectionError


@pytest.fixture(autouse=True)
def cleanup_circuit_breaker_registry():
    """Ensure circuit breaker registry is clean for each test."""
    get_registry().clear()
    yield
    get_registry().clear()


@pytest.fixture
def sample_request_envelope() -> Envelope:
    """Create a sample request envelope."""
    return Envelope(
        asap_version="1.0.0",
        sender="urn:asap:agent:caller",
        recipient="urn:asap:agent:remote-service",
        payload_type="task.request",
        payload=TaskRequest(
            conversation_id="conv-e2e-circuit",
            skill_id="echo",
            input={"message": "ping"},
        ).model_dump(),
    )


def create_success_response(request_envelope: Envelope) -> dict:
    """Create a successful JSON-RPC response."""
    return {
        "jsonrpc": "2.0",
        "result": {
            "envelope": {
                "asap_version": "1.0.0",
                "id": "resp-001",
                "sender": "urn:asap:agent:remote-service",
                "recipient": request_envelope.sender,
                "payload_type": "task.response",
                "payload": {
                    "task_id": "task-123",
                    "status": "completed",
                    "result": {"echoed": request_envelope.payload.get("input", {})},
                },
                "correlation_id": request_envelope.id,
                "timestamp": "2026-02-04T22:00:00Z",
            }
        },
        "id": "req-1",
    }


class TestCircuitBreakerE2E:
    """E2E tests simulating a remote agent going down and recovering."""

    @pytest.mark.asyncio
    async def test_circuit_opens_when_server_unavailable(
        self, sample_request_envelope: Envelope
    ) -> None:
        """Circuit opens after repeated failures to reach remote agent."""

        def failing_transport(request: httpx.Request) -> httpx.Response:
            return httpx.Response(status_code=503, content=b"Service Unavailable")

        async with ASAPClient(
            "http://remote-agent:8000",
            transport=httpx.MockTransport(failing_transport),
            circuit_breaker_enabled=True,
            circuit_breaker_threshold=3,
            max_retries=1,
            require_https=False,
        ) as client:
            # First 3 requests fail and open the circuit
            for _ in range(3):
                with pytest.raises(ASAPConnectionError):
                    await client.send(sample_request_envelope)

            assert client._circuit_breaker is not None
            assert client._circuit_breaker.get_state() == CircuitState.OPEN

            # Next request is rejected immediately without hitting the server
            with pytest.raises(CircuitOpenError) as exc_info:
                await client.send(sample_request_envelope)

            assert exc_info.value.base_url == "http://remote-agent:8000"

    @pytest.mark.asyncio
    async def test_circuit_recovers_after_server_comes_back(
        self, sample_request_envelope: Envelope
    ) -> None:
        """Circuit closes when server recovers (HALF_OPEN -> CLOSED)."""
        call_count = 0
        server_healthy = False

        def intermittent_transport(request: httpx.Request) -> httpx.Response:
            nonlocal call_count
            call_count += 1

            if server_healthy:
                return httpx.Response(
                    status_code=200,
                    json=create_success_response(sample_request_envelope),
                )
            return httpx.Response(status_code=503, content=b"Service Unavailable")

        async with ASAPClient(
            "http://remote-agent:8000",
            transport=httpx.MockTransport(intermittent_transport),
            circuit_breaker_enabled=True,
            circuit_breaker_threshold=3,
            circuit_breaker_timeout=0.1,  # Short timeout for test
            max_retries=1,
            require_https=False,
        ) as client:
            # Phase 1: Server is down, circuit opens
            for _ in range(3):
                with pytest.raises(ASAPConnectionError):
                    await client.send(sample_request_envelope)

            assert client._circuit_breaker is not None
            assert client._circuit_breaker.get_state() == CircuitState.OPEN
            initial_calls = call_count

            # Phase 2: Wait so next can_attempt() will transition OPEN -> HALF_OPEN
            await asyncio.sleep(0.15)

            # Phase 3: Server comes back online
            server_healthy = True

            # Phase 4: First request gets single HALF_OPEN permit, succeeds, closes circuit
            response = await client.send(sample_request_envelope)

            assert response.payload_type == "task.response"
            assert client._circuit_breaker.get_state() == CircuitState.CLOSED
            assert client._circuit_breaker.get_consecutive_failures() == 0
            assert call_count > initial_calls

    @pytest.mark.asyncio
    async def test_circuit_stays_open_when_recovery_fails(
        self, sample_request_envelope: Envelope
    ) -> None:
        """Circuit reopens if request fails during HALF_OPEN state."""

        def always_failing_transport(request: httpx.Request) -> httpx.Response:
            return httpx.Response(status_code=503, content=b"Service Unavailable")

        async with ASAPClient(
            "http://remote-agent:8000",
            transport=httpx.MockTransport(always_failing_transport),
            circuit_breaker_enabled=True,
            circuit_breaker_threshold=3,
            circuit_breaker_timeout=0.1,
            max_retries=1,
            require_https=False,
        ) as client:
            # Open the circuit
            for _ in range(3):
                with pytest.raises(ASAPConnectionError):
                    await client.send(sample_request_envelope)

            assert client._circuit_breaker is not None
            assert client._circuit_breaker.get_state() == CircuitState.OPEN

            # Wait so next can_attempt() will transition OPEN -> HALF_OPEN
            await asyncio.sleep(0.15)

            # Recovery attempt gets single HALF_OPEN permit, fails, reopens circuit
            with pytest.raises(ASAPConnectionError):
                await client.send(sample_request_envelope)

            assert client._circuit_breaker.get_state() == CircuitState.OPEN

    @pytest.mark.asyncio
    async def test_circuit_shared_across_client_instances(
        self, sample_request_envelope: Envelope
    ) -> None:
        """Multiple clients to same URL share circuit breaker state."""

        def failing_transport(request: httpx.Request) -> httpx.Response:
            return httpx.Response(status_code=503, content=b"Service Unavailable")

        # First client opens the circuit
        async with ASAPClient(
            "http://shared-agent:8000",
            transport=httpx.MockTransport(failing_transport),
            circuit_breaker_enabled=True,
            circuit_breaker_threshold=3,
            max_retries=1,
            require_https=False,
        ) as client1:
            for _ in range(3):
                with pytest.raises(ASAPConnectionError):
                    await client1.send(sample_request_envelope)

            assert client1._circuit_breaker is not None
            assert client1._circuit_breaker.get_state() == CircuitState.OPEN

        # Second client should see the circuit already open
        async with ASAPClient(
            "http://shared-agent:8000",
            transport=httpx.MockTransport(failing_transport),
            circuit_breaker_enabled=True,
            circuit_breaker_threshold=3,
            max_retries=1,
            require_https=False,
        ) as client2:
            # Should fail immediately without retrying
            with pytest.raises(CircuitOpenError):
                await client2.send(sample_request_envelope)

    @pytest.mark.asyncio
    async def test_full_lifecycle_down_and_recovery(
        self, sample_request_envelope: Envelope
    ) -> None:
        """Full lifecycle: healthy -> down -> open -> half-open -> recovery."""
        phase = "healthy"

        def lifecycle_transport(request: httpx.Request) -> httpx.Response:
            if phase == "healthy":
                return httpx.Response(
                    status_code=200,
                    json=create_success_response(sample_request_envelope),
                )
            if phase == "down":
                return httpx.Response(status_code=503, content=b"Down")
            if phase == "recovering":
                return httpx.Response(
                    status_code=200,
                    json=create_success_response(sample_request_envelope),
                )
            return httpx.Response(status_code=500, content=b"Unknown")

        async with ASAPClient(
            "http://lifecycle-agent:8000",
            transport=httpx.MockTransport(lifecycle_transport),
            circuit_breaker_enabled=True,
            circuit_breaker_threshold=3,
            circuit_breaker_timeout=0.1,
            max_retries=1,
            require_https=False,
        ) as client:
            # Phase 1: Healthy - requests succeed
            response = await client.send(sample_request_envelope)
            assert response.payload_type == "task.response"
            assert client._circuit_breaker is not None
            assert client._circuit_breaker.get_state() == CircuitState.CLOSED

            # Phase 2: Server goes down
            phase = "down"
            for _ in range(3):
                with pytest.raises(ASAPConnectionError):
                    await client.send(sample_request_envelope)

            assert client._circuit_breaker.get_state() == CircuitState.OPEN

            # Phase 3: Circuit blocks requests
            with pytest.raises(CircuitOpenError):
                await client.send(sample_request_envelope)

            # Phase 4: Wait for half-open
            await asyncio.sleep(0.15)

            # Phase 5: Server recovers
            phase = "recovering"
            response = await client.send(sample_request_envelope)
            assert response.payload_type == "task.response"
            assert client._circuit_breaker.get_state() == CircuitState.CLOSED
