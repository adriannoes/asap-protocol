"""ASAP Protocol HTTP Transport Layer.

This module provides HTTP-based transport for ASAP messages using:
- JSON-RPC 2.0 for request/response wrapping
- FastAPI for server implementation
- httpx for async client implementation

Public exports:
    JsonRpcRequest: JSON-RPC 2.0 request wrapper
    JsonRpcResponse: JSON-RPC 2.0 response wrapper
    JsonRpcError: JSON-RPC 2.0 error object
    JsonRpcErrorResponse: JSON-RPC 2.0 error response wrapper
    create_app: FastAPI application factory
"""

from asap.transport.jsonrpc import (
    JsonRpcError,
    JsonRpcErrorResponse,
    JsonRpcRequest,
    JsonRpcResponse,
)
from asap.transport.server import create_app

__all__ = [
    "JsonRpcRequest",
    "JsonRpcResponse",
    "JsonRpcError",
    "JsonRpcErrorResponse",
    "create_app",
]
