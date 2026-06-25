"""DEPRECATED re-export shim — import from :mod:`asap.mcp.auth` instead.

Kept for the deprecation window so ``from asap.adapters.mcp.config import
MCPAuthConfig, resolve_jwt_extractor, MCP_COMPLIANCE_ENV_VAR`` continues to
resolve. The real implementation lives in :mod:`asap.mcp.auth.config`.
"""

from __future__ import annotations

from asap.mcp.auth.config import (
    MCP_COMPLIANCE_ENV_VAR as MCP_COMPLIANCE_ENV_VAR,
    MCPAuthConfig as MCPAuthConfig,
    resolve_jwt_extractor as resolve_jwt_extractor,
)

__all__ = ["MCPAuthConfig", "MCP_COMPLIANCE_ENV_VAR", "resolve_jwt_extractor"]
