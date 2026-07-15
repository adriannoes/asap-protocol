"""Transport integration: shared Redis Host JWT ``jti`` replay across workers.

Unit coverage lives in ``tests/auth/test_jti_replay_cache_redis.py``. This file
proves ``create_app(identity_jti_cache=...)`` shares replay state across two
logical workers (separate FastAPI apps / TestClients) via FakeRedis.
"""

from __future__ import annotations

import importlib.util
from typing import TYPE_CHECKING

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from fastapi import FastAPI
from fastapi.testclient import TestClient

from asap.auth.agent_jwt import create_host_jwt
from asap.auth.identity import InMemoryAgentStore, InMemoryHostStore
from asap.auth.jti_replay_cache import RedisJtiReplayCache
from asap.models.entities import Manifest
from asap.transport.server import create_app
from tests.crypto.jwk_helpers import ed25519_public_jwk

if TYPE_CHECKING:
    from asap.transport.rate_limit import ASAPRateLimiter

_HOST_JWT_AUDIENCE = "urn:asap:agent:test-server"


def _fakeredis_available() -> bool:
    return (
        importlib.util.find_spec("redis") is not None
        and importlib.util.find_spec("fakeredis") is not None
    )


def _shared_redis_jti_cache() -> RedisJtiReplayCache:
    import fakeredis

    client = fakeredis.FakeStrictRedis(decode_responses=False)
    return RedisJtiReplayCache(client, ttl_seconds=90.0)


def _two_workers_sharing_jti_cache(
    sample_manifest: Manifest,
    isolated_rate_limiter: ASAPRateLimiter | None,
    jti_cache: RedisJtiReplayCache,
) -> tuple[FastAPI, FastAPI]:
    """Build two create_app instances that share identity stores and JTI cache."""
    agent_store = InMemoryAgentStore()
    host_store = InMemoryHostStore(agent_store=agent_store)

    def _worker() -> FastAPI:
        return create_app(
            sample_manifest,
            rate_limit="999999/minute",
            identity_host_store=host_store,
            identity_agent_store=agent_store,
            identity_jti_cache=jti_cache,
            identity_rate_limit="999999/minute",
        )

    worker_a = _worker()
    worker_b = _worker()
    if isolated_rate_limiter is not None:
        worker_a.state.limiter = isolated_rate_limiter
        worker_b.state.limiter = isolated_rate_limiter
    return worker_a, worker_b


@pytest.mark.skipif(not _fakeredis_available(), reason="redis/fakeredis not installed")
def test_host_jwt_jti_replay_rejected_across_workers_on_register(
    sample_manifest: Manifest,
    isolated_rate_limiter: ASAPRateLimiter | None,
) -> None:
    """Worker B rejects a Host JWT whose ``jti`` worker A already recorded."""
    jti_cache = _shared_redis_jti_cache()
    worker_a, worker_b = _two_workers_sharing_jti_cache(
        sample_manifest, isolated_rate_limiter, jti_cache
    )
    host_sk = Ed25519PrivateKey.generate()
    agent_sk = Ed25519PrivateKey.generate()
    reg_tok = create_host_jwt(
        host_sk,
        aud=_HOST_JWT_AUDIENCE,
        agent_public_key=ed25519_public_jwk(agent_sk),
        ttl_seconds=120,
    )
    headers = {"Authorization": f"Bearer {reg_tok}"}

    with TestClient(worker_a) as client_a, TestClient(worker_b) as client_b:
        first = client_a.post("/asap/agent/register", headers=headers)
        assert first.status_code == 200
        assert "agent_id" in first.json()

        replay = client_b.post("/asap/agent/register", headers=headers)
        assert replay.status_code == 401
        assert replay.json() == {"detail": "jti replay detected"}


@pytest.mark.skipif(not _fakeredis_available(), reason="redis/fakeredis not installed")
def test_host_jwt_jti_replay_rejected_across_workers_on_revoke(
    sample_manifest: Manifest,
    isolated_rate_limiter: ASAPRateLimiter | None,
) -> None:
    """Revoke on worker A records ``jti``; the same bearer fails on worker B."""
    jti_cache = _shared_redis_jti_cache()
    worker_a, worker_b = _two_workers_sharing_jti_cache(
        sample_manifest, isolated_rate_limiter, jti_cache
    )
    host_sk = Ed25519PrivateKey.generate()
    agent_sk = Ed25519PrivateKey.generate()
    reg_tok = create_host_jwt(
        host_sk,
        aud=_HOST_JWT_AUDIENCE,
        agent_public_key=ed25519_public_jwk(agent_sk),
        ttl_seconds=120,
    )
    revoke_tok = create_host_jwt(host_sk, aud=_HOST_JWT_AUDIENCE, ttl_seconds=120)
    revoke_headers = {"Authorization": f"Bearer {revoke_tok}"}

    with TestClient(worker_a) as client_a, TestClient(worker_b) as client_b:
        aid = client_a.post(
            "/asap/agent/register",
            headers={"Authorization": f"Bearer {reg_tok}"},
        ).json()["agent_id"]

        revoked = client_a.post(
            "/asap/agent/revoke",
            headers=revoke_headers,
            json={"agent_id": aid},
        )
        assert revoked.status_code == 200
        assert revoked.json()["status"] == "revoked"

        replay = client_b.post(
            "/asap/agent/revoke",
            headers=revoke_headers,
            json={"agent_id": aid},
        )
        assert replay.status_code == 401
        assert replay.json() == {"detail": "jti replay detected"}
