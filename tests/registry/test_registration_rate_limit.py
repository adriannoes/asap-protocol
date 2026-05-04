"""Unit tests for registration-specific rate limit helpers (AUTO-003)."""

from __future__ import annotations

from unittest.mock import MagicMock

from starlette.datastructures import Headers

from asap.transport.rate_limit import (
    create_registration_rate_limiter,
    registration_token_key,
)


def test_registration_token_key_stable_per_bearer_secret() -> None:
    req = MagicMock()
    req.headers = Headers({"authorization": "Bearer same-secret"})
    req.client = MagicMock()
    req.client.host = "203.0.113.10"
    k1 = registration_token_key(req)
    k2 = registration_token_key(req)
    assert k1 == k2
    assert k1.startswith("regtok:")


def test_registration_token_key_fallback_uses_client_ip() -> None:
    req = MagicMock()
    req.headers = Headers({})
    req.client = MagicMock()
    req.client.host = "198.51.100.2"
    key = registration_token_key(req)
    assert key == "ip:198.51.100.2"


def test_registration_token_key_empty_bearer_falls_back_to_ip() -> None:
    req = MagicMock()
    req.headers = Headers({"authorization": "Bearer "})
    req.client = MagicMock()
    req.client.host = "198.51.100.3"
    key = registration_token_key(req)
    assert key.startswith("ip:")


def test_create_registration_rate_limiter_has_hour_budget() -> None:
    limiter = create_registration_rate_limiter()
    assert len(limiter.limits) >= 1
