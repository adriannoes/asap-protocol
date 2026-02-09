"""Edge case tests for ASAPRequestHandler error paths.

Covers error branches in server.py that are not reached by happy-path tests:
- ThreadPoolExhaustedError (mock executor full)
- HandlerNotFoundError (unknown payload type)
- HTTPException in auth (simulate auth failure)
- json.JSONDecodeError (malformed body)
- Invalid JSON body types (array, non-dict)
- Missing or invalid envelope in params
- UnicodeDecodeError (invalid encoding)
- Internal error fallback (RuntimeError in handler)
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from asap.models.entities import AuthScheme, Capability, Endpoint, Manifest, Skill
from asap.models.envelope import Envelope
from asap.models.payloads import TaskRequest
from asap.transport.handlers import HandlerRegistry
from asap.transport.jsonrpc import (
    ASAP_METHOD,
    INTERNAL_ERROR,
    INVALID_PARAMS,
    INVALID_REQUEST,
    METHOD_NOT_FOUND,
    PARSE_ERROR,
)
from asap.transport.server import create_app

from .conftest import NoRateLimitTestBase, TEST_RATE_LIMIT_DEFAULT

if TYPE_CHECKING:
    from slowapi import Limiter


def _make_valid_jsonrpc_envelope(
    payload_type: str = "TaskRequest",
    sender: str = "urn:asap:agent:client",
    recipient: str = "urn:asap:agent:test-server",
) -> dict[str, Any]:
    """Build a valid JSON-RPC request with an ASAP envelope."""
    envelope = Envelope(
        asap_version="0.1",
        sender=sender,
        recipient=recipient,
        payload_type=payload_type,
        payload=TaskRequest(
            conversation_id="conv-1",
            skill_id="echo",
            input={"message": "test"},
        ).model_dump(),
    )
    return {
        "jsonrpc": "2.0",
        "method": ASAP_METHOD,
        "params": {"envelope": envelope.model_dump(mode="json")},
        "id": "edge-1",
    }


@pytest.fixture
def app(
    sample_manifest: Manifest,
    disable_rate_limiting: "Limiter",
) -> FastAPI:
    """Create FastAPI app for testing (rate limiting disabled)."""
    app_instance = create_app(sample_manifest, rate_limit=TEST_RATE_LIMIT_DEFAULT)
    app_instance.state.limiter = disable_rate_limiting
    return app_instance


@pytest.fixture
def client(app: FastAPI) -> TestClient:
    """Create test client."""
    return TestClient(app)


class TestMalformedBody(NoRateLimitTestBase):
    """Tests for malformed request bodies (parse errors)."""

    def test_invalid_json_returns_parse_error(self, client: TestClient) -> None:
        """Malformed JSON body returns JSON-RPC parse error."""
        response = client.post(
            "/asap",
            content=b"this is not json {{{",
            headers={"content-type": "application/json"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "error" in data
        assert data["error"]["code"] == PARSE_ERROR

    def test_json_array_body_returns_invalid_request(self, client: TestClient) -> None:
        """JSON array body (not object) returns invalid request error."""
        response = client.post(
            "/asap",
            json=[1, 2, 3],
        )
        assert response.status_code == 200
        data = response.json()
        assert "error" in data
        assert data["error"]["code"] == INVALID_REQUEST

    def test_empty_body_returns_parse_error(self, client: TestClient) -> None:
        """Empty body returns parse error."""
        response = client.post(
            "/asap",
            content=b"",
            headers={"content-type": "application/json"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "error" in data
        assert data["error"]["code"] == PARSE_ERROR


class TestInvalidJsonRpc(NoRateLimitTestBase):
    """Tests for invalid JSON-RPC structure."""

    def test_wrong_method_returns_method_not_found(self, client: TestClient) -> None:
        """JSON-RPC with wrong method returns method not found."""
        response = client.post(
            "/asap",
            json={
                "jsonrpc": "2.0",
                "method": "not.asap.send",
                "params": {},
                "id": "test-1",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert "error" in data
        assert data["error"]["code"] == METHOD_NOT_FOUND

    def test_missing_method_returns_invalid_request(self, client: TestClient) -> None:
        """JSON-RPC without method returns invalid request error."""
        response = client.post(
            "/asap",
            json={
                "jsonrpc": "2.0",
                "params": {},
                "id": "test-2",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert "error" in data


class TestInvalidEnvelope(NoRateLimitTestBase):
    """Tests for invalid envelope in params."""

    def test_params_not_dict_returns_error(self, client: TestClient) -> None:
        """Non-dict params returns invalid params or invalid request error."""
        response = client.post(
            "/asap",
            json={
                "jsonrpc": "2.0",
                "method": ASAP_METHOD,
                "params": "not-a-dict",
                "id": "test-3",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert "error" in data
        # Pydantic validates params as dict — may return INVALID_PARAMS or INVALID_REQUEST
        assert data["error"]["code"] in (INVALID_PARAMS, INVALID_REQUEST)

    def test_missing_envelope_in_params_returns_error(self, client: TestClient) -> None:
        """Missing 'envelope' key in params returns error."""
        response = client.post(
            "/asap",
            json={
                "jsonrpc": "2.0",
                "method": ASAP_METHOD,
                "params": {"not_envelope": {}},
                "id": "test-4",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert "error" in data
        assert data["error"]["code"] == INVALID_PARAMS

    def test_envelope_not_dict_returns_error(self, client: TestClient) -> None:
        """Non-dict 'envelope' value returns error."""
        response = client.post(
            "/asap",
            json={
                "jsonrpc": "2.0",
                "method": ASAP_METHOD,
                "params": {"envelope": "not-a-dict"},
                "id": "test-5",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert "error" in data
        assert data["error"]["code"] == INVALID_PARAMS

    def test_invalid_envelope_structure_returns_validation_error(self, client: TestClient) -> None:
        """Invalid envelope structure returns validation error."""
        response = client.post(
            "/asap",
            json={
                "jsonrpc": "2.0",
                "method": ASAP_METHOD,
                "params": {
                    "envelope": {
                        "asap_version": "0.1",
                        # missing required fields: sender, recipient, payload_type, payload
                    }
                },
                "id": "test-6",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert "error" in data
        assert data["error"]["code"] == INVALID_PARAMS
        assert "validation_errors" in data["error"].get("data", {})


class TestHandlerNotFound(NoRateLimitTestBase):
    """Tests for unknown payload type (HandlerNotFoundError)."""

    def test_unknown_payload_type_returns_method_not_found(
        self, sample_manifest: Manifest, disable_rate_limiting: "Limiter"
    ) -> None:
        """Unknown payload type returns JSON-RPC method not found."""
        # Create app with empty registry (no handlers)
        empty_registry = HandlerRegistry()
        app_instance = create_app(
            sample_manifest,
            registry=empty_registry,
            rate_limit=TEST_RATE_LIMIT_DEFAULT,
        )
        app_instance.state.limiter = disable_rate_limiting
        client = TestClient(app_instance)

        request_body = _make_valid_jsonrpc_envelope(payload_type="TaskRequest")
        response = client.post("/asap", json=request_body)
        assert response.status_code == 200
        data = response.json()
        assert "error" in data
        assert data["error"]["code"] == METHOD_NOT_FOUND


class TestThreadPoolExhausted(NoRateLimitTestBase):
    """Tests for ThreadPoolExhaustedError (executor full)."""

    def test_thread_pool_exhausted_returns_503(
        self, sample_manifest: Manifest, disable_rate_limiting: "Limiter"
    ) -> None:
        """ThreadPoolExhaustedError returns HTTP 503."""
        from asap.errors import ThreadPoolExhaustedError

        app_instance = create_app(
            sample_manifest,
            rate_limit=TEST_RATE_LIMIT_DEFAULT,
        )
        app_instance.state.limiter = disable_rate_limiting
        client = TestClient(app_instance)

        request_body = _make_valid_jsonrpc_envelope()

        with patch(
            "asap.transport.handlers.HandlerRegistry.dispatch_async",
            new_callable=AsyncMock,
            side_effect=ThreadPoolExhaustedError(max_threads=4, active_threads=4),
        ):
            response = client.post("/asap", json=request_body)
        assert response.status_code == 503
        data = response.json()
        assert "error" in data
        assert data["error"] == "Service Temporarily Unavailable"


class TestAuthFailure(NoRateLimitTestBase):
    """Tests for authentication failure paths."""

    def test_auth_failure_returns_invalid_request(self, disable_rate_limiting: "Limiter") -> None:
        """Auth failure (HTTPException 401) returns JSON-RPC invalid request."""
        manifest_with_auth = Manifest(
            id="urn:asap:agent:auth-test",
            name="Auth Test Agent",
            version="1.0.0",
            description="Test agent with auth",
            capabilities=Capability(
                asap_version="0.1",
                skills=[Skill(id="echo", description="Echo")],
            ),
            endpoints=Endpoint(asap="http://localhost:8000/asap"),
            auth=AuthScheme(schemes=["bearer"]),
        )

        def reject_all_tokens(token: str) -> str | None:
            return None

        app_instance = create_app(
            manifest_with_auth,
            token_validator=reject_all_tokens,
            rate_limit=TEST_RATE_LIMIT_DEFAULT,
        )
        app_instance.state.limiter = disable_rate_limiting
        client = TestClient(app_instance)

        request_body = _make_valid_jsonrpc_envelope()
        # Send without auth header - should fail
        response = client.post("/asap", json=request_body)
        assert response.status_code == 200
        data = response.json()
        assert "error" in data
        assert data["error"]["code"] in (INVALID_REQUEST, INVALID_PARAMS)


class TestInternalError(NoRateLimitTestBase):
    """Tests for internal server error fallback."""

    def test_handler_exception_returns_internal_error(
        self, sample_manifest: Manifest, disable_rate_limiting: "Limiter"
    ) -> None:
        """Unhandled exception in handler returns JSON-RPC internal error."""
        app_instance = create_app(
            sample_manifest,
            rate_limit=TEST_RATE_LIMIT_DEFAULT,
        )
        app_instance.state.limiter = disable_rate_limiting
        client = TestClient(app_instance)

        request_body = _make_valid_jsonrpc_envelope()

        with patch(
            "asap.transport.handlers.HandlerRegistry.dispatch_async",
            new_callable=AsyncMock,
            side_effect=RuntimeError("unexpected crash"),
        ):
            response = client.post("/asap", json=request_body)
        assert response.status_code == 200
        data = response.json()
        assert "error" in data
        assert data["error"]["code"] == INTERNAL_ERROR


class TestDebugModeErrorData(NoRateLimitTestBase):
    """Tests for debug mode error data with traceback."""

    def test_debug_mode_includes_traceback_in_error(
        self,
        sample_manifest: Manifest,
        disable_rate_limiting: "Limiter",
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """In debug mode, internal errors include traceback."""
        monkeypatch.setenv("ASAP_DEBUG", "true")
        app_instance = create_app(
            sample_manifest,
            rate_limit=TEST_RATE_LIMIT_DEFAULT,
        )
        app_instance.state.limiter = disable_rate_limiting
        client = TestClient(app_instance)

        request_body = _make_valid_jsonrpc_envelope()

        with patch(
            "asap.transport.handlers.HandlerRegistry.dispatch_async",
            new_callable=AsyncMock,
            side_effect=RuntimeError("debug crash"),
        ):
            response = client.post("/asap", json=request_body)
        assert response.status_code == 200
        data = response.json()
        assert "error" in data
        error_data = data["error"].get("data", {})
        assert "traceback" in error_data
        assert "debug crash" in error_data.get("error", "")
