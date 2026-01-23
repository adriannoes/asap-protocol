"""FastAPI server implementation for ASAP protocol.

This module provides a production-ready FastAPI server that:
- Exposes POST /asap endpoint for JSON-RPC 2.0 wrapped ASAP messages
- Exposes GET /.well-known/asap/manifest.json for agent discovery
- Exposes GET /asap/metrics for Prometheus-compatible metrics
- Handles errors with proper JSON-RPC error responses
- Validates all incoming requests against ASAP schemas
- Uses HandlerRegistry for extensible payload processing
- Provides structured logging for observability

Example:
    >>> from asap.models.entities import Manifest, Capability, Endpoint, Skill
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
    ...     endpoints=Endpoint(asap="http://localhost:8000/asap")
    ... )
    >>>
    >>> # Create app with default registry
    >>> app = create_app(manifest)
    >>>
    >>> # Or with custom registry
    >>> registry = HandlerRegistry()
    >>> registry.register("task.request", my_custom_handler)
    >>> app = create_app(manifest, registry)
    >>>
    >>> # Run with: uvicorn asap.transport.server:app --host 0.0.0.0 --port 8000
"""

import time
from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, PlainTextResponse
from pydantic import ValidationError

from asap.models.entities import Capability, Endpoint, Manifest, Skill
from asap.models.envelope import Envelope
from asap.observability import get_logger, get_metrics
from asap.transport.handlers import (
    HandlerNotFoundError,
    HandlerRegistry,
    create_default_registry,
)
from asap.transport.jsonrpc import (
    INTERNAL_ERROR,
    INVALID_PARAMS,
    INVALID_REQUEST,
    METHOD_NOT_FOUND,
    JsonRpcError,
    JsonRpcErrorResponse,
    JsonRpcRequest,
    JsonRpcResponse,
)

# Module logger
logger = get_logger(__name__)


def create_app(
    manifest: Manifest,
    registry: HandlerRegistry | None = None,
) -> FastAPI:
    """Create and configure a FastAPI application for ASAP protocol.

    This factory function creates a FastAPI app with:
    - POST /asap endpoint for handling ASAP messages via JSON-RPC
    - GET /.well-known/asap/manifest.json for agent discovery
    - Error handling middleware
    - Request validation
    - Extensible handler registry for payload processing

    Args:
        manifest: The agent's manifest describing capabilities and endpoints
        registry: Optional handler registry for processing payloads.
            If None, a default registry with echo handler is created.

    Returns:
        Configured FastAPI application ready to run

    Example:
        >>> from asap.models.entities import Manifest, Capability, Endpoint, Skill
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
        >>> # With custom registry:
        >>> registry = HandlerRegistry()
        >>> registry.register("task.request", my_handler)
        >>> app = create_app(manifest, registry)
        >>> # Run with uvicorn: uvicorn module:app
    """
    # Use default registry if none provided
    if registry is None:
        registry = create_default_registry()
    app = FastAPI(
        title="ASAP Protocol Server",
        description=f"ASAP server for {manifest.name}",
        version=manifest.version,
    )

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
        start_time = time.perf_counter()
        metrics = get_metrics()
        payload_type = "unknown"

        try:
            # Parse JSON body
            body = await request.json()

            # Validate JSON-RPC request structure
            try:
                rpc_request = JsonRpcRequest(**body)
            except ValidationError as e:
                # Invalid JSON-RPC structure
                logger.warning(
                    "asap.request.invalid_structure",
                    error="Invalid JSON-RPC structure",
                    validation_errors=str(e.errors()),
                )
                error_response = JsonRpcErrorResponse(
                    error=JsonRpcError.from_code(
                        INVALID_REQUEST,
                        data={"validation_errors": e.errors()},
                    ),
                    id=body.get("id"),
                )
                return JSONResponse(
                    status_code=200,
                    content=error_response.model_dump(),
                )

            # Check method
            if rpc_request.method != "asap.send":
                logger.warning(
                    "asap.request.unknown_method",
                    method=rpc_request.method,
                )
                error_response = JsonRpcErrorResponse(
                    error=JsonRpcError.from_code(
                        METHOD_NOT_FOUND,
                        data={"method": rpc_request.method},
                    ),
                    id=rpc_request.id,
                )
                return JSONResponse(
                    status_code=200,
                    content=error_response.model_dump(),
                )

            # Extract envelope from params
            envelope_data = rpc_request.params.get("envelope")
            if envelope_data is None:
                logger.warning("asap.request.missing_envelope")
                error_response = JsonRpcErrorResponse(
                    error=JsonRpcError.from_code(
                        INVALID_PARAMS,
                        data={"error": "Missing 'envelope' in params"},
                    ),
                    id=rpc_request.id,
                )
                return JSONResponse(
                    status_code=200,
                    content=error_response.model_dump(),
                )

            # Validate envelope structure
            try:
                envelope = Envelope(**envelope_data)
                payload_type = envelope.payload_type
            except ValidationError as e:
                logger.warning(
                    "asap.request.invalid_envelope",
                    error="Invalid envelope structure",
                    validation_errors=str(e.errors()),
                )
                # Record error metric
                duration_seconds = time.perf_counter() - start_time
                metrics.increment_counter(
                    "asap_requests_total",
                    {"payload_type": payload_type, "status": "error"},
                )
                metrics.increment_counter(
                    "asap_requests_error_total",
                    {"payload_type": payload_type, "error_type": "invalid_envelope"},
                )
                metrics.observe_histogram(
                    "asap_request_duration_seconds",
                    duration_seconds,
                    {"payload_type": payload_type, "status": "error"},
                )
                error_response = JsonRpcErrorResponse(
                    error=JsonRpcError.from_code(
                        INVALID_PARAMS,
                        data={
                            "error": "Invalid envelope structure",
                            "validation_errors": e.errors(),
                        },
                    ),
                    id=rpc_request.id,
                )
                return JSONResponse(
                    status_code=200,
                    content=error_response.model_dump(),
                )

            # Log request received
            logger.info(
                "asap.request.received",
                envelope_id=envelope.id,
                trace_id=envelope.trace_id,
                payload_type=envelope.payload_type,
                sender=envelope.sender,
                recipient=envelope.recipient,
            )

            # Process the envelope using the handler registry
            try:
                response_envelope = registry.dispatch(envelope, manifest)
            except HandlerNotFoundError as e:
                # No handler registered for this payload type
                logger.warning(
                    "asap.request.handler_not_found",
                    payload_type=e.payload_type,
                    envelope_id=envelope.id,
                )
                # Record error metric
                duration_seconds = time.perf_counter() - start_time
                metrics.increment_counter(
                    "asap_requests_total",
                    {"payload_type": payload_type, "status": "error"},
                )
                metrics.increment_counter(
                    "asap_requests_error_total",
                    {"payload_type": payload_type, "error_type": "handler_not_found"},
                )
                metrics.observe_histogram(
                    "asap_request_duration_seconds",
                    duration_seconds,
                    {"payload_type": payload_type, "status": "error"},
                )
                error_response = JsonRpcErrorResponse(
                    error=JsonRpcError.from_code(
                        METHOD_NOT_FOUND,
                        data={
                            "payload_type": e.payload_type,
                            "error": str(e),
                        },
                    ),
                    id=rpc_request.id,
                )
                return JSONResponse(
                    status_code=200,
                    content=error_response.model_dump(),
                )

            # Calculate duration
            duration_seconds = time.perf_counter() - start_time
            duration_ms = duration_seconds * 1000

            # Record success metrics
            metrics.increment_counter(
                "asap_requests_total",
                {"payload_type": payload_type, "status": "success"},
            )
            metrics.increment_counter(
                "asap_requests_success_total",
                {"payload_type": payload_type},
            )
            metrics.observe_histogram(
                "asap_request_duration_seconds",
                duration_seconds,
                {"payload_type": payload_type, "status": "success"},
            )

            # Log successful processing
            logger.info(
                "asap.request.processed",
                envelope_id=envelope.id,
                response_id=response_envelope.id,
                trace_id=envelope.trace_id,
                payload_type=envelope.payload_type,
                duration_ms=round(duration_ms, 2),
            )

            # Wrap response in JSON-RPC
            rpc_response = JsonRpcResponse(
                result={"envelope": response_envelope.model_dump(mode="json")},
                id=rpc_request.id,
            )

            return JSONResponse(
                status_code=200,
                content=rpc_response.model_dump(),
            )

        except Exception as e:
            # Calculate duration for error case
            duration_seconds = time.perf_counter() - start_time
            duration_ms = duration_seconds * 1000

            # Record error metrics
            metrics.increment_counter(
                "asap_requests_total",
                {"payload_type": payload_type, "status": "error"},
            )
            metrics.increment_counter(
                "asap_requests_error_total",
                {"payload_type": payload_type, "error_type": "internal_error"},
            )
            metrics.observe_histogram(
                "asap_request_duration_seconds",
                duration_seconds,
                {"payload_type": payload_type, "status": "error"},
            )

            # Log error
            logger.exception(
                "asap.request.error",
                error=str(e),
                error_type=type(e).__name__,
                duration_ms=round(duration_ms, 2),
            )

            # Internal server error
            error_response = JsonRpcErrorResponse(
                error=JsonRpcError.from_code(
                    INTERNAL_ERROR,
                    data={"error": str(e), "type": type(e).__name__},
                ),
                id=None,
            )
            return JSONResponse(
                status_code=200,
                content=error_response.model_dump(),
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
