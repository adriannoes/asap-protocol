"""Tests for asap.client.http_client (429 Retry-After and get_with_429_retry)."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from asap.client.http_client import BASE_DELAY_SECONDS, _delay_seconds_for_429, get_with_429_retry


def test_delay_seconds_numeric_retry_after() -> None:
    resp = httpx.Response(429, headers={"Retry-After": "10"})
    assert _delay_seconds_for_429(resp, 0) == 10.0


def test_delay_seconds_numeric_capped_at_300() -> None:
    resp = httpx.Response(429, headers={"Retry-After": "99999"})
    assert _delay_seconds_for_429(resp, 0) == 300.0


def test_delay_seconds_retry_after_zero_uses_exponential_backoff() -> None:
    resp = httpx.Response(429, headers={"Retry-After": "0"})
    expected = max(0.1, min(BASE_DELAY_SECONDS * (2**2), 60.0))
    assert _delay_seconds_for_429(resp, 2) == expected


def test_delay_seconds_exponential_when_no_header() -> None:
    resp = httpx.Response(429)
    assert _delay_seconds_for_429(resp, 0) == max(0.1, min(BASE_DELAY_SECONDS, 60.0))
    assert _delay_seconds_for_429(resp, 3) == max(0.1, min(BASE_DELAY_SECONDS * 8, 60.0))


def test_delay_seconds_http_date_retry_after_positive_delta() -> None:
    resp = httpx.Response(429, headers={"Retry-After": "Wed, 21 Oct 2030 07:28:00 GMT"})
    with patch("asap.client.http_client.time.time", return_value=0.0):
        delay = _delay_seconds_for_429(resp, 0)
    assert 0.1 <= delay <= 300.0


def test_delay_seconds_invalid_retry_after_falls_back_to_exponential() -> None:
    resp = httpx.Response(429, headers={"Retry-After": "not-a-number-or-date"})
    assert _delay_seconds_for_429(resp, 1) == max(0.1, min(BASE_DELAY_SECONDS * 2, 60.0))


def test_delay_seconds_retry_after_unparseable_date_falls_back() -> None:
    resp = httpx.Response(429, headers={"Retry-After": "Wed, Not A Real Date"})
    with patch("asap.client.http_client.parsedate_to_datetime", return_value=None):
        delay = _delay_seconds_for_429(resp, 2)
    assert delay == max(0.1, min(BASE_DELAY_SECONDS * 4, 60.0))


def test_delay_seconds_past_http_date_uses_exponential_backoff() -> None:
    resp = httpx.Response(429, headers={"Retry-After": "Wed, 21 Oct 1990 07:28:00 GMT"})
    with patch("asap.client.http_client.time.time", return_value=1_700_000_000.0):
        delay = _delay_seconds_for_429(resp, 2)
    assert delay == max(0.1, min(BASE_DELAY_SECONDS * 4, 60.0))


def test_delay_seconds_float_conversion_valueerror_falls_through() -> None:
    resp = httpx.Response(429, headers={"Retry-After": "42"})
    real_float = float

    def selective_float(x: object) -> float:
        if x == "42":
            raise ValueError("invalid")
        return real_float(x)

    with patch("builtins.float", selective_float):
        delay = _delay_seconds_for_429(resp, 0)
    assert delay == max(0.1, min(BASE_DELAY_SECONDS, 60.0))


@pytest.mark.asyncio
async def test_get_with_429_retry_returns_on_success() -> None:
    client = MagicMock()
    client.get = AsyncMock(return_value=httpx.Response(200, content=b"{}"))
    resp = await get_with_429_retry(client, "https://example.com/r")
    assert resp.status_code == 200
    client.get.assert_awaited_once_with("https://example.com/r")


@pytest.mark.asyncio
async def test_get_with_429_retry_retries_then_succeeds() -> None:
    ok = httpx.Response(200, content=b"{}")
    client = MagicMock()
    client.get = AsyncMock(
        side_effect=[
            httpx.Response(429, headers={"Retry-After": "0"}),
            ok,
        ]
    )
    with patch("asap.client.http_client.asyncio.sleep", new_callable=AsyncMock):
        resp = await get_with_429_retry(client, "https://example.com/r")
    assert resp is ok
    assert client.get.await_count == 2


@pytest.mark.asyncio
async def test_get_with_429_retry_raises_after_max_retries() -> None:
    req = httpx.Request("GET", "https://example.com/r")
    too_many = httpx.Response(429, request=req)
    client = MagicMock()
    client.get = AsyncMock(return_value=too_many)
    with (
        patch("asap.client.http_client.asyncio.sleep", new_callable=AsyncMock),
        pytest.raises(httpx.HTTPStatusError),
    ):
        await get_with_429_retry(client, "https://example.com/r", max_retries=2)
    assert client.get.await_count == 3
