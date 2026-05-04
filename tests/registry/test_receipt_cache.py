"""Tests for bounded TTL registration receipt cache."""

from __future__ import annotations

import time

import pytest

from asap.registry.receipt_cache import (
    RegistrationReceiptTTLCache,
    create_registration_receipt_cache,
)


def test_ttl_cache_basic_set_get() -> None:
    c: RegistrationReceiptTTLCache[str] = RegistrationReceiptTTLCache(maxsize=10, ttl=60.0)
    c["a"] = "one"
    assert c["a"] == "one"
    assert "a" in c


def test_ttl_cache_expires() -> None:
    c: RegistrationReceiptTTLCache[str] = RegistrationReceiptTTLCache(maxsize=10, ttl=0.01)
    c["k"] = "v"
    time.sleep(0.03)
    assert "k" not in c
    with pytest.raises(KeyError):
        _ = c["k"]


def test_ttl_cache_evicts_when_full() -> None:
    c: RegistrationReceiptTTLCache[int] = RegistrationReceiptTTLCache(maxsize=2, ttl=3600.0)
    c["a"] = 1
    c["b"] = 2
    c["c"] = 3
    assert "a" not in c
    assert "b" in c
    assert "c" in c


def test_factory_returns_empty_cache() -> None:
    c: RegistrationReceiptTTLCache[object] = create_registration_receipt_cache()
    assert len(c) == 0
