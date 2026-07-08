"""JWT ``jti`` replay protection backends (in-memory default, optional Redis).

Multi-instance deployments should inject :class:`RedisJtiReplayCache` via
``create_app(identity_jti_cache=...)`` or ``MCPAuthConfig.jti_replay_cache``
so replay state is shared across workers. Requires ``pip install 'asap-protocol[redis]'``.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable

if TYPE_CHECKING:
    from redis import Redis


@runtime_checkable
class JtiReplayCacheProtocol(Protocol):
    """Structural interface for ``jti`` replay guards."""

    def contains(self, partition_key: str, jti: str) -> bool:
        """Return whether ``jti`` is still recorded for ``partition_key``."""
        ...

    def check_and_record(self, partition_key: str, jti: str) -> bool:
        """Record ``jti`` for ``partition_key``; return False on replay."""
        ...


def _jti_blank(jti: str) -> bool:
    return not jti or not str(jti).strip()


def _redis_key(prefix: str, partition_key: str, jti: str) -> str:
    return f"{prefix}:{partition_key}:{jti}"


class RedisJtiReplayCache:
    """Redis-backed ``jti`` replay guard (default 90s TTL per key).

    Uses ``SET key 1 NX EX ttl`` for atomic first-use recording and ``EXISTS``
    for read-only replay checks (Host JWT polling routes).

    ``partition_key`` and ``jti`` are assumed URL-safe (no ``:``); keys are
    ``{prefix}:{partition_key}:{jti}``.

    Redis connection errors propagate to callers (same pattern as
    :mod:`asap.transport.rate_limit`); wrap with health checks or retries
    if you need graceful degradation.

    Example:
        >>> cache = RedisJtiReplayCache.from_url("redis://localhost:6379/0")
        >>> cache.check_and_record("host-thumbprint", "jwt_abc")
        True
    """

    def __init__(
        self,
        client: Redis,
        *,
        ttl_seconds: float = 90.0,
        key_prefix: str = "asap:jti-replay",
    ) -> None:
        self._client = client
        self._ttl = ttl_seconds
        self._key_prefix = key_prefix

    @classmethod
    def from_url(
        cls,
        url: str,
        *,
        ttl_seconds: float = 90.0,
        key_prefix: str = "asap:jti-replay",
        **redis_kwargs: Any,
    ) -> RedisJtiReplayCache:
        """Build a cache from a Redis URI (requires the optional ``redis`` extra)."""
        try:
            import redis
        except ImportError as exc:
            msg = (
                "Redis JTI replay cache requires the 'redis' package. "
                "Install it with: pip install 'asap-protocol[redis]'"
            )
            raise ImportError(msg) from exc
        client = redis.Redis.from_url(url, **redis_kwargs)
        return cls(client, ttl_seconds=ttl_seconds, key_prefix=key_prefix)

    def contains(self, partition_key: str, jti: str) -> bool:
        """Return whether ``jti`` is still recorded for ``partition_key``."""
        if _jti_blank(jti):
            return False
        key = _redis_key(self._key_prefix, partition_key, jti)
        return bool(self._client.exists(key))

    def check_and_record(self, partition_key: str, jti: str) -> bool:
        """Record ``jti`` for ``partition_key``.

        Returns:
            True if this is the first use within the TTL window.

            False if the same ``(partition_key, jti)`` was seen within the TTL
            (replay).
        """
        if _jti_blank(jti):
            return False
        key = _redis_key(self._key_prefix, partition_key, jti)
        # Floor fractional seconds to whole-second Redis EX (in-memory keeps float TTL).
        ttl_int = max(1, int(self._ttl))
        return bool(self._client.set(key, "1", nx=True, ex=ttl_int))
