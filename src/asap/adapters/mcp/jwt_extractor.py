"""DEPRECATED re-export shim — import from :mod:`asap.mcp.auth` instead.

Kept for the deprecation window so ``from asap.adapters.mcp.jwt_extractor
import default_jwt_extractor`` continues to resolve. The real implementation
lives in :mod:`asap.mcp.auth.jwt_extractor`.
"""

from __future__ import annotations

from asap.mcp.auth.jwt_extractor import default_jwt_extractor as default_jwt_extractor

__all__ = ["default_jwt_extractor"]
