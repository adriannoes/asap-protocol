"""Tests for registration approval flows (Device Authorization, CIBA, A2H channel)."""

from __future__ import annotations

import base64
from datetime import datetime, timedelta, timezone
from typing import Any

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from asap.auth.approval import (
    A2HApprovalChannel,
    ApprovalObject,
    InMemoryApprovalStore,
    USER_CODE_ALPHABET,
    USER_CODE_LENGTH,
    check_approval_status,
    create_ciba_approval,
    create_device_authorization,
    select_approval_method,
)
from asap.auth.identity import (
    AgentSession,
    HostIdentity,
    HostStatus,
    host_urn_from_thumbprint,
    jwk_thumbprint_sha256,
)
from asap.handlers.hitl import ApprovalDecision, ApprovalResult


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
    default_capabilities: list[str] | None = None,
) -> HostIdentity:
    now = datetime.now(timezone.utc)
    pk = _make_ed25519_jwk()
    hid = host_urn_from_thumbprint(jwk_thumbprint_sha256(pk))
    return HostIdentity(
        host_id=hid,
        public_key=pk,
        user_id=user_id,
        status=status,
        default_capabilities=default_capabilities or [],
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


class _StubHumanApproval:
    """Minimal async human approval backend for A2H channel tests."""

    def __init__(self, result: ApprovalResult) -> None:
        self._result = result

    async def request_approval(
        self,
        *,
        context: str,
        principal_id: str,
        assurance_level: str = "LOW",
        timeout_seconds: float = 300.0,
    ) -> ApprovalResult:
        _ = (context, principal_id, assurance_level, timeout_seconds)
        return self._result


def test_approval_object_validates_device_and_ciba_shapes() -> None:
    d = ApprovalObject(
        method="device_authorization",
        verification_uri="https://ex.example/device",
        verification_uri_complete="https://ex.example/device?u=1",
        user_code="A" * USER_CODE_LENGTH,
        expires_in=100,
        interval=5,
    )
    assert d.method == "device_authorization"
    c = ApprovalObject(
        method="ciba",
        binding_message="confirm",
        expires_in=200,
        interval=7,
    )
    assert c.verification_uri is None


@pytest.mark.asyncio
async def test_device_flow_poll_approve_and_deny() -> None:
    store = InMemoryApprovalStore()
    obj = await create_device_authorization(store, "ag-1", ["read"])
    assert await check_approval_status(store, "ag-1") == "pending"
    assert len(obj.user_code or "") == USER_CODE_LENGTH
    assert all(ch in USER_CODE_ALPHABET for ch in (obj.user_code or ""))

    await store.approve("ag-1", "user-1")
    assert await check_approval_status(store, "ag-1") == "approved"

    store2 = InMemoryApprovalStore()
    await create_device_authorization(store2, "ag-2", [])
    await store2.deny("ag-2", "no trust")
    assert await check_approval_status(store2, "ag-2") == "denied"


@pytest.mark.asyncio
async def test_ciba_flow_create_then_approve() -> None:
    store = InMemoryApprovalStore()
    obj = await create_ciba_approval(
        store,
        "ag-c",
        ["read"],
        binding_message="Custom binding",
    )
    assert obj.method == "ciba"
    assert obj.binding_message == "Custom binding"
    assert obj.user_code is None
    assert await check_approval_status(store, "ag-c") == "pending"
    await store.approve("ag-c", "op-1")
    assert await check_approval_status(store, "ag-c") == "approved"


@pytest.mark.asyncio
async def test_idempotent_pending_reregistration() -> None:
    store = InMemoryApprovalStore()
    a = await create_device_authorization(store, "r1", ["a"])
    b = await create_device_authorization(store, "r1", ["a"])
    assert a.user_code == b.user_code


def test_select_linked_host_prefers_ciba_when_supported() -> None:
    h = _sample_host(user_id="u1", status="active")
    assert select_approval_method(h, _sample_agent(), host_supports_ciba=True) == "ciba"


def test_select_unlinked_host_uses_device_authorization() -> None:
    h = _sample_host(user_id=None, status="active")
    assert (
        select_approval_method(h, _sample_agent(), host_supports_ciba=True)
        == "device_authorization"
    )


def test_select_preferred_device_forces_device() -> None:
    h = _sample_host(user_id="u1", status="active")
    assert (
        select_approval_method(
            h,
            _sample_agent(),
            host_supports_ciba=True,
            preferred_method="device_authorization",
        )
        == "device_authorization"
    )


def test_select_preferred_ciba_falls_back_when_unlinked() -> None:
    h = _sample_host(user_id=None, status="active")
    assert (
        select_approval_method(
            h,
            _sample_agent(),
            host_supports_ciba=True,
            preferred_method="ciba",
        )
        == "device_authorization"
    )


@pytest.mark.asyncio
async def test_pending_expired_after_deadline(monkeypatch: pytest.MonkeyPatch) -> None:
    store = InMemoryApprovalStore()
    frozen = datetime(2022, 6, 1, 12, 0, 0, tzinfo=timezone.utc)
    monkeypatch.setattr("asap.auth.approval._utcnow", lambda: frozen)
    await create_device_authorization(store, "ex-1", [], expires_in=30)
    monkeypatch.setattr(
        "asap.auth.approval._utcnow",
        lambda: frozen + timedelta(seconds=60),
    )
    assert await check_approval_status(store, "ex-1") == "expired"


@pytest.mark.asyncio
async def test_a2h_channel_approve_updates_store() -> None:
    store = InMemoryApprovalStore()
    await create_device_authorization(store, "a2h-1", ["read"])
    provider = _StubHumanApproval(ApprovalResult(decision=ApprovalDecision.APPROVE))
    ch = A2HApprovalChannel(provider, store)
    await ch.resolve_via_a2h(
        "a2h-1",
        context="register",
        principal_id="human-1",
        timeout_seconds=1.0,
    )
    assert await check_approval_status(store, "a2h-1") == "approved"


@pytest.mark.asyncio
async def test_a2h_channel_decline_updates_store() -> None:
    store = InMemoryApprovalStore()
    await create_device_authorization(store, "a2h-2", [])
    provider = _StubHumanApproval(
        ApprovalResult(
            decision=ApprovalDecision.DECLINE,
            data={"reason": "not today"},
        ),
    )
    ch = A2HApprovalChannel(provider, store)
    await ch.resolve_via_a2h("a2h-2", context="register", principal_id="human-1")
    assert await check_approval_status(store, "a2h-2") == "denied"
    st = await store.get("a2h-2")
    assert st is not None
    assert st.deny_reason == "not today"


@pytest.mark.asyncio
async def test_capability_specs_round_trip_on_store() -> None:
    store = InMemoryApprovalStore()
    specs: list[dict[str, Any]] = [{"name": "cap:x", "constraints": {"max": 1}}]
    await create_device_authorization(store, "cs-1", ["cap:x"], capability_specs=specs)
    st = await store.get("cs-1")
    assert st is not None
    assert st.capability_specs == specs
