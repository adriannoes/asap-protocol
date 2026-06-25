"""DEPRECATED re-export shim — import from :mod:`asap.mcp.auth` instead.

Kept for the deprecation window so ``from asap.adapters.mcp.protected_server
import ProtectedMCPServer`` continues to resolve. The real implementation lives
in :mod:`asap.mcp.auth.protected_server`.
"""

from __future__ import annotations

from asap.mcp.auth.protected_server import ProtectedMCPServer as ProtectedMCPServer

__all__ = ["ProtectedMCPServer"]
