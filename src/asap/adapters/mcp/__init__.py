"""MCP Auth Bridge adapter — DEPRECATED re-export shim (kept for the deprecation window).

The MCP Auth Bridge was folded into :mod:`asap.mcp.auth` in Sprint S3 Wave C
Task 4.2. The ``asap.adapters.mcp`` boundary was a layering inversion (MCP auth
belongs inside the MCP package, not under the OpenAPI-centric ``adapters``
namespace). This module re-exports the public surface so existing
``from asap.adapters.mcp import protect_server, MCPAuthConfig,
ProtectedMCPServer, resolve_jwt_extractor`` callers keep working. New code
should import from :mod:`asap.mcp.auth` directly.

No ``patch("asap.adapters.mcp...")`` test seams exist (verified via grep
during the fold), so a plain re-export suffices — there are no patchable names
to bind before the real-package import.

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
