"""Redis-backed Host JWT read-only JTI checks (multi-worker polling, v2.5.2)."""

from __future__ import annotations

import importlib.util
from datetime import datetime, timezone

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from asap.auth.agent_jwt import create_host_jwt, verify_host_jwt
from asap.auth.identity import HostIdentity, InMemoryHostStore
from asap.auth.jti_replay_cache import RedisJtiReplayCache
from tests.crypto.jwk_helpers import ed25519_public_jwk

_HOST_JWT_AUDIENCE = "https://aud.example"


def _fakeredis_shared_caches() -> tuple[RedisJtiReplayCache, RedisJtiReplayCache] | None:
    """Two cache instances on one FakeRedis client (multi-worker sharing)."""
    if importlib.util.find_spec("redis") is None:
        return None
    if importlib.util.find_spec("fakeredis") is None:
        return None
    import fakeredis

    client = fakeredis.FakeStrictRedis(decode_responses=False)
    worker_a = RedisJtiReplayCache(client, ttl_seconds=90.0)
    worker_b = RedisJtiReplayCache(client, ttl_seconds=90.0)
    return worker_a, worker_b


@pytest.mark.asyncio
@pytest.mark.filterwarnings("ignore:EdDSA is deprecated:UserWarning")
@pytest.mark.skipif(
    _fakeredis_shared_caches() is None,
    reason="redis/fakeredis not installed",
)
async def test_verify_host_jwt_redis_read_only_jti_multi_worker_polling() -> None:
    """Shared Redis JTI: poll read-only until spend, then reject replay.

    Mirrors transport ``verify_host_bearer`` polling semantics across two
    workers that share one FakeRedis-backed :class:`RedisJtiReplayCache`.
    """
    caches = _fakeredis_shared_caches()
    assert caches is not None
    worker_a_cache, worker_b_cache = caches

    now = datetime.now(timezone.utc)
    host_sk = Ed25519PrivateKey.generate()
    hosts = InMemoryHostStore()
    await hosts.save(
        HostIdentity(
            host_id="host-redis-jti",
            public_key=ed25519_public_jwk(host_sk),
            status="active",
            created_at=now,
            updated_at=now,
        )
    )
    token = create_host_jwt(host_sk, aud=_HOST_JWT_AUDIENCE, ttl_seconds=120)

    for _ in range(2):
        poll = await verify_host_jwt(
            token,
            hosts,
            jti_replay_cache=worker_b_cache,
            record_jti=False,
        )
        assert poll.ok is True

    spend = await verify_host_jwt(
        token,
        hosts,
        jti_replay_cache=worker_a_cache,
        record_jti=True,
    )
    assert spend.ok is True

    replay = await verify_host_jwt(
        token,
        hosts,
        jti_replay_cache=worker_b_cache,
        record_jti=False,
    )
    assert replay.ok is False
    assert replay.error == "jti replay detected"
