"""MCP Auth Bridge adapter (v2.5.0).

Opt-in protection for native ``MCPServer`` via ``protect_server``.
"""

from __future__ import annotations

from asap.adapters.mcp.auth_middleware import MCPAuthConfig, protect_server
from asap.adapters.mcp.errors import (
    AUTH_REQUIRED,
    CAPABILITY_DENIED,
    CONSTRAINT_VIOLATION,
    INVALID_TOKEN,
    tool_error_result,
)
from asap.adapters.mcp.jwt_extractor import default_jwt_extractor

__all__ = [
    "AUTH_REQUIRED",
    "CAPABILITY_DENIED",
    "CONSTRAINT_VIOLATION",
    "INVALID_TOKEN",
    "MCPAuthConfig",
    "default_jwt_extractor",
    "protect_server",
    "tool_error_result",
]
