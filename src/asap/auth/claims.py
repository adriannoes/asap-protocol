"""JWT claim validation helpers."""

from __future__ import annotations

from typing import Any


def audience_matches_expected(
    claims: dict[str, Any],
    expected_audience: str | list[str],
) -> bool:
    """Return True if ``aud`` intersects ``expected_audience``."""
    aud = claims.get("aud")
    expected = (
        [expected_audience] if isinstance(expected_audience, str) else list(expected_audience)
    )
    if isinstance(aud, str):
        token_auds = [aud]
    elif isinstance(aud, list):
        token_auds = [a for a in aud if isinstance(a, str)]
    else:
        return False
    return any(a in expected for a in token_auds)


def issuer_matches_expected(claims: dict[str, Any], expected_issuer: str) -> bool:
    """Return True if ``iss`` matches ``expected_issuer``."""
    iss = claims.get("iss")
    if not isinstance(iss, str) or not iss.strip():
        return False
    return iss.rstrip("/") == expected_issuer.rstrip("/")


def parse_expected_audience_from_env(raw: str | None) -> str | list[str] | None:
    """Parse ``ASAP_AUTH_AUDIENCE`` env value (comma-separated list allowed)."""
    if not raw or not raw.strip():
        return None
    parts = [p.strip() for p in raw.split(",") if p.strip()]
    if not parts:
        return None
    if len(parts) == 1:
        return parts[0]
    return parts
