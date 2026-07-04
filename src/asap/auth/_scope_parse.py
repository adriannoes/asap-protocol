"""Scope claim parsing helpers for ASAP Protocol."""

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
