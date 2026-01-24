"""ASAP Protocol HTTP Transport Layer.

This module provides HTTP-based transport for ASAP messages using:
- JSON-RPC 2.0 for request/response wrapping
- FastAPI for server implementation
- httpx for async client implementation
- Handler registry for payload dispatch

Public exports:
    JsonRpcRequest: JSON-RPC 2.0 request wrapper
    JsonRpcResponse: JSON-RPC 2.0 response wrapper
    JsonRpcError: JSON-RPC 2.0 error object
    JsonRpcErrorResponse: JSON-RPC 2.0 error response wrapper
    create_app: FastAPI application factory
    HandlerRegistry: Registry for payload handlers
    HandlerNotFoundError: Error for missing handlers
    Handler: Type alias for handler functions
    create_echo_handler: Factory for echo handler
    create_default_registry: Factory for default registry
    ASAPClient: Async HTTP client for agent communication
    ASAPConnectionError: Connection error exception
    ASAPTimeoutError: Timeout error exception
    ASAPRemoteError: Remote error exception

Example:
    >>> from asap.transport import ASAPClient, create_app
    >>> from asap.models.entities import Manifest, Capability, Endpoint, Skill
    >>> manifest = Manifest(
    ...     id="urn:asap:agent:demo",
    ...     name="Demo Agent",
    ...     version="1.0.0",
    ...     description="Demo manifest",
    ...     capabilities=Capability(
    ...         asap_version="0.1",
    ...         skills=[Skill(id="echo", description="Echo")],
    ...         state_persistence=False,
    ...     ),
    ...     endpoints=Endpoint(asap="http://localhost:8000/asap"),
    ... )
    >>> app = create_app(manifest)
"""

from asap.transport.client import (
    ASAPClient,
    ASAPConnectionError,
    ASAPRemoteError,
    ASAPTimeoutError,
)
from asap.transport.handlers import (
    Handler,
    HandlerNotFoundError,
    HandlerRegistry,
    create_default_registry,
    create_echo_handler,
)
from asap.transport.jsonrpc import (
    JsonRpcError,
    JsonRpcErrorResponse,
    JsonRpcRequest,
    JsonRpcResponse,
)
from asap.transport.server import ASAPRequestHandler, create_app

__all__ = [
    # JSON-RPC
    "JsonRpcRequest",
    "JsonRpcResponse",
    "JsonRpcError",
    "JsonRpcErrorResponse",
    # Server
    "create_app",
    "ASAPRequestHandler",
    # Handlers
    "HandlerRegistry",
    "HandlerNotFoundError",
    "Handler",
    "create_echo_handler",
    "create_default_registry",
    # Client
    "ASAPClient",
    "ASAPConnectionError",
    "ASAPTimeoutError",
    "ASAPRemoteError",
]
