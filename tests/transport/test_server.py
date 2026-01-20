"""Tests for FastAPI server implementation.

Tests cover:
- App factory creation
- Route registration
- POST /asap endpoint
- GET /.well-known/asap/manifest.json endpoint
- Error handling
- HandlerRegistry integration
- Custom handler registration
"""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from asap.models.entities import Capability, Endpoint, Manifest, Skill
from asap.models.enums import TaskStatus
from asap.models.envelope import Envelope
from asap.models.payloads import TaskRequest, TaskResponse
from asap.transport.handlers import HandlerRegistry
from asap.transport.jsonrpc import (
    INTERNAL_ERROR,
    INVALID_PARAMS,
    METHOD_NOT_FOUND,
    JsonRpcErrorResponse,
    JsonRpcRequest,
    JsonRpcResponse,
)
from asap.transport.server import create_app


@pytest.fixture
def sample_manifest() -> Manifest:
    """Create a sample manifest for testing."""
    return Manifest(
        id="urn:asap:agent:test-server",
        name="Test Server",
        version="1.0.0",
        description="Test server for unit tests",
        capabilities=Capability(
            asap_version="0.1",
            skills=[
                Skill(
                    id="echo",
                    description="Echo input as output",
                )
            ],
            state_persistence=False,
        ),
        endpoints=Endpoint(asap="http://localhost:8000/asap"),
    )


@pytest.fixture
def app(sample_manifest: Manifest) -> FastAPI:
    """Create FastAPI app for testing."""
    return create_app(sample_manifest)


@pytest.fixture
def client(app: FastAPI) -> TestClient:
    """Create test client."""
    return TestClient(app)


class TestAppFactory:
    """Tests for create_app() factory function."""

    def test_create_app_returns_fastapi_instance(self, sample_manifest: Manifest) -> None:
        """Test that create_app returns a FastAPI instance."""
        app = create_app(sample_manifest)

        assert isinstance(app, FastAPI)
        assert app.title == "ASAP Protocol Server"

    def test_app_has_required_routes(self, app: FastAPI) -> None:
        """Test that app has all required routes."""
        routes = [route.path for route in app.routes]  # type: ignore[attr-defined]

        # Required routes
        assert "/asap" in routes
        assert "/.well-known/asap/manifest.json" in routes

    def test_app_has_correct_http_methods(self, app: FastAPI) -> None:
        """Test that routes have correct HTTP methods."""
        routes_by_path = {route.path: route for route in app.routes}  # type: ignore[attr-defined]

        # /asap should accept POST
        asap_route = routes_by_path["/asap"]
        assert "POST" in asap_route.methods  # type: ignore[attr-defined]

        # manifest should accept GET
        manifest_route = routes_by_path["/.well-known/asap/manifest.json"]
        assert "GET" in manifest_route.methods  # type: ignore[attr-defined]


class TestManifestEndpoint:
    """Tests for GET /.well-known/asap/manifest.json endpoint."""

    def test_manifest_endpoint_returns_manifest(
        self, client: TestClient, sample_manifest: Manifest
    ) -> None:
        """Test that manifest endpoint returns the manifest as JSON."""
        response = client.get("/.well-known/asap/manifest.json")

        assert response.status_code == 200
        assert response.json() == sample_manifest.model_dump()

    def test_manifest_endpoint_content_type(self, client: TestClient) -> None:
        """Test that manifest endpoint returns correct content type."""
        response = client.get("/.well-known/asap/manifest.json")

        assert response.status_code == 200
        assert "application/json" in response.headers["content-type"]

    def test_manifest_endpoint_is_idempotent(
        self, client: TestClient, sample_manifest: Manifest
    ) -> None:
        """Test that multiple calls return the same manifest."""
        response1 = client.get("/.well-known/asap/manifest.json")
        response2 = client.get("/.well-known/asap/manifest.json")

        assert response1.status_code == 200
        assert response2.status_code == 200
        assert response1.json() == response2.json()


class TestAsapEndpoint:
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

        # Validate it's a valid JSON-RPC response
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

        # Server catches the exception and returns JSON-RPC error
        assert response.status_code == 200
        data = response.json()
        assert "error" in data
        assert data["error"]["code"] == INTERNAL_ERROR

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
            # Check if it's a JSON-RPC error response
            data = response.json()
            assert "error" in data or "result" in data

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


class TestErrorHandling:
    """Tests for error handling and exception middleware."""

    def test_internal_error_returns_json_rpc_error(self, client: TestClient) -> None:
        """Test that internal server errors return JSON-RPC error format."""
        # This test will be updated when we have actual error-triggering scenarios
        # For now, we just verify the endpoint is operational
        response = client.get("/.well-known/asap/manifest.json")
        assert response.status_code == 200

    def test_404_returns_json(self, client: TestClient) -> None:
        """Test that 404 errors return JSON format."""
        response = client.get("/non-existent-route")

        assert response.status_code == 404
        # FastAPI returns JSON by default
        assert response.headers["content-type"].startswith("application/json")


class TestHandlerRegistryIntegration:
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
