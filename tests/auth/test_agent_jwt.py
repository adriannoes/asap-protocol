"""Tests for Host JWT and Agent JWT builders and verification (S2.1 / S2.2)."""

from __future__ import annotations

import base64
from datetime import datetime, timezone
from typing import Any

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from joserfc import jwt as jose_jwt
from joserfc.jwk import OKPKey

from asap.auth.agent_jwt import (
    AGENT_JWT_TTL_SECONDS,
    AGENT_JWT_TYP,
    CAPABILITIES_CLAIM,
    HOST_JWT_TYP,
    HOST_PUBLIC_KEY_CLAIM,
    JWT_ALGS_VERIFY,
    JtiReplayCache,
    create_agent_jwt,
    create_host_jwt,
    verify_agent_jwt,
    verify_host_jwt,
)
from asap.auth.identity import (
    AgentSession,
    HostIdentity,
    InMemoryAgentStore,
    InMemoryHostStore,
    jwk_thumbprint_sha256,
)


def _public_jwk_dict(private_key: Ed25519PrivateKey) -> dict[str, Any]:
    """Public JWK dict (OKP / Ed25519) for identity models."""
    raw = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
    x = base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")
    return {"kty": "OKP", "crv": "Ed25519", "x": x}


def _public_okp(private_key: Ed25519PrivateKey) -> OKPKey:
    """Public OKP JWK for verifying tokens signed by ``private_key``."""
    raw = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
    x = base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")
    return OKPKey.import_key({"kty": "OKP", "crv": "Ed25519", "x": x})


@pytest.mark.filterwarnings("ignore:EdDSA is deprecated:UserWarning")
def test_host_jwt_round_trip_and_claims() -> None:
    """Create host JWT, verify signature, check ``iss`` and embedded JWK claims."""
    sk = Ed25519PrivateKey.generate()
    token = create_host_jwt(sk, aud="https://asap.example", ttl_seconds=120)
    pub = _public_okp(sk)
    decoded = jose_jwt.decode(token, pub, algorithms=JWT_ALGS_VERIFY)
    assert decoded.header.get("typ") == HOST_JWT_TYP
    claims = dict(decoded.claims)
    host_pub = claims[HOST_PUBLIC_KEY_CLAIM]
    assert isinstance(host_pub, dict)
    assert claims["iss"] == jwk_thumbprint_sha256(host_pub)
    assert claims["aud"] == "https://asap.example"


@pytest.mark.filterwarnings("ignore:EdDSA is deprecated:UserWarning")
def test_host_jwt_with_optional_agent_public_key() -> None:
    """Optional ``agent_public_key`` claim is present when provided."""
    sk = Ed25519PrivateKey.generate()
    agent_pk = {"kty": "OKP", "crv": "Ed25519", "x": "dGVzdA"}
    token = create_host_jwt(
        sk,
        aud="asap:registry",
        agent_public_key=agent_pk,
    )
    pub = _public_okp(sk)
    decoded = jose_jwt.decode(token, pub, algorithms=JWT_ALGS_VERIFY)
    claims = dict(decoded.claims)
    assert claims.get("agent_public_key") == agent_pk


@pytest.mark.filterwarnings("ignore:EdDSA is deprecated:UserWarning")
def test_agent_jwt_round_trip_and_claims() -> None:
    """Create agent JWT, verify signature, check ``iss``, ``sub``, TTL, capabilities."""
    agent_sk = Ed25519PrivateKey.generate()
    host_tp = "BeHE0RFM9jC46s0RCLfWvd-yfBVwRzIYZ_fp_IpsoUs"
    token = create_agent_jwt(
        agent_sk,
        host_thumbprint=host_tp,
        agent_id="agent-urn-1",
        aud="https://asap.example/asap",
        capabilities=["asap:read", "asap:execute"],
    )
    pub = _public_okp(agent_sk)
    decoded = jose_jwt.decode(token, pub, algorithms=JWT_ALGS_VERIFY)
    assert decoded.header.get("typ") == AGENT_JWT_TYP
    claims = dict(decoded.claims)
    assert claims["iss"] == host_tp
    assert claims["sub"] == "agent-urn-1"
    assert claims["aud"] == "https://asap.example/asap"
    assert claims[CAPABILITIES_CLAIM] == ["asap:read", "asap:execute"]
    exp = int(claims["exp"])
    iat = int(claims["iat"])
    assert exp - iat == AGENT_JWT_TTL_SECONDS


# --- Verification (S2.2) ---


@pytest.mark.filterwarnings("ignore:EdDSA is deprecated:UserWarning")
async def test_verify_host_jwt_with_registered_host() -> None:
    """Registered host resolves; claims and host row returned."""
    now = datetime.now(timezone.utc)
    sk = Ed25519PrivateKey.generate()
    pub = _public_jwk_dict(sk)
    hosts = InMemoryHostStore()
    await hosts.save(
        HostIdentity(
            host_id="h1",
            public_key=pub,
            status="active",
            created_at=now,
            updated_at=now,
        )
    )
    token = create_host_jwt(sk, aud="https://aud.example")
    res = await verify_host_jwt(token, hosts)
    assert res.ok
    assert res.host is not None and res.host.host_id == "h1"
    assert res.claims is not None and res.claims["aud"] == "https://aud.example"


@pytest.mark.filterwarnings("ignore:EdDSA is deprecated:UserWarning")
async def test_verify_host_jwt_dynamic_registration() -> None:
    """Unknown thumbprint in store still verifies signature; host is None."""
    sk = Ed25519PrivateKey.generate()
    hosts = InMemoryHostStore()
    token = create_host_jwt(sk, aud="dyn")
    res = await verify_host_jwt(token, hosts)
    assert res.ok
    assert res.host is None
    assert res.claims is not None


@pytest.mark.filterwarnings("ignore:EdDSA is deprecated:UserWarning")
async def test_verify_host_jwt_revoked_host_rejected() -> None:
    """Stored host in revoked state rejects the token."""
    now = datetime.now(timezone.utc)
    sk = Ed25519PrivateKey.generate()
    pub = _public_jwk_dict(sk)
    hosts = InMemoryHostStore()
    await hosts.save(
        HostIdentity(
            host_id="h1",
            public_key=pub,
            status="revoked",
            created_at=now,
            updated_at=now,
        )
    )
    token = create_host_jwt(sk, aud="x")
    res = await verify_host_jwt(token, hosts)
    assert not res.ok
    assert res.error == "host revoked"


@pytest.mark.filterwarnings("ignore:EdDSA is deprecated:UserWarning")
async def test_verify_agent_jwt_success() -> None:
    """Valid agent JWT with matching host and active agent."""
    now = datetime.now(timezone.utc)
    host_sk = Ed25519PrivateKey.generate()
    host_pub = _public_jwk_dict(host_sk)
    host_tp = jwk_thumbprint_sha256(host_pub)
    agent_sk = Ed25519PrivateKey.generate()
    agent_pub = _public_jwk_dict(agent_sk)

    hosts = InMemoryHostStore()
    agents = InMemoryAgentStore()
    await hosts.save(
        HostIdentity(
            host_id="h1",
            public_key=host_pub,
            status="active",
            created_at=now,
            updated_at=now,
        )
    )
    await agents.save(
        AgentSession(
            agent_id="a1",
            host_id="h1",
            public_key=agent_pub,
            mode="delegated",
            status="active",
            created_at=now,
        )
    )
    token = create_agent_jwt(agent_sk, host_thumbprint=host_tp, agent_id="a1", aud="aud")
    res = await verify_agent_jwt(token, hosts, agents)
    assert res.ok
    assert res.agent is not None and res.agent.agent_id == "a1"
    assert res.host is not None and res.host.host_id == "h1"


@pytest.mark.filterwarnings("ignore:EdDSA is deprecated:UserWarning")
async def test_verify_agent_jwt_unknown_host() -> None:
    """iss thumbprint not in host store."""
    now = datetime.now(timezone.utc)
    host_sk = Ed25519PrivateKey.generate()
    host_pub = _public_jwk_dict(host_sk)
    agent_sk = Ed25519PrivateKey.generate()
    agent_pub = _public_jwk_dict(agent_sk)

    hosts = InMemoryHostStore()
    agents = InMemoryAgentStore()
    await hosts.save(
        HostIdentity(
            host_id="h1",
            public_key=host_pub,
            status="active",
            created_at=now,
            updated_at=now,
        )
    )
    await agents.save(
        AgentSession(
            agent_id="a1",
            host_id="h1",
            public_key=agent_pub,
            mode="delegated",
            status="active",
            created_at=now,
        )
    )
    wrong_tp = "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
    token = create_agent_jwt(agent_sk, host_thumbprint=wrong_tp, agent_id="a1", aud="aud")
    res = await verify_agent_jwt(token, hosts, agents)
    assert not res.ok
    assert res.error == "unknown host for iss"


@pytest.mark.filterwarnings("ignore:EdDSA is deprecated:UserWarning")
async def test_verify_agent_jwt_revoked_agent() -> None:
    """Agent session revoked is rejected before signature checks complete."""
    now = datetime.now(timezone.utc)
    host_sk = Ed25519PrivateKey.generate()
    host_pub = _public_jwk_dict(host_sk)
    host_tp = jwk_thumbprint_sha256(host_pub)
    agent_sk = Ed25519PrivateKey.generate()
    agent_pub = _public_jwk_dict(agent_sk)

    hosts = InMemoryHostStore()
    agents = InMemoryAgentStore()
    await hosts.save(
        HostIdentity(
            host_id="h1",
            public_key=host_pub,
            status="active",
            created_at=now,
            updated_at=now,
        )
    )
    await agents.save(
        AgentSession(
            agent_id="a1",
            host_id="h1",
            public_key=agent_pub,
            mode="delegated",
            status="revoked",
            created_at=now,
        )
    )
    token = create_agent_jwt(agent_sk, host_thumbprint=host_tp, agent_id="a1", aud="aud")
    res = await verify_agent_jwt(token, hosts, agents)
    assert not res.ok
    assert res.error is not None and "revoked" in res.error


@pytest.mark.filterwarnings("ignore:EdDSA is deprecated:UserWarning")
async def test_verify_agent_jwt_expired(monkeypatch: pytest.MonkeyPatch) -> None:
    """jose_jwt rejects token when exp is in the past (wall clock advanced)."""
    now = datetime.now(timezone.utc)
    host_sk = Ed25519PrivateKey.generate()
    host_pub = _public_jwk_dict(host_sk)
    host_tp = jwk_thumbprint_sha256(host_pub)
    agent_sk = Ed25519PrivateKey.generate()
    agent_pub = _public_jwk_dict(agent_sk)

    hosts = InMemoryHostStore()
    agents = InMemoryAgentStore()
    await hosts.save(
        HostIdentity(
            host_id="h1",
            public_key=host_pub,
            status="active",
            created_at=now,
            updated_at=now,
        )
    )
    await agents.save(
        AgentSession(
            agent_id="a1",
            host_id="h1",
            public_key=agent_pub,
            mode="delegated",
            status="active",
            created_at=now,
        )
    )

    t0 = 1_700_000_000.0
    monkeypatch.setattr("time.time", lambda: t0)
    token = create_agent_jwt(agent_sk, host_thumbprint=host_tp, agent_id="a1", aud="aud")

    monkeypatch.setattr("time.time", lambda: t0 + 120.0)
    res = await verify_agent_jwt(token, hosts, agents)
    assert not res.ok
    assert res.error == "token expired or missing exp"


@pytest.mark.filterwarnings("ignore:EdDSA is deprecated:UserWarning")
async def test_verify_agent_jwt_jti_replay() -> None:
    """Second presentation of the same token fails when replay cache is enabled."""
    now = datetime.now(timezone.utc)
    host_sk = Ed25519PrivateKey.generate()
    host_pub = _public_jwk_dict(host_sk)
    host_tp = jwk_thumbprint_sha256(host_pub)
    agent_sk = Ed25519PrivateKey.generate()
    agent_pub = _public_jwk_dict(agent_sk)

    hosts = InMemoryHostStore()
    agents = InMemoryAgentStore()
    await hosts.save(
        HostIdentity(
            host_id="h1",
            public_key=host_pub,
            status="active",
            created_at=now,
            updated_at=now,
        )
    )
    await agents.save(
        AgentSession(
            agent_id="a1",
            host_id="h1",
            public_key=agent_pub,
            mode="delegated",
            status="active",
            created_at=now,
        )
    )
    token = create_agent_jwt(agent_sk, host_thumbprint=host_tp, agent_id="a1", aud="aud")
    cache = JtiReplayCache()
    res1 = await verify_agent_jwt(token, hosts, agents, jti_replay_cache=cache)
    res2 = await verify_agent_jwt(token, hosts, agents, jti_replay_cache=cache)
    assert res1.ok
    assert not res2.ok
    assert res2.error == "jti replay detected"


@pytest.mark.filterwarnings("ignore:EdDSA is deprecated:UserWarning")
async def test_verify_host_jwt_rejects_wrong_typ() -> None:
    """Agent JWT must not pass host verifier typ check."""
    now = datetime.now(timezone.utc)
    host_sk = Ed25519PrivateKey.generate()
    host_pub = _public_jwk_dict(host_sk)
    host_tp = jwk_thumbprint_sha256(host_pub)
    agent_sk = Ed25519PrivateKey.generate()
    agent_pub = _public_jwk_dict(agent_sk)

    hosts = InMemoryHostStore()
    agents = InMemoryAgentStore()
    await hosts.save(
        HostIdentity(
            host_id="h1",
            public_key=host_pub,
            status="active",
            created_at=now,
            updated_at=now,
        )
    )
    await agents.save(
        AgentSession(
            agent_id="a1",
            host_id="h1",
            public_key=agent_pub,
            mode="delegated",
            status="active",
            created_at=now,
        )
    )
    agent_token = create_agent_jwt(agent_sk, host_thumbprint=host_tp, agent_id="a1", aud="aud")
    res = await verify_host_jwt(agent_token, hosts)
    assert not res.ok
    assert res.error == "invalid typ for host JWT"


def test_jti_replay_cache_same_jti_allowed_after_ttl(monkeypatch: pytest.MonkeyPatch) -> None:
    """After the TTL window, the same jti may be used again (partitioned key)."""
    cache = JtiReplayCache(ttl_seconds=1.0)
    t0 = 10_000.0
    monkeypatch.setattr("asap.auth.agent_jwt.time.time", lambda: t0)
    assert cache.check_and_record("part", "jti-1")
    assert not cache.check_and_record("part", "jti-1")
    monkeypatch.setattr("asap.auth.agent_jwt.time.time", lambda: t0 + 2.0)
    assert cache.check_and_record("part", "jti-1")
