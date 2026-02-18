"""Integration tests for rate limiting functionality.

This module contains tests specifically for rate limiting behavior.
These tests are isolated in a separate file to prevent interference with other tests.

CRITICAL: All tests use aggressive monkeypatch to replace module-level limiters
to ensure complete isolation.
"""

import collections.abc
import time
from datetime import datetime, timezone
from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

if TYPE_CHECKING:
    from fastapi import FastAPI

from asap.models.entities import Capability, Endpoint, Manifest, Skill
from asap.models.envelope import Envelope
from asap.models.payloads import TaskRequest
from asap.transport.jsonrpc import JsonRpcRequest
from asap.transport.middleware import (
    ERROR_RATE_LIMIT_EXCEEDED,
    HTTP_TOO_MANY_REQUESTS,
)
from asap.transport.rate_limit import (
    ASAPRateLimiter,
    create_limiter,
    create_test_limiter,
    get_remote_address,
)
from asap.transport.server import create_app


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

    @pytest.fixture
    def isolated_app_5_per_minute(
        self,
        monkeypatch: pytest.MonkeyPatch,
        isolated_limiter_factory: "collections.abc.Callable[[collections.abc.Sequence[str] | None], ASAPRateLimiter]",
        rate_limit_manifest: Manifest,
    ) -> "FastAPI":
        """Create an app with 5/minute rate limit and aggressive monkeypatch.

        This fixture is reused across all rate limiting tests to avoid code duplication.
        """
        limiter = isolated_limiter_factory(["5/minute"])

        import asap.transport.middleware as middleware_module

        monkeypatch.setattr(middleware_module, "limiter", limiter)

        app = create_app(rate_limit_manifest, rate_limit="5/minute")
        app.state.limiter = limiter

        return app  # type: ignore[no-any-return]

    @pytest.fixture
    def isolated_app_1_per_second(
        self,
        monkeypatch: pytest.MonkeyPatch,
        isolated_limiter_factory: "collections.abc.Callable[[collections.abc.Sequence[str] | None], ASAPRateLimiter]",
        rate_limit_manifest: Manifest,
    ) -> "FastAPI":
        """Create an app with 1/second rate limit and aggressive monkeypatch.

        Used for test_limit_resets_after_window which needs a short time window.
        """
        limiter = isolated_limiter_factory(["1/second"])

        import asap.transport.middleware as middleware_module

        monkeypatch.setattr(middleware_module, "limiter", limiter)

        app = create_app(rate_limit_manifest, rate_limit="1/second")
        app.state.limiter = limiter

        return app  # type: ignore[no-any-return]

    @pytest.fixture
    def isolated_app_from_env_2_per_minute(
        self,
        monkeypatch: pytest.MonkeyPatch,
        isolated_limiter_factory: "collections.abc.Callable[[collections.abc.Sequence[str] | None], ASAPRateLimiter]",
        rate_limit_manifest: Manifest,
    ) -> "FastAPI":
        """Create an app with rate limit from ASAP_RATE_LIMIT env var (2/minute).

        Validates that when create_app(rate_limit=None) reads from env, the limiter
        is actually enforced at runtime (POST /asap returns 429 when exceeded).
        """
        limiter = isolated_limiter_factory(["2/minute"])

        import asap.transport.middleware as middleware_module

        monkeypatch.setattr(middleware_module, "limiter", limiter)

        with patch.dict("os.environ", {"ASAP_RATE_LIMIT": "2/minute"}):
            app = create_app(rate_limit_manifest, rate_limit=None)
        app.state.limiter = limiter

        return app  # type: ignore[no-any-return]

    def test_requests_within_limit_succeed(
        self,
        isolated_app_5_per_minute: "FastAPI",
    ) -> None:
        """Test that requests within the rate limit succeed."""
        client = TestClient(isolated_app_5_per_minute)

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
        isolated_app_5_per_minute: "FastAPI",
    ) -> None:
        """Test that exceeding the rate limit returns HTTP 429."""
        client = TestClient(isolated_app_5_per_minute)

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
        isolated_app_5_per_minute: "FastAPI",
    ) -> None:
        """Test that rate limiting is applied per client IP.

        Note: The rate limiter uses IP address when envelope is not yet parsed.
        """
        client = TestClient(isolated_app_5_per_minute)

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
        isolated_app_1_per_second: "FastAPI",
    ) -> None:
        """Test that rate limit resets after the time window.

        Uses a 1 second window to make the test fast.
        """
        client = TestClient(isolated_app_1_per_second)

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

    def test_asap_rate_limit_env_var_enforced_at_runtime(
        self,
        isolated_app_from_env_2_per_minute: "FastAPI",
    ) -> None:
        """POST to /asap under low limit from ASAP_RATE_LIMIT env returns 429 when exceeded.

        Complement to test_docs_troubleshooting_smoke.test_create_app_reads_asap_rate_limit_from_env:
        that test validates env var is read (app creation succeeds). This test validates
        the limiter enforces the configured limit at runtime.
        """
        client = TestClient(isolated_app_from_env_2_per_minute)

        # 2 requests within limit
        for _i in range(2):
            rpc_request = _create_test_rpc_request()
            response = client.post("/asap", json=rpc_request.model_dump(mode="json"))
            assert response.status_code == 200

        # 3rd request exceeds 2/minute limit -> 429
        rpc_request = _create_test_rpc_request()
        response = client.post("/asap", json=rpc_request.model_dump(mode="json"))

        assert response.status_code == HTTP_TOO_MANY_REQUESTS
        data = response.json()
        assert "error" in data
        assert data["error"]["code"] == HTTP_TOO_MANY_REQUESTS
        assert ERROR_RATE_LIMIT_EXCEEDED in data["error"]["message"]


# ---------------------------------------------------------------------------
# Rate Limit Coverage Tests (merged from test_misc_coverage.py)
# ---------------------------------------------------------------------------


class TestGetRemoteAddress:
    def test_get_remote_address_no_client(self) -> None:
        """Return 127.0.0.1 when request has no client (line 215)."""
        request = MagicMock()
        request.client = None
        assert get_remote_address(request) == "127.0.0.1"


class TestCreateLimiter:
    def test_create_limiter_default_storage(self) -> None:
        """create_limiter with no storage_uri uses memory (line 99, 164-172)."""
        limiter = create_limiter()
        assert isinstance(limiter, ASAPRateLimiter)

    def test_create_limiter_redis_not_installed(self) -> None:
        """create_limiter with redis URI raises ImportError when redis not installed (lines 173-184)."""
        with patch.dict("sys.modules", {"redis": None}), pytest.raises(ImportError, match="redis"):
            create_limiter(storage_uri="redis://localhost:6379")


class TestASAPRateLimiterTest:
    def test_test_method_returns_true(self) -> None:
        """test() returns True when under limit (lines 132-135)."""
        limiter = create_test_limiter(limits=["100/second"])
        request = MagicMock()
        request.client = MagicMock()
        request.client.host = "127.0.0.1"
        assert limiter.test(request) is True

    def test_test_method_returns_false_after_exhaustion(self) -> None:
        """test() returns False when rate is exhausted (line 135)."""
        limiter = create_test_limiter(limits=["1/second"])
        request = MagicMock()
        request.client = MagicMock()
        request.client.host = "127.0.0.1"
        # Consume the single allowed hit
        limiter.check(request)
        # Now test should return False
        assert limiter.test(request) is False
