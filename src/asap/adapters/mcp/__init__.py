"""MCP Auth Bridge adapter (v2.5.0).

Opt-in protection for native ``MCPServer`` via ``protect_server``.
"""

from __future__ import annotations

from asap.adapters.mcp.auth_middleware import MCPAuthConfig, protect_server

__all__ = [
    "MCPAuthConfig",
    "protect_server",
]
