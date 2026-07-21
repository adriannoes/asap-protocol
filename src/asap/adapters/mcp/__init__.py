"""Deprecated MCP Auth Bridge re-export shim.

MCP auth now lives in :mod:`asap.mcp.auth`, inside the MCP package rather than
the OpenAPI-centric ``adapters`` namespace. This module keeps the old import
path working during the deprecation window. New code should import from
:mod:`asap.mcp.auth` directly.

Example:
    >>> from asap.adapters.mcp import protect_server, MCPAuthConfig  # still works
"""

from __future__ import annotations

from asap.mcp.auth import (
    MCPAuthConfig as MCPAuthConfig,
    ProtectedMCPServer as ProtectedMCPServer,
    protect_server as protect_server,
    resolve_jwt_extractor as resolve_jwt_extractor,
)

__all__ = [
    "MCPAuthConfig",
    "ProtectedMCPServer",
    "protect_server",
    "resolve_jwt_extractor",
]
