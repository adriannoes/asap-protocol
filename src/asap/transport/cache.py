"""Manifest caching for ASAP protocol.

This module provides caching for agent manifests to reduce HTTP requests
and improve performance when discovering agent capabilities.

The cache uses a simple in-memory dictionary with TTL (Time To Live)
expiration. Entries expire after the configured TTL (default: 5 minutes).
"""

import time
from threading import Lock
from typing import Optional

from asap.models.entities import Manifest


# Default TTL in seconds (5 minutes)
DEFAULT_TTL = 300.0


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
    """Thread-safe in-memory cache for agent manifests.

    Provides TTL-based expiration and methods for cache management.
    Thread-safe for concurrent access from multiple async tasks.

    Attributes:
        _cache: Dictionary mapping URL to CacheEntry
        _lock: Lock for thread-safe access
        _default_ttl: Default TTL in seconds

    Example:
        >>> cache = ManifestCache(default_ttl=300.0)
        >>> cache.set("http://agent.example.com/manifest.json", manifest, ttl=300.0)
        >>> cached = cache.get("http://agent.example.com/manifest.json")
        >>> if cached:
        ...     print(cached.id)
    """

    def __init__(self, default_ttl: float = DEFAULT_TTL) -> None:
        """Initialize manifest cache.

        Args:
            default_ttl: Default TTL in seconds for cache entries (default: 300.0)
        """
        self._cache: dict[str, CacheEntry] = {}
        self._lock = Lock()
        self._default_ttl = default_ttl

    def get(self, url: str) -> Optional[Manifest]:
        """Get manifest from cache if present and not expired.

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
            return entry.manifest

    def set(self, url: str, manifest: Manifest, ttl: Optional[float] = None) -> None:
        """Store manifest in cache with TTL.

        Args:
            url: Manifest URL (cache key)
            manifest: Manifest to cache
            ttl: Time to live in seconds (defaults to default_ttl)
        """
        if ttl is None:
            ttl = self._default_ttl
        with self._lock:
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

    def cleanup_expired(self) -> int:
        """Remove all expired entries from cache.

        Returns:
            Number of expired entries removed
        """
        with self._lock:
            expired_urls = [
                url for url, entry in self._cache.items() if entry.is_expired()
            ]
            for url in expired_urls:
                del self._cache[url]
            return len(expired_urls)
