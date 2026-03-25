"""Tests for self-authorization prevention (fresh session, WebAuthn, CIBA preference)."""

from __future__ import annotations

import base64
from datetime import datetime, timezone
from typing import Any

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from asap.auth.approval import select_approval_method
from asap.auth.identity import (
    AgentSession,
    HostIdentity,
    HostStatus,
    host_urn_from_thumbprint,
    jwk_thumbprint_sha256,
)
from asap.auth.self_auth import (
    FreshSessionConfig,
    PlaceholderWebAuthnVerifier,
    WebAuthnVerifier,
    check_fresh_session,
    fresh_session_violation_detail,
    host_jwt_issued_at_seconds,
    verify_webauthn_if_required,
    webauthn_required_capability_names,
)


def _make_ed25519_jwk() -> dict[str, str]:
    sk = Ed25519PrivateKey.generate()
    raw = sk.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
    x = base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")
    return {"kty": "OKP", "crv": "Ed25519", "x": x}


def _sample_host(
    *,
    user_id: str | None = None,
    status: HostStatus = "pending",
) -> HostIdentity:
    now = datetime.now(timezone.utc)
    pk = _make_ed25519_jwk()
    hid = host_urn_from_thumbprint(jwk_thumbprint_sha256(pk))
    return HostIdentity(
        host_id=hid,
        public_key=pk,
        user_id=user_id,
        status=status,
        default_capabilities=[],
        created_at=now,
        updated_at=now,
    )


def _sample_agent() -> AgentSession:
    now = datetime.now(timezone.utc)
    pk = _make_ed25519_jwk()
    return AgentSession(
        agent_id="agent-x",
        host_id="host-y",
        public_key=pk,
        mode="delegated",
        status="pending",
        created_at=now,
    )


def test_check_fresh_session_within_window() -> None:
    cfg = FreshSessionConfig(window_seconds=300)
    now = 1000.0
    assert check_fresh_session(950.0, cfg, now_ts=now) is True


def test_host_jwt_issued_at_invalid() -> None:
    assert host_jwt_issued_at_seconds({"iat": "not-a-number"}) is None


def test_check_fresh_session_uses_system_time_when_now_omitted(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("asap.auth.self_auth.time.time", lambda: 2000.0)
    cfg = FreshSessionConfig(window_seconds=100)
    assert check_fresh_session(1950.0, cfg) is True


def test_webauthn_required_capability_names_order() -> None:
    cfg = FreshSessionConfig(require_webauthn_for=["b", "a"])
    assert webauthn_required_capability_names(["a", "c", "b"], cfg) == ["a", "b"]


def test_check_fresh_session_outside_window() -> None:
    cfg = FreshSessionConfig(window_seconds=300)
    now = 1000.0
    assert check_fresh_session(600.0, cfg, now_ts=now) is False


def test_fresh_session_violation_missing_iat() -> None:
    cfg = FreshSessionConfig()
    detail = fresh_session_violation_detail({}, cfg, now_ts=0.0)
    assert detail is not None


def test_fresh_session_violation_stale() -> None:
    cfg = FreshSessionConfig(window_seconds=60)
    detail = fresh_session_violation_detail({"iat": 100}, cfg, now_ts=200.0)
    assert detail is not None
    assert "stale" in detail


def test_fresh_session_ok() -> None:
    cfg = FreshSessionConfig(window_seconds=300)
    assert fresh_session_violation_detail({"iat": 1000}, cfg, now_ts=1005.0) is None


def test_webauthn_protocol_runtime_checkable() -> None:
    v = PlaceholderWebAuthnVerifier()
    assert isinstance(v, WebAuthnVerifier)


@pytest.mark.asyncio
async def test_placeholder_webauthn_verifier_accepts_anything() -> None:
    v = PlaceholderWebAuthnVerifier()
    assert await v.verify("ch", {"x": 1}) is True


@pytest.mark.asyncio
async def test_verify_webauthn_skips_when_no_overlap() -> None:
    cfg = FreshSessionConfig(require_webauthn_for=["admin.task"])
    v = PlaceholderWebAuthnVerifier()
    err = await verify_webauthn_if_required(["read"], {}, cfg, v)
    assert err is None


@pytest.mark.asyncio
async def test_verify_webauthn_requires_block() -> None:
    cfg = FreshSessionConfig(require_webauthn_for=["admin.task"])
    v = PlaceholderWebAuthnVerifier()
    err = await verify_webauthn_if_required(["admin.task"], {}, cfg, v)
    assert err is not None


@pytest.mark.asyncio
async def test_verify_webauthn_rejects_blank_challenge() -> None:
    cfg = FreshSessionConfig(require_webauthn_for=["admin.task"])
    v = PlaceholderWebAuthnVerifier()
    body: dict[str, Any] = {"webauthn": {"challenge": "", "response": {}}}
    err = await verify_webauthn_if_required(["admin.task"], body, cfg, v)
    assert err is not None


@pytest.mark.asyncio
async def test_verify_webauthn_rejects_missing_response() -> None:
    cfg = FreshSessionConfig(require_webauthn_for=["admin.task"])
    v = PlaceholderWebAuthnVerifier()
    body: dict[str, Any] = {"webauthn": {"challenge": "ok"}}
    err = await verify_webauthn_if_required(["admin.task"], body, cfg, v)
    assert err is not None


@pytest.mark.asyncio
async def test_verify_webauthn_success_with_placeholder() -> None:
    cfg = FreshSessionConfig(require_webauthn_for=["admin.task"])
    v = PlaceholderWebAuthnVerifier()
    body: dict[str, Any] = {"webauthn": {"challenge": "c1", "response": {}}}
    err = await verify_webauthn_if_required(["admin.task"], body, cfg, v)
    assert err is None


@pytest.mark.asyncio
async def test_verify_webauthn_failure_when_verifier_rejects() -> None:
    class _Reject(WebAuthnVerifier):
        async def verify(self, _challenge: str, _response: Any) -> bool:
            return False

    cfg = FreshSessionConfig(require_webauthn_for=["admin.task"])
    body: dict[str, Any] = {"webauthn": {"challenge": "c1", "response": {}}}
    err = await verify_webauthn_if_required(["admin.task"], body, cfg, _Reject())
    assert err is not None


def test_select_browser_controls_forces_ciba_despite_device_hint() -> None:
    """Mitigation: browser-controlling clients should not complete Device Auth on same device."""
    h = _sample_host(user_id="u1", status="active")
    assert (
        select_approval_method(
            h,
            _sample_agent(),
            host_supports_ciba=True,
            preferred_method="device_authorization",
            agent_controls_browser=True,
        )
        == "ciba"
    )


def test_select_browser_controls_device_when_unlinked() -> None:
    h = _sample_host(user_id=None, status="active")
    assert (
        select_approval_method(
            h,
            _sample_agent(),
            host_supports_ciba=True,
            preferred_method="device_authorization",
            agent_controls_browser=True,
        )
        == "device_authorization"
    )
