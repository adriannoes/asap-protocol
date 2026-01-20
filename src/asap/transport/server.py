"""FastAPI server implementation for ASAP protocol.

This module provides a production-ready FastAPI server that:
- Exposes POST /asap endpoint for JSON-RPC 2.0 wrapped ASAP messages
- Exposes GET /.well-known/asap/manifest.json for agent discovery
- Handles errors with proper JSON-RPC error responses
- Validates all incoming requests against ASAP schemas

Example:
    >>> from asap.models.entities import Manifest, Capability, Endpoint, Skill
    >>> from asap.transport.server import create_app
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
    >>> app = create_app(manifest)
    >>> # Run with: uvicorn asap.transport.server:app --host 0.0.0.0 --port 8000
"""

from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from pydantic import ValidationError

from asap.models.entities import Manifest
from asap.models.enums import TaskStatus
from asap.models.envelope import Envelope
from asap.models.payloads import TaskRequest, TaskResponse
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


def create_app(manifest: Manifest) -> FastAPI:
    """Create and configure a FastAPI application for ASAP protocol.

    This factory function creates a FastAPI app with:
    - POST /asap endpoint for handling ASAP messages via JSON-RPC
    - GET /.well-known/asap/manifest.json for agent discovery
    - Error handling middleware
    - Request validation

    Args:
        manifest: The agent's manifest describing capabilities and endpoints

    Returns:
        Configured FastAPI application ready to run

    Example:
        >>> from asap.models.entities import Manifest, Capability, Endpoint, Skill
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
        >>> # Run with uvicorn: uvicorn module:app
    """
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
        """
        return manifest.model_dump()

    @app.post("/asap")
    async def handle_asap_message(request: Request) -> JSONResponse:
        """Handle ASAP messages wrapped in JSON-RPC 2.0.

        This endpoint:
        1. Receives JSON-RPC wrapped ASAP envelopes
        2. Validates the request structure
        3. Extracts and processes the ASAP envelope
        4. Returns response wrapped in JSON-RPC

        Args:
            request: FastAPI request object with JSON body

        Returns:
            JSON-RPC response or error response
        """
        try:
            # Parse JSON body
            body = await request.json()

            # Validate JSON-RPC request structure
            try:
                rpc_request = JsonRpcRequest(**body)
            except ValidationError as e:
                # Invalid JSON-RPC structure
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
            except ValidationError as e:
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

            # Process the envelope
            # For now, we'll create a simple echo response
            # This will be replaced by proper handler dispatch in task 4.3
            response_envelope = _process_envelope(envelope, manifest)

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


def _process_envelope(envelope: Envelope, manifest: Manifest) -> Envelope:
    """Process an ASAP envelope and generate response.

    This is a temporary implementation that echoes TaskRequest as TaskResponse.
    Will be replaced by proper HandlerRegistry in task 4.3.

    Args:
        envelope: Incoming ASAP envelope
        manifest: Server manifest for context

    Returns:
        Response envelope
    """
    # Simple echo implementation for testing
    # Check if it's a TaskRequest
    if envelope.payload_type == "task.request":
        task_request = TaskRequest(**envelope.payload)

        # Create a simple response
        response_payload = TaskResponse(
            task_id=f"task-{envelope.id}",
            status=TaskStatus.COMPLETED,
            result={"echoed": task_request.input},
        )

        # Create response envelope
        return Envelope(
            asap_version="0.1",
            sender=manifest.id,
            recipient=envelope.sender,
            payload_type="task.response",
            payload=response_payload.model_dump(),
            correlation_id=envelope.id,
            trace_id=envelope.trace_id,
        )


    # For other payload types, return a generic response
    # This will be improved with handler registry
    return Envelope(
        asap_version="0.1",
        sender=manifest.id,
        recipient=envelope.sender,
        payload_type="task.response",
        payload=TaskResponse(
            task_id=f"task-{envelope.id}",
            status=TaskStatus.FAILED,
            result={
                "error": {
                    "code": "unsupported_payload",
                    "message": "Payload type not supported",
                }
            },
        ).model_dump(),
        correlation_id=envelope.id,
        trace_id=envelope.trace_id,
    )

