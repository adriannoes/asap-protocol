"""DEPRECATED re-export shim — import from :mod:`asap.mcp.auth` instead.

Kept for the deprecation window so ``from asap.adapters.mcp.errors import
AUTH_REQUIRED, ...`` continues to resolve. The real implementation lives in
:mod:`asap.mcp.auth.errors`.
"""

from __future__ import annotations

from asap.mcp.auth.errors import (
    AUTH_REQUIRED as AUTH_REQUIRED,
    CAPABILITY_DENIED as CAPABILITY_DENIED,
    CONSTRAINT_VIOLATION as CONSTRAINT_VIOLATION,
    INVALID_TOKEN as INVALID_TOKEN,
    tool_error_result as tool_error_result,
)

__all__ = [
    "AUTH_REQUIRED",
    "CAPABILITY_DENIED",
    "CONSTRAINT_VIOLATION",
    "INVALID_TOKEN",
    "tool_error_result",
]
