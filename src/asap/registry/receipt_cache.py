"""Bounded TTL cache for idempotent registration receipts (PR-134 hardening).

Avoids unbounded growth of ``registration_receipt_cache`` when many distinct
``manifest_url`` values are submitted.
"""

from __future__ import annotations

import time
from collections import OrderedDict
from collections.abc import Iterator, MutableMapping
from typing import TypeVar

V = TypeVar("V")

# Defaults aligned with code review PR-134 (§4.1).
_DEFAULT_MAXSIZE = 10_000
_DEFAULT_TTL_SEC = 3600.0


class RegistrationReceiptTTLCache(MutableMapping[str, V]):
    """String-keyed cache with TTL and a maximum entry count.

    On ``__setitem__``, expired entries at the front are dropped and, if still
    over capacity, the oldest entries are evicted. Successful reads refresh LRU
    order via :meth:`move_to_end`.
    """

    __slots__ = ("_maxsize", "_store", "_ttl")

    def __init__(self, *, maxsize: int = _DEFAULT_MAXSIZE, ttl: float = _DEFAULT_TTL_SEC) -> None:
        if maxsize < 1:
            raise ValueError("maxsize must be >= 1")
        if ttl <= 0:
            raise ValueError("ttl must be > 0")
        self._maxsize = maxsize
        self._ttl = ttl
        self._store: OrderedDict[str, tuple[float, V]] = OrderedDict()

    def _drop_expired_from_head(self) -> None:
        now = time.monotonic()
        while self._store:
            _key, (expires_at, _val) = next(iter(self._store.items()))
            if expires_at > now:
                break
            self._store.popitem(last=False)

    def __getitem__(self, key: str) -> V:
        self._drop_expired_from_head()
        expires_at, val = self._store[key]
        if time.monotonic() >= expires_at:
            del self._store[key]
            raise KeyError(key)
        self._store.move_to_end(key)
        return val

    def __setitem__(self, key: str, value: V) -> None:
        now = time.monotonic()
        self._drop_expired_from_head()
        if key in self._store:
            del self._store[key]
        while len(self._store) >= self._maxsize:
            self._store.popitem(last=False)
        self._store[key] = (now + self._ttl, value)

    def __delitem__(self, key: str) -> None:
        del self._store[key]

    def __iter__(self) -> Iterator[str]:
        return iter(self._store)

    def __len__(self) -> int:
        return len(self._store)

    def __contains__(self, key: object) -> bool:
        if not isinstance(key, str):
            return False
        if key not in self._store:
            return False
        expires_at, _ = self._store[key]
        if time.monotonic() >= expires_at:
            del self._store[key]
            return False
        return True


def create_registration_receipt_cache(
    *,
    maxsize: int = _DEFAULT_MAXSIZE,
    ttl: float = _DEFAULT_TTL_SEC,
) -> RegistrationReceiptTTLCache[object]:
    """Factory used by :mod:`asap.transport.server` and registry-bot."""
    return RegistrationReceiptTTLCache(maxsize=maxsize, ttl=ttl)


__all__ = ["RegistrationReceiptTTLCache", "create_registration_receipt_cache"]
