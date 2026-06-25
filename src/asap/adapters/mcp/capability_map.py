"""DEPRECATED re-export shim — import from :mod:`asap.mcp.auth` instead.

Kept for the deprecation window so ``from asap.adapters.mcp.capability_map
import resolve_capability, format_constraint_violations`` continues to resolve.
The real implementation lives in :mod:`asap.mcp.auth.capability_map`.
"""

from __future__ import annotations

from asap.mcp.auth.capability_map import (
    format_constraint_violations as format_constraint_violations,
    resolve_capability as resolve_capability,
)

__all__ = ["format_constraint_violations", "resolve_capability"]
