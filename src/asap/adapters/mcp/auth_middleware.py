"""MCP Auth Bridge middleware entry point (v2.5.0)."""

from __future__ import annotations

from asap.adapters.mcp.config import MCPAuthConfig, resolve_jwt_extractor
from asap.adapters.mcp.protected_server import ProtectedMCPServer
from asap.mcp.server import MCPServer

__all__ = ["MCPAuthConfig", "protect_server", "resolve_jwt_extractor"]


def protect_server(server: MCPServer, config: MCPAuthConfig) -> ProtectedMCPServer:
    """Return an MCP server with JWT and capability enforcement on ``tools/call``.

    Verifies Agent JWT extraction/verification, the ``public_tools`` allowlist, and
    (when ``enforce_grants=True``) JWT capability claims plus
    :meth:`~asap.auth.capabilities.CapabilityRegistry.check_grant`.

    ``from_server`` copies register-time capability metadata onto the protected instance
    without mutating ``config``.

    See PRD v2.5.0 MCP Auth Bridge (``product/prd/prd-v2.5.0-mcp-auth-bridge.md``)
    and design lock ADR (``engineering/tasks/v2.5.0/design-lock-mcp-auth-bridge.md``).

    Args:
        server: Native MCP server with registered tools.
        config: Auth configuration (identity stores, capability registry, extractors).

    Returns:
        Protected server instance; unprotected ``MCPServer`` usage remains valid when
        this function is not called.
    """
    return ProtectedMCPServer.from_server(server, config)
