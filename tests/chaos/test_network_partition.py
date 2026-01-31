"""Chaos engineering tests for network partition simulation.

This module tests the resilience of the ASAP client when facing network
partitions and connectivity issues. It simulates:
- Complete connection failures
- Intermittent network outages
- Partial failures (some requests succeed, others fail)
- Network recovery scenarios

These tests verify that:
1. The client properly retries failed requests
2. Circuit breakers open under sustained network failures
3. The system recovers gracefully when network is restored
4. Error messages are clear and actionable
"""

import asyncio
from typing import TYPE_CHECKING, Generator
from unittest.mock import patch

import httpx
import pytest

from asap.errors import CircuitOpenError
from asap.models.envelope import Envelope
from asap.models.enums import TaskStatus
from asap.models.payloads import TaskRequest, TaskResponse
from asap.transport.circuit_breaker import CircuitState, get_registry
from asap.transport.client import (
    ASAPClient,
    ASAPConnectionError,
    ASAPTimeoutError,
    RetryConfig,
)

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


class TestNetworkPartitionBasic:
    """Tests for basic network partition scenarios."""

    @pytest.fixture
    def sample_request_envelope(self) -> Envelope:
        """Create a sample request envelope for testing."""
        return Envelope(
            asap_version="0.1",
            sender="urn:asap:agent:client",
            recipient="urn:asap:agent:server",
            payload_type="task.request",
            payload=TaskRequest(
                conversation_id="conv_chaos_001",
                skill_id="echo",
                input={"message": "Chaos test"},
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
                task_id="task_chaos_001",
                status=TaskStatus.COMPLETED,
                result={"echoed": {"message": "Chaos test"}},
            ).model_dump(),
            correlation_id=sample_request_envelope.id,
        )

    async def test_complete_connection_failure(self, sample_request_envelope: Envelope) -> None:
        """Test client behavior when connection is completely refused.

        Simulates a scenario where the server is unreachable (e.g., network partition,
        server down, firewall blocking). The client should:
        1. Retry according to max_retries configuration
        2. Apply exponential backoff between retries
        3. Raise ASAPConnectionError after all retries exhausted
        """
        call_count = 0
        delays: list[float] = []

        def mock_transport(request: httpx.Request) -> httpx.Response:
            nonlocal call_count
            call_count += 1
            # Always raise connection error - server unreachable
            raise httpx.ConnectError("Connection refused - network partition")

        with patch("asap.transport.client.asyncio.sleep") as mock_sleep:

            async def sleep_capture(delay: float) -> None:
                delays.append(delay)

            mock_sleep.side_effect = sleep_capture

            async with ASAPClient(
                "http://localhost:8000",
                transport=httpx.MockTransport(mock_transport),
                max_retries=3,
                base_delay=0.1,
                jitter=False,
            ) as client:
                with pytest.raises(ASAPConnectionError) as exc_info:
                    await client.send(sample_request_envelope)

                # Verify error message is helpful
                assert "Connection" in str(exc_info.value)
                assert "localhost:8000" in str(exc_info.value)

        # Should have attempted max_retries times
        assert call_count == 3
        # Should have backed off max_retries - 1 times
        assert len(delays) == 2
        # Verify exponential backoff: 0.1, 0.2
        assert delays[0] == pytest.approx(0.1, abs=0.01)
        assert delays[1] == pytest.approx(0.2, abs=0.01)

    async def test_connection_timeout(self, sample_request_envelope: Envelope) -> None:
        """Test client behavior when connection times out.

        Simulates a scenario where the server is reachable but unresponsive
        (e.g., network congestion, server overloaded). The client should:
        1. Raise ASAPTimeoutError after timeout
        2. Include timeout value in error message
        """
        call_count = 0

        def mock_transport(request: httpx.Request) -> httpx.Response:
            nonlocal call_count
            call_count += 1
            # Raise timeout error - server not responding
            raise httpx.TimeoutException("Connection timed out")

        with patch("asap.transport.client.asyncio.sleep"):
            async with ASAPClient(
                "http://localhost:8000",
                transport=httpx.MockTransport(mock_transport),
                timeout=5.0,
                max_retries=2,
            ) as client:
                with pytest.raises(ASAPTimeoutError) as exc_info:
                    await client.send(sample_request_envelope)

                # Verify timeout is included in error
                assert exc_info.value.timeout == 5.0

        # Should have attempted max_retries times
        assert call_count == 2

    async def test_intermittent_network_failure(
        self, sample_request_envelope: Envelope, sample_response_envelope: Envelope
    ) -> None:
        """Test client behavior with intermittent network failures.

        Simulates a flaky network where some requests fail and others succeed.
        This is common in distributed systems with network issues.
        """
        call_count = 0

        def mock_transport(request: httpx.Request) -> httpx.Response:
            nonlocal call_count
            call_count += 1
            # First 2 attempts fail, then succeed
            if call_count <= 2:
                raise httpx.ConnectError("Intermittent network failure")
            return create_mock_response(sample_response_envelope)

        with patch("asap.transport.client.asyncio.sleep"):
            async with ASAPClient(
                "http://localhost:8000",
                transport=httpx.MockTransport(mock_transport),
                max_retries=5,
                base_delay=0.1,
                jitter=False,
            ) as client:
                response = await client.send(sample_request_envelope)

                # Should eventually succeed
                assert response.payload_type == "task.response"

        # Should have retried and eventually succeeded
        assert call_count == 3  # 2 failures + 1 success


class TestNetworkPartitionWithCircuitBreaker:
    """Tests for network partition scenarios with circuit breaker enabled."""

    @pytest.fixture(autouse=True)
    def clear_registry(self) -> Generator[None, None, None]:
        """Clear circuit breaker registry before each test to ensure isolation."""
        registry = get_registry()
        registry.clear()
        yield
        registry.clear()

    @pytest.fixture
    def sample_request_envelope(self) -> Envelope:
        """Create a sample request envelope for testing."""
        return Envelope(
            asap_version="0.1",
            sender="urn:asap:agent:client",
            recipient="urn:asap:agent:server",
            payload_type="task.request",
            payload=TaskRequest(
                conversation_id="conv_chaos_cb_001",
                skill_id="echo",
                input={"message": "Circuit breaker chaos test"},
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
                task_id="task_chaos_cb_001",
                status=TaskStatus.COMPLETED,
                result={"echoed": {"message": "Circuit breaker chaos test"}},
            ).model_dump(),
            correlation_id=sample_request_envelope.id,
        )

    async def test_circuit_breaker_opens_on_network_partition(
        self, sample_request_envelope: Envelope
    ) -> None:
        """Test circuit breaker opens after sustained network failures.

        Simulates a network partition that causes multiple consecutive failures.
        The circuit breaker should open to prevent resource exhaustion.
        """
        call_count = 0

        def mock_transport(request: httpx.Request) -> httpx.Response:
            nonlocal call_count
            call_count += 1
            # Always fail - simulating complete network partition
            raise httpx.ConnectError("Network partition - no route to host")

        with patch("asap.transport.client.asyncio.sleep"):
            retry_config = RetryConfig(
                max_retries=1,  # Single attempt per send() to count failures accurately
                circuit_breaker_enabled=True,
                circuit_breaker_threshold=5,
                circuit_breaker_timeout=60.0,
            )

            async with ASAPClient(
                "http://localhost:8000",
                transport=httpx.MockTransport(mock_transport),
                retry_config=retry_config,
            ) as client:
                # Make 5 requests to trigger circuit breaker
                for _ in range(5):
                    with pytest.raises(ASAPConnectionError):
                        await client.send(sample_request_envelope)

                # Circuit should now be open
                assert client._circuit_breaker is not None
                assert client._circuit_breaker.get_state() == CircuitState.OPEN

                # Next request should fail immediately with CircuitOpenError
                with pytest.raises(CircuitOpenError) as exc_info:
                    await client.send(sample_request_envelope)

                assert exc_info.value.consecutive_failures >= 5

    async def test_circuit_breaker_recovery_after_network_restored(
        self, sample_request_envelope: Envelope, sample_response_envelope: Envelope
    ) -> None:
        """Test circuit breaker recovery when network is restored.

        Simulates a network partition followed by recovery. The circuit
        breaker should transition from OPEN -> HALF_OPEN -> CLOSED.
        """
        network_up = False

        def mock_transport(request: httpx.Request) -> httpx.Response:
            if network_up:
                return create_mock_response(sample_response_envelope)
            raise httpx.ConnectError("Network partition")

        # Don't mock asyncio.sleep - we need real time to pass for circuit breaker timeout
        retry_config = RetryConfig(
            max_retries=1,
            circuit_breaker_enabled=True,
            circuit_breaker_threshold=3,
            circuit_breaker_timeout=0.05,  # Very short timeout for testing (50ms)
        )

        async with ASAPClient(
            "http://localhost:8000",
            transport=httpx.MockTransport(mock_transport),
            retry_config=retry_config,
        ) as client:
            # Trigger circuit breaker with 3 failures
            for _ in range(3):
                with pytest.raises(ASAPConnectionError):
                    await client.send(sample_request_envelope)

            # Circuit should be open
            assert client._circuit_breaker is not None
            assert client._circuit_breaker.get_state() == CircuitState.OPEN

            # Wait for timeout to transition to HALF_OPEN (real sleep, not mocked)
            await asyncio.sleep(0.1)

            # Verify circuit is in HALF_OPEN state (can_attempt returns True)
            assert client._circuit_breaker.can_attempt() is True

            # Simulate network recovery
            network_up = True

            # Next request should succeed and close circuit
            response = await client.send(sample_request_envelope)
            assert response.payload_type == "task.response"
            assert client._circuit_breaker.get_state() == CircuitState.CLOSED


class TestNetworkPartitionPatterns:
    """Tests for specific network partition patterns."""

    @pytest.fixture
    def sample_request_envelope(self) -> Envelope:
        """Create a sample request envelope for testing."""
        return Envelope(
            asap_version="0.1",
            sender="urn:asap:agent:client",
            recipient="urn:asap:agent:server",
            payload_type="task.request",
            payload=TaskRequest(
                conversation_id="conv_chaos_pattern_001",
                skill_id="echo",
                input={"message": "Pattern test"},
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
                task_id="task_chaos_pattern_001",
                status=TaskStatus.COMPLETED,
                result={"echoed": {"message": "Pattern test"}},
            ).model_dump(),
            correlation_id=sample_request_envelope.id,
        )

    async def test_alternating_success_failure(
        self, sample_request_envelope: Envelope, sample_response_envelope: Envelope
    ) -> None:
        """Test client behavior with alternating success/failure pattern.

        This pattern can occur with load balancers routing to healthy/unhealthy instances.
        """
        call_count = 0
        successes = 0
        failures = 0

        def mock_transport(request: httpx.Request) -> httpx.Response:
            nonlocal call_count, successes, failures
            call_count += 1
            # Odd calls fail, even calls succeed
            if call_count % 2 == 1:
                failures += 1
                raise httpx.ConnectError("One node is down")
            successes += 1
            return create_mock_response(sample_response_envelope)

        with patch("asap.transport.client.asyncio.sleep"):
            async with ASAPClient(
                "http://localhost:8000",
                transport=httpx.MockTransport(mock_transport),
                max_retries=5,
                base_delay=0.1,
            ) as client:
                # First request: fails on 1st try, succeeds on 2nd
                response = await client.send(sample_request_envelope)
                assert response.payload_type == "task.response"

                # Second request: fails on 3rd try, succeeds on 4th
                response = await client.send(sample_request_envelope)
                assert response.payload_type == "task.response"

        # Verify alternating pattern
        assert failures == 2
        assert successes == 2

    async def test_progressive_degradation(
        self, sample_request_envelope: Envelope, sample_response_envelope: Envelope
    ) -> None:
        """Test client behavior when network progressively degrades.

        Simulates a scenario where network becomes increasingly unreliable
        (e.g., cable damage, increasing latency).
        """
        call_count = 0
        failure_probability = 0.0

        def mock_transport(request: httpx.Request) -> httpx.Response:
            nonlocal call_count, failure_probability
            call_count += 1
            # Increase failure probability with each call
            failure_probability = min(1.0, failure_probability + 0.2)
            # Deterministic "random" based on call count for reproducibility
            if (call_count * 7) % 10 < failure_probability * 10:
                raise httpx.ConnectError("Network degrading")
            return create_mock_response(sample_response_envelope)

        with patch("asap.transport.client.asyncio.sleep"):
            async with ASAPClient(
                "http://localhost:8000",
                transport=httpx.MockTransport(mock_transport),
                max_retries=5,
                base_delay=0.1,
            ) as client:
                # First few requests should succeed more easily
                successful_requests = 0
                for _ in range(3):
                    try:
                        response = await client.send(sample_request_envelope)
                        if response.payload_type == "task.response":
                            successful_requests += 1
                    except ASAPConnectionError:
                        pass

                # At least some requests should succeed
                assert successful_requests >= 1

    async def test_network_split_brain(
        self, sample_request_envelope: Envelope, sample_response_envelope: Envelope
    ) -> None:
        """Test client behavior during network split-brain scenario.

        Simulates a scenario where the network is partitioned but connections
        to one partition work while others fail.
        """
        call_count = 0

        def mock_transport(request: httpx.Request) -> httpx.Response:
            nonlocal call_count
            call_count += 1
            # First 3 calls fail (partition A is unreachable)
            # Then partition heals
            if call_count <= 3:
                raise httpx.ConnectError("Partition A unreachable")
            return create_mock_response(sample_response_envelope)

        with patch("asap.transport.client.asyncio.sleep"):
            async with ASAPClient(
                "http://localhost:8000",
                transport=httpx.MockTransport(mock_transport),
                max_retries=5,
                base_delay=0.05,
            ) as client:
                # Request should eventually succeed after partition heals
                response = await client.send(sample_request_envelope)
                assert response.payload_type == "task.response"

        # Verify we attempted through the partition
        assert call_count == 4  # 3 failures + 1 success


class TestNetworkPartitionEdgeCases:
    """Edge case tests for network partition scenarios."""

    @pytest.fixture
    def sample_request_envelope(self) -> Envelope:
        """Create a sample request envelope for testing."""
        return Envelope(
            asap_version="0.1",
            sender="urn:asap:agent:client",
            recipient="urn:asap:agent:server",
            payload_type="task.request",
            payload=TaskRequest(
                conversation_id="conv_chaos_edge_001",
                skill_id="echo",
                input={"message": "Edge case test"},
            ).model_dump(),
        )

    async def test_dns_resolution_failure(self, sample_request_envelope: Envelope) -> None:
        """Test client behavior when DNS resolution fails.

        This simulates a complete DNS outage or misconfigured DNS.
        """

        def mock_transport(request: httpx.Request) -> httpx.Response:
            raise httpx.ConnectError("DNS resolution failed: NXDOMAIN")

        with patch("asap.transport.client.asyncio.sleep"):
            async with ASAPClient(
                "http://nonexistent.example.com",
                transport=httpx.MockTransport(mock_transport),
                max_retries=2,
                require_https=False,
            ) as client:
                with pytest.raises(ASAPConnectionError) as exc_info:
                    await client.send(sample_request_envelope)

                # Error should mention connection issue
                assert "Connection" in str(exc_info.value) or "error" in str(exc_info.value).lower()

    async def test_connection_reset(self, sample_request_envelope: Envelope) -> None:
        """Test client behavior when connection is reset mid-request.

        This can happen when a firewall terminates connections or when
        a server crashes during request processing.
        """

        def mock_transport(request: httpx.Request) -> httpx.Response:
            raise httpx.ConnectError("Connection reset by peer")

        with patch("asap.transport.client.asyncio.sleep"):
            async with ASAPClient(
                "http://localhost:8000",
                transport=httpx.MockTransport(mock_transport),
                max_retries=2,
            ) as client:
                with pytest.raises(ASAPConnectionError) as exc_info:
                    await client.send(sample_request_envelope)

                assert "Connection" in str(exc_info.value)

    async def test_ssl_handshake_failure(self, sample_request_envelope: Envelope) -> None:
        """Test client behavior when SSL/TLS handshake fails.

        This can happen with certificate issues or TLS version mismatches.
        """

        def mock_transport(request: httpx.Request) -> httpx.Response:
            raise httpx.ConnectError("SSL: CERTIFICATE_VERIFY_FAILED")

        with patch("asap.transport.client.asyncio.sleep"):
            async with ASAPClient(
                "https://localhost:8000",
                transport=httpx.MockTransport(mock_transport),
                max_retries=2,
            ) as client:
                with pytest.raises(ASAPConnectionError):
                    await client.send(sample_request_envelope)

    async def test_rapid_connect_disconnect(self, sample_request_envelope: Envelope) -> None:
        """Test client behavior with rapid connect/disconnect cycles.

        Simulates unstable network where connections are established and
        immediately dropped.
        """
        call_count = 0

        def mock_transport(request: httpx.Request) -> httpx.Response:
            nonlocal call_count
            call_count += 1
            # Simulate connection established but immediately dropped
            if call_count <= 2:
                raise httpx.ConnectError("Connection closed unexpectedly")
            # Eventually stabilizes
            response_envelope = Envelope(
                asap_version="0.1",
                sender="urn:asap:agent:server",
                recipient="urn:asap:agent:client",
                payload_type="task.response",
                payload=TaskResponse(
                    task_id="task_rapid",
                    status=TaskStatus.COMPLETED,
                    result={},
                ).model_dump(),
                correlation_id=sample_request_envelope.id,
            )
            return create_mock_response(response_envelope)

        with patch("asap.transport.client.asyncio.sleep"):
            async with ASAPClient(
                "http://localhost:8000",
                transport=httpx.MockTransport(mock_transport),
                max_retries=5,
                base_delay=0.05,
            ) as client:
                response = await client.send(sample_request_envelope)
                assert response.payload_type == "task.response"

        assert call_count == 3  # 2 failures + 1 success
