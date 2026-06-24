"""MCP Auth Bridge adapter (v2.5.0).

Opt-in protection for native ``MCPServer`` via ``protect_server``.
"""

from __future__ import annotations

from asap.adapters.mcp.auth_middleware import protect_server
from asap.adapters.mcp.config import MCPAuthConfig, resolve_jwt_extractor
from asap.adapters.mcp.protected_server import ProtectedMCPServer

__all__ = [
    "MCPAuthConfig",
    "ProtectedMCPServer",
    "protect_server",
    "resolve_jwt_extractor",
]
