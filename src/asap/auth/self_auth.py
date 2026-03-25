"""Self-authorization prevention: fresh sessions, WebAuthn hooks (v2.2 §4.5)."""

from __future__ import annotations

import time
from typing import Any, Protocol, runtime_checkable

from pydantic import ConfigDict, Field

from asap.models.base import ASAPBaseModel
from asap.observability import get_logger

__all__ = [
    "FreshSessionConfig",
    "PlaceholderWebAuthnVerifier",
    "WebAuthnVerifier",
    "check_fresh_session",
    "fresh_session_violation_detail",
    "host_jwt_issued_at_seconds",
    "verify_webauthn_if_required",
    "webauthn_required_capability_names",
]


class FreshSessionConfig(ASAPBaseModel):
    """Policy for requiring a recently issued Host JWT on approval paths.

    Aligns with PRD ``freshSessionWindow`` (default 300 seconds).
    """

    window_seconds: int = Field(default=300, ge=1, description="Max age of ``iat`` for approval.")
    require_webauthn_for: list[str] = Field(
        default_factory=list,
        description="Capability names that require a WebAuthn assertion in the register body.",
    )

    model_config = ConfigDict(extra="forbid")


def host_jwt_issued_at_seconds(claims: dict[str, Any]) -> float | None:
    """Return ``iat`` from Host JWT claims as Unix seconds, or ``None`` if invalid."""
    iat = claims.get("iat")
    if iat is None:
        return None
    try:
        return float(iat)
    except (TypeError, ValueError):
        return None


def check_fresh_session(
    session_timestamp: float,
    config: FreshSessionConfig,
    *,
    now_ts: float | None = None,
) -> bool:
    """Return True if the session was issued within ``config.window_seconds``."""
    if now_ts is None:
        now_ts = time.time()
    return (now_ts - session_timestamp) <= float(config.window_seconds)


def fresh_session_violation_detail(
    claims: dict[str, Any],
    config: FreshSessionConfig,
    *,
    now_ts: float | None = None,
) -> str | None:
    """Return a short error detail if the Host JWT is too old for approval, else ``None``."""
    iat_ts = host_jwt_issued_at_seconds(claims)
    if iat_ts is None:
        return "missing iat on host token; cannot enforce fresh session for approval"
    if not check_fresh_session(iat_ts, config, now_ts=now_ts):
        return (
            "stale host session; re-authenticate within the fresh-session window "
            f"({config.window_seconds}s) to use approval endpoints"
        )
    return None


@runtime_checkable
class WebAuthnVerifier(Protocol):
    """Verify a WebAuthn assertion for proof-of-presence (optional integration)."""

    async def verify(self, challenge: str, response: Any) -> bool:
        """Return True if ``response`` proves possession for ``challenge``."""
        ...


class PlaceholderWebAuthnVerifier:
    """Stub verifier that always succeeds; replace with a real WebAuthn stack in production."""

    _warned: bool = False

    async def verify(self, _challenge: str, _response: Any) -> bool:
        if not PlaceholderWebAuthnVerifier._warned:
            get_logger(__name__).warning(
                "asap.identity.placeholder_webauthn_verifier",
                detail=(
                    "PlaceholderWebAuthnVerifier in use; all WebAuthn checks will pass. "
                    "Replace with a real verifier in production."
                ),
            )
            PlaceholderWebAuthnVerifier._warned = True
        return True


def webauthn_required_capability_names(
    requested_capabilities: list[str],
    config: FreshSessionConfig,
) -> list[str]:
    """Capabilities in the request that appear in ``require_webauthn_for``."""
    required = set(config.require_webauthn_for)
    return [n for n in requested_capabilities if n in required]


async def verify_webauthn_if_required(
    requested_capabilities: list[str],
    raw_body: dict[str, Any],
    config: FreshSessionConfig,
    verifier: WebAuthnVerifier,
) -> str | None:
    """If high-risk capabilities are requested, validate the ``webauthn`` object in ``raw_body``.

    Returns an error detail string on failure, or ``None`` if checks pass / not applicable.
    """
    needed = webauthn_required_capability_names(requested_capabilities, config)
    if not needed:
        return None

    block = raw_body.get("webauthn")
    if not isinstance(block, dict):
        return "webauthn object required for high-risk capabilities"
    challenge_raw = block.get("challenge")
    if not isinstance(challenge_raw, str) or not challenge_raw.strip():
        return "webauthn.challenge must be a non-empty string"
    response = block.get("response")
    if response is None:
        return "webauthn.response is required"

    ok = await verifier.verify(challenge_raw, response)
    if not ok:
        return "webauthn verification failed"
    return None
