"""Tests for FastAPI server implementation.

Tests cover:
- App factory creation
- Route registration
- POST /asap endpoint
- GET /health and GET /ready (liveness/readiness probes)
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
from unittest.mock import MagicMock, patch

import pytest
from fastapi import FastAPI

if TYPE_CHECKING:
    from asap.transport.rate_limit import ASAPRateLimiter

from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient


from asap.models.entities import Manifest
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
from asap.transport.server import (
    ASAPRequestHandler,
    RegistryHolder,
    RequestContext,
    create_app,
    _run_handler_watcher,
)


@pytest.fixture
def app(
    sample_manifest: Manifest,
    isolated_rate_limiter: "ASAPRateLimiter | None",
) -> FastAPI:
    """Create FastAPI app for testing (very high rate limit, isolated limiter)."""
    app_instance = create_app(sample_manifest, rate_limit="999999/minute")
    if isolated_rate_limiter is not None:
        app_instance.state.limiter = isolated_rate_limiter
    return app_instance


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
        routes = [route.path for route in app.routes]

        # Required routes
        assert "/asap" in routes
        assert "/health" in routes
        assert "/ready" in routes
        assert "/.well-known/asap/manifest.json" in routes

    def test_app_has_correct_http_methods(self, app: FastAPI) -> None:
        """Test that routes have correct HTTP methods."""
        routes_by_path = {route.path: route for route in app.routes}

        # /asap should accept POST
        asap_route = routes_by_path["/asap"]
        assert "POST" in asap_route.methods

        # manifest should accept GET
        manifest_route = routes_by_path["/.well-known/asap/manifest.json"]
        assert "GET" in manifest_route.methods

        # health and ready should accept GET
        health_route = routes_by_path["/health"]
        assert "GET" in health_route.methods
        ready_route = routes_by_path["/ready"]
        assert "GET" in ready_route.methods

    def test_create_app_with_hot_reload_returns_app(self, sample_manifest: Manifest) -> None:
        """Test that create_app(..., hot_reload=True) returns an app (watcher starts in background)."""
        app = create_app(sample_manifest, hot_reload=True)
        assert isinstance(app, FastAPI)


class TestRegistryHolder:
    """Tests for RegistryHolder hot-reload support."""

    def test_replace_registry_copies_executor_when_set(self) -> None:
        """When holder has _executor set, replace_registry copies it to the new registry."""
        registry = HandlerRegistry()
        holder = RegistryHolder(registry)
        executor = MagicMock()
        holder._executor = executor
        new_registry = HandlerRegistry()
        holder.replace_registry(new_registry)
        assert holder.registry is new_registry
        assert getattr(new_registry, "_executor", None) is executor

    def test_replace_registry_no_executor_when_not_set(self) -> None:
        """When holder has no _executor, replace_registry only swaps the registry."""
        registry = HandlerRegistry()
        holder = RegistryHolder(registry)
        new_registry = HandlerRegistry()
        holder.replace_registry(new_registry)
        assert holder.registry is new_registry
        assert (
            not hasattr(new_registry, "_executor")
            or getattr(new_registry, "_executor", None) is None
        )


class TestHandlerWatcher:
    """Tests for _run_handler_watcher (hot reload when watchfiles missing)."""

    def test_run_handler_watcher_exits_when_watchfiles_not_installed(self) -> None:
        """When watchfiles is not importable, watcher logs and returns without blocking."""
        holder = RegistryHolder(HandlerRegistry())
        import builtins

        real_import = builtins.__import__

        def fake_import(name: str, *args: object, **kwargs: object) -> object:
            if name == "watchfiles":
                raise ImportError("watchfiles not installed")
            return real_import(name, *args, **kwargs)

        with patch.object(builtins, "__import__", side_effect=fake_import):
            _run_handler_watcher(holder, "/nonexistent/path")


class TestHealthEndpoints:
    """Tests for GET /health and GET /ready (liveness/readiness probes)."""

    def test_health_returns_ok(self, client: TestClient) -> None:
        """Test that /health returns 200 with status ok."""
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}

    def test_ready_returns_ok(self, client: TestClient) -> None:
        """Test that /ready returns 200 with status ok."""
        response = client.get("/ready")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}


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

    def test_manifest_endpoint_returns_cache_headers(self, client: TestClient) -> None:
        """Test that manifest endpoint returns Cache-Control and ETag."""
        response = client.get("/.well-known/asap/manifest.json")
        assert response.status_code == 200
        assert "cache-control" in response.headers
        assert "public" in response.headers["cache-control"]
        assert "max-age=300" in response.headers["cache-control"]
        assert "etag" in response.headers
        assert response.headers["etag"].startswith('"') and response.headers["etag"].endswith('"')

    def test_manifest_endpoint_returns_304_when_etag_matches(self, client: TestClient) -> None:
        """Test that second request with If-None-Match returns 304 Not Modified."""
        first = client.get("/.well-known/asap/manifest.json")
        assert first.status_code == 200
        etag = first.headers.get("etag")
        assert etag is not None
        second = client.get(
            "/.well-known/asap/manifest.json",
            headers={"If-None-Match": etag},
        )
        assert second.status_code == 304
        assert second.content in (b"", b"None") or len(second.content) == 0


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
        return ASAPRequestHandler(RegistryHolder(registry), sample_manifest, None)

    @pytest.fixture
    def metrics(self) -> MetricsCollector:
        """Get metrics collector."""
        reset_metrics()
        return get_metrics()

    def test_log_response_debug_handles_memoryview_body(self, handler: ASAPRequestHandler) -> None:
        """Test _log_response_debug decodes memoryview body when debug log is enabled."""
        payload = b'{"jsonrpc":"2.0","result":{"ok":true}}'
        response = MagicMock(spec=JSONResponse)
        response.body = memoryview(payload)
        response.status_code = 200
        with patch("asap.transport.server.is_debug_log_mode", return_value=True):
            handler._log_response_debug(response)

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

    def test_validate_envelope_with_envelope_not_dict(
        self, handler: ASAPRequestHandler, metrics: MetricsCollector
    ) -> None:
        """Test _validate_envelope when envelope is not a dict (e.g. string) returns 400."""
        rpc_request = JsonRpcRequest(
            method="asap.send",
            params={"envelope": "string_not_dict"},
            id="test-3b",
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
        assert "envelope" in error_data["error"]["data"]["error"].lower()

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
                payload={"task_id": "t1", "status": "completed", "result": {}},
                correlation_id=envelope.id,
                trace_id=envelope.trace_id,
            )

        handler.registry_holder.registry.register("task.request", sync_handler)

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
            payload={"task_id": "t1", "status": "completed", "result": {}},
            correlation_id="req-7",
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

        # Create a mock request with headers (required for compression detection)
        request = Request(scope={"type": "http", "method": "POST", "path": "/asap", "headers": []})
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
            payload={"conversation_id": "c1", "skill_id": "s1", "input": {}},
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

    @pytest.mark.asyncio
    async def test_parse_and_validate_request_invalid_json(
        self, handler: ASAPRequestHandler, metrics: MetricsCollector
    ) -> None:
        """Test _parse_and_validate_request with invalid JSON."""
        from fastapi import Request

        # Create a mock request with headers (required for compression detection)
        request = Request(scope={"type": "http", "method": "POST", "path": "/asap", "headers": []})

        # Mock the stream() method to return invalid JSON bytes
        async def invalid_json_stream() -> collections.abc.AsyncGenerator[bytes, None]:
            yield b"{invalid json"

        request.stream = lambda: invalid_json_stream()

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

        # Create a mock request with headers (required for compression detection)
        request = Request(scope={"type": "http", "method": "POST", "path": "/asap", "headers": []})

        # Mock the stream() method to return a JSON array (not a dict)
        async def array_json_stream() -> collections.abc.AsyncGenerator[bytes, None]:
            yield json.dumps(["not", "a", "dict"]).encode("utf-8")

        request.stream = lambda: array_json_stream()

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

        # Create a mock request with headers (required for compression detection)
        request = Request(scope={"type": "http", "method": "POST", "path": "/asap", "headers": []})
        # Make request.json() raise an exception that's not ValueError
        request.json = AsyncMock(side_effect=RuntimeError("Unexpected error"))

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

        # Create a mock request with headers (required for compression detection)
        request = Request(scope={"type": "http", "method": "POST", "path": "/asap", "headers": []})

        # Mock the stream() method to return valid JSON
        async def valid_json_stream() -> collections.abc.AsyncGenerator[bytes, None]:
            yield json.dumps({"jsonrpc": "2.0", "method": "asap.send", "params": {}}).encode(
                "utf-8"
            )

        request.stream = lambda: valid_json_stream()

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

        # Create a mock request with headers (required for compression detection)
        request = Request(scope={"type": "http", "method": "POST", "path": "/asap", "headers": []})

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

        try:
            handler._validate_request_size(request, max_size=1024)
        except ValueError:
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


class TestDebugLogMode:
    """Tests for ASAP_DEBUG_LOG: full request/response logging."""

    def test_debug_log_mode_logs_request_and_response(
        self, sample_manifest: Manifest, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """When ASAP_DEBUG_LOG=true, handler logs debug_request and debug_response."""
        from unittest.mock import patch
        from asap.transport.rate_limit import create_test_limiter

        # Use aggressive monkeypatch to replace global limiter (learned from v0.5.0)
        # This prevents rate limit state from accumulating across tests
        isolated_limiter = create_test_limiter(limits=["999999/minute"])

        # Replace in middleware module (server reads from app.state.limiter)
        import asap.transport.middleware as middleware_module

        monkeypatch.setattr(middleware_module, "limiter", isolated_limiter)

        # Create app - it will use the monkeypatched limiter
        app = create_app(sample_manifest, rate_limit="999999/minute")
        app.state.limiter = isolated_limiter
        client = TestClient(app)

        envelope = Envelope(
            asap_version="0.1",
            sender="urn:asap:agent:client",
            recipient=sample_manifest.id,
            payload_type="task.request",
            payload=TaskRequest(
                conversation_id="conv-debug",
                skill_id="echo",
                input={"message": "hello"},
            ).model_dump(),
        )
        body = {
            "jsonrpc": "2.0",
            "method": "asap.send",
            "params": {"envelope": envelope.model_dump(mode="json")},
            "id": "debug-1",
        }

        with (
            patch("asap.transport.server.is_debug_log_mode", return_value=True),
            patch("asap.transport.server.logger") as mock_logger,
        ):
            response = client.post("/asap", json=body)

        assert response.status_code == 200
        info_calls = [c for c in mock_logger.info.call_args_list if c[0]]
        events = [c[0][0] for c in info_calls if c[0]]
        assert "asap.request.debug_request" in events
        assert "asap.request.debug_response" in events


class TestSwaggerUiDebugMode:
    """Tests for Swagger UI /docs enabled only when ASAP_DEBUG=true."""

    def test_docs_disabled_when_not_debug(self, sample_manifest: Manifest) -> None:
        """When ASAP_DEBUG is not set, /docs and /openapi.json return 404."""
        from unittest.mock import patch

        with patch.dict("os.environ", {"ASAP_DEBUG": ""}, clear=False):
            app = create_app(sample_manifest, rate_limit="100000/minute")
            client = TestClient(app)

        assert client.get("/docs").status_code == 404
        assert client.get("/openapi.json").status_code == 404

    def test_docs_enabled_when_debug(self, sample_manifest: Manifest) -> None:
        """When ASAP_DEBUG=true, /docs and /openapi.json are available."""
        from unittest.mock import patch

        with patch.dict("os.environ", {"ASAP_DEBUG": "true"}):
            app = create_app(sample_manifest, rate_limit="100000/minute")
            client = TestClient(app)

        # /docs may redirect (307) or return 200
        docs_resp = client.get("/docs")
        assert docs_resp.status_code in (200, 307)
        assert client.get("/openapi.json").status_code == 200
