"""MCP Auth Bridge — ASAP auth on native ``MCPServer`` ``tools/call`` (v2.5.0).

Folded from ``asap.adapters.mcp`` in Sprint S3 Wave C Task 4.2. The adapter
boundary was a layering inversion: MCP auth belongs inside the MCP package
(``asap.mcp.auth``) next to :mod:`asap.mcp.protocol` and :mod:`asap.mcp.server`,
not under the OpenAPI-centric ``asap.adapters`` namespace. The legacy
``asap.adapters.mcp`` import path is preserved as a thin deprecation shim so
existing callers keep working during the deprecation window.

Public surface (unchanged): ``protect_server``, ``MCPAuthConfig``,
``ProtectedMCPServer``, ``resolve_jwt_extractor``.

Example:
    >>> from asap.mcp.auth import MCPAuthConfig, protect_server
    >>> protected = protect_server(server, config)
"""

from __future__ import annotations

from asap.mcp.auth.auth_middleware import protect_server
from asap.mcp.auth.config import MCPAuthConfig, resolve_jwt_extractor
from asap.mcp.auth.protected_server import ProtectedMCPServer

__all__ = [
    "MCPAuthConfig",
    "ProtectedMCPServer",
    "protect_server",
    "resolve_jwt_extractor",
]
