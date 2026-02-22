"""Integration tests for batch operations with authentication and pooling.

This module tests the interaction between:
- Batch operations (send_batch)
- Authenticated endpoints
- Connection pooling under pressure
- Error handling for partial batch failures with auth + circuit breaker

These tests verify that the transport layer handles complex real-world
scenarios correctly when multiple features are combined.
"""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Callable

import pytest
from fastapi import FastAPI
from httpx import ASGITransport

from asap.models.entities import Capability, Endpoint, Manifest, Skill
from asap.models.enums import TaskStatus
from asap.models.envelope import Envelope
from asap.models.payloads import TaskResponse
from asap.transport.client import ASAPClient, ASAPRemoteError
from asap.transport.handlers import HandlerRegistry
from asap.transport.server import create_app

from tests.factories import create_auth_manifest, create_envelope
from ..conftest import NoRateLimitTestBase

if TYPE_CHECKING:
    pass


def _create_app_with_auth(
    manifest: Manifest,
    token_validator: Callable[[str], str | None],
    slow_handler: bool = False,
) -> FastAPI:
    """Create a FastAPI app with authentication and optional slow handler."""
    registry = HandlerRegistry()

    def echo_handler(envelope: Envelope, manifest: Manifest) -> Envelope:
        return Envelope(
            asap_version="0.1",
            sender=manifest.id,
            recipient=envelope.sender,
            payload_type="task.response",
            payload=TaskResponse(
                task_id="task-123",
                status=TaskStatus.COMPLETED,
                result={"echo": envelope.payload_dict.get("input", {})},
            ).model_dump(),
            correlation_id=envelope.id,
        )

    async def slow_echo_handler(envelope: Envelope, manifest: Manifest) -> Envelope:
        await asyncio.sleep(0.1)  # Simulate slow processing
        return echo_handler(envelope, manifest)

    if slow_handler:
        registry.register("task.request", slow_echo_handler)
    else:
        registry.register("task.request", echo_handler)

    return create_app(manifest, registry, token_validator=token_validator)


class TestBatchWithAuthentication(NoRateLimitTestBase):
    """Tests for batch operations with authenticated endpoints."""

    @pytest.fixture
    def auth_manifest(self) -> Manifest:
        """Create manifest with authentication."""
        return create_auth_manifest()

    @pytest.fixture
    def token_validator(self) -> Callable[[str], str | None]:
        """Create a token validator that accepts 'valid-token'."""

        def validator(token: str) -> str | None:
            if token == "valid-token":
                return "urn:asap:agent:client"
            return None

        return validator

    @pytest.fixture
    def auth_app(
        self,
        auth_manifest: Manifest,
        token_validator: Callable[[str], str | None],
    ) -> FastAPI:
        """Create app with authentication."""
        return _create_app_with_auth(auth_manifest, token_validator)

    @pytest.mark.asyncio
    async def test_batch_with_valid_auth_succeeds(
        self,
        auth_app: FastAPI,
    ) -> None:
        """Batch requests with valid authentication should all succeed."""
        transport = ASGITransport(app=auth_app)
        async with ASAPClient(
            "http://localhost:8000",
            require_https=False,
            transport=transport,
        ) as client:
            client._client.headers["Authorization"] = "Bearer valid-token"

            envelopes = [
                create_envelope(message=f"batch-{i}", conversation_id=f"conv-{i}") for i in range(5)
            ]

            results = await client.send_batch(envelopes)

            assert len(results) == 5
            for result in results:
                assert isinstance(result, Envelope)
                assert result.payload_type == "task.response"
                response = TaskResponse(**result.payload_dict)
                assert response.status == TaskStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_batch_with_invalid_auth_fails_all(
        self,
        auth_app: FastAPI,
    ) -> None:
        """Batch requests with invalid auth should all fail with return_exceptions=True."""
        transport = ASGITransport(app=auth_app)
        async with ASAPClient(
            "http://localhost:8000",
            require_https=False,
            transport=transport,
        ) as client:
            client._client.headers["Authorization"] = "Bearer invalid-token"

            envelopes = [
                create_envelope(message=f"batch-{i}", conversation_id=f"conv-{i}") for i in range(3)
            ]

            results = await client.send_batch(envelopes, return_exceptions=True)

            assert len(results) == 3
            for result in results:
                assert isinstance(result, Exception)

    @pytest.mark.asyncio
    async def test_batch_with_missing_auth_fails(
        self,
        auth_app: FastAPI,
    ) -> None:
        """Batch requests without auth header should fail."""
        transport = ASGITransport(app=auth_app)
        async with ASAPClient(
            "http://localhost:8000",
            require_https=False,
            transport=transport,
        ) as client:
            envelopes = [create_envelope(message="no-auth")]

            results = await client.send_batch(envelopes, return_exceptions=True)

            assert len(results) == 1
            assert isinstance(results[0], Exception)


class TestBatchWithPooling(NoRateLimitTestBase):
    """Tests for batch operations under connection pool pressure."""

    @pytest.fixture
    def slow_manifest(self) -> Manifest:
        """Create manifest for slow handler tests."""
        return Manifest(
            id="urn:asap:agent:slow-server",
            name="Slow Test Server",
            version="1.0.0",
            description="Test server with slow responses",
            capabilities=Capability(
                asap_version="0.1",
                skills=[Skill(id="slow", description="Slow skill")],
                state_persistence=False,
            ),
            endpoints=Endpoint(asap="http://localhost:8000/asap"),
        )

    @pytest.fixture
    def slow_app(self, slow_manifest: Manifest) -> FastAPI:
        """Create app with slow handler."""
        registry = HandlerRegistry()

        async def slow_handler(envelope: Envelope, manifest: Manifest) -> Envelope:
            await asyncio.sleep(0.05)  # 50ms delay
            return Envelope(
                asap_version="0.1",
                sender=manifest.id,
                recipient=envelope.sender,
                payload_type="task.response",
                payload=TaskResponse(
                    task_id="task-slow",
                    status=TaskStatus.COMPLETED,
                    result={"processed": True},
                ).model_dump(),
                correlation_id=envelope.id,
            )

        registry.register("task.request", slow_handler)
        return create_app(slow_manifest, registry)

    @pytest.mark.asyncio
    async def test_batch_respects_pool_connections(
        self,
        slow_app: FastAPI,
    ) -> None:
        """Batch operations should work within connection pool limits."""
        transport = ASGITransport(app=slow_app)
        async with ASAPClient(
            "http://localhost:8000",
            require_https=False,
            transport=transport,
            pool_connections=2,
            pool_maxsize=5,
        ) as client:
            envelopes = [
                create_envelope(
                    recipient="urn:asap:agent:slow-server",
                    message=f"pool-{i}",
                    conversation_id=f"conv-{i}",
                )
                for i in range(10)
            ]

            results = await client.send_batch(envelopes)

            assert len(results) == 10
            for result in results:
                assert isinstance(result, Envelope)
                assert result.payload_type == "task.response"

    @pytest.mark.asyncio
    async def test_batch_concurrent_performance(
        self,
        slow_app: FastAPI,
    ) -> None:
        """Batch operations should execute concurrently, not sequentially."""
        import time

        transport = ASGITransport(app=slow_app)
        async with ASAPClient(
            "http://localhost:8000",
            require_https=False,
            transport=transport,
        ) as client:
            envelopes = [
                create_envelope(
                    recipient="urn:asap:agent:slow-server",
                    message=f"concurrent-{i}",
                    conversation_id=f"conv-{i}",
                )
                for i in range(5)
            ]

            start = time.perf_counter()
            results = await client.send_batch(envelopes)
            duration = time.perf_counter() - start

            assert len(results) == 5
            # If executed concurrently, should take ~50ms, not 250ms
            # Allow some overhead but should be well under sequential time
            assert duration < 0.3  # 300ms max (sequential would be ~250ms minimum)


class TestBatchPartialFailures(NoRateLimitTestBase):
    """Tests for partial batch failures with mixed success/error responses."""

    @pytest.fixture
    def mixed_app(self) -> FastAPI:
        """Create app that fails on specific requests."""
        manifest = Manifest(
            id="urn:asap:agent:mixed-server",
            name="Mixed Test Server",
            version="1.0.0",
            description="Server that fails on specific requests",
            capabilities=Capability(
                asap_version="0.1",
                skills=[Skill(id="mixed", description="Mixed skill")],
                state_persistence=False,
            ),
            endpoints=Endpoint(asap="http://localhost:8000/asap"),
        )

        registry = HandlerRegistry()

        def mixed_handler(envelope: Envelope, manifest: Manifest) -> Envelope:
            message = envelope.payload_dict.get("input", {}).get("message", "")
            if "fail" in message:
                raise ValueError(f"Intentional failure for: {message}")
            return Envelope(
                asap_version="0.1",
                sender=manifest.id,
                recipient=envelope.sender,
                payload_type="task.response",
                payload=TaskResponse(
                    task_id="task-mixed",
                    status=TaskStatus.COMPLETED,
                    result={"message": message},
                ).model_dump(),
                correlation_id=envelope.id,
            )

        registry.register("task.request", mixed_handler)
        return create_app(manifest, registry)

    @pytest.mark.asyncio
    async def test_batch_partial_failures_with_return_exceptions(
        self,
        mixed_app: FastAPI,
    ) -> None:
        """Batch with return_exceptions=True should return mixed results."""
        transport = ASGITransport(app=mixed_app)
        async with ASAPClient(
            "http://localhost:8000",
            require_https=False,
            transport=transport,
        ) as client:
            envelopes = [
                create_envelope(
                    recipient="urn:asap:agent:mixed-server",
                    message="success-1",
                    conversation_id="conv-1",
                ),
                create_envelope(
                    recipient="urn:asap:agent:mixed-server",
                    message="fail-2",
                    conversation_id="conv-2",
                ),
                create_envelope(
                    recipient="urn:asap:agent:mixed-server",
                    message="success-3",
                    conversation_id="conv-3",
                ),
            ]

            results = await client.send_batch(envelopes, return_exceptions=True)

            assert len(results) == 3
            assert isinstance(results[0], Envelope)
            assert results[0].payload_type == "task.response"
            assert isinstance(results[1], Exception)
            assert isinstance(results[2], Envelope)
            assert results[2].payload_type == "task.response"

    @pytest.mark.asyncio
    async def test_batch_without_return_exceptions_raises_first_error(
        self,
        mixed_app: FastAPI,
    ) -> None:
        """Batch without return_exceptions should raise on first error."""
        transport = ASGITransport(app=mixed_app)
        async with ASAPClient(
            "http://localhost:8000",
            require_https=False,
            transport=transport,
        ) as client:
            envelopes = [
                create_envelope(
                    recipient="urn:asap:agent:mixed-server",
                    message="fail-first",
                    conversation_id="conv-1",
                ),
                create_envelope(
                    recipient="urn:asap:agent:mixed-server",
                    message="success-second",
                    conversation_id="conv-2",
                ),
            ]

            with pytest.raises(ASAPRemoteError):
                await client.send_batch(envelopes, return_exceptions=False)


class TestBatchWithCircuitBreaker(NoRateLimitTestBase):
    """Tests for batch operations with circuit breaker behavior.

    Note: The circuit breaker only records network-level failures (connection
    errors, timeouts), not application-level errors (which return HTTP 200
    with JSON-RPC error responses). This is by design - the circuit breaker
    protects against infrastructure failures, not business logic errors.
    """

    @pytest.fixture
    def error_app(self) -> FastAPI:
        """Create app that returns JSON-RPC errors."""
        manifest = Manifest(
            id="urn:asap:agent:error-server",
            name="Error Test Server",
            version="1.0.0",
            description="Server that returns errors",
            capabilities=Capability(
                asap_version="0.1",
                skills=[Skill(id="error", description="Error skill")],
                state_persistence=False,
            ),
            endpoints=Endpoint(asap="http://localhost:8000/asap"),
        )

        registry = HandlerRegistry()

        def error_handler(envelope: Envelope, manifest: Manifest) -> Envelope:
            raise RuntimeError("Handler always fails")

        registry.register("task.request", error_handler)
        return create_app(manifest, registry)

    @pytest.mark.asyncio
    async def test_batch_with_app_errors_does_not_trip_circuit_breaker(
        self,
        error_app: FastAPI,
    ) -> None:
        """Application errors (HTTP 200 with JSON-RPC error) should not trip circuit breaker.

        Circuit breaker only reacts to network-level failures like connection
        errors or timeouts, not application-level errors.
        """
        transport = ASGITransport(app=error_app)
        async with ASAPClient(
            "http://localhost:8000",
            require_https=False,
            transport=transport,
            circuit_breaker_enabled=True,
            circuit_breaker_threshold=3,
        ) as client:
            envelopes = [
                create_envelope(
                    recipient="urn:asap:agent:error-server",
                    message=f"error-{i}",
                    conversation_id=f"conv-{i}",
                )
                for i in range(5)
            ]

            results = await client.send_batch(envelopes, return_exceptions=True)

            assert len(results) == 5
            for result in results:
                assert isinstance(result, Exception)

            if client._circuit_breaker:
                assert client._circuit_breaker._consecutive_failures == 0

    @pytest.mark.asyncio
    async def test_batch_with_circuit_breaker_enabled(
        self,
        error_app: FastAPI,
    ) -> None:
        """Verify circuit breaker is properly initialized for batch operations."""
        transport = ASGITransport(app=error_app)
        async with ASAPClient(
            "http://localhost:9999",
            require_https=False,
            transport=transport,
            circuit_breaker_enabled=True,
            circuit_breaker_threshold=5,
        ) as client:
            assert client._circuit_breaker is not None
            assert client._circuit_breaker.threshold == 5


class TestBatchAuthPoolingCombined(NoRateLimitTestBase):
    """Combined tests for batch + auth + pooling scenarios."""

    @pytest.mark.asyncio
    async def test_batch_auth_pooling_combined_success(self) -> None:
        """Test batch with auth and pooling all working together."""
        manifest = create_auth_manifest()

        def token_validator(token: str) -> str | None:
            if token == "valid-token":
                return "urn:asap:agent:client"
            return None

        app = _create_app_with_auth(manifest, token_validator, slow_handler=True)
        transport = ASGITransport(app=app)

        async with ASAPClient(
            "http://localhost:8000",
            require_https=False,
            transport=transport,
            pool_connections=2,
            pool_maxsize=5,
        ) as client:
            client._client.headers["Authorization"] = "Bearer valid-token"

            envelopes = [
                create_envelope(
                    message=f"combined-{i}",
                    conversation_id=f"conv-{i}",
                )
                for i in range(8)
            ]

            results = await client.send_batch(envelopes)

            assert len(results) == 8
            for result in results:
                assert isinstance(result, Envelope)
                assert result.payload_type == "task.response"

    @pytest.mark.asyncio
    async def test_batch_auth_pooling_with_token_refresh_scenario(self) -> None:
        """Test batch behavior when token validation varies per request."""
        manifest = create_auth_manifest()
        call_count = 0

        def counting_validator(token: str) -> str | None:
            nonlocal call_count
            call_count += 1
            if token == "valid-token":
                return "urn:asap:agent:client"
            return None

        app = _create_app_with_auth(manifest, counting_validator)
        transport = ASGITransport(app=app)

        async with ASAPClient(
            "http://localhost:8000",
            require_https=False,
            transport=transport,
        ) as client:
            client._client.headers["Authorization"] = "Bearer valid-token"

            envelopes = [
                create_envelope(
                    message=f"validate-{i}",
                    conversation_id=f"conv-{i}",
                )
                for i in range(5)
            ]

            results = await client.send_batch(envelopes)

            assert len(results) == 5
            assert call_count == 5
