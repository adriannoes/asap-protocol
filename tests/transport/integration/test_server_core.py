"""Core server tests without rate limiting.

This module contains tests for core server functionality that should not
be affected by rate limiting. All test classes inherit from NoRateLimitTestBase
to ensure rate limiting is completely disabled.
"""

from typing import TYPE_CHECKING

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

if TYPE_CHECKING:
    from slowapi import Limiter

from asap.models.entities import AuthScheme, Capability, Endpoint, Manifest, Skill
from asap.models.enums import TaskStatus
from asap.models.envelope import Envelope
from asap.models.payloads import TaskRequest, TaskResponse
from asap.observability import get_metrics, reset_metrics
from asap.transport.handlers import HandlerRegistry
from asap.transport.jsonrpc import (
    INVALID_PARAMS,
    INVALID_REQUEST,
    METHOD_NOT_FOUND,
    JsonRpcErrorResponse,
    JsonRpcRequest,
    JsonRpcResponse,
)
from asap.transport.server import create_app

from ..conftest import NoRateLimitTestBase, TEST_RATE_LIMIT_DEFAULT


@pytest.fixture
def app(
    sample_manifest: Manifest,
    disable_rate_limiting: "Limiter",
) -> FastAPI:
    """Create FastAPI app for testing (rate limiting disabled via NoRateLimitTestBase)."""
    app_instance = create_app(
        sample_manifest, rate_limit=TEST_RATE_LIMIT_DEFAULT
    )
    app_instance.state.limiter = disable_rate_limiting
    return app_instance  # type: ignore[no-any-return]


@pytest.fixture
def client(app: FastAPI) -> TestClient:
    """Create test client."""
    return TestClient(app)


class TestAsapEndpoint(NoRateLimitTestBase):
    """Tests for POST /asap endpoint."""

    def test_asap_endpoint_accepts_json_rpc_request(self, client: TestClient) -> None:
        """Test that /asap endpoint accepts valid JSON-RPC requests."""
        # Create a minimal ASAP envelope
        envelope = Envelope(
            asap_version="0.1",
            sender="urn:asap:agent:client",
            recipient="urn:asap:agent:test-server",
            payload_type="task.request",
            payload=TaskRequest(
                conversation_id="conv-123",
                skill_id="echo",
                input={"message": "test"},
            ).model_dump(),
        )

        # Wrap in JSON-RPC
        rpc_request = JsonRpcRequest(
            method="asap.send",
            params={"envelope": envelope.model_dump(mode="json")},
            id="test-req-1",
        )

        response = client.post("/asap", json=rpc_request.model_dump())

        assert response.status_code == 200
        assert "jsonrpc" in response.json()
        assert response.json()["jsonrpc"] == "2.0"

    def test_asap_endpoint_returns_json_rpc_response(self, client: TestClient) -> None:
        """Test that /asap endpoint returns JSON-RPC response format."""
        envelope = Envelope(
            asap_version="0.1",
            sender="urn:asap:agent:client",
            recipient="urn:asap:agent:test-server",
            payload_type="task.request",
            payload=TaskRequest(
                conversation_id="conv-123",
                skill_id="echo",
                input={"message": "test"},
            ).model_dump(),
        )

        rpc_request = JsonRpcRequest(
            method="asap.send",
            params={"envelope": envelope.model_dump(mode="json")},
            id="test-req-2",
        )

        response = client.post("/asap", json=rpc_request.model_dump())

        assert response.status_code == 200

        response_data = response.json()

        # If there's an error, it should be a valid error response
        if "error" in response_data:
            error_response = JsonRpcErrorResponse(**response_data)
            # Fail the test but show the error details
            pytest.fail(
                f"Server returned error: {error_response.error.message} - "
                f"Data: {error_response.error.data}"
            )

        rpc_response = JsonRpcResponse(**response_data)
        assert rpc_response.id == "test-req-2"
        assert "envelope" in rpc_response.result

    def test_asap_endpoint_correlates_request_and_response_ids(self, client: TestClient) -> None:
        """Test that response id matches request id."""
        envelope = Envelope(
            asap_version="0.1",
            sender="urn:asap:agent:client",
            recipient="urn:asap:agent:test-server",
            payload_type="task.request",
            payload=TaskRequest(
                conversation_id="conv-123",
                skill_id="echo",
                input={"message": "correlation test"},
            ).model_dump(),
        )

        request_id = "correlation-test-id"
        rpc_request = JsonRpcRequest(
            method="asap.send",
            params={"envelope": envelope.model_dump(mode="json")},
            id=request_id,
        )

        response = client.post("/asap", json=rpc_request.model_dump())

        assert response.status_code == 200
        assert response.json()["id"] == request_id

    def test_asap_endpoint_handles_malformed_json(self, client: TestClient) -> None:
        """Test that malformed JSON returns appropriate error."""
        response = client.post(
            "/asap",
            content=b"{invalid json",
            headers={"content-type": "application/json"},
        )

        assert response.status_code == 200
        data = response.json()
        assert "error" in data
        # PARSE_ERROR (-32700) is the correct JSON-RPC 2.0 code for invalid JSON
        assert data["error"]["code"] == -32700

    def test_asap_endpoint_handles_invalid_json_rpc(self, client: TestClient) -> None:
        """Test that invalid JSON-RPC structure returns error."""
        # Missing required fields
        invalid_rpc = {
            "jsonrpc": "2.0",
            "method": "asap.send",
            # missing params and id
        }

        response = client.post("/asap", json=invalid_rpc)

        # Should return error response or validation error
        assert response.status_code in [200, 422]  # 200 with error or 422

        if response.status_code == 200:
            data = response.json()
            assert "error" in data or "result" in data

    def test_asap_endpoint_handles_non_dict_body(self, client: TestClient) -> None:
        """Test that non-dict JSON body returns INVALID_REQUEST."""
        # Send array instead of object
        response = client.post("/asap", json=["not", "an", "object"])

        assert response.status_code == 200
        data = response.json()
        assert "error" in data
        assert data["error"]["code"] == INVALID_REQUEST
        assert "object" in data["error"]["data"]["error"].lower()

    def test_asap_endpoint_handles_string_body(self, client: TestClient) -> None:
        """Test that string JSON body returns INVALID_REQUEST."""
        # Send string instead of object
        response = client.post("/asap", json="not an object")

        assert response.status_code == 200
        data = response.json()
        assert "error" in data
        assert data["error"]["code"] == INVALID_REQUEST

    def test_asap_endpoint_handles_non_dict_params(self, client: TestClient) -> None:
        """Test that non-dict params returns INVALID_PARAMS."""
        # Params as array
        invalid_rpc = {
            "jsonrpc": "2.0",
            "method": "asap.send",
            "params": ["not", "an", "object"],
            "id": "test-1",
        }

        response = client.post("/asap", json=invalid_rpc)

        assert response.status_code == 200
        data = response.json()
        assert "error" in data
        assert data["error"]["code"] == INVALID_PARAMS
        assert data["error"]["data"]["error"] == "JSON-RPC 'params' must be an object"

    def test_asap_endpoint_handles_none_params(self, client: TestClient) -> None:
        """Test that None params returns INVALID_PARAMS."""
        # Params as None (if JSON allows it)
        invalid_rpc = {
            "jsonrpc": "2.0",
            "method": "asap.send",
            "params": None,
            "id": "test-2",
        }

        response = client.post("/asap", json=invalid_rpc)

        assert response.status_code == 200
        data = response.json()
        assert "error" in data
        assert data["error"]["code"] == INVALID_PARAMS

    def test_asap_endpoint_handles_missing_envelope(self, client: TestClient) -> None:
        """Test that request without envelope returns error."""
        rpc_request = JsonRpcRequest(
            method="asap.send",
            params={},  # No envelope
            id="missing-envelope",
        )

        response = client.post("/asap", json=rpc_request.model_dump())

        assert response.status_code == 200

        # Should return JSON-RPC error
        error_response = JsonRpcErrorResponse(**response.json())
        assert error_response.error.code == INVALID_PARAMS
        assert error_response.id == "missing-envelope"

    def test_asap_endpoint_handles_invalid_envelope(self, client: TestClient) -> None:
        """Test that invalid envelope structure returns error."""
        rpc_request = JsonRpcRequest(
            method="asap.send",
            params={
                "envelope": {
                    # Invalid envelope - missing required fields
                    "sender": "urn:asap:agent:client",
                    # missing recipient, payload_type, payload
                }
            },
            id="invalid-envelope",
        )

        response = client.post("/asap", json=rpc_request.model_dump())

        assert response.status_code == 200

        # Should return JSON-RPC error
        error_response = JsonRpcErrorResponse(**response.json())
        assert error_response.error.code == INVALID_PARAMS
        assert error_response.id == "invalid-envelope"

    def test_asap_endpoint_handles_unknown_method(self, client: TestClient) -> None:
        """Test that unknown JSON-RPC method returns error."""
        rpc_request = JsonRpcRequest(
            method="unknown.method",
            params={},
            id="unknown-method",
        )

        response = client.post("/asap", json=rpc_request.model_dump())

        assert response.status_code == 200

        # Should return JSON-RPC error
        data = response.json()
        assert "error" in data
        assert data["id"] == "unknown-method"


class TestHandlerRegistryIntegration(NoRateLimitTestBase):
    """Tests for HandlerRegistry integration with server."""

    def test_create_app_with_custom_registry(self, sample_manifest: Manifest) -> None:
        """Test create_app accepts custom HandlerRegistry."""
        registry = HandlerRegistry()
        app = create_app(sample_manifest, registry)

        assert isinstance(app, FastAPI)

    def test_create_app_uses_default_registry_when_none(self, sample_manifest: Manifest) -> None:
        """Test create_app uses default registry when not provided."""
        app = create_app(sample_manifest)

        # Should work without explicit registry
        assert isinstance(app, FastAPI)

    def test_custom_handler_is_called(self, sample_manifest: Manifest) -> None:
        """Test that custom registered handler is called for requests."""
        registry = HandlerRegistry()
        handler_called = {"count": 0}

        def custom_handler(envelope: Envelope, manifest: Manifest) -> Envelope:
            handler_called["count"] += 1
            return Envelope(
                asap_version="0.1",
                sender=manifest.id,
                recipient=envelope.sender,
                payload_type="task.response",
                payload=TaskResponse(
                    task_id="custom-task-123",
                    status=TaskStatus.COMPLETED,
                    result={"custom": True, "original_input": envelope.payload},
                ).model_dump(),
                correlation_id=envelope.id,
            )

        registry.register("task.request", custom_handler)
        app = create_app(sample_manifest, registry)
        client = TestClient(app)

        envelope = Envelope(
            asap_version="0.1",
            sender="urn:asap:agent:client",
            recipient="urn:asap:agent:test-server",
            payload_type="task.request",
            payload=TaskRequest(
                conversation_id="conv-custom",
                skill_id="test",
                input={"test": "data"},
            ).model_dump(),
        )

        rpc_request = JsonRpcRequest(
            method="asap.send",
            params={"envelope": envelope.model_dump(mode="json")},
            id="custom-handler-test",
        )

        response = client.post("/asap", json=rpc_request.model_dump())

        assert response.status_code == 200
        assert handler_called["count"] == 1

        # Verify custom response
        rpc_response = JsonRpcResponse(**response.json())
        response_envelope = Envelope(**rpc_response.result["envelope"])
        response_payload = TaskResponse(**response_envelope.payload)
        assert response_payload.task_id == "custom-task-123"
        assert response_payload.result is not None
        assert response_payload.result.get("custom") is True

    def test_unknown_payload_type_returns_method_not_found(self, sample_manifest: Manifest) -> None:
        """Test that unknown payload type returns METHOD_NOT_FOUND error."""
        # Create registry without handler for "unknown.type"
        registry = HandlerRegistry()
        # Only register task.request handler
        registry.register("task.request", lambda e, m: e)

        app = create_app(sample_manifest, registry)
        client = TestClient(app)

        # Send envelope with unregistered payload type
        envelope = Envelope(
            asap_version="0.1",
            sender="urn:asap:agent:client",
            recipient="urn:asap:agent:test-server",
            payload_type="unknown.payload.type",
            payload={"some": "data"},
        )

        rpc_request = JsonRpcRequest(
            method="asap.send",
            params={"envelope": envelope.model_dump(mode="json")},
            id="unknown-type-test",
        )

        response = client.post("/asap", json=rpc_request.model_dump())

        assert response.status_code == 200

        # Should return JSON-RPC error
        error_response = JsonRpcErrorResponse(**response.json())
        assert error_response.error.code == METHOD_NOT_FOUND
        assert error_response.id == "unknown-type-test"
        assert error_response.error.data is not None
        assert error_response.error.data.get("payload_type") == "unknown.payload.type"

    def test_empty_registry_returns_error_for_all_types(self, sample_manifest: Manifest) -> None:
        """Test that empty registry returns error for any payload type."""
        registry = HandlerRegistry()  # No handlers registered
        app = create_app(sample_manifest, registry)
        client = TestClient(app)

        envelope = Envelope(
            asap_version="0.1",
            sender="urn:asap:agent:client",
            recipient="urn:asap:agent:test-server",
            payload_type="task.request",
            payload=TaskRequest(
                conversation_id="conv-123",
                skill_id="echo",
                input={"message": "test"},
            ).model_dump(),
        )

        rpc_request = JsonRpcRequest(
            method="asap.send",
            params={"envelope": envelope.model_dump(mode="json")},
            id="empty-registry-test",
        )

        response = client.post("/asap", json=rpc_request.model_dump())

        assert response.status_code == 200
        error_response = JsonRpcErrorResponse(**response.json())
        assert error_response.error.code == METHOD_NOT_FOUND


class TestMetricsEndpoint(NoRateLimitTestBase):
    """Tests for GET /asap/metrics endpoint."""

    @pytest.fixture(autouse=True)
    def reset_metrics_before_test(self) -> None:
        """Reset metrics before each test."""
        reset_metrics()

    def test_metrics_endpoint_exists(self, app: FastAPI) -> None:
        """Test that metrics endpoint is registered."""
        routes = [route.path for route in app.routes]  # type: ignore[attr-defined]
        assert "/asap/metrics" in routes

    def test_metrics_endpoint_returns_prometheus_format(self, client: TestClient) -> None:
        """Test that metrics endpoint returns Prometheus/OpenMetrics text format."""
        response = client.get("/asap/metrics")

        assert response.status_code == 200
        content_type = response.headers.get("content-type", "")
        assert "text/plain" in content_type or "openmetrics-text" in content_type

        content = response.text
        assert "# HELP" in content
        assert "# TYPE" in content

    def test_metrics_endpoint_contains_request_metrics(self, client: TestClient) -> None:
        """Test that metrics endpoint contains request-related metrics."""
        response = client.get("/asap/metrics")

        assert response.status_code == 200
        content = response.text

        assert "asap_requests_total" in content
        assert "asap_requests_success_total" in content
        assert "asap_requests_error_total" in content
        assert "asap_request_duration_seconds" in content
        assert "asap_process_uptime_seconds" in content

    def test_metrics_updated_on_successful_request(self, client: TestClient) -> None:
        """Test that metrics are updated after successful request."""
        # Make a successful request
        envelope = Envelope(
            asap_version="0.1",
            sender="urn:asap:agent:client",
            recipient="urn:asap:agent:test-server",
            payload_type="task.request",
            payload=TaskRequest(
                conversation_id="conv-metrics-test",
                skill_id="echo",
                input={"message": "metrics test"},
            ).model_dump(),
        )

        rpc_request = JsonRpcRequest(
            method="asap.send",
            params={"envelope": envelope.model_dump(mode="json")},
            id="metrics-test-1",
        )

        client.post("/asap", json=rpc_request.model_dump())

        metrics = get_metrics()
        success_count = metrics.get_counter(
            "asap_requests_success_total",
            {"payload_type": "task.request"},
        )
        assert success_count >= 1.0
        handler_count = metrics.get_counter(
            "asap_handler_executions_total",
            {"payload_type": "task.request"},
        )
        assert handler_count >= 1.0
        handler_duration_count = metrics.get_histogram_count(
            "asap_handler_duration_seconds",
            {"payload_type": "task.request"},
        )
        assert handler_duration_count >= 1.0

    def test_metrics_updated_on_error_request(self, sample_manifest: Manifest) -> None:
        """Test that error metrics are updated on failed request."""
        # Create app with empty registry to trigger handler not found
        registry = HandlerRegistry()
        app = create_app(sample_manifest, registry, rate_limit=TEST_RATE_LIMIT_DEFAULT)
        client = TestClient(app)

        envelope = Envelope(
            asap_version="0.1",
            sender="urn:asap:agent:client",
            recipient="urn:asap:agent:test-server",
            payload_type="task.request",
            payload=TaskRequest(
                conversation_id="conv-error-test",
                skill_id="echo",
                input={"message": "error test"},
            ).model_dump(),
        )

        rpc_request = JsonRpcRequest(
            method="asap.send",
            params={"envelope": envelope.model_dump(mode="json")},
            id="error-metrics-test",
        )

        client.post("/asap", json=rpc_request.model_dump())

        metrics = get_metrics()
        error_count = metrics.get_counter(
            "asap_requests_error_total",
            {"payload_type": "other", "error_type": "handler_not_found"},
        )
        assert error_count >= 1.0

    def test_metrics_histogram_records_duration(self, client: TestClient) -> None:
        """Test that request duration is recorded in histogram."""
        # Make a request
        envelope = Envelope(
            asap_version="0.1",
            sender="urn:asap:agent:client",
            recipient="urn:asap:agent:test-server",
            payload_type="task.request",
            payload=TaskRequest(
                conversation_id="conv-duration-test",
                skill_id="echo",
                input={"message": "duration test"},
            ).model_dump(),
        )

        rpc_request = JsonRpcRequest(
            method="asap.send",
            params={"envelope": envelope.model_dump(mode="json")},
            id="duration-test",
        )

        client.post("/asap", json=rpc_request.model_dump())

        metrics = get_metrics()
        hist_count = metrics.get_histogram_count(
            "asap_request_duration_seconds",
            {"payload_type": "task.request", "status": "success"},
        )
        assert hist_count >= 1.0

    def test_metrics_endpoint_idempotent(self, client: TestClient) -> None:
        """Test that metrics endpoint is idempotent."""
        response1 = client.get("/asap/metrics")
        response2 = client.get("/asap/metrics")

        assert response1.status_code == 200
        assert response2.status_code == 200
        # Both should return valid Prometheus format
        assert "# HELP" in response1.text
        assert "# HELP" in response2.text


class TestServerExceptionHandling(NoRateLimitTestBase):
    """Tests for server exception handling."""

    @pytest.fixture
    def manifest(self) -> Manifest:
        """Create a sample manifest for testing."""
        return Manifest(
            id="urn:asap:agent:test-exception",
            name="Test Exception Server",
            version="1.0.0",
            description="Test server for exception handling",
            capabilities=Capability(
                asap_version="0.1",
                skills=[Skill(id="error", description="Error skill")],
                state_persistence=False,
            ),
            endpoints=Endpoint(asap="http://localhost:8000/asap"),
        )

    def test_handler_exception_returns_internal_error(self, manifest: Manifest) -> None:
        """Test that exceptions in handlers return JSON-RPC internal error."""
        registry = HandlerRegistry()

        def failing_handler(envelope: Envelope, _manifest: Manifest) -> Envelope:
            raise RuntimeError("Intentional test error")

        registry.register("task.request", failing_handler)
        app = create_app(manifest, registry)
        client = TestClient(app, raise_server_exceptions=False)

        envelope = Envelope(
            asap_version="0.1",
            sender="urn:asap:agent:client",
            recipient="urn:asap:agent:test-exception",
            payload_type="task.request",
            payload=TaskRequest(
                conversation_id="conv-error",
                skill_id="error",
                input={"cause": "exception"},
            ).model_dump(),
        )

        rpc_request = JsonRpcRequest(
            method="asap.send",
            params={"envelope": envelope.model_dump(mode="json")},
            id="error-test",
        )

        response = client.post("/asap", json=rpc_request.model_dump())

        assert response.status_code == 200
        data = response.json()
        assert "error" in data
        # Internal error code is -32603
        assert data["error"]["code"] == -32603
        # Production (no ASAP_DEBUG): generic message only
        assert "Internal server error" in data["error"]["data"]["error"]

    def test_handler_exception_records_error_metrics(self, manifest: Manifest) -> None:
        """Test that handler exceptions record error metrics."""
        reset_metrics()
        registry = HandlerRegistry()

        def failing_handler(envelope: Envelope, _manifest: Manifest) -> Envelope:
            raise ValueError("Metrics test error")

        registry.register("task.request", failing_handler)
        app = create_app(manifest, registry)
        client = TestClient(app, raise_server_exceptions=False)

        envelope = Envelope(
            asap_version="0.1",
            sender="urn:asap:agent:client",
            recipient="urn:asap:agent:test-exception",
            payload_type="task.request",
            payload=TaskRequest(
                conversation_id="conv-metrics",
                skill_id="error",
                input={},
            ).model_dump(),
        )

        rpc_request = JsonRpcRequest(
            method="asap.send",
            params={"envelope": envelope.model_dump(mode="json")},
            id="metrics-error-test",
        )

        client.post("/asap", json=rpc_request.model_dump())

        metrics = get_metrics()
        error_count = metrics.get_counter(
            "asap_requests_error_total",
            {"payload_type": "task.request", "error_type": "internal_error"},
        )
        assert error_count >= 1.0


class TestAuthenticationIntegration(NoRateLimitTestBase):
    """Test authentication integration in server.

    All tests inherit from NoRateLimitTestBase to ensure rate limiting
    is completely disabled and doesn't interfere with authentication tests.
    """

    def test_create_app_with_auth_requires_validator(self) -> None:
        """Test that create_app raises ValueError when auth configured without validator."""
        manifest_with_auth = Manifest(
            id="urn:asap:agent:auth-test",
            name="Auth Test Agent",
            version="1.0.0",
            description="Agent with auth",
            capabilities=Capability(
                asap_version="0.1",
                skills=[Skill(id="test", description="Test skill")],
                state_persistence=False,
            ),
            endpoints=Endpoint(asap="http://localhost:8000/asap"),
            auth=AuthScheme(schemes=["bearer"]),
        )

        with pytest.raises(ValueError, match="token_validator is required"):
            create_app(manifest_with_auth, token_validator=None)

    def test_authentication_failure_returns_jsonrpc_error(self) -> None:
        """Test that authentication failure returns proper JSON-RPC error."""
        manifest_with_auth = Manifest(
            id="urn:asap:agent:auth-test",
            name="Auth Test Agent",
            version="1.0.0",
            description="Agent with auth",
            capabilities=Capability(
                asap_version="0.1",
                skills=[Skill(id="test", description="Test skill")],
                state_persistence=False,
            ),
            endpoints=Endpoint(asap="http://localhost:8000/asap"),
            auth=AuthScheme(schemes=["bearer"]),
        )

        def always_reject_validator(token: str) -> str | None:
            return None  # Always reject

        app = create_app(manifest_with_auth, token_validator=always_reject_validator)
        client = TestClient(app, raise_server_exceptions=False)

        envelope = Envelope(
            asap_version="0.1",
            sender="urn:asap:agent:client",
            recipient="urn:asap:agent:auth-test",
            payload_type="task.request",
            payload=TaskRequest(
                conversation_id="conv-1",
                skill_id="test",
                input={},
            ).model_dump(),
        )

        rpc_request = JsonRpcRequest(
            method="asap.send",
            params={"envelope": envelope.model_dump(mode="json")},
            id="auth-fail-test",
        )

        # Send request with invalid token
        response = client.post(
            "/asap",
            json=rpc_request.model_dump(),
            headers={"Authorization": "Bearer invalid-token"},
        )

        assert response.status_code == 200
        data = response.json()
        assert "error" in data
        assert data["error"]["code"] == INVALID_REQUEST
        assert "Invalid authentication token" in data["error"]["data"]["error"]

    def test_sender_mismatch_returns_jsonrpc_error(self) -> None:
        """Test that sender mismatch returns proper JSON-RPC error."""
        manifest_with_auth = Manifest(
            id="urn:asap:agent:auth-test",
            name="Auth Test Agent",
            version="1.0.0",
            description="Agent with auth",
            capabilities=Capability(
                asap_version="0.1",
                skills=[Skill(id="test", description="Test skill")],
                state_persistence=False,
            ),
            endpoints=Endpoint(asap="http://localhost:8000/asap"),
            auth=AuthScheme(schemes=["bearer"]),
        )

        def validator(token: str) -> str | None:
            if token == "valid-token":
                return "urn:asap:agent:authenticated-client"
            return None

        app = create_app(manifest_with_auth, token_validator=validator)
        client = TestClient(app, raise_server_exceptions=False)

        # Create envelope with sender that doesn't match authenticated identity
        envelope = Envelope(
            asap_version="0.1",
            sender="urn:asap:agent:spoofed-sender",  # Different from authenticated agent
            recipient="urn:asap:agent:auth-test",
            payload_type="task.request",
            payload=TaskRequest(
                conversation_id="conv-1",
                skill_id="test",
                input={},
            ).model_dump(),
        )

        rpc_request = JsonRpcRequest(
            method="asap.send",
            params={"envelope": envelope.model_dump(mode="json")},
            id="sender-mismatch-test",
        )

        # Send with valid token but mismatched sender
        response = client.post(
            "/asap",
            json=rpc_request.model_dump(),
            headers={"Authorization": "Bearer valid-token"},
        )

        assert response.status_code == 200
        data = response.json()
        assert "error" in data
        assert data["error"]["code"] == INVALID_PARAMS
        assert "Sender does not match" in data["error"]["data"]["error"]

    def test_authentication_success_processes_request(self) -> None:
        """Test that successful authentication allows request processing."""
        manifest_with_auth = Manifest(
            id="urn:asap:agent:auth-test",
            name="Auth Test Agent",
            version="1.0.0",
            description="Agent with auth",
            capabilities=Capability(
                asap_version="0.1",
                skills=[Skill(id="test", description="Test skill")],
                state_persistence=False,
            ),
            endpoints=Endpoint(asap="http://localhost:8000/asap"),
            auth=AuthScheme(schemes=["bearer"]),
        )

        def validator(token: str) -> str | None:
            if token == "valid-token":
                return "urn:asap:agent:client"
            return None

        app = create_app(manifest_with_auth, token_validator=validator)
        client = TestClient(app, raise_server_exceptions=False)

        # Create envelope with correct sender
        envelope = Envelope(
            asap_version="0.1",
            sender="urn:asap:agent:client",  # Matches authenticated agent
            recipient="urn:asap:agent:auth-test",
            payload_type="task.request",
            payload=TaskRequest(
                conversation_id="conv-1",
                skill_id="test",
                input={"message": "authenticated request"},
            ).model_dump(),
        )

        rpc_request = JsonRpcRequest(
            method="asap.send",
            params={"envelope": envelope.model_dump(mode="json")},
            id="auth-success-test",
        )

        # Send with valid token and matching sender
        response = client.post(
            "/asap",
            json=rpc_request.model_dump(),
            headers={"Authorization": "Bearer valid-token"},
        )

        assert response.status_code == 200
        data = response.json()
        assert "result" in data
        assert data["id"] == "auth-success-test"

    def test_authentication_missing_header_returns_error(self) -> None:
        """Test that missing auth header returns proper error."""
        manifest_with_auth = Manifest(
            id="urn:asap:agent:auth-test",
            name="Auth Test Agent",
            version="1.0.0",
            description="Agent with auth",
            capabilities=Capability(
                asap_version="0.1",
                skills=[Skill(id="test", description="Test skill")],
                state_persistence=False,
            ),
            endpoints=Endpoint(asap="http://localhost:8000/asap"),
            auth=AuthScheme(schemes=["bearer"]),
        )

        def validator(token: str) -> str | None:
            return "urn:asap:agent:client"

        app = create_app(manifest_with_auth, token_validator=validator)
        client = TestClient(app, raise_server_exceptions=False)

        envelope = Envelope(
            asap_version="0.1",
            sender="urn:asap:agent:client",
            recipient="urn:asap:agent:auth-test",
            payload_type="task.request",
            payload=TaskRequest(
                conversation_id="conv-1",
                skill_id="test",
                input={},
            ).model_dump(),
        )

        rpc_request = JsonRpcRequest(
            method="asap.send",
            params={"envelope": envelope.model_dump(mode="json")},
            id="no-auth-test",
        )

        # Send without Authorization header
        response = client.post("/asap", json=rpc_request.model_dump())

        assert response.status_code == 200
        data = response.json()
        assert "error" in data
        assert data["error"]["code"] == INVALID_REQUEST
        assert "Authentication required" in data["error"]["data"]["error"]
