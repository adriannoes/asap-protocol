"""Registry cache: TTL from ASAP_REGISTRY_CACHE_TTL, 429 retry (ECO-001)."""

from __future__ import annotations

import asyncio
import os
import httpx

from asap.client.http_client import MAX_429_RETRIES, _delay_seconds_for_429
from asap.discovery.registry import (
    LiteRegistry,
    discover_from_registry,
    reset_registry_cache,
)
from asap.observability import get_logger

logger = get_logger(__name__)

# Default TTL in seconds (5 minutes) per ADR-25 / SDK-003.
DEFAULT_REGISTRY_CACHE_TTL: int = 300

_ENV_REGISTRY_CACHE_TTL: str = "ASAP_REGISTRY_CACHE_TTL"


def _cache_ttl_seconds() -> int:
    raw = os.environ.get(_ENV_REGISTRY_CACHE_TTL, str(DEFAULT_REGISTRY_CACHE_TTL))
    try:
        value = int(raw)
        return value if value > 0 else DEFAULT_REGISTRY_CACHE_TTL
    except ValueError:
        return DEFAULT_REGISTRY_CACHE_TTL


async def get_registry(
    registry_url: str,
    *,
    ttl_seconds: int | None = None,
    transport: httpx.AsyncBaseTransport | None = None,
) -> LiteRegistry:
    ttl = ttl_seconds if ttl_seconds is not None else _cache_ttl_seconds()
    logger.debug("get_registry", registry_url=registry_url, ttl_seconds=ttl)
    registry: LiteRegistry | None = None
    for attempt in range(MAX_429_RETRIES + 1):
        try:
            registry = await discover_from_registry(
                registry_url,
                ttl_seconds=ttl,
                transport=transport,
            )
            break
        except httpx.HTTPStatusError as e:
            if e.response.status_code != 429 or attempt == MAX_429_RETRIES:
                raise
            logger.warning(
                "retry_429",
                registry_url=registry_url,
                attempt=attempt,
                status_code=429,
            )
            await asyncio.sleep(_delay_seconds_for_429(e.response, attempt))
    if registry is None:
        raise RuntimeError("Registry fetch loop completed without result or exception")
    return registry


def invalidate() -> None:
    reset_registry_cache()
