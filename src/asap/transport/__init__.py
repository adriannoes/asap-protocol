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
from asap.transport.server import create_app

__all__ = [
    # JSON-RPC
    "JsonRpcRequest",
    "JsonRpcResponse",
    "JsonRpcError",
    "JsonRpcErrorResponse",
    # Server
    "create_app",
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
