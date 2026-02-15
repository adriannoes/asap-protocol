"""Manifest caching for ASAP protocol.

This module provides caching for agent manifests to reduce HTTP requests
and improve performance when discovering agent capabilities.

The cache uses an OrderedDict with TTL (Time To Live) expiration and LRU
eviction when max_size is reached. Entries expire after the configured
TTL (default: 5 minutes).
"""

import time
from collections import OrderedDict
from threading import Lock
from typing import Optional

from asap.models.entities import Manifest


# Default TTL in seconds (5 minutes)
DEFAULT_TTL = 300.0

# Default max cache size (number of entries)
DEFAULT_MAX_SIZE = 1000


class CacheEntry:
    """Cache entry with TTL expiration.

    Attributes:
        manifest: Cached manifest object
        expires_at: Timestamp when entry expires (seconds since epoch)
    """

    def __init__(self, manifest: Manifest, ttl: float) -> None:
        self.manifest = manifest
        self.expires_at = time.monotonic() + ttl

    def is_expired(self) -> bool:
        return time.monotonic() >= self.expires_at


class ManifestCache:
    """Thread-safe in-memory LRU cache for agent manifests.

    Provides TTL-based expiration, LRU eviction when max_size is reached,
    and methods for cache management. Thread-safe for concurrent access
    from multiple async tasks.

    Attributes:
        _cache: OrderedDict mapping URL to CacheEntry (maintains LRU order)
        _lock: Lock for thread-safe access
        _default_ttl: Default TTL in seconds
        _max_size: Maximum number of entries (0 for unlimited)

    Example:
        >>> cache = ManifestCache(default_ttl=300.0, max_size=100)
        >>> cache.set("http://agent.example.com/manifest.json", manifest, ttl=300.0)
        >>> cached = cache.get("http://agent.example.com/manifest.json")
        >>> if cached:
        ...     print(cached.id)
    """

    def __init__(
        self,
        default_ttl: float = DEFAULT_TTL,
        max_size: int = DEFAULT_MAX_SIZE,
    ) -> None:
        self._cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self._lock = Lock()
        self._default_ttl = default_ttl
        self._max_size = max_size

    def get(self, url: str) -> Optional[Manifest]:
        with self._lock:
            entry = self._cache.get(url)
            if entry is None:
                return None
            if entry.is_expired():
                del self._cache[url]
                return None
            self._cache.move_to_end(url)
            return entry.manifest

    def set(self, url: str, manifest: Manifest, ttl: Optional[float] = None) -> None:
        if ttl is None:
            ttl = self._default_ttl
        with self._lock:
            if url in self._cache:
                del self._cache[url]
            elif self._max_size > 0:
                while len(self._cache) >= self._max_size:
                    self._cache.popitem(last=False)
            self._cache[url] = CacheEntry(manifest, ttl)

    def invalidate(self, url: str) -> None:
        with self._lock:
            self._cache.pop(url, None)

    def clear_all(self) -> None:
        with self._lock:
            self._cache.clear()

    def size(self) -> int:
        with self._lock:
            return len(self._cache)

    @property
    def max_size(self) -> int:
        return self._max_size

    def cleanup_expired(self) -> int:
        """Remove all expired entries from cache.

        Holds the lock for O(N). For very large max_size, prefer lazy eviction
        in get() or call less frequently.

        Returns:
            Number of expired entries removed
        """
        with self._lock:
            expired_urls = [url for url, entry in self._cache.items() if entry.is_expired()]
            for url in expired_urls:
                del self._cache[url]
            return len(expired_urls)
