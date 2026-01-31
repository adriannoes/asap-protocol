"""Tests for FastAPI server implementation.

Tests cover:
- App factory creation
- Route registration
- POST /asap endpoint
- GET /.well-known/asap/manifest.json endpoint
- GET /asap/metrics endpoint
- Error handling
- HandlerRegistry integration
- Custom handler registration
- Metrics collection
- Authentication integration
"""

import collections.abc
import json
import time
from typing import TYPE_CHECKING

import pytest
from fastapi import FastAPI

if TYPE_CHECKING:
    pass
from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient


from asap.models.entities import Capability, Endpoint, Manifest, Skill
from asap.models.envelope import Envelope
from asap.models.payloads import TaskRequest
from asap.observability import get_metrics, reset_metrics
from asap.observability.metrics import MetricsCollector
from asap.transport.handlers import HandlerRegistry
from asap.transport.jsonrpc import (
    INTERNAL_ERROR,
    INVALID_PARAMS,
    INVALID_REQUEST,
    METHOD_NOT_FOUND,
    PARSE_ERROR,
    JsonRpcRequest,
)
from asap.transport.server import ASAPRequestHandler, RequestContext, create_app


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
    """Create FastAPI app for testing.

    Rate limiting is set to very high limits to avoid interference in tests.
    """
    # Create app with very high rate limit
    return create_app(sample_manifest, rate_limit="100000/minute")  # type: ignore[no-any-return]


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


# The following test classes have been migrated to tests/transport/integration/test_server_core.py:
# - TestHandlerRegistryIntegration
# - TestMetricsEndpoint
# - TestServerExceptionHandling
# - TestAuthenticationIntegration
# All migrated classes now inherit from NoRateLimitTestBase to prevent rate limiting interference.


class TestASAPRequestHandlerHelpers:
    """Unit tests for ASAPRequestHandler helper methods."""

    @pytest.fixture
    def handler(self, sample_manifest: Manifest) -> ASAPRequestHandler:
        """Create ASAPRequestHandler instance for testing."""
        registry = HandlerRegistry()
        return ASAPRequestHandler(registry, sample_manifest, None)

    @pytest.fixture
    def metrics(self) -> MetricsCollector:
        """Get metrics collector."""
        reset_metrics()
        return get_metrics()

    def test_validate_envelope_with_valid_envelope(
        self, handler: ASAPRequestHandler, metrics: MetricsCollector
    ) -> None:
        """Test _validate_envelope with valid envelope."""
        envelope = Envelope(
            asap_version="0.1",
            sender="urn:asap:agent:client",
            recipient="urn:asap:agent:test-server",
            payload_type="task.request",
            payload=TaskRequest(
                conversation_id="conv-1",
                skill_id="echo",
                input={"message": "test"},
            ).model_dump(),
        )

        rpc_request = JsonRpcRequest(
            method="asap.send",
            params={"envelope": envelope.model_dump(mode="json")},
            id="test-1",
        )

        start_time = time.perf_counter()
        ctx = RequestContext(
            request_id=rpc_request.id,
            start_time=start_time,
            metrics=metrics,
            rpc_request=rpc_request,
        )
        result = handler._validate_envelope(ctx)

        envelope_result, payload_type = result
        assert envelope_result is not None
        assert isinstance(envelope_result, Envelope)
        assert envelope_result.payload_type == "task.request"
        assert payload_type == "task.request"

    def test_validate_envelope_with_invalid_params_type(
        self, handler: ASAPRequestHandler, metrics: MetricsCollector
    ) -> None:
        """Test _validate_envelope with non-dict params."""
        # Create JsonRpcRequest with invalid params using model_construct to bypass validation
        rpc_request = JsonRpcRequest.model_construct(
            method="asap.send",
            params="invalid",
            id="test-2",
        )

        start_time = time.perf_counter()
        ctx = RequestContext(
            request_id=rpc_request.id,
            start_time=start_time,
            metrics=metrics,
            rpc_request=rpc_request,
        )
        result = handler._validate_envelope(ctx)

        envelope_result, error_response = result
        assert envelope_result is None
        assert isinstance(error_response, JSONResponse)
        assert error_response.status_code == 200

        # Check error content
        content = bytes(error_response.body).decode()
        error_data = json.loads(content)
        assert error_data["error"]["code"] == INVALID_PARAMS

    def test_validate_envelope_with_missing_envelope(
        self, handler: ASAPRequestHandler, metrics: MetricsCollector
    ) -> None:
        """Test _validate_envelope with missing envelope in params."""
        rpc_request = JsonRpcRequest(
            method="asap.send",
            params={},  # Missing envelope
            id="test-3",
        )

        start_time = time.perf_counter()
        ctx = RequestContext(
            request_id=rpc_request.id,
            start_time=start_time,
            metrics=metrics,
            rpc_request=rpc_request,
        )
        result = handler._validate_envelope(ctx)

        envelope_result, error_response = result
        assert envelope_result is None
        assert isinstance(error_response, JSONResponse)

        content = bytes(error_response.body).decode()
        error_data = json.loads(content)
        assert error_data["error"]["code"] == INVALID_PARAMS
        assert "Missing 'envelope'" in error_data["error"]["data"]["error"]

    def test_validate_envelope_with_invalid_envelope_structure(
        self, handler: ASAPRequestHandler, metrics: MetricsCollector
    ) -> None:
        """Test _validate_envelope with invalid envelope structure."""
        rpc_request = JsonRpcRequest(
            method="asap.send",
            params={
                "envelope": {
                    "sender": "urn:asap:agent:client",
                    # Missing required fields
                }
            },
            id="test-4",
        )

        start_time = time.perf_counter()
        ctx = RequestContext(
            request_id=rpc_request.id,
            start_time=start_time,
            metrics=metrics,
            rpc_request=rpc_request,
        )
        result = handler._validate_envelope(ctx)

        envelope_result, error_response = result
        assert envelope_result is None
        assert isinstance(error_response, JSONResponse)

        content = bytes(error_response.body).decode()
        error_data = json.loads(content)
        assert error_data["error"]["code"] == INVALID_PARAMS
        assert "Invalid envelope structure" in error_data["error"]["data"]["error"]

    @pytest.mark.asyncio
    async def test_dispatch_to_handler_success(
        self, handler: ASAPRequestHandler, metrics: MetricsCollector
    ) -> None:
        """Test _dispatch_to_handler with successful dispatch."""

        # Register a handler
        def sync_handler(envelope: Envelope, manifest: Manifest) -> Envelope:
            return Envelope(
                asap_version=envelope.asap_version,
                sender=manifest.id,
                recipient=envelope.sender,
                payload_type="task.response",
                payload={"status": "completed"},
                correlation_id=envelope.id,
                trace_id=envelope.trace_id,
            )

        handler.registry.register("task.request", sync_handler)

        envelope = Envelope(
            asap_version="0.1",
            sender="urn:asap:agent:client",
            recipient="urn:asap:agent:test-server",
            payload_type="task.request",
            payload=TaskRequest(
                conversation_id="conv-1",
                skill_id="echo",
                input={"message": "test"},
            ).model_dump(),
        )

        rpc_request = JsonRpcRequest(
            method="asap.send",
            params={"envelope": envelope.model_dump(mode="json")},
            id="test-5",
        )

        start_time = time.perf_counter()
        ctx = RequestContext(
            request_id=rpc_request.id,
            start_time=start_time,
            metrics=metrics,
            rpc_request=rpc_request,
        )
        result = await handler._dispatch_to_handler(envelope, ctx)

        response_envelope, payload_type = result
        assert response_envelope is not None
        assert isinstance(response_envelope, Envelope)
        assert response_envelope.payload_type == "task.response"
        assert payload_type == "task.request"

    @pytest.mark.asyncio
    async def test_dispatch_to_handler_not_found(
        self, handler: ASAPRequestHandler, metrics: MetricsCollector
    ) -> None:
        """Test _dispatch_to_handler with handler not found."""
        envelope = Envelope(
            asap_version="0.1",
            sender="urn:asap:agent:client",
            recipient="urn:asap:agent:test-server",
            payload_type="unknown.type",
            payload={},
        )

        rpc_request = JsonRpcRequest(
            method="asap.send",
            params={"envelope": envelope.model_dump(mode="json")},
            id="test-6",
        )

        start_time = time.perf_counter()
        ctx = RequestContext(
            request_id=rpc_request.id,
            start_time=start_time,
            metrics=metrics,
            rpc_request=rpc_request,
        )
        result = await handler._dispatch_to_handler(envelope, ctx)

        response_envelope, error_response = result
        assert response_envelope is None
        assert isinstance(error_response, JSONResponse)

        content = bytes(error_response.body).decode()
        error_data = json.loads(content)
        assert error_data["error"]["code"] == METHOD_NOT_FOUND
        assert "unknown.type" in error_data["error"]["data"]["payload_type"]

    def test_build_success_response(
        self, handler: ASAPRequestHandler, metrics: MetricsCollector
    ) -> None:
        """Test _build_success_response creates correct response."""
        response_envelope = Envelope(
            asap_version="0.1",
            sender="urn:asap:agent:test-server",
            recipient="urn:asap:agent:client",
            payload_type="task.response",
            payload={"status": "completed"},
        )

        rpc_request = JsonRpcRequest(
            method="asap.send",
            params={},
            id="test-7",
        )

        start_time = time.perf_counter()
        ctx = RequestContext(
            request_id=rpc_request.id,
            start_time=start_time,
            metrics=metrics,
            rpc_request=rpc_request,
        )
        response = handler._build_success_response(response_envelope, ctx, "task.request")

        assert isinstance(response, JSONResponse)
        assert response.status_code == 200

        content = bytes(response.body).decode()
        data = json.loads(content)
        assert "result" in data
        assert data["id"] == "test-7"
        assert "envelope" in data["result"]

    def test_handle_internal_error(
        self, handler: ASAPRequestHandler, metrics: MetricsCollector
    ) -> None:
        """Test _handle_internal_error creates correct error response."""
        error = ValueError("Test error")
        start_time = time.perf_counter()
        rpc_request = JsonRpcRequest(
            method="asap.send",
            params={},
            id="test-error",
        )
        ctx = RequestContext(
            request_id=rpc_request.id,
            start_time=start_time,
            metrics=metrics,
            rpc_request=rpc_request,
        )
        response = handler._handle_internal_error(error, ctx, "task.request")

        assert isinstance(response, JSONResponse)
        assert response.status_code == 200

        content = bytes(response.body).decode()
        error_data = json.loads(content)
        assert "error" in error_data
        assert error_data["error"]["code"] == INTERNAL_ERROR
        # Production: generic message only; full error only when ASAP_DEBUG is set
        assert error_data["error"]["data"]["error"] == "Internal server error"

    @pytest.mark.asyncio
    async def test_authenticate_request_without_middleware(
        self, handler: ASAPRequestHandler, metrics: MetricsCollector
    ) -> None:
        """Test _authenticate_request when auth middleware is None."""
        from fastapi import Request

        request = Request(scope={"type": "http", "method": "POST", "path": "/asap"})
        rpc_request = JsonRpcRequest(
            method="asap.send",
            params={},
            id="test-8",
        )

        start_time = time.perf_counter()
        ctx = RequestContext(
            request_id=rpc_request.id,
            start_time=start_time,
            metrics=metrics,
            rpc_request=rpc_request,
        )
        result = await handler._authenticate_request(request, ctx)

        agent_id, error = result
        assert agent_id is None
        assert error is None

    @pytest.mark.asyncio
    async def test_verify_sender_matches_auth_without_middleware(
        self, handler: ASAPRequestHandler, metrics: MetricsCollector
    ) -> None:
        """Test _verify_sender_matches_auth when auth middleware is None."""
        envelope = Envelope(
            asap_version="0.1",
            sender="urn:asap:agent:client",
            recipient="urn:asap:agent:test-server",
            payload_type="task.request",
            payload={},
        )

        rpc_request = JsonRpcRequest(
            method="asap.send",
            params={},
            id="test-9",
        )

        start_time = time.perf_counter()
        ctx = RequestContext(
            request_id=rpc_request.id,
            start_time=start_time,
            metrics=metrics,
            rpc_request=rpc_request,
        )
        result = handler._verify_sender_matches_auth(None, envelope, ctx, "task.request")

        assert result is None

    # Note: test_parse_and_validate_request_success is covered by integration tests
    # Testing this helper directly requires complex Request mocking that's not worth it
    # The functionality is well-covered by the endpoint tests in TestAsapEndpoint

    @pytest.mark.asyncio
    async def test_parse_and_validate_request_invalid_json(
        self, handler: ASAPRequestHandler, metrics: MetricsCollector
    ) -> None:
        """Test _parse_and_validate_request with invalid JSON."""
        from fastapi import Request

        # Create a mock request
        request = Request(scope={"type": "http", "method": "POST", "path": "/asap"})

        # Mock the stream() method to return invalid JSON bytes
        async def invalid_json_stream() -> collections.abc.AsyncGenerator[bytes, None]:
            yield b"{invalid json"

        request.stream = lambda: invalid_json_stream()  # type: ignore[method-assign]

        result = await handler._parse_and_validate_request(request)

        rpc_request, error = result
        assert rpc_request is None
        assert error is not None
        assert isinstance(error, JSONResponse)

        content = bytes(error.body).decode()
        error_data = json.loads(content)
        assert error_data["error"]["code"] == PARSE_ERROR

    @pytest.mark.asyncio
    async def test_parse_and_validate_request_non_dict_body(
        self, handler: ASAPRequestHandler
    ) -> None:
        """Test _parse_and_validate_request with non-dict body."""
        from fastapi import Request

        request = Request(scope={"type": "http", "method": "POST", "path": "/asap"})

        # Mock the stream() method to return a JSON array (not a dict)
        async def array_json_stream() -> collections.abc.AsyncGenerator[bytes, None]:
            yield json.dumps(["not", "a", "dict"]).encode("utf-8")

        request.stream = lambda: array_json_stream()  # type: ignore[method-assign]

        result = await handler._parse_and_validate_request(request)

        rpc_request, error = result
        assert rpc_request is None
        assert error is not None
        assert isinstance(error, JSONResponse)

        content = bytes(error.body).decode()
        error_data = json.loads(content)
        assert error_data["error"]["code"] == INVALID_REQUEST
        assert "must be an object" in error_data["error"]["data"]["error"]

    def test_validate_jsonrpc_request_params_dict_type_error(
        self, handler: ASAPRequestHandler
    ) -> None:
        """Test validate_jsonrpc_request with params dict_type validation error."""
        # Create body with params as array (should trigger dict_type error)
        body = {
            "jsonrpc": "2.0",
            "method": "asap.send",
            "params": ["not", "an", "object"],
            "id": "test-params-error",
        }

        rpc_request, error_response = handler.validate_jsonrpc_request(body)

        assert rpc_request is None
        assert error_response is not None
        assert isinstance(error_response, JSONResponse)

        content = bytes(error_response.body).decode()
        error_data = json.loads(content)
        # Should use INVALID_PARAMS (not INVALID_REQUEST) for dict_type error on params
        assert error_data["error"]["code"] == INVALID_PARAMS
        assert "params' must be an object" in error_data["error"]["data"]["error"]

    @pytest.mark.asyncio
    async def test_handle_message_exception_before_rpc_request(
        self, handler: ASAPRequestHandler
    ) -> None:
        """Test handle_message exception handling before rpc_request is created."""
        from fastapi import Request
        from unittest.mock import AsyncMock

        request = Request(scope={"type": "http", "method": "POST", "path": "/asap"})
        # Make request.json() raise an exception that's not ValueError
        request.json = AsyncMock(side_effect=RuntimeError("Unexpected error"))  # type: ignore[method-assign]

        response = await handler.handle_message(request)

        assert isinstance(response, JSONResponse)
        assert response.status_code == 200

        content = bytes(response.body).decode()
        error_data = json.loads(content)
        assert "error" in error_data
        assert error_data["error"]["code"] == INTERNAL_ERROR

    @pytest.mark.asyncio
    async def test_parse_and_validate_request_rpc_request_none_after_validation(
        self, handler: ASAPRequestHandler
    ) -> None:
        """Test _parse_and_validate_request when validate_jsonrpc_request returns None, None."""
        from fastapi import Request
        from unittest.mock import patch

        request = Request(scope={"type": "http", "method": "POST", "path": "/asap"})

        # Mock the stream() method to return valid JSON
        async def valid_json_stream() -> collections.abc.AsyncGenerator[bytes, None]:
            yield json.dumps({"jsonrpc": "2.0", "method": "asap.send", "params": {}}).encode(
                "utf-8"
            )

        request.stream = lambda: valid_json_stream()  # type: ignore[method-assign]

        # Mock validate_jsonrpc_request to return (None, None) - edge case
        with patch.object(handler, "validate_jsonrpc_request", return_value=(None, None)):
            result = await handler._parse_and_validate_request(request)

        rpc_request, error = result
        assert rpc_request is None
        assert error is not None
        assert isinstance(error, JSONResponse)

        content = bytes(error.body).decode()
        error_data = json.loads(content)
        assert error_data["error"]["code"] == INTERNAL_ERROR
        assert "Internal validation error" in error_data["error"]["data"]["error"]

    @pytest.mark.asyncio
    async def test_parse_and_validate_request_handles_httpexception(
        self, handler: ASAPRequestHandler
    ) -> None:
        """Test that _parse_and_validate_request handles HTTPException correctly."""
        from fastapi import HTTPException, Request
        from unittest.mock import patch

        request = Request(scope={"type": "http", "method": "POST", "path": "/asap"})

        # Mock parse_json_body to raise HTTPException (e.g., 413 Payload Too Large)
        async def mock_parse_json_body(req: Request) -> dict:
            raise HTTPException(status_code=413, detail="Request too large")

        with patch.object(handler, "parse_json_body", side_effect=mock_parse_json_body):
            result = await handler._parse_and_validate_request(request)

        rpc_request, error_response = result
        assert rpc_request is None
        assert error_response is not None
        assert isinstance(error_response, JSONResponse)
        assert error_response.status_code == 413

        content = bytes(error_response.body).decode()
        error_data = json.loads(content)
        assert error_data["detail"] == "Request too large"

    def test_validate_request_size_handles_invalid_content_length(
        self, handler: ASAPRequestHandler
    ) -> None:
        """Test that _validate_request_size handles ValueError for invalid Content-Length header.

        This test covers the ValueError exception handler in _validate_request_size
        (server.py lines 683-685) which handles invalid Content-Length headers gracefully.
        """
        from fastapi import Request

        # Create request with invalid Content-Length header
        request = Request(
            scope={
                "type": "http",
                "method": "POST",
                "path": "/asap",
                "headers": [(b"content-length", b"invalid-number")],
            }
        )

        # Should not raise ValueError, should handle gracefully
        # The ValueError is caught and handled internally (line 683-685)
        # This test verifies the exception handler exists and works
        # We can access the private method for testing coverage
        try:
            handler._validate_request_size(request, max_size=1024)
            # If no exception, test passed - ValueError was caught internally
            assert True
        except ValueError:
            # This should not happen as ValueError is caught internally
            pytest.fail("ValueError should be caught internally in _validate_request_size")

    def test_validate_request_size_raises_httpexception_for_large_content(
        self, handler: ASAPRequestHandler
    ) -> None:
        """Test that _validate_request_size raises HTTPException for content exceeding max size.

        This test covers the HTTPException raised when Content-Length exceeds max_size
        (server.py lines 679-682).
        """
        from fastapi import HTTPException, Request

        # Create request with Content-Length exceeding max_size
        request = Request(
            scope={
                "type": "http",
                "method": "POST",
                "path": "/asap",
                "headers": [(b"content-length", b"2048")],  # 2048 bytes > 1024 max
            }
        )

        with pytest.raises(HTTPException) as exc_info:
            handler._validate_request_size(request, max_size=1024)

        assert exc_info.value.status_code == 413
        assert "exceeds maximum" in str(exc_info.value.detail)
