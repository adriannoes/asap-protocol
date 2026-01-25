"""FastAPI server implementation for ASAP protocol.

This module provides a production-ready FastAPI server that:
- Exposes POST /asap endpoint for JSON-RPC 2.0 wrapped ASAP messages
- Exposes GET /.well-known/asap/manifest.json for agent discovery
- Exposes GET /asap/metrics for Prometheus-compatible metrics
- Handles errors with proper JSON-RPC error responses
- Validates all incoming requests against ASAP schemas
- Uses HandlerRegistry for extensible payload processing
- Provides structured logging for observability
- Supports authentication based on manifest configuration

Example:
    >>> from asap.models.entities import Manifest, Capability, Endpoint, Skill, AuthScheme
    >>> from asap.transport.server import create_app
    >>> from asap.transport.handlers import HandlerRegistry
    >>>
    >>> manifest = Manifest(
    ...     id="urn:asap:agent:my-agent",
    ...     name="My Agent",
    ...     version="1.0.0",
    ...     description="Example agent",
    ...     capabilities=Capability(
    ...         asap_version="0.1",
    ...         skills=[Skill(id="echo", description="Echo skill")],
    ...         state_persistence=False
    ...     ),
    ...     endpoints=Endpoint(asap="http://localhost:8000/asap"),
    ...     auth=AuthScheme(schemes=["bearer"])  # Optional authentication
    ... )
    >>>
    >>> # Create app with default registry
    >>> app = create_app(manifest)
    >>>
    >>> # Or with custom registry and auth
    >>> registry = HandlerRegistry()
    >>> registry.register("task.request", my_custom_handler)
    >>> app = create_app(manifest, registry)
    >>>
    >>> # Run with: uvicorn asap.transport.server:app --host 0.0.0.0 --port 8000
"""

import time
from dataclasses import dataclass
from typing import Any, Callable, TypeVar

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse, PlainTextResponse
from pydantic import ValidationError

from asap.models.entities import Capability, Endpoint, Manifest, Skill
from asap.models.envelope import Envelope
from asap.observability import get_logger, get_metrics
from asap.transport.middleware import AuthenticationMiddleware, BearerTokenValidator
from asap.observability.metrics import MetricsCollector
from asap.transport.handlers import (
    HandlerNotFoundError,
    HandlerRegistry,
    create_default_registry,
)
from asap.transport.jsonrpc import (
    ASAP_METHOD,
    INTERNAL_ERROR,
    INVALID_PARAMS,
    INVALID_REQUEST,
    METHOD_NOT_FOUND,
    PARSE_ERROR,
    JsonRpcError,
    JsonRpcErrorResponse,
    JsonRpcRequest,
    JsonRpcResponse,
)

# Module logger
logger = get_logger(__name__)

# Type variable for handler result pattern
T = TypeVar("T")
HandlerResult = tuple[T | None, JSONResponse | None]


@dataclass
class RequestContext:
    """Request-scoped context for handler processing.

    Groups request-scoped data that is passed to multiple helper methods
    to reduce parameter noise and improve code readability.

    Attributes:
        request_id: JSON-RPC request ID (str, int, or None)
        start_time: Request start time for duration calculation
        metrics: Metrics collector for observability
        rpc_request: Validated JSON-RPC request object
    """

    request_id: str | int | None
    start_time: float
    metrics: MetricsCollector
    rpc_request: JsonRpcRequest


class ASAPRequestHandler:
    """Handler for processing ASAP protocol requests.

    Encapsulates the logic for:
    - Parsing and validating JSON-RPC requests
    - Authenticating requests based on manifest configuration
    - Validating sender identity
    - Dispatching to registered handlers
    - Building error responses
    - Recording metrics

    This class is instantiated by create_app() and used to handle
    incoming requests on the /asap endpoint.

    Attributes:
        registry: Handler registry for payload dispatch
        manifest: Agent manifest for context
        auth_middleware: Optional authentication middleware

    Example:
        >>> handler = ASAPRequestHandler(registry, manifest, auth_middleware)
        >>> response = await handler.handle_message(request)
    """

    def __init__(
        self,
        registry: HandlerRegistry,
        manifest: Manifest,
        auth_middleware: AuthenticationMiddleware | None = None,
    ) -> None:
        """Initialize the request handler.

        Args:
            registry: Handler registry for dispatching payloads
            manifest: Agent manifest describing capabilities
            auth_middleware: Optional authentication middleware for request validation
        """
        self.registry = registry
        self.manifest = manifest
        self.auth_middleware = auth_middleware

    def build_error_response(
        self,
        code: int,
        data: dict[str, Any] | None = None,
        request_id: str | int | None = None,
    ) -> JSONResponse:
        """Build a JSON-RPC error response.

        Args:
            code: JSON-RPC error code
            data: Optional error data
            request_id: Optional request ID from original request

        Returns:
            JSONResponse with error
        """
        error_response = JsonRpcErrorResponse(
            error=JsonRpcError.from_code(code, data=data),
            id=request_id,
        )
        return JSONResponse(status_code=200, content=error_response.model_dump())

    def record_error_metrics(
        self,
        metrics: MetricsCollector,
        payload_type: str,
        error_type: str,
        duration_seconds: float,
    ) -> None:
        """Record error metrics for a failed request.

        Args:
            metrics: Metrics collector instance
            payload_type: Payload type (or "unknown")
            error_type: Type of error that occurred
            duration_seconds: Request duration in seconds
        """
        metrics.increment_counter(
            "asap_requests_total",
            {"payload_type": payload_type, "status": "error"},
        )
        metrics.increment_counter(
            "asap_requests_error_total",
            {"payload_type": payload_type, "error_type": error_type},
        )
        metrics.observe_histogram(
            "asap_request_duration_seconds",
            duration_seconds,
            {"payload_type": payload_type, "status": "error"},
        )

    def _validate_envelope(
        self,
        ctx: RequestContext,
    ) -> tuple[Envelope | None, JSONResponse | str]:
        """Validate and extract envelope from JSON-RPC params.

        Validates that params is a dict, extracts the envelope field,
        and validates the envelope structure.

        Args:
            ctx: Request context with rpc_request, start_time, and metrics

        Returns:
            Tuple of (Envelope, payload_type) if valid, or (None, error_response) if invalid
        """
        rpc_request = ctx.rpc_request
        # Validate params is a dict before accessing
        if not isinstance(rpc_request.params, dict):
            logger.warning(
                "asap.request.invalid_params_type",
                params_type=type(rpc_request.params).__name__,
            )
            error_response = self.build_error_response(
                INVALID_PARAMS,
                data={
                    "error": "JSON-RPC 'params' must be an object",
                    "received_type": type(rpc_request.params).__name__,
                },
                request_id=ctx.request_id,
            )
            self.record_error_metrics(
                ctx.metrics,
                "unknown",
                "invalid_params",
                time.perf_counter() - ctx.start_time,
            )
            return None, error_response

        # Extract envelope from params
        envelope_data = rpc_request.params.get("envelope")
        if envelope_data is None:
            logger.warning("asap.request.missing_envelope")
            error_response = self.build_error_response(
                INVALID_PARAMS,
                data={"error": "Missing 'envelope' in params"},
                request_id=ctx.request_id,
            )
            self.record_error_metrics(
                ctx.metrics,
                "unknown",
                "missing_envelope",
                time.perf_counter() - ctx.start_time,
            )
            return None, error_response

        # Validate envelope structure
        try:
            envelope = Envelope(**envelope_data)
            payload_type = envelope.payload_type
            return envelope, payload_type
        except ValidationError as e:
            logger.warning(
                "asap.request.invalid_envelope",
                error="Invalid envelope structure",
                validation_errors=str(e.errors()),
            )
            duration_seconds = time.perf_counter() - ctx.start_time
            self.record_error_metrics(ctx.metrics, "unknown", "invalid_envelope", duration_seconds)
            error_response = self.build_error_response(
                INVALID_PARAMS,
                data={
                    "error": "Invalid envelope structure",
                    "validation_errors": e.errors(),
                },
                request_id=ctx.request_id,
            )
            return None, error_response

    async def _dispatch_to_handler(
        self,
        envelope: Envelope,
        ctx: RequestContext,
    ) -> tuple[Envelope | None, JSONResponse | str]:
        """Dispatch envelope to registered handler.

        Looks up and executes the handler for the envelope's payload type.
        Handles HandlerNotFoundError and converts it to JSON-RPC error response.

        Args:
            envelope: Validated ASAP envelope
            ctx: Request context with rpc_request, start_time, and metrics

        Returns:
            Tuple of (response_envelope, payload_type) if successful,
            or (None, error_response) if handler not found
        """
        payload_type = envelope.payload_type
        try:
            response_envelope = await self.registry.dispatch_async(envelope, self.manifest)
            return response_envelope, payload_type
        except HandlerNotFoundError as e:
            # No handler registered for this payload type
            logger.warning(
                "asap.request.handler_not_found",
                payload_type=e.payload_type,
                envelope_id=envelope.id,
            )
            # Record error metric
            duration_seconds = time.perf_counter() - ctx.start_time
            ctx.metrics.increment_counter(
                "asap_requests_total",
                {"payload_type": payload_type, "status": "error"},
            )
            ctx.metrics.increment_counter(
                "asap_requests_error_total",
                {"payload_type": payload_type, "error_type": "handler_not_found"},
            )
            ctx.metrics.observe_histogram(
                "asap_request_duration_seconds",
                duration_seconds,
                {"payload_type": payload_type, "status": "error"},
            )
            handler_error = JsonRpcErrorResponse(
                error=JsonRpcError.from_code(
                    METHOD_NOT_FOUND,
                    data={
                        "payload_type": e.payload_type,
                        "error": str(e),
                    },
                ),
                id=ctx.request_id,
            )
            error_response = JSONResponse(
                status_code=200,
                content=handler_error.model_dump(),
            )
            return None, error_response

    async def _authenticate_request(
        self,
        request: Request,
        ctx: RequestContext,
    ) -> HandlerResult[str]:
        """Authenticate the request if authentication is enabled.

        Args:
            request: FastAPI request object
            ctx: Request context with rpc_request, start_time, and metrics

        Returns:
            Tuple of (authenticated_agent_id, None) if successful or auth disabled,
            or (None, error_response) if authentication failed
        """
        if self.auth_middleware is None:
            return None, None

        try:
            authenticated_agent_id = await self.auth_middleware.verify_authentication(request)
            return authenticated_agent_id, None
        except HTTPException as e:
            # Authentication failed - return JSON-RPC error
            logger.warning(
                "asap.request.auth_failed",
                status_code=e.status_code,
                detail=e.detail,
            )
            # Map HTTP status to JSON-RPC error code
            error_code = INVALID_REQUEST if e.status_code == 401 else INVALID_PARAMS
            error_response = self.build_error_response(
                error_code,
                data={"error": str(e.detail), "status_code": e.status_code},
                request_id=ctx.request_id,
            )
            self.record_error_metrics(
                ctx.metrics,
                "unknown",
                "auth_failed",
                time.perf_counter() - ctx.start_time,
            )
            return None, error_response

    def _verify_sender_matches_auth(
        self,
        authenticated_agent_id: str | None,
        envelope: Envelope,
        ctx: RequestContext,
        payload_type: str,
    ) -> JSONResponse | None:
        """Verify that envelope sender matches authenticated identity.

        Args:
            authenticated_agent_id: Authenticated agent ID from auth middleware
            envelope: Validated ASAP envelope
            ctx: Request context with rpc_request, start_time, and metrics
            payload_type: Payload type for metrics

        Returns:
            None if verification passes, or error_response if sender mismatch
        """
        if self.auth_middleware is None:
            return None

        try:
            self.auth_middleware.verify_sender_matches_auth(authenticated_agent_id, envelope.sender)
            return None
        except HTTPException as e:
            # Sender mismatch - return JSON-RPC error
            logger.warning(
                "asap.request.sender_mismatch",
                authenticated_agent=authenticated_agent_id,
                envelope_sender=envelope.sender,
            )
            error_response = self.build_error_response(
                INVALID_PARAMS,
                data={"error": str(e.detail), "status_code": e.status_code},
                request_id=ctx.request_id,
            )
            duration_seconds = time.perf_counter() - ctx.start_time
            self.record_error_metrics(
                ctx.metrics, payload_type, "sender_mismatch", duration_seconds
            )
            return error_response

    def _build_success_response(
        self,
        response_envelope: Envelope,
        ctx: RequestContext,
        payload_type: str,
    ) -> JSONResponse:
        """Build success response with metrics and logging.

        Args:
            response_envelope: Response envelope from handler
            ctx: Request context with rpc_request, start_time, and metrics
            payload_type: Payload type for metrics

        Returns:
            JSON-RPC success response
        """
        duration_seconds = time.perf_counter() - ctx.start_time
        duration_ms = duration_seconds * 1000

        # Record success metrics
        ctx.metrics.increment_counter(
            "asap_requests_total",
            {"payload_type": payload_type, "status": "success"},
        )
        ctx.metrics.increment_counter(
            "asap_requests_success_total",
            {"payload_type": payload_type},
        )
        ctx.metrics.observe_histogram(
            "asap_request_duration_seconds",
            duration_seconds,
            {"payload_type": payload_type, "status": "success"},
        )

        # Log successful processing
        logger.info(
            "asap.request.processed",
            envelope_id=response_envelope.id,
            response_id=response_envelope.id,
            trace_id=response_envelope.trace_id,
            payload_type=payload_type,
            duration_ms=round(duration_ms, 2),
        )

        # Wrap response in JSON-RPC
        # JsonRpcResponse requires id to be str | int, not None
        response_id: str | int = ctx.request_id if ctx.request_id is not None else ""
        rpc_response = JsonRpcResponse(
            result={"envelope": response_envelope.model_dump(mode="json")},
            id=response_id,
        )

        return JSONResponse(
            status_code=200,
            content=rpc_response.model_dump(),
        )

    def _handle_internal_error(
        self,
        error: Exception,
        ctx: RequestContext,
        payload_type: str,
    ) -> JSONResponse:
        """Handle internal server errors with metrics and logging.

        Args:
            error: The exception that occurred
            ctx: Request context with rpc_request, start_time, and metrics
            payload_type: Payload type for metrics

        Returns:
            JSON-RPC internal error response
        """
        duration_seconds = time.perf_counter() - ctx.start_time
        duration_ms = duration_seconds * 1000

        # Record error metrics
        ctx.metrics.increment_counter(
            "asap_requests_total",
            {"payload_type": payload_type, "status": "error"},
        )
        ctx.metrics.increment_counter(
            "asap_requests_error_total",
            {"payload_type": payload_type, "error_type": "internal_error"},
        )
        ctx.metrics.observe_histogram(
            "asap_request_duration_seconds",
            duration_seconds,
            {"payload_type": payload_type, "status": "error"},
        )

        # Log error
        logger.exception(
            "asap.request.error",
            error=str(error),
            error_type=type(error).__name__,
            duration_ms=round(duration_ms, 2),
        )

        # Internal server error
        internal_error = JsonRpcErrorResponse(
            error=JsonRpcError.from_code(
                INTERNAL_ERROR,
                data={"error": str(error), "type": type(error).__name__},
            ),
            id=ctx.request_id,
        )
        return JSONResponse(
            status_code=200,
            content=internal_error.model_dump(),
        )

    async def _parse_and_validate_request(
        self,
        request: Request,
    ) -> HandlerResult[JsonRpcRequest]:
        """Parse JSON body and validate JSON-RPC request structure.

        Args:
            request: FastAPI request object

        Returns:
            Tuple of (JsonRpcRequest, None) if valid, or (None, error_response) if invalid
        """
        # Parse JSON body
        try:
            body = await self.parse_json_body(request)
        except ValueError as e:
            # Invalid JSON - return parse error
            error_response = self.build_error_response(
                PARSE_ERROR,
                data={"error": str(e)},
                request_id=None,
            )
            # Create temporary context for metrics (before we have rpc_request)
            temp_metrics = get_metrics()
            self.record_error_metrics(temp_metrics, "unknown", "parse_error", 0.0)
            return None, error_response

        # Validate body is a dict (JSON-RPC requires object at root)
        if not isinstance(body, dict):
            error_response = self.build_error_response(
                INVALID_REQUEST,
                data={
                    "error": "JSON-RPC request must be an object",
                    "received_type": type(body).__name__,
                },
                request_id=None,
            )
            temp_metrics = get_metrics()
            self.record_error_metrics(temp_metrics, "unknown", "invalid_request", 0.0)
            return None, error_response

        # Validate JSON-RPC request structure and method
        rpc_request, validation_error = self.validate_jsonrpc_request(body)
        if validation_error is not None:
            temp_metrics = get_metrics()
            self.record_error_metrics(temp_metrics, "unknown", "invalid_request", 0.0)
            return None, validation_error

        # Type narrowing: rpc_request is not None here
        if rpc_request is None:
            # This should not happen if validate_jsonrpc_request is correct
            # but guard against it for robustness
            error_response = self.build_error_response(
                INTERNAL_ERROR,
                data={"error": "Internal validation error"},
                request_id=None,
            )
            temp_metrics = get_metrics()
            self.record_error_metrics(
                temp_metrics, "unknown", "internal_error", time.perf_counter()
            )
            return None, error_response

        return rpc_request, None

    async def parse_json_body(self, request: Request) -> dict[str, Any]:
        """Parse JSON body from request.

        Args:
            request: FastAPI request object

        Returns:
            Parsed JSON body

        Raises:
            ValueError: If JSON is invalid
        """
        try:
            body: dict[str, Any] = await request.json()
            return body
        except ValueError as e:
            logger.warning("asap.request.invalid_json", error=str(e))
            raise

    def validate_jsonrpc_request(
        self, body: dict[str, Any]
    ) -> tuple[JsonRpcRequest | None, JSONResponse | None]:
        """Validate JSON-RPC request structure and method.

        Args:
            body: Parsed JSON body

        Returns:
            Tuple of (JsonRpcRequest, None) if valid, or (None, error_response) if invalid
        """
        # Validate JSON-RPC structure
        try:
            rpc_request = JsonRpcRequest(**body)
        except (ValidationError, TypeError) as e:
            # Check if error is specifically about params type
            error_code = INVALID_REQUEST
            error_message = "Invalid JSON-RPC structure"
            if isinstance(e, ValidationError):
                errors = e.errors()
                # If params validation failed with dict_type error, use INVALID_PARAMS
                for error in errors:
                    if error.get("loc") == ("params",) and error.get("type") == "dict_type":
                        error_code = INVALID_PARAMS
                        error_message = "JSON-RPC 'params' must be an object"
                        break

            logger.warning(
                "asap.request.invalid_structure",
                error=error_message,
                error_type=type(e).__name__,
                validation_errors=str(e.errors()) if isinstance(e, ValidationError) else str(e),
            )
            error_response = self.build_error_response(
                error_code,
                data={
                    "error": error_message,
                    "validation_errors": (
                        e.errors()
                        if isinstance(e, ValidationError)
                        else [{"type": "type_error", "loc": (), "msg": str(e), "input": None}]
                    ),
                },
                request_id=body.get("id") if isinstance(body, dict) else None,
            )
            return None, error_response

        # Check method
        if rpc_request.method != ASAP_METHOD:
            logger.warning("asap.request.unknown_method", method=rpc_request.method)
            error_response = self.build_error_response(
                METHOD_NOT_FOUND,
                data={"method": rpc_request.method},
                request_id=rpc_request.id,
            )
            return None, error_response

        return rpc_request, None

    async def handle_message(self, request: Request) -> JSONResponse:
        """Handle ASAP messages wrapped in JSON-RPC 2.0.

        This method:
        1. Receives JSON-RPC wrapped ASAP envelopes
        2. Validates the request structure
        3. Extracts and processes the ASAP envelope
        4. Returns response wrapped in JSON-RPC
        5. Records metrics for observability

        Args:
            request: FastAPI request object with JSON body

        Returns:
            JSON-RPC response or error response

        Example:
            >>> response = await handler.handle_message(request)
        """
        start_time = time.perf_counter()
        metrics = get_metrics()
        payload_type = "unknown"

        try:
            # Parse and validate JSON-RPC request
            parse_result = await self._parse_and_validate_request(request)
            rpc_request, parse_error = parse_result
            if parse_error is not None:
                return parse_error
            # Type narrowing: rpc_request is not None here
            assert rpc_request is not None

            # Create request context
            ctx = RequestContext(
                request_id=rpc_request.id,
                start_time=start_time,
                metrics=metrics,
                rpc_request=rpc_request,
            )

            # Authenticate request if enabled
            auth_result = await self._authenticate_request(request, ctx)
            authenticated_agent_id, auth_error = auth_result
            if auth_error is not None:
                return auth_error

            # Validate and extract envelope
            envelope_result = self._validate_envelope(ctx)
            envelope_or_none, result = envelope_result
            if envelope_or_none is None:
                # result is JSONResponse when envelope is None
                return result  # type: ignore[return-value]
            envelope = envelope_or_none
            # result is payload_type (str) when envelope is not None
            payload_type = result  # type: ignore[assignment]

            # Verify sender matches authenticated identity
            sender_error = self._verify_sender_matches_auth(
                authenticated_agent_id,
                envelope,
                ctx,
                payload_type,
            )
            if sender_error is not None:
                return sender_error

            # Log request received
            logger.info(
                "asap.request.received",
                envelope_id=envelope.id,
                trace_id=envelope.trace_id,
                payload_type=envelope.payload_type,
                sender=envelope.sender,
                recipient=envelope.recipient,
                authenticated=authenticated_agent_id is not None,
            )

            # Dispatch to handler
            dispatch_result = await self._dispatch_to_handler(envelope, ctx)
            response_or_none, result = dispatch_result
            if response_or_none is None:
                # result is JSONResponse when response is None
                return result  # type: ignore[return-value]
            response_envelope = response_or_none
            # result is payload_type (str) when response is not None
            payload_type = result  # type: ignore[assignment]

            # Build and return success response
            return self._build_success_response(response_envelope, ctx, payload_type)

        except Exception as e:
            # Create minimal context for error handling if we don't have rpc_request yet
            if "ctx" not in locals():
                # Fallback: create context with minimal info
                temp_metrics = get_metrics()
                # JsonRpcRequest requires id to be str | int, use empty string as fallback
                temp_rpc_request = JsonRpcRequest(
                    jsonrpc="2.0", method=ASAP_METHOD, params={}, id=""
                )
                ctx = RequestContext(
                    request_id="",
                    start_time=start_time,
                    metrics=temp_metrics,
                    rpc_request=temp_rpc_request,
                )
            return self._handle_internal_error(e, ctx, payload_type)


def create_app(
    manifest: Manifest,
    registry: HandlerRegistry | None = None,
    token_validator: Callable[[str], str | None] | None = None,
) -> FastAPI:
    """Create and configure a FastAPI application for ASAP protocol.

    This factory function creates a FastAPI app with:
    - POST /asap endpoint for handling ASAP messages via JSON-RPC
    - GET /.well-known/asap/manifest.json for agent discovery
    - GET /asap/metrics for Prometheus-compatible metrics
    - Authentication middleware (if manifest.auth is configured)
    - Error handling middleware
    - Request validation
    - Extensible handler registry for payload processing

    Args:
        manifest: The agent's manifest describing capabilities and endpoints
        registry: Optional handler registry for processing payloads.
            If None, a default registry with echo handler is created.
        token_validator: Optional function to validate Bearer tokens.
            Required if manifest.auth is configured. Should return agent ID
            if token is valid, None otherwise.

    Returns:
        Configured FastAPI application ready to run

    Raises:
        ValueError: If manifest requires authentication but no token_validator provided

    Example:
        >>> from asap.models.entities import Manifest, Capability, Endpoint, Skill, AuthScheme
        >>> from asap.transport.handlers import HandlerRegistry
        >>> manifest = Manifest(
        ...     id="urn:asap:agent:test",
        ...     name="Test Agent",
        ...     version="1.0.0",
        ...     description="Test agent",
        ...     capabilities=Capability(
        ...         asap_version="0.1",
        ...         skills=[Skill(id="test", description="Test skill")],
        ...         state_persistence=False
        ...     ),
        ...     endpoints=Endpoint(asap="http://localhost:8000/asap")
        ... )
        >>> app = create_app(manifest)
        >>>
        >>> # With authentication:
        >>> manifest_with_auth = Manifest(
        ...     ...,  # same as above
        ...     auth=AuthScheme(schemes=["bearer"])
        ... )
        >>> def my_token_validator(token: str) -> str | None:
        ...     if token == "valid-token":
        ...         return "urn:asap:agent:client"
        ...     return None
        >>> app = create_app(manifest_with_auth, token_validator=my_token_validator)
        >>>
        >>> # With custom registry:
        >>> registry = HandlerRegistry()
        >>> registry.register("task.request", my_handler)
        >>> app = create_app(manifest, registry)
        >>> # Run with uvicorn: uvicorn module:app
    """
    # Use default registry if none provided
    if registry is None:
        registry = create_default_registry()

    # Create authentication middleware if auth is configured
    auth_middleware: AuthenticationMiddleware | None = None
    if manifest.auth is not None:
        if token_validator is None:
            raise ValueError(
                "token_validator is required when manifest.auth is configured. "
                "Provide a function that validates tokens and returns agent IDs."
            )
        validator = BearerTokenValidator(token_validator)
        auth_middleware = AuthenticationMiddleware(manifest, validator)
        logger.info(
            "asap.server.auth_enabled",
            manifest_id=manifest.id,
            schemes=manifest.auth.schemes,
        )

    # Create request handler
    handler = ASAPRequestHandler(registry, manifest, auth_middleware)

    app = FastAPI(
        title="ASAP Protocol Server",
        description=f"ASAP server for {manifest.name}",
        version=manifest.version,
    )
    # Note: Request size limits should be configured at the ASGI server level (e.g., uvicorn).
    # For production, consider setting --limit-max-requests or using a reverse proxy
    # (nginx, traefik) to enforce request size limits (e.g., 10MB max).

    @app.get("/.well-known/asap/manifest.json")
    async def get_manifest() -> dict[str, Any]:
        """Return the agent's manifest for discovery.

        This endpoint allows other agents to discover this agent's
        capabilities, skills, and communication endpoints.

        Returns:
            Agent manifest as JSON dictionary

        Example:
            >>> manifest = get_manifest()
            >>> "id" in manifest
            True
        """
        return manifest.model_dump()

    @app.get("/asap/metrics")
    async def get_metrics_endpoint() -> PlainTextResponse:
        """Return Prometheus-compatible metrics.

        This endpoint exposes server metrics in Prometheus text format,
        including request counts, error rates, and latency histograms.

        Returns:
            PlainTextResponse with metrics in Prometheus format

        Example:
            curl http://localhost:8000/asap/metrics
        """
        metrics = get_metrics()
        return PlainTextResponse(
            content=metrics.export_prometheus(),
            media_type="text/plain; version=0.0.4; charset=utf-8",
        )

    @app.post("/asap")
    async def handle_asap_message(request: Request) -> JSONResponse:
        """Handle ASAP messages wrapped in JSON-RPC 2.0.

        This endpoint:
        1. Receives JSON-RPC wrapped ASAP envelopes
        2. Validates the request structure
        3. Extracts and processes the ASAP envelope
        4. Returns response wrapped in JSON-RPC
        5. Records metrics for observability

        Args:
            request: FastAPI request object with JSON body

        Returns:
            JSON-RPC response or error response

        Example:
            >>> # Send JSON-RPC to POST /asap and receive JSON-RPC response.
            >>> # See tests/transport/test_server.py for full request examples.
        """
        return await handler.handle_message(request)

    return app


def _create_default_manifest() -> Manifest:
    """Create a default manifest for standalone server execution.

    This manifest is used when running the server directly via uvicorn
    without providing a custom manifest.

    Returns:
        Default manifest with basic echo capabilities
    """
    return Manifest(
        id="urn:asap:agent:default-server",
        name="ASAP Default Server",
        version="0.1.0",
        description="Default ASAP protocol server with echo capabilities",
        capabilities=Capability(
            asap_version="0.1",
            skills=[Skill(id="echo", description="Echo back the input")],
            state_persistence=False,
        ),
        endpoints=Endpoint(asap="http://localhost:8000/asap"),
    )


# Default app instance for direct uvicorn execution:
#   uvicorn asap.transport.server:app --host 0.0.0.0 --port 8000
app = create_app(_create_default_manifest(), create_default_registry())
