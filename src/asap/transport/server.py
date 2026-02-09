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

import importlib
import json
import os
import sys
import threading
import time
import traceback
from contextlib import asynccontextmanager, suppress
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, TypeVar, cast

from fastapi import FastAPI, HTTPException, Request, WebSocket
from fastapi.responses import JSONResponse, PlainTextResponse, Response
from opentelemetry import context
from pydantic import ValidationError
from slowapi.errors import RateLimitExceeded

from asap.discovery import health as discovery_health
from asap.discovery import wellknown
from asap.errors import InvalidNonceError, InvalidTimestampError, ThreadPoolExhaustedError
from asap.models.constants import MAX_REQUEST_SIZE
from asap.models.entities import Capability, Endpoint, Manifest, Skill
from asap.models.envelope import Envelope
from asap.observability import (
    get_logger,
    get_metrics,
    is_debug_log_mode,
    is_debug_mode,
    sanitize_for_logging,
)
from asap.observability.tracing import (
    configure_tracing,
    extract_and_activate_envelope_trace_context,
    inject_envelope_trace_context,
)
from asap.utils.sanitization import sanitize_nonce
from asap.auth import OAuth2Config, OAuth2Middleware
from asap.transport.middleware import (
    AuthenticationMiddleware,
    BearerTokenValidator,
    SizeLimitMiddleware,
    create_limiter,
    limiter,
    rate_limit_handler,
)
from asap.observability.metrics import MetricsCollector
from asap.transport.executors import BoundedExecutor
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
from asap.transport.compression import (
    decompress_payload,
    get_supported_encodings,
)
from asap.state.snapshot import SnapshotStore
from asap.state.stores import create_snapshot_store
from asap.transport.validators import (
    InMemoryNonceStore,
    NonceStore,
    validate_envelope_nonce,
    validate_envelope_timestamp,
)
from asap.transport.websocket import (
    WS_CLOSE_GOING_AWAY,
    WS_CLOSE_REASON_SHUTDOWN,
    handle_websocket_connection,
)

# Module logger
logger = get_logger(__name__)

# Type variable for handler result pattern
T = TypeVar("T")
HandlerResult = tuple[T | None, JSONResponse | None]

# Environment variable to enable handler hot reload (development)
ENV_HOT_RELOAD = "ASAP_HOT_RELOAD"


class RegistryHolder:
    """Mutable holder for HandlerRegistry to support hot reload.

    When hot reload is enabled, a background thread watches handlers.py and
    replaces the registry on file change so new handler code is used without
    restarting the server.
    """

    def __init__(self, registry: HandlerRegistry) -> None:
        self.registry = registry
        self._executor: BoundedExecutor | None = None

    def replace_registry(self, new_registry: HandlerRegistry) -> None:
        """Replace the held registry (e.g. after reloading handlers module)."""
        if self._executor is not None:
            new_registry._executor = self._executor
        self.registry = new_registry


_HOT_RELOAD_RETRY_DELAY_SECONDS = 5.0


def _run_handler_watcher(holder: RegistryHolder, handlers_path: str) -> None:
    """Background thread: watch handlers_path and reload registry on change.

    On filesystem/watch errors the loop retries after a delay so the thread
    keeps running. If watchfiles is not installed, hot reload is skipped.
    """
    try:
        from watchfiles import watch
    except ImportError:
        logger.warning(
            "asap.server.handler_watcher_skip",
            path=handlers_path,
            message="watchfiles not installed; hot reload disabled. Install with: pip install watchfiles",
        )
        return
    while True:
        try:
            for changes in watch(handlers_path):
                if not changes:
                    continue
                try:
                    import asap.transport.handlers as handlers_module

                    importlib.reload(handlers_module)
                    new_registry = handlers_module.create_default_registry()
                    holder.replace_registry(new_registry)
                    logger.info(
                        "asap.server.handlers_reloaded",
                        path=handlers_path,
                        handlers=new_registry.list_handlers(),
                    )
                except Exception as e:
                    logger.warning(
                        "asap.server.handlers_reload_failed",
                        path=handlers_path,
                        error=str(e),
                    )
        except Exception as e:
            logger.warning(
                "asap.server.handler_watcher_retry",
                path=handlers_path,
                error=str(e),
                retry_seconds=_HOT_RELOAD_RETRY_DELAY_SECONDS,
            )
            time.sleep(_HOT_RELOAD_RETRY_DELAY_SECONDS)


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
        >>> handler = ASAPRequestHandler(RegistryHolder(registry), manifest, auth_middleware)
        >>> response = await handler.handle_message(request)
    """

    def __init__(
        self,
        registry_holder: RegistryHolder,
        manifest: Manifest,
        auth_middleware: AuthenticationMiddleware | None = None,
        max_request_size: int = MAX_REQUEST_SIZE,
        nonce_store: NonceStore | None = None,
    ) -> None:
        """Initialize the request handler.

        Args:
            registry_holder: Holder for handler registry (supports hot reload).
            manifest: Agent manifest describing capabilities
            auth_middleware: Optional authentication middleware for request validation
            max_request_size: Maximum allowed request size in bytes
            nonce_store: Optional nonce store for replay attack prevention
        """
        self.registry_holder = registry_holder
        self.manifest = manifest
        self.auth_middleware = auth_middleware
        self.max_request_size = max_request_size
        self.nonce_store = nonce_store

    def _normalize_payload_type_for_metrics(self, payload_type: str) -> str:
        """Normalize payload type for metrics to prevent cardinality explosion.

        Only registered payload types are used as metric labels. Unknown
        payload types are normalized to "other" to prevent DoS attacks
        through metric cardinality explosion.

        Args:
            payload_type: The payload type to normalize

        Returns:
            The payload type if registered, or "other" if unknown
        """
        if self.registry_holder.registry.has_handler(payload_type):
            return payload_type
        return "other"

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
        # Normalize payload_type to prevent cardinality explosion
        normalized_payload_type = self._normalize_payload_type_for_metrics(payload_type)
        metrics.increment_counter(
            "asap_requests_total",
            {"payload_type": normalized_payload_type, "status": "error"},
        )
        metrics.increment_counter(
            "asap_requests_error_total",
            {"payload_type": normalized_payload_type, "error_type": error_type},
        )
        metrics.observe_histogram(
            "asap_request_duration_seconds",
            duration_seconds,
            {"payload_type": normalized_payload_type, "status": "error"},
        )
        # Specific error counters for observability
        if error_type == "parse_error":
            metrics.increment_counter("asap_parse_errors_total")
        elif error_type == "auth_failed":
            metrics.increment_counter("asap_auth_failures_total")
        elif error_type == "invalid_timestamp":
            metrics.increment_counter("asap_invalid_timestamp_total")
        elif error_type == "invalid_nonce":
            metrics.increment_counter("asap_invalid_nonce_total")
        elif error_type == "sender_mismatch":
            metrics.increment_counter("asap_sender_mismatch_total")
        elif error_type in (
            "invalid_envelope",
            "missing_envelope",
            "invalid_params",
        ):
            metrics.increment_counter("asap_validation_errors_total", {"reason": error_type})

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

        if not isinstance(envelope_data, dict):
            logger.warning(
                "asap.request.invalid_envelope_type",
                type=type(envelope_data).__name__,
            )
            error_response = self.build_error_response(
                INVALID_PARAMS,
                data={"error": "'envelope' must be a JSON object"},
                request_id=ctx.request_id,
            )
            self.record_error_metrics(
                ctx.metrics,
                "unknown",
                "invalid_envelope",
                time.perf_counter() - ctx.start_time,
            )
            return None, error_response

        try:
            envelope = Envelope(**envelope_data)
            payload_type = envelope.payload_type
            return envelope, payload_type
        except ValidationError as e:
            log_data: dict[str, Any] = {
                "error": "Invalid envelope structure",
                "validation_errors": e.errors(),
            }
            if not is_debug_mode():
                log_data = sanitize_for_logging(log_data)
            logger.warning("asap.request.invalid_envelope", **log_data)
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
            response_envelope = await self.registry_holder.registry.dispatch_async(
                envelope, self.manifest
            )
            return response_envelope, payload_type
        except ThreadPoolExhaustedError as e:
            # Thread pool exhausted - service temporarily unavailable
            logger.warning(
                "asap.request.thread_pool_exhausted",
                payload_type=payload_type,
                envelope_id=envelope.id,
                max_threads=e.max_threads,
                active_threads=e.active_threads,
            )
            # Record error metric
            duration_seconds = time.perf_counter() - ctx.start_time
            self.record_error_metrics(
                ctx.metrics, payload_type, "thread_pool_exhausted", duration_seconds
            )
            # Return HTTP 503 Service Unavailable (not JSON-RPC error)
            error_response = JSONResponse(
                status_code=503,
                content={
                    "error": "Service Temporarily Unavailable",
                    "code": e.code,
                    "message": e.message,
                    "details": e.details,
                },
            )
            return None, error_response
        except HandlerNotFoundError as e:
            # No handler registered for this payload type
            logger.warning(
                "asap.request.handler_not_found",
                payload_type=e.payload_type,
                envelope_id=envelope.id,
            )
            # Record error metric
            duration_seconds = time.perf_counter() - ctx.start_time
            self.record_error_metrics(
                ctx.metrics, payload_type, "handler_not_found", duration_seconds
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
        response_envelope = inject_envelope_trace_context(response_envelope)
        duration_seconds = time.perf_counter() - ctx.start_time
        duration_ms = duration_seconds * 1000

        # Normalize payload_type to prevent cardinality explosion
        normalized_payload_type = self._normalize_payload_type_for_metrics(payload_type)

        # Record success metrics
        ctx.metrics.increment_counter(
            "asap_requests_total",
            {"payload_type": normalized_payload_type, "status": "success"},
        )
        ctx.metrics.increment_counter(
            "asap_requests_success_total",
            {"payload_type": normalized_payload_type},
        )
        ctx.metrics.observe_histogram(
            "asap_request_duration_seconds",
            duration_seconds,
            {"payload_type": normalized_payload_type, "status": "success"},
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

        # Record error metrics (normalized to prevent cardinality explosion)
        self.record_error_metrics(ctx.metrics, payload_type, "internal_error", duration_seconds)

        # Always log full error server-side for diagnostics
        logger.exception(
            "asap.request.error",
            error=str(error),
            error_type=type(error).__name__,
            duration_ms=round(duration_ms, 2),
        )

        # Production: generic error to client; debug: full error and stack trace
        if is_debug_mode():
            error_data: dict[str, Any] = {
                "error": str(error),
                "type": type(error).__name__,
                "traceback": traceback.format_exc(),
            }
        else:
            error_data = {"error": "Internal server error"}

        internal_error = JsonRpcErrorResponse(
            error=JsonRpcError.from_code(INTERNAL_ERROR, data=error_data),
            id=ctx.request_id,
        )
        return JSONResponse(
            status_code=200,
            content=internal_error.model_dump(),
        )

    def _log_request_debug(self, rpc_request: JsonRpcRequest) -> None:
        """Log full JSON-RPC request when ASAP_DEBUG_LOG is enabled (structured JSON)."""
        if not is_debug_log_mode():
            return
        request_dict: dict[str, Any] = rpc_request.model_dump()
        if not is_debug_mode():
            request_dict = sanitize_for_logging(request_dict)
        logger.info("asap.request.debug_request", request_json=request_dict)

    def _log_response_debug(self, response: JSONResponse) -> None:
        """Log full response when ASAP_DEBUG_LOG is enabled (structured JSON)."""
        if not is_debug_log_mode():
            return
        try:
            body_bytes = response.body
            # Handle both bytes and memoryview
            if isinstance(body_bytes, memoryview):
                body_bytes = body_bytes.tobytes()
            response_dict: dict[str, Any] = json.loads(body_bytes.decode("utf-8"))
        except (ValueError, AttributeError):
            response_dict = {"_raw": "(unable to decode response body)"}
        if not is_debug_mode():
            response_dict = sanitize_for_logging(response_dict)
        logger.info(
            "asap.request.debug_response",
            status_code=response.status_code,
            response_json=response_dict,
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
        except HTTPException as e:
            # HTTPException (e.g., 413 Payload Too Large) should be returned directly
            # Don't convert to JSON-RPC error response
            from fastapi.responses import JSONResponse

            return None, JSONResponse(
                status_code=e.status_code,
                content={"detail": e.detail},
                headers=e.headers if hasattr(e, "headers") else None,
            )
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

        rpc_request, validation_error = self.validate_jsonrpc_request(body)
        if validation_error is not None:
            temp_metrics = get_metrics()
            self.record_error_metrics(temp_metrics, "unknown", "invalid_request", 0.0)
            return None, validation_error

        if rpc_request is None:
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

    def _validate_request_size(self, request: Request, max_size: int) -> None:
        """Validate that request size does not exceed maximum.

        Checks Content-Length header first, then validates actual body size
        if available. Raises HTTPException(413) if request is too large.

        Args:
            request: FastAPI request object
            max_size: Maximum allowed request size in bytes

        Raises:
            HTTPException: If request size exceeds maximum (413 Payload Too Large)
        """
        content_length = request.headers.get("content-length")
        if content_length:
            try:
                size = int(content_length)
                if size > max_size:
                    logger.warning(
                        "asap.request.size_exceeded",
                        content_length=size,
                        max_size=max_size,
                    )
                    raise HTTPException(
                        status_code=413,
                        detail=f"Request size ({size} bytes) exceeds maximum ({max_size} bytes)",
                    )
            except ValueError:
                pass

    async def parse_json_body(self, request: Request) -> dict[str, Any]:
        """Parse JSON body from request with size validation and decompression.

        Validates request size before parsing to prevent DoS attacks.
        Checks both Content-Length header and actual body size.
        Automatically decompresses gzip/brotli encoded requests.

        Args:
            request: FastAPI request object

        Returns:
            Parsed JSON body

        Raises:
            HTTPException: If request size exceeds maximum (413)
            HTTPException: If Content-Encoding is unsupported (415)
            ValueError: If JSON is invalid
        """
        content_encoding = request.headers.get("content-encoding", "").lower().strip()
        supported_encodings = get_supported_encodings() + ["identity", ""]
        if content_encoding and content_encoding not in supported_encodings:
            logger.warning(
                "asap.request.unsupported_encoding",
                content_encoding=content_encoding,
                supported=supported_encodings,
            )
            raise HTTPException(
                status_code=415,
                detail=f"Unsupported Content-Encoding: {content_encoding}. Supported: {', '.join(get_supported_encodings())}",
            )

        try:
            body_bytes = bytearray()
            async for chunk in request.stream():
                body_bytes.extend(chunk)
                if len(body_bytes) > self.max_request_size:
                    logger.warning(
                        "asap.request.size_exceeded",
                        actual_size=len(body_bytes),
                        max_size=self.max_request_size,
                    )
                    raise HTTPException(
                        status_code=413,
                        detail=f"Request size ({len(body_bytes)} bytes) exceeds maximum ({self.max_request_size} bytes)",
                    )

            # Decompress if Content-Encoding is specified
            if content_encoding and content_encoding not in ("identity", ""):
                try:
                    compressed_size = len(body_bytes)
                    body_bytes = bytearray(decompress_payload(bytes(body_bytes), content_encoding))
                    decompressed_size = len(body_bytes)

                    logger.debug(
                        "asap.request.decompressed",
                        content_encoding=content_encoding,
                        compressed_size=compressed_size,
                        decompressed_size=decompressed_size,
                    )

                    if decompressed_size > self.max_request_size:
                        compression_ratio = (
                            decompressed_size / compressed_size if compressed_size > 0 else 0
                        )
                        logger.warning(
                            "asap.request.decompressed_size_exceeded",
                            decompressed_size=decompressed_size,
                            original_compressed_size=compressed_size,
                            compression_ratio=round(compression_ratio, 2),
                            max_size=self.max_request_size,
                        )
                        raise HTTPException(
                            status_code=413,
                            detail=f"Decompressed request size ({decompressed_size} bytes) exceeds maximum ({self.max_request_size} bytes)",
                        )
                except ValueError as e:
                    # Decompression failed (invalid compressed data or unsupported encoding)
                    logger.warning(
                        "asap.request.decompression_failed",
                        content_encoding=content_encoding,
                        error=str(e),
                    )
                    raise HTTPException(
                        status_code=400,
                        detail=f"Failed to decompress request: {e}",
                    ) from e
                except (OSError, EOFError) as e:
                    # Invalid gzip/brotli data (OSError) or truncated data (EOFError)
                    logger.warning(
                        "asap.request.invalid_compressed_data",
                        content_encoding=content_encoding,
                        error=str(e),
                    )
                    raise HTTPException(
                        status_code=400,
                        detail=f"Invalid compressed data: {e}",
                    ) from e

            # Parse JSON from bytes
            body: dict[str, Any] = json.loads(body_bytes.decode("utf-8"))
            return body
        except UnicodeDecodeError as e:
            logger.warning("asap.request.invalid_encoding", error=str(e))
            raise ValueError(f"Invalid UTF-8 encoding: {e}") from e
        except json.JSONDecodeError as e:
            logger.warning("asap.request.invalid_json", error=str(e))
            raise ValueError(f"Invalid JSON: {e}") from e

    def validate_jsonrpc_request(
        self, body: dict[str, Any]
    ) -> tuple[JsonRpcRequest | None, JSONResponse | None]:
        """Validate JSON-RPC request structure and method.

        Args:
            body: Parsed JSON body

        Returns:
            Tuple of (JsonRpcRequest, None) if valid, or (None, error_response) if invalid
        """
        try:
            rpc_request = JsonRpcRequest(**body)
        except (ValidationError, TypeError) as e:
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

            log_struct: dict[str, Any] = {
                "error": error_message,
                "error_type": type(e).__name__,
                "validation_errors": (
                    e.errors()
                    if isinstance(e, ValidationError)
                    else [{"type": "type_error", "loc": (), "msg": str(e), "input": None}]
                ),
            }
            if not is_debug_mode():
                log_struct = sanitize_for_logging(log_struct)
            logger.warning("asap.request.invalid_structure", **log_struct)
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
            parse_result = await self._parse_and_validate_request(request)
            rpc_request, parse_error = parse_result
            if parse_error is not None:
                self._log_response_debug(parse_error)
                return parse_error
            if rpc_request is None:
                raise RuntimeError("Internal error: rpc_request is None after validation")

            self._log_request_debug(rpc_request)

            ctx = RequestContext(
                request_id=rpc_request.id,
                start_time=start_time,
                metrics=metrics,
                rpc_request=rpc_request,
            )

            auth_result = await self._authenticate_request(request, ctx)
            authenticated_agent_id, auth_error = auth_result
            if auth_error is not None:
                self._log_response_debug(auth_error)
                return auth_error

            envelope_result = self._validate_envelope(ctx)
            envelope_or_none, result = envelope_result
            if envelope_or_none is None:
                error_resp = cast(JSONResponse, result)
                self._log_response_debug(error_resp)
                return error_resp
            envelope = envelope_or_none
            payload_type = cast(str, result)

            trace_token = extract_and_activate_envelope_trace_context(envelope)
            try:
                sender_error = self._verify_sender_matches_auth(
                    authenticated_agent_id,
                    envelope,
                    ctx,
                    payload_type,
                )
                if sender_error is not None:
                    self._log_response_debug(sender_error)
                    return sender_error

                try:
                    validate_envelope_timestamp(envelope)
                except InvalidTimestampError as e:
                    log_ts: dict[str, Any] = {
                        "envelope_id": envelope.id,
                        "error": e.message,
                        "details": e.details,
                    }
                    if not is_debug_mode() and isinstance(e.details, dict):
                        log_ts["details"] = sanitize_for_logging(e.details)
                    logger.warning("asap.request.invalid_timestamp", **log_ts)
                    duration_seconds = time.perf_counter() - ctx.start_time
                    self.record_error_metrics(
                        ctx.metrics, payload_type, "invalid_timestamp", duration_seconds
                    )
                    err_resp = self.build_error_response(
                        INVALID_PARAMS,
                        data={
                            "error": "Invalid envelope timestamp",
                            "code": e.code,
                            "message": e.message,
                            "details": e.details,
                        },
                        request_id=ctx.request_id,
                    )
                    self._log_response_debug(err_resp)
                    return err_resp

                try:
                    validate_envelope_nonce(envelope, self.nonce_store)
                except InvalidNonceError as e:
                    # Sanitize nonce in logs to prevent full value exposure
                    nonce_sanitized = sanitize_nonce(e.nonce)
                    error_msg = e.message if is_debug_mode() else "Duplicate nonce detected"
                    logger.warning(
                        "asap.request.invalid_nonce",
                        envelope_id=envelope.id,
                        nonce=nonce_sanitized,
                        error=error_msg,
                    )
                    duration_seconds = time.perf_counter() - ctx.start_time
                    self.record_error_metrics(
                        ctx.metrics, payload_type, "invalid_nonce", duration_seconds
                    )
                    err_resp = self.build_error_response(
                        INVALID_PARAMS,
                        data={
                            "error": "Invalid envelope nonce",
                            "code": e.code,
                            "message": e.message,
                            "details": e.details,
                        },
                        request_id=ctx.request_id,
                    )
                    self._log_response_debug(err_resp)
                    return err_resp

                logger.info(
                    "asap.request.received",
                    envelope_id=envelope.id,
                    trace_id=envelope.trace_id,
                    payload_type=envelope.payload_type,
                    sender=envelope.sender,
                    recipient=envelope.recipient,
                    authenticated=authenticated_agent_id is not None,
                )

                dispatch_result = await self._dispatch_to_handler(envelope, ctx)
                response_or_none, result = dispatch_result
                if response_or_none is None:
                    error_resp = cast(JSONResponse, result)
                    self._log_response_debug(error_resp)
                    return error_resp
                response_envelope = response_or_none
                payload_type = cast(str, result)

                success_resp = self._build_success_response(response_envelope, ctx, payload_type)
                self._log_response_debug(success_resp)
                return success_resp
            finally:
                if trace_token is not None:
                    context.detach(trace_token)

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
            err_resp = self._handle_internal_error(e, ctx, payload_type)
            self._log_response_debug(err_resp)
            return err_resp


def create_app(
    manifest: Manifest,
    registry: HandlerRegistry | None = None,
    token_validator: Callable[[str], str | None] | None = None,
    oauth2_config: OAuth2Config | None = None,
    rate_limit: str | None = None,
    max_request_size: int | None = None,
    max_threads: int | None = None,
    require_nonce: bool = False,
    hot_reload: bool | None = None,
    snapshot_store: SnapshotStore | None = None,
) -> FastAPI:
    """Create and configure a FastAPI application for ASAP protocol.

    This factory function creates a FastAPI app with:
    - POST /asap endpoint for handling ASAP messages via JSON-RPC
    - WebSocket /asap/ws for real-time JSON-RPC (same protocol as POST /asap)
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
        oauth2_config: Optional OAuth2 config. When provided, OAuth2Middleware
            is applied to all /asap/* routes (JWT validation via JWKS). If not
            provided, /asap remains unauthenticated unless manifest.auth is used.
        rate_limit: Optional rate limit string (e.g., "10/second;100/minute").
            Rate limiting is IP-based (per client IP address) to prevent DoS attacks.
            Uses token bucket pattern: burst limit + sustained limit.
            Defaults to ASAP_RATE_LIMIT environment variable or "10/second;100/minute".
            **Warning:** The default storage is ``memory://`` (per-process). In
            multi-worker deployments (e.g., Gunicorn with 4 workers), each worker
            has isolated limits, so effective rate = limit × workers (e.g.,
            10/s → 40/s). For production, use Redis-backed storage via slowapi.
        max_request_size: Optional maximum request size in bytes.
            Defaults to ASAP_MAX_REQUEST_SIZE environment variable or 10MB.
        max_threads: Optional maximum number of threads for sync handlers.
            Defaults to ASAP_MAX_THREADS environment variable or min(32, cpu_count + 4).
            Set to None to use unbounded executor (not recommended for production).
        require_nonce: If True, enables nonce validation for replay attack prevention.
            When enabled, creates an InMemoryNonceStore and validates nonces in envelopes.
            Defaults to False (nonce validation is optional).
        hot_reload: If True, watch handlers.py and reload handler registry on file change
            (development only). Defaults to ASAP_HOT_RELOAD env or False.
        snapshot_store: Optional SnapshotStore for state persistence. If None, uses
            create_snapshot_store() (ASAP_STORAGE_BACKEND and ASAP_STORAGE_PATH).
            Stored on app.state.snapshot_store for handlers.
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
    # Configure thread pool executor for DoS prevention
    executor: BoundedExecutor | None = None
    if max_threads is None:
        max_threads_env = os.getenv("ASAP_MAX_THREADS")
        if max_threads_env:
            max_threads = int(max_threads_env)
    if max_threads is not None:
        executor = BoundedExecutor(max_threads=max_threads)
        logger.info(
            "asap.server.bounded_executor_enabled",
            manifest_id=manifest.id,
            max_threads=max_threads,
        )

    # Use default registry if none provided
    use_default_registry = registry is None
    if registry is None:
        registry = create_default_registry()

    # Attach executor to registry if provided
    if executor is not None:
        registry._executor = executor

    # Wrap registry in holder for hot reload support
    registry_holder = RegistryHolder(registry)
    if executor is not None:
        registry_holder._executor = executor

    # Resolve hot_reload from env if not specified
    if hot_reload is None:
        hot_reload = os.getenv(ENV_HOT_RELOAD, "").strip().lower() in ("true", "1", "yes")

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

    # Configure max request size
    if max_request_size is None:
        max_request_size = int(os.getenv("ASAP_MAX_REQUEST_SIZE", str(MAX_REQUEST_SIZE)))

    # Create nonce store if required
    nonce_store: NonceStore | None = None
    if require_nonce:
        nonce_store = InMemoryNonceStore()
        logger.info(
            "asap.server.nonce_validation_enabled",
            manifest_id=manifest.id,
        )

    # Resolve snapshot store (env-based when not provided)
    if snapshot_store is None:
        snapshot_store = create_snapshot_store()
        logger.info(
            "asap.server.snapshot_store_from_env",
            manifest_id=manifest.id,
            backend=os.environ.get("ASAP_STORAGE_BACKEND", "memory"),
        )

    # Create request handler
    handler = ASAPRequestHandler(
        registry_holder, manifest, auth_middleware, max_request_size, nonce_store
    )

    # Start handler file watcher when hot reload is enabled (only with default registry)
    if hot_reload and use_default_registry:
        _handlers_module = sys.modules.get("asap.transport.handlers")
        _handlers_file = getattr(_handlers_module, "__file__", "") if _handlers_module else ""
        if _handlers_file and Path(_handlers_file).exists():
            watcher = threading.Thread(
                target=_run_handler_watcher,
                args=(registry_holder, _handlers_file),
                name="asap-handler-watcher",
                daemon=True,
            )
            watcher.start()
            logger.info(
                "asap.server.hot_reload_enabled",
                manifest_id=manifest.id,
                path=_handlers_file,
            )
        else:
            logger.warning(
                "asap.server.hot_reload_skipped",
                reason="handlers module path not found",
            )

    # Enable Swagger UI (/docs) and ReDoc (/redoc) only when ASAP_DEBUG=true
    _docs_url = "/docs" if is_debug_mode() else None
    _redoc_url = "/redoc" if is_debug_mode() else None
    _openapi_url = "/openapi.json" if is_debug_mode() else None

    # Track active WebSocket connections for graceful shutdown (close with reason)
    _active_websockets: set[WebSocket] = set()

    @asynccontextmanager
    async def _lifespan(app: FastAPI) -> Any:
        yield
        for ws in list(_active_websockets):
            with suppress(OSError):
                await ws.close(
                    code=WS_CLOSE_GOING_AWAY,
                    reason=WS_CLOSE_REASON_SHUTDOWN,
                )

    app = FastAPI(
        title="ASAP Protocol Server",
        description=f"ASAP server for {manifest.name}",
        version=manifest.version,
        docs_url=_docs_url,
        redoc_url=_redoc_url,
        openapi_url=_openapi_url,
        lifespan=_lifespan,
    )
    app.state.websocket_connections = _active_websockets

    # Add size limit middleware (runs before routing)
    app.add_middleware(SizeLimitMiddleware, max_size=max_request_size)

    if oauth2_config is not None:
        middleware_kwargs: dict[str, Any] = {
            "jwks_uri": oauth2_config.jwks_uri,
            "required_scope": oauth2_config.required_scope,
            "path_prefix": oauth2_config.path_prefix,
            "manifest_id": manifest.id,
            "custom_claim": oauth2_config.custom_claim,
        }
        if oauth2_config.jwks_fetcher is not None:
            middleware_kwargs["jwks_fetcher"] = oauth2_config.jwks_fetcher
        app.add_middleware(OAuth2Middleware, **middleware_kwargs)
        logger.info(
            "asap.server.oauth2_enabled",
            manifest_id=manifest.id,
            jwks_uri=oauth2_config.jwks_uri,
            path_prefix=oauth2_config.path_prefix,
        )

    # Configure rate limiting
    if rate_limit is None:
        # Default matches DD-012: Burst allowance for better UX with bursty agent traffic
        rate_limit_str = os.getenv("ASAP_RATE_LIMIT", "10/second;100/minute")
    else:
        rate_limit_str = rate_limit

    # Create isolated limiter instance for this app
    # This ensures each app instance has its own rate limiter storage
    # Tests can override this via monkeypatch or direct assignment to app.state.limiter
    app.state.limiter = create_limiter([rate_limit_str])
    app.state.max_request_size = max_request_size
    app.state.snapshot_store = snapshot_store
    app.add_exception_handler(RateLimitExceeded, rate_limit_handler)
    logger.info(
        "asap.server.rate_limit_enabled",
        manifest_id=manifest.id,
        rate_limit=rate_limit_str,
    )
    logger.info(
        "asap.server.max_request_size",
        manifest_id=manifest.id,
        max_request_size=max_request_size,
    )

    @app.get("/health")
    async def health() -> JSONResponse:
        """Liveness probe: always OK if the process is running.

        Used by Kubernetes livenessProbe and Docker HEALTHCHECK.
        Returns 200 with {"status": "ok"}.

        Returns:
            JSONResponse with status ok
        """
        return JSONResponse(status_code=200, content={"status": "ok"})

    @app.get("/ready")
    async def ready() -> JSONResponse:
        """Readiness probe: OK when the server is ready to accept traffic.

        Used by Kubernetes readinessProbe. Returns 200 when the app
        is initialized and can serve requests.

        Returns:
            JSONResponse with status ok
        """
        return JSONResponse(status_code=200, content={"status": "ok"})

    server_started_at = time.monotonic()
    if manifest is not None:

        @app.get(wellknown.WELLKNOWN_MANIFEST_PATH)
        async def get_manifest(request: Request) -> Response:
            """Return the agent's manifest for discovery.

            This endpoint allows other agents to discover this agent's
            capabilities, skills, and communication endpoints.
            """
            return await wellknown.get_manifest_response(manifest, request)

        @app.get(discovery_health.WELLKNOWN_HEALTH_PATH)
        async def get_health() -> JSONResponse:
            """Return agent health/liveness status (200 healthy, 503 unhealthy)."""
            return await discovery_health.get_health_response_async(manifest, server_started_at)

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
            media_type="application/openmetrics-text; version=1.0.0; charset=utf-8",
        )

    # OpenTelemetry tracing (zero-config via OTEL_* env vars)
    configure_tracing(service_name=manifest.id, app=app)

    @app.post("/asap")
    @limiter.limit(rate_limit_str)  # slowapi uses app.state.limiter at runtime
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

    @app.websocket("/asap/ws")
    async def websocket_asap(websocket: WebSocket) -> None:
        """ASAP JSON-RPC over WebSocket; same handlers as POST /asap."""
        await handle_websocket_connection(
            websocket,
            handler,
            app.state.websocket_connections,
        )

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
        version="1.0.0-dev",
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
