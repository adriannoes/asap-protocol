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


def test_ttl_cache_rejects_invalid_maxsize() -> None:
    with pytest.raises(ValueError, match="maxsize must be >= 1"):
        RegistrationReceiptTTLCache(maxsize=0)


def test_ttl_cache_rejects_non_positive_ttl() -> None:
    with pytest.raises(ValueError, match="ttl must be > 0"):
        RegistrationReceiptTTLCache(ttl=0.0)


def test_ttl_cache_getitem_raises_when_entry_expired(monkeypatch: pytest.MonkeyPatch) -> None:
    """Expired entries removed on read without relying on ``time.sleep``."""
    clock: dict[str, float] = {"t": 0.0}

    def fake_monotonic() -> float:
        return clock["t"]

    monkeypatch.setattr("asap.registry.receipt_cache.time.monotonic", fake_monotonic)
    c: RegistrationReceiptTTLCache[str] = RegistrationReceiptTTLCache(maxsize=10, ttl=10.0)
    c["k"] = "v"
    clock["t"] = 25.0
    with pytest.raises(KeyError):
        _ = c["k"]


def test_ttl_cache_contains_false_for_non_string_keys() -> None:
    c: RegistrationReceiptTTLCache[str] = RegistrationReceiptTTLCache(maxsize=10, ttl=60.0)
    assert (42 in c) is False


def test_ttl_cache_contains_drops_expired_entry(monkeypatch: pytest.MonkeyPatch) -> None:
    clock: dict[str, float] = {"t": 0.0}

    def fake_monotonic() -> float:
        return clock["t"]

    monkeypatch.setattr("asap.registry.receipt_cache.time.monotonic", fake_monotonic)
    c: RegistrationReceiptTTLCache[str] = RegistrationReceiptTTLCache(maxsize=10, ttl=10.0)
    c["k"] = "v"
    clock["t"] = 25.0
    assert "k" not in c


def test_ttl_cache_delitem_removes_key() -> None:
    c: RegistrationReceiptTTLCache[str] = RegistrationReceiptTTLCache(maxsize=10, ttl=60.0)
    c["a"] = "1"
    del c["a"]
    assert "a" not in c
    assert len(c) == 0


def test_ttl_cache_setitem_replaces_existing_key(monkeypatch: pytest.MonkeyPatch) -> None:
    clock: dict[str, float] = {"t": 0.0}

    def fake_monotonic() -> float:
        return clock["t"]

    monkeypatch.setattr("asap.registry.receipt_cache.time.monotonic", fake_monotonic)
    c: RegistrationReceiptTTLCache[str] = RegistrationReceiptTTLCache(maxsize=10, ttl=60.0)
    c["k"] = "first"
    clock["t"] = 5.0
    c["k"] = "second"
    assert c["k"] == "second"


def test_getitem_removes_expired_entry_behind_still_valid_head(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Head may still be valid while a tail entry is expired (LRU order)."""
    clock: dict[str, float] = {"t": 0.0}

    def fake_monotonic() -> float:
        return clock["t"]

    monkeypatch.setattr("asap.registry.receipt_cache.time.monotonic", fake_monotonic)
    c: RegistrationReceiptTTLCache[str] = RegistrationReceiptTTLCache(maxsize=10, ttl=100.0)
    clock["t"] = 0.0
    c["k1"] = "a"
    clock["t"] = 10.0
    c["k2"] = "b"
    clock["t"] = 11.0
    _ = c["k1"]
    clock["t"] = 102.0
    with pytest.raises(KeyError):
        _ = c["k1"]


def test_iter_yields_cache_keys() -> None:
    c: RegistrationReceiptTTLCache[str] = RegistrationReceiptTTLCache(maxsize=10, ttl=60.0)
    c["a"] = "1"
    c["b"] = "2"
    assert list(c) == ["a", "b"]
