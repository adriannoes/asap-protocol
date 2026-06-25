"""DEPRECATED re-export shim — import from :mod:`asap.mcp.auth` instead.

Kept for the deprecation window so ``from asap.adapters.mcp.auth_middleware
import protect_server`` continues to resolve. The real implementation lives in
:mod:`asap.mcp.auth.auth_middleware`.
"""

from __future__ import annotations

from asap.mcp.auth.auth_middleware import (
    MCPAuthConfig as MCPAuthConfig,
    protect_server as protect_server,
    resolve_jwt_extractor as resolve_jwt_extractor,
)

__all__ = ["MCPAuthConfig", "protect_server", "resolve_jwt_extractor"]
