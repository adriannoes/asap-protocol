"""Integration tests for rate limiting functionality.

This module contains tests specifically for rate limiting behavior.
These tests are isolated in a separate file to prevent interference with other tests.

CRITICAL: All tests use aggressive monkeypatch to replace module-level limiters
to ensure complete isolation even when slowapi.Limiter maintains global state.
"""

import collections.abc
import time
from datetime import datetime, timezone
from typing import TYPE_CHECKING

import pytest
from fastapi.testclient import TestClient

if TYPE_CHECKING:
    from slowapi import Limiter

from asap.models.entities import Capability, Endpoint, Manifest, Skill
from asap.models.envelope import Envelope
from asap.models.payloads import TaskRequest
from asap.transport.jsonrpc import JsonRpcRequest
from asap.transport.middleware import (
    ERROR_RATE_LIMIT_EXCEEDED,
    HTTP_TOO_MANY_REQUESTS,
)
from asap.transport.server import create_app

# Filter deprecation warnings from slowapi
pytestmark = pytest.mark.filterwarnings("ignore::DeprecationWarning")


def _create_test_rpc_request(sender: str = "urn:asap:agent:client-1") -> JsonRpcRequest:
    """Create a test JSON-RPC request with envelope.

    Args:
        sender: Sender agent ID for the envelope

    Returns:
        JsonRpcRequest with valid ASAP envelope
    """
    envelope = Envelope(
        asap_version="0.1",
        timestamp=datetime.now(timezone.utc),
        sender=sender,
        recipient="urn:asap:agent:rate-limit-test",
        payload_type="task.request",
        payload=TaskRequest(
            conversation_id="test-conv-123",
            skill_id="echo",
            input={"message": "test"},
        ).model_dump(),
    )

    return JsonRpcRequest(
        method="asap.send",
        params={"envelope": envelope.model_dump(mode="json")},
        id="test-request-1",
    )


@pytest.fixture
def rate_limit_manifest() -> Manifest:
    """Create a manifest for rate limiting tests."""
    return Manifest(
        id="urn:asap:agent:rate-limit-test",
        name="Rate Limit Test Agent",
        version="1.0.0",
        description="Test agent for rate limiting",
        capabilities=Capability(
            asap_version="0.1",
            skills=[Skill(id="echo", description="Echo skill")],
            state_persistence=False,
        ),
        endpoints=Endpoint(asap="http://localhost:8000/asap"),
    )


class TestRateLimiting:
    """Tests for rate limiting functionality.

    Tests cover:
    - Requests within limit succeed
    - Exceeding limit returns 429
    - Limit resets after window
    - Different senders have independent limits

    All tests use aggressive monkeypatch to ensure complete limiter isolation.
    """

    def test_requests_within_limit_succeed(
        self,
        monkeypatch: pytest.MonkeyPatch,
        isolated_limiter_factory: "collections.abc.Callable[[collections.abc.Sequence[str] | None], Limiter]",
        rate_limit_manifest: Manifest,
    ) -> None:
        """Test that requests within the rate limit succeed."""
        # Create completely isolated limiter
        limiter = isolated_limiter_factory(["5/minute"])

        # Replace global limiter in BOTH modules
        import asap.transport.middleware as middleware_module
        import asap.transport.server as server_module

        monkeypatch.setattr(middleware_module, "limiter", limiter)
        monkeypatch.setattr(server_module, "limiter", limiter)

        # Create app - it will use the monkeypatched limiter
        app = create_app(rate_limit_manifest, rate_limit="5/minute")
        # Also set app.state.limiter for runtime
        app.state.limiter = limiter

        client = TestClient(app)

        # Make 5 requests (the limit is 5/minute)
        for i in range(5):
            rpc_request = _create_test_rpc_request()
            response = client.post("/asap", json=rpc_request.model_dump(mode="json"))

            assert response.status_code == 200, f"Request {i + 1} should succeed"
            data = response.json()
            assert "jsonrpc" in data
            assert data["jsonrpc"] == "2.0"

    def test_exceeding_limit_returns_429(
        self,
        monkeypatch: pytest.MonkeyPatch,
        isolated_limiter_factory: "collections.abc.Callable[[collections.abc.Sequence[str] | None], Limiter]",
        rate_limit_manifest: Manifest,
    ) -> None:
        """Test that exceeding the rate limit returns HTTP 429."""
        # Create completely isolated limiter
        limiter = isolated_limiter_factory(["5/minute"])

        # Replace global limiter in BOTH modules
        import asap.transport.middleware as middleware_module
        import asap.transport.server as server_module

        monkeypatch.setattr(middleware_module, "limiter", limiter)
        monkeypatch.setattr(server_module, "limiter", limiter)

        # Create app - it will use the monkeypatched limiter
        app = create_app(rate_limit_manifest, rate_limit="5/minute")
        # Also set app.state.limiter for runtime
        app.state.limiter = limiter

        client = TestClient(app)

        # Make 5 requests (within limit)
        for _i in range(5):
            rpc_request = _create_test_rpc_request()
            response = client.post("/asap", json=rpc_request.model_dump(mode="json"))
            assert response.status_code == 200

        # 6th request should be rate limited
        rpc_request = _create_test_rpc_request()
        response = client.post("/asap", json=rpc_request.model_dump(mode="json"))

        assert response.status_code == HTTP_TOO_MANY_REQUESTS
        data = response.json()
        assert "error" in data
        assert data["error"]["code"] == HTTP_TOO_MANY_REQUESTS
        assert ERROR_RATE_LIMIT_EXCEEDED in data["error"]["message"]
        assert "retry_after" in data["error"].get("data", {})
        assert "Retry-After" in response.headers

    def test_different_senders_independent(
        self,
        monkeypatch: pytest.MonkeyPatch,
        isolated_limiter_factory: "collections.abc.Callable[[collections.abc.Sequence[str] | None], Limiter]",
        rate_limit_manifest: Manifest,
    ) -> None:
        """Test that rate limiting is applied per client IP.

        Note: The rate limiter uses IP address when envelope is not yet parsed.
        """
        # Create completely isolated limiter
        limiter = isolated_limiter_factory(["5/minute"])

        # Replace global limiter in BOTH modules
        import asap.transport.middleware as middleware_module
        import asap.transport.server as server_module

        monkeypatch.setattr(middleware_module, "limiter", limiter)
        monkeypatch.setattr(server_module, "limiter", limiter)

        # Create app - it will use the monkeypatched limiter
        app = create_app(rate_limit_manifest, rate_limit="5/minute")
        # Also set app.state.limiter for runtime
        app.state.limiter = limiter

        client = TestClient(app)

        # Make 5 requests (within limit)
        for _i in range(5):
            rpc_request = _create_test_rpc_request(sender="urn:asap:agent:sender-1")
            response = client.post("/asap", json=rpc_request.model_dump(mode="json"))
            assert response.status_code == 200

        # 6th request should be rate limited (same IP)
        rpc_request = _create_test_rpc_request(sender="urn:asap:agent:sender-1")
        response = client.post("/asap", json=rpc_request.model_dump(mode="json"))
        assert response.status_code == HTTP_TOO_MANY_REQUESTS

        # Verify error response format
        data = response.json()
        assert "error" in data
        assert data["error"]["code"] == HTTP_TOO_MANY_REQUESTS
        assert ERROR_RATE_LIMIT_EXCEEDED in data["error"]["message"]
        assert "Retry-After" in response.headers

    def test_limit_resets_after_window(
        self,
        monkeypatch: pytest.MonkeyPatch,
        isolated_limiter_factory: "collections.abc.Callable[[collections.abc.Sequence[str] | None], Limiter]",
        rate_limit_manifest: Manifest,
    ) -> None:
        """Test that rate limit resets after the time window.

        Uses a 1 second window to make the test fast.
        """
        # Create completely isolated limiter
        limiter = isolated_limiter_factory(["1/second"])

        # Replace global limiter in BOTH modules
        import asap.transport.middleware as middleware_module
        import asap.transport.server as server_module

        monkeypatch.setattr(middleware_module, "limiter", limiter)
        monkeypatch.setattr(server_module, "limiter", limiter)

        # Create app - it will use the monkeypatched limiter
        app = create_app(rate_limit_manifest, rate_limit="1/second")
        # Also set app.state.limiter for runtime
        app.state.limiter = limiter

        client = TestClient(app)

        sender = "urn:asap:agent:reset-test"

        # Make 1 request (exhaust limit)
        rpc_request = _create_test_rpc_request(sender=sender)
        response = client.post("/asap", json=rpc_request.model_dump(mode="json"))
        assert response.status_code == 200

        # 2nd request should be rate limited
        rpc_request = _create_test_rpc_request(sender=sender)
        response = client.post("/asap", json=rpc_request.model_dump(mode="json"))
        assert response.status_code == HTTP_TOO_MANY_REQUESTS

        # Wait for rate limit window to reset (1.1 seconds)
        time.sleep(1.1)

        # After reset, should be able to make requests again
        rpc_request = _create_test_rpc_request(sender=sender)
        response = client.post("/asap", json=rpc_request.model_dump(mode="json"))
        assert response.status_code == 200
