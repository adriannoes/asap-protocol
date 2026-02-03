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
        """Initialize cache entry.

        Args:
            manifest: Manifest to cache
            ttl: Time to live in seconds
        """
        self.manifest = manifest
        self.expires_at = time.time() + ttl

    def is_expired(self) -> bool:
        """Check if cache entry has expired.

        Returns:
            True if entry has expired, False otherwise
        """
        return time.time() >= self.expires_at


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
        """Initialize manifest cache.

        Args:
            default_ttl: Default TTL in seconds for cache entries (default: 300.0)
            max_size: Maximum number of cache entries. When exceeded, the least
                recently used entry is evicted. Set to 0 for unlimited size.
                Default: 1000.
        """
        self._cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self._lock = Lock()
        self._default_ttl = default_ttl
        self._max_size = max_size

    def get(self, url: str) -> Optional[Manifest]:
        """Get manifest from cache if present and not expired.

        Accessing an entry moves it to the end of the LRU queue,
        marking it as most recently used.

        Args:
            url: Manifest URL

        Returns:
            Cached manifest if found and not expired, None otherwise
        """
        with self._lock:
            entry = self._cache.get(url)
            if entry is None:
                return None
            if entry.is_expired():
                # Remove expired entry
                del self._cache[url]
                return None
            # Move to end (most recently used) for LRU ordering
            self._cache.move_to_end(url)
            return entry.manifest

    def set(self, url: str, manifest: Manifest, ttl: Optional[float] = None) -> None:
        """Store manifest in cache with TTL.

        If max_size is set and the cache is full, the least recently used
        entry is evicted before adding the new entry.

        Args:
            url: Manifest URL (cache key)
            manifest: Manifest to cache
            ttl: Time to live in seconds (defaults to default_ttl)
        """
        if ttl is None:
            ttl = self._default_ttl
        with self._lock:
            # If URL already exists, remove it first (will be re-added at end)
            if url in self._cache:
                del self._cache[url]
            # Evict LRU entries if max_size is set and cache is at capacity
            elif self._max_size > 0:
                while len(self._cache) >= self._max_size:
                    # Remove oldest entry (first in OrderedDict)
                    self._cache.popitem(last=False)
            # Add new entry at end (most recently used)
            self._cache[url] = CacheEntry(manifest, ttl)

    def invalidate(self, url: str) -> None:
        """Remove manifest from cache.

        Args:
            url: Manifest URL to invalidate
        """
        with self._lock:
            self._cache.pop(url, None)

    def clear_all(self) -> None:
        """Clear all cached manifests."""
        with self._lock:
            self._cache.clear()

    def size(self) -> int:
        """Get number of cached entries (including expired).

        Returns:
            Number of entries in cache
        """
        with self._lock:
            return len(self._cache)

    @property
    def max_size(self) -> int:
        """Get the configured maximum cache size.

        Returns:
            Maximum number of entries (0 for unlimited)
        """
        return self._max_size

    def cleanup_expired(self) -> int:
        """Remove all expired entries from cache.

        Returns:
            Number of expired entries removed
        """
        with self._lock:
            expired_urls = [url for url, entry in self._cache.items() if entry.is_expired()]
            for url in expired_urls:
                del self._cache[url]
            return len(expired_urls)
