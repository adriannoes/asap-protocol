"""HTTP helpers for the Consumer SDK: 429 retry with Retry-After / exponential backoff (ECO-001)."""

from __future__ import annotations

import asyncio
import time
from email.utils import parsedate_to_datetime

import httpx

# Retry up to 3 times on 429 (4 attempts total).
MAX_429_RETRIES: int = 3
# Exponential backoff: 1s, 2s, 4s when Retry-After is absent or invalid.
BASE_DELAY_SECONDS: float = 1.0


def delay_seconds_for_429(response: httpx.Response, attempt: int) -> float:
    """Retry-After header or exponential backoff; returns seconds (min 0.1)."""
    raw = response.headers.get("Retry-After")
    if raw:
        if raw.replace(".", "", 1).isdigit():
            try:
                secs = float(raw)
                if secs > 0:
                    return float(max(0.1, min(secs, 300.0)))
            except ValueError:
                pass
        else:
            try:
                retry_date = parsedate_to_datetime(raw)
                if retry_date:
                    delta = retry_date.timestamp() - time.time()
                    if delta > 0:
                        return float(max(0.1, min(delta, 300.0)))
            except (ValueError, TypeError, AttributeError, OSError):
                pass
    delay = BASE_DELAY_SECONDS * (2**attempt)
    return float(max(0.1, min(delay, 60.0)))


async def get_with_429_retry(
    client: httpx.AsyncClient,
    url: str,
    *,
    max_retries: int = MAX_429_RETRIES,
) -> httpx.Response:
    resp = None
    for attempt in range(max_retries + 1):
        resp = await client.get(url)
        if resp.status_code != 429 or attempt == max_retries:
            return resp
        await asyncio.sleep(delay_seconds_for_429(resp, attempt))
    assert resp is not None
    return resp
