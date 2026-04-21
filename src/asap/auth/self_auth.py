"""Self-authorization prevention: fresh sessions, WebAuthn hooks (v2.2 §4.5)."""

from __future__ import annotations

import os
import time
from dataclasses import dataclass
from typing import Any, Protocol, runtime_checkable

from pydantic import ConfigDict, Field

from asap.models.base import ASAPBaseModel
from asap.observability import get_logger

__all__ = [
    "FreshSessionConfig",
    "PlaceholderWebAuthnVerifier",
    "WebAuthnApprovalCheckResult",
    "WebAuthnVerifier",
    "check_fresh_session",
    "check_webauthn_for_approval_path",
    "default_webauthn_verifier",
    "fresh_session_violation_detail",
    "host_jwt_issued_at_seconds",
    "uses_real_webauthn_verifier",
    "verify_webauthn_if_required",
    "webauthn_required_capability_names",
]

_ASAP_WEBAUTHN_RP_ID_ENV = "ASAP_WEBAUTHN_RP_ID"
_ASAP_WEBAUTHN_ORIGIN_ENV = "ASAP_WEBAUTHN_ORIGIN"


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

    async def verify(
        self,
        challenge: str,
        response: Any,
        *,
        host_id: str | None = None,
        require_user_verification: bool = False,
    ) -> bool:
        """Return True if ``response`` proves possession for ``challenge``.

        Real verifiers should receive ``host_id`` (host principal from the Host JWT) so credential
        state can be scoped; the placeholder ignores it. When ``require_user_verification`` is True,
        implementations backed by WebAuthn MUST require the UV bit in authenticator data.
        """
        ...


class PlaceholderWebAuthnVerifier:
    """Stub verifier that always succeeds; replace with a real WebAuthn stack in production."""

    _warned: bool = False

    async def verify(
        self,
        _challenge: str,
        _response: Any,
        *,
        host_id: str | None = None,
        require_user_verification: bool = False,
    ) -> bool:
        _ = (host_id, require_user_verification)
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


def _webauthn_extra_installed() -> bool:
    try:
        import webauthn  # noqa: F401
    except ImportError:
        return False
    return True


def default_webauthn_verifier() -> WebAuthnVerifier:
    """Return a real WebAuthn verifier when the extra is installed and configured, else the placeholder.

    Without the ``webauthn`` distribution package, or without both ``ASAP_WEBAUTHN_RP_ID`` and
    ``ASAP_WEBAUTHN_ORIGIN`` set in the environment, this returns :class:`PlaceholderWebAuthnVerifier`
    so behavior stays backward-compatible until operators opt in to real verification.

    ``create_app`` stores the result on ``app.state.identity_webauthn_verifier`` when callers do not
    pass an explicit verifier.
    """
    if not _webauthn_extra_installed():
        return PlaceholderWebAuthnVerifier()
    rp_id = os.environ.get(_ASAP_WEBAUTHN_RP_ID_ENV, "").strip()
    origin = os.environ.get(_ASAP_WEBAUTHN_ORIGIN_ENV, "").strip()
    if not rp_id or not origin:
        return PlaceholderWebAuthnVerifier()
    from asap.auth.webauthn import (
        InMemoryWebAuthnCredentialStore,
        WebAuthnSelfAuthVerifier,
        WebAuthnVerifierImpl,
    )

    store = InMemoryWebAuthnCredentialStore()
    impl = WebAuthnVerifierImpl(store, rp_id=rp_id, origin=origin)
    return WebAuthnSelfAuthVerifier(impl)


def uses_real_webauthn_verifier(verifier: object) -> bool:
    """True when ``verifier`` performs cryptographic WebAuthn checks (not the placeholder)."""
    return getattr(verifier, "__asap_performs_real_webauthn__", False) is True


@dataclass(frozen=True, slots=True)
class WebAuthnApprovalCheckResult:
    """Outcome of WebAuthn checks on an agent registration approval path."""

    detail: str | None
    """Human-readable error detail for HTTP 400 responses; ignored when ``http_status`` is 403."""

    http_status: int = 400
    """400 for configuration/body issues on the high-risk capability path; 403 for ``webauthn_required``."""

    @property
    def failed(self) -> bool:
        return self.detail is not None


async def check_webauthn_for_approval_path(
    requested_capabilities: list[str],
    raw_body: dict[str, Any],
    config: FreshSessionConfig | None,
    verifier: WebAuthnVerifier,
    *,
    host_id: str | None,
    agent_controls_browser: bool,
) -> WebAuthnApprovalCheckResult:
    """Validate WebAuthn on registration when policies require it.

    Runs when (1) a requested capability is listed in ``config.require_webauthn_for``, and/or
    (2) the client sets ``agent_controls_browser: true`` while a real WebAuthn verifier is in use.
    Case (2) enforces ``userVerification`` (library flag ``require_user_verification``) on verify.

    Returns :class:`WebAuthnApprovalCheckResult` with ``http_status`` 403 and a non-``None``
    ``detail`` when the browser-controlled + real-verifier gate fails (response body should use
    ``{"detail": "webauthn_required"}``).
    """
    needed: list[str] = []
    if config is not None and config.require_webauthn_for:
        needed = webauthn_required_capability_names(requested_capabilities, config)
    browser_gate = agent_controls_browser and uses_real_webauthn_verifier(verifier)
    if not needed and not browser_gate:
        return WebAuthnApprovalCheckResult(None)

    block = raw_body.get("webauthn")
    if not isinstance(block, dict):
        msg = "webauthn object required for high-risk capabilities"
        if browser_gate and not needed:
            msg = "webauthn object required for browser-controlled agent registration"
        return WebAuthnApprovalCheckResult(
            msg,
            http_status=403 if browser_gate else 400,
        )
    challenge_raw = block.get("challenge")
    if not isinstance(challenge_raw, str) or not challenge_raw.strip():
        return WebAuthnApprovalCheckResult(
            "webauthn.challenge must be a non-empty string",
            http_status=403 if browser_gate else 400,
        )
    response = block.get("response")
    if response is None:
        return WebAuthnApprovalCheckResult(
            "webauthn.response is required",
            http_status=403 if browser_gate else 400,
        )

    require_uv = browser_gate
    ok = await verifier.verify(
        challenge_raw,
        response,
        host_id=host_id,
        require_user_verification=require_uv,
    )
    if not ok:
        return WebAuthnApprovalCheckResult(
            "webauthn verification failed",
            http_status=403 if browser_gate else 400,
        )
    return WebAuthnApprovalCheckResult(None)


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
    *,
    host_id: str | None = None,
) -> str | None:
    """If high-risk capabilities are requested, validate the ``webauthn`` object in ``raw_body``.

    Returns an error detail string on failure, or ``None`` if checks pass / not applicable.
    Does not apply the browser-controlled agent gate (use :func:`check_webauthn_for_approval_path`).
    """
    result = await check_webauthn_for_approval_path(
        requested_capabilities,
        raw_body,
        config,
        verifier,
        host_id=host_id,
        agent_controls_browser=False,
    )
    return result.detail
