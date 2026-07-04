"""Scope claim parsing helpers for ASAP Protocol.

Kept as a tiny leaf module so ``asap.auth.scopes`` and
``asap.auth.middleware`` can both normalize OAuth2/JWT scope claims without
importing each other. ``scopes.require_scope`` references
``middleware.OAuth2Claims`` at runtime, while middleware needs
``parse_scope`` during bearer token validation, so this module breaks that
import cycle.
"""

from __future__ import annotations

from typing import Any


def parse_scope(claim: Any) -> list[str]:
    """Normalize a scope claim to a list of strings.

    JWT/OAuth2 scope can be a space-separated string (RFC 6749) or a list.

    Args:
        claim: Raw scope value from JWT claims or introspection response.

    Returns:
        List of scope strings (empty if claim is None or invalid).

    Example:
        >>> parse_scope("asap:read asap:execute")
        ['asap:read', 'asap:execute']
        >>> parse_scope(["a", "b"])
        ['a', 'b']
    """
    if claim is None:
        return []
    if isinstance(claim, list):
        return [str(s) for s in claim]
    if isinstance(claim, str):
        return [s.strip() for s in claim.split() if s.strip()]
    return []
