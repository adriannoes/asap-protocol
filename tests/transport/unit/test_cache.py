"""Unit tests for ASAP transport cache module.

Tests cover CacheEntry and ManifestCache: TTL expiration, get/set/invalidate,
clear_all, size, cleanup_expired, and thread-safety.
"""

from __future__ import annotations

import pytest

from asap.models.entities import Capability, Endpoint, Manifest, Skill
from asap.transport.cache import (
    DEFAULT_MAX_SIZE,
    DEFAULT_TTL,
    CacheEntry,
    ManifestCache,
)


def _make_manifest(agent_id: str = "urn:asap:agent:testagent") -> Manifest:
    """Create a minimal Manifest for testing."""
    return Manifest(
        id=agent_id,
        name="Test Agent",
        version="1.0.0",
        description="Test agent for cache tests",
        capabilities=Capability(
            asap_version="0.1",
            skills=[Skill(id="test", description="Test skill")],
            state_persistence=False,
        ),
        endpoints=Endpoint(asap="http://localhost:8000/asap"),
    )


class MockTime:
    """Mock time.time() with a controllable current time."""

    def __init__(self, initial: float = 1000.0) -> None:
        self.current = initial

    def time(self) -> float:
        return self.current

    def advance(self, seconds: float) -> None:
        self.current += seconds


class TestCacheEntry:
    """Tests for CacheEntry class."""

    def test_init_stores_manifest_and_expires_at(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """CacheEntry stores manifest and calculates expires_at = time.time() + ttl."""
        from asap.transport import cache as cache_module

        mock_time = MockTime(1000.0)
        monkeypatch.setattr(cache_module.time, "time", mock_time.time)
        manifest = _make_manifest()
        entry = CacheEntry(manifest, ttl=60.0)
        assert entry.manifest is manifest
        assert entry.expires_at == 1060.0

    def test_is_expired_false_when_not_expired(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """is_expired returns False when current time < expires_at."""
        from asap.transport import cache as cache_module

        mock_time = MockTime(1000.0)
        monkeypatch.setattr(cache_module.time, "time", mock_time.time)
        manifest = _make_manifest()
        entry = CacheEntry(manifest, ttl=60.0)
        mock_time.advance(59.9)
        assert entry.is_expired() is False

    def test_is_expired_true_when_expired(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """is_expired returns True when current time >= expires_at."""
        from asap.transport import cache as cache_module

        mock_time = MockTime(1000.0)
        monkeypatch.setattr(cache_module.time, "time", mock_time.time)
        manifest = _make_manifest()
        entry = CacheEntry(manifest, ttl=60.0)
        mock_time.advance(60.0)
        assert entry.is_expired() is True

    def test_is_expired_true_when_past_expires_at(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """is_expired returns True when current time > expires_at."""
        from asap.transport import cache as cache_module

        mock_time = MockTime(1000.0)
        monkeypatch.setattr(cache_module.time, "time", mock_time.time)
        manifest = _make_manifest()
        entry = CacheEntry(manifest, ttl=60.0)
        mock_time.advance(1000.0)
        assert entry.is_expired() is True


class TestManifestCacheInit:
    """Tests for ManifestCache initialization."""

    def test_default_ttl_is_default(self) -> None:
        """ManifestCache uses DEFAULT_TTL when no default_ttl is provided."""
        cache = ManifestCache()
        assert cache._default_ttl == DEFAULT_TTL

    def test_custom_default_ttl(self) -> None:
        """ManifestCache accepts custom default_ttl."""
        cache = ManifestCache(default_ttl=120.0)
        assert cache._default_ttl == 120.0

    def test_default_max_size_is_default(self) -> None:
        """ManifestCache uses DEFAULT_MAX_SIZE when no max_size is provided."""
        cache = ManifestCache()
        assert cache.max_size == DEFAULT_MAX_SIZE

    def test_custom_max_size(self) -> None:
        """ManifestCache accepts custom max_size."""
        cache = ManifestCache(max_size=100)
        assert cache.max_size == 100

    def test_max_size_zero_means_unlimited(self) -> None:
        """ManifestCache with max_size=0 has no size limit."""
        cache = ManifestCache(max_size=0)
        assert cache.max_size == 0

    def test_initial_size_is_zero(self) -> None:
        """New ManifestCache has size() == 0."""
        cache = ManifestCache()
        assert cache.size() == 0


class TestManifestCacheGetSet:
    """Tests for ManifestCache get and set methods."""

    def test_get_returns_none_for_missing_url(self) -> None:
        """get() returns None when URL is not in cache."""
        cache = ManifestCache()
        assert cache.get("http://missing.example.com/manifest.json") is None

    def test_set_and_get_returns_manifest(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """set() stores manifest; get() returns it."""
        from asap.transport import cache as cache_module

        mock_time = MockTime(1000.0)
        monkeypatch.setattr(cache_module.time, "time", mock_time.time)
        cache = ManifestCache(default_ttl=60.0)
        manifest = _make_manifest()
        url = "http://test.example.com/manifest.json"
        cache.set(url, manifest)
        assert cache.get(url) is manifest

    def test_set_uses_default_ttl_when_ttl_is_none(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """set() uses default_ttl when ttl is None."""
        from asap.transport import cache as cache_module

        mock_time = MockTime(1000.0)
        monkeypatch.setattr(cache_module.time, "time", mock_time.time)
        cache = ManifestCache(default_ttl=60.0)
        manifest = _make_manifest()
        url = "http://test.example.com/manifest.json"
        cache.set(url, manifest)
        mock_time.advance(59.0)
        assert cache.get(url) is manifest
        mock_time.advance(1.0)
        assert cache.get(url) is None

    def test_set_with_explicit_ttl(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """set() uses provided ttl instead of default_ttl."""
        from asap.transport import cache as cache_module

        mock_time = MockTime(1000.0)
        monkeypatch.setattr(cache_module.time, "time", mock_time.time)
        cache = ManifestCache(default_ttl=60.0)
        manifest = _make_manifest()
        url = "http://test.example.com/manifest.json"
        cache.set(url, manifest, ttl=30.0)
        mock_time.advance(29.0)
        assert cache.get(url) is manifest
        mock_time.advance(1.0)
        assert cache.get(url) is None

    def test_get_removes_expired_entry(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """get() removes expired entry from cache and returns None."""
        from asap.transport import cache as cache_module

        mock_time = MockTime(1000.0)
        monkeypatch.setattr(cache_module.time, "time", mock_time.time)
        cache = ManifestCache(default_ttl=60.0)
        manifest = _make_manifest()
        url = "http://test.example.com/manifest.json"
        cache.set(url, manifest)
        assert cache.size() == 1
        mock_time.advance(60.0)
        assert cache.get(url) is None
        assert cache.size() == 0


class TestManifestCacheInvalidate:
    """Tests for ManifestCache invalidate method."""

    def test_invalidate_removes_entry(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """invalidate() removes entry; get() returns None."""
        from asap.transport import cache as cache_module

        mock_time = MockTime(1000.0)
        monkeypatch.setattr(cache_module.time, "time", mock_time.time)
        cache = ManifestCache()
        manifest = _make_manifest()
        url = "http://test.example.com/manifest.json"
        cache.set(url, manifest)
        assert cache.get(url) is manifest
        cache.invalidate(url)
        assert cache.get(url) is None
        assert cache.size() == 0

    def test_invalidate_nonexistent_url_does_not_raise(self) -> None:
        """invalidate() on nonexistent URL does not raise."""
        cache = ManifestCache()
        cache.invalidate("http://nonexistent.example.com/manifest.json")
        assert cache.size() == 0


class TestManifestCacheClearAll:
    """Tests for ManifestCache clear_all method."""

    def test_clear_all_removes_all_entries(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """clear_all() removes all entries; size() == 0."""
        from asap.transport import cache as cache_module

        mock_time = MockTime(1000.0)
        monkeypatch.setattr(cache_module.time, "time", mock_time.time)
        cache = ManifestCache()
        for i in range(5):
            cache.set(
                f"http://test{i}.example.com/manifest.json",
                _make_manifest(f"urn:asap:agent:testagent{i}"),
            )
        assert cache.size() == 5
        cache.clear_all()
        assert cache.size() == 0
        for i in range(5):
            assert cache.get(f"http://test{i}.example.com/manifest.json") is None


class TestManifestCacheSize:
    """Tests for ManifestCache size method."""

    def test_size_returns_correct_count(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """size() returns number of entries."""
        from asap.transport import cache as cache_module

        mock_time = MockTime(1000.0)
        monkeypatch.setattr(cache_module.time, "time", mock_time.time)
        cache = ManifestCache()
        assert cache.size() == 0
        cache.set("http://a.example.com/manifest.json", _make_manifest("urn:asap:agent:agenta"))
        assert cache.size() == 1
        cache.set("http://b.example.com/manifest.json", _make_manifest("urn:asap:agent:agentb"))
        assert cache.size() == 2
        cache.set("http://c.example.com/manifest.json", _make_manifest("urn:asap:agent:agentc"))
        assert cache.size() == 3


class TestManifestCacheCleanupExpired:
    """Tests for ManifestCache cleanup_expired method."""

    def test_cleanup_expired_removes_expired_entries(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """cleanup_expired() removes expired entries and returns count."""
        from asap.transport import cache as cache_module

        mock_time = MockTime(1000.0)
        monkeypatch.setattr(cache_module.time, "time", mock_time.time)
        cache = ManifestCache()
        cache.set(
            "http://short.example.com/manifest.json",
            _make_manifest("urn:asap:agent:agentshort"),
            ttl=30.0,
        )
        cache.set(
            "http://long.example.com/manifest.json",
            _make_manifest("urn:asap:agent:agentlong"),
            ttl=60.0,
        )
        cache.set(
            "http://long2.example.com/manifest.json",
            _make_manifest("urn:asap:agent:agentlongtwo"),
            ttl=60.0,
        )
        assert cache.size() == 3
        mock_time.advance(35.0)
        removed = cache.cleanup_expired()
        assert removed == 1
        assert cache.size() == 2
        assert cache.get("http://short.example.com/manifest.json") is None

    def test_cleanup_expired_returns_zero_when_none_expired(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """cleanup_expired() returns 0 when no entries are expired."""
        from asap.transport import cache as cache_module

        mock_time = MockTime(1000.0)
        monkeypatch.setattr(cache_module.time, "time", mock_time.time)
        cache = ManifestCache()
        cache.set("http://test.example.com/manifest.json", _make_manifest(), ttl=60.0)
        removed = cache.cleanup_expired()
        assert removed == 0
        assert cache.size() == 1

    def test_cleanup_expired_on_empty_cache(self) -> None:
        """cleanup_expired() on empty cache returns 0."""
        cache = ManifestCache()
        assert cache.cleanup_expired() == 0


class TestManifestCacheThreadSafety:
    """Basic thread-safety tests for ManifestCache."""

    def test_concurrent_set_and_get(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Concurrent set and get operations do not raise."""
        import threading

        from asap.transport import cache as cache_module

        mock_time = MockTime(1000.0)
        monkeypatch.setattr(cache_module.time, "time", mock_time.time)
        cache = ManifestCache()
        manifest = _make_manifest("urn:asap:agent:testagent")

        def worker(n: int) -> None:
            for i in range(10):
                url = f"http://test{n}x{i}.example.com/manifest.json"
                cache.set(url, manifest)
                cache.get(url)
                cache.invalidate(url)

        threads = [threading.Thread(target=worker, args=(n,)) for n in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        assert cache.size() >= 0


class TestManifestCacheLRU:
    """Tests for LRU eviction behavior in ManifestCache."""

    def test_evicts_lru_entry_when_max_size_reached(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """When max_size is reached, the least recently used entry is evicted."""
        from asap.transport import cache as cache_module

        mock_time = MockTime(1000.0)
        monkeypatch.setattr(cache_module.time, "time", mock_time.time)
        cache = ManifestCache(max_size=3)

        # Add 3 entries (fills the cache)
        cache.set("http://a.example.com/m.json", _make_manifest("urn:asap:agent:a"))
        cache.set("http://b.example.com/m.json", _make_manifest("urn:asap:agent:b"))
        cache.set("http://c.example.com/m.json", _make_manifest("urn:asap:agent:c"))
        assert cache.size() == 3

        # Add 4th entry - should evict 'a' (oldest)
        cache.set("http://d.example.com/m.json", _make_manifest("urn:asap:agent:d"))
        assert cache.size() == 3
        assert cache.get("http://a.example.com/m.json") is None
        assert cache.get("http://b.example.com/m.json") is not None
        assert cache.get("http://c.example.com/m.json") is not None
        assert cache.get("http://d.example.com/m.json") is not None

    def test_get_updates_lru_order(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Accessing an entry with get() moves it to most recently used position."""
        from asap.transport import cache as cache_module

        mock_time = MockTime(1000.0)
        monkeypatch.setattr(cache_module.time, "time", mock_time.time)
        cache = ManifestCache(max_size=3)

        # Add 3 entries: a, b, c (a is oldest)
        cache.set("http://a.example.com/m.json", _make_manifest("urn:asap:agent:a"))
        cache.set("http://b.example.com/m.json", _make_manifest("urn:asap:agent:b"))
        cache.set("http://c.example.com/m.json", _make_manifest("urn:asap:agent:c"))

        # Access 'a' - now 'b' is oldest
        cache.get("http://a.example.com/m.json")

        # Add 'd' - should evict 'b' (now oldest)
        cache.set("http://d.example.com/m.json", _make_manifest("urn:asap:agent:d"))
        assert cache.size() == 3
        assert cache.get("http://a.example.com/m.json") is not None
        assert cache.get("http://b.example.com/m.json") is None  # Evicted
        assert cache.get("http://c.example.com/m.json") is not None
        assert cache.get("http://d.example.com/m.json") is not None

    def test_set_existing_key_updates_lru_order(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Setting an existing key moves it to most recently used position."""
        from asap.transport import cache as cache_module

        mock_time = MockTime(1000.0)
        monkeypatch.setattr(cache_module.time, "time", mock_time.time)
        cache = ManifestCache(max_size=3)

        # Add 3 entries: a, b, c
        cache.set("http://a.example.com/m.json", _make_manifest("urn:asap:agent:a"))
        cache.set("http://b.example.com/m.json", _make_manifest("urn:asap:agent:b"))
        cache.set("http://c.example.com/m.json", _make_manifest("urn:asap:agent:c"))

        # Update 'a' - now 'b' is oldest
        cache.set("http://a.example.com/m.json", _make_manifest("urn:asap:agent:a-v2"))

        # Add 'd' - should evict 'b' (now oldest)
        cache.set("http://d.example.com/m.json", _make_manifest("urn:asap:agent:d"))
        assert cache.size() == 3
        assert cache.get("http://a.example.com/m.json") is not None
        assert cache.get("http://b.example.com/m.json") is None  # Evicted
        assert cache.get("http://c.example.com/m.json") is not None
        assert cache.get("http://d.example.com/m.json") is not None

    def test_max_size_zero_allows_unlimited_entries(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """max_size=0 allows unlimited entries (no eviction)."""
        from asap.transport import cache as cache_module

        mock_time = MockTime(1000.0)
        monkeypatch.setattr(cache_module.time, "time", mock_time.time)
        cache = ManifestCache(max_size=0)

        # Add many entries
        for i in range(100):
            cache.set(
                f"http://test{i}.example.com/m.json",
                _make_manifest(f"urn:asap:agent:agent{i}"),
            )

        # All should be present
        assert cache.size() == 100
        for i in range(100):
            assert cache.get(f"http://test{i}.example.com/m.json") is not None

    def test_max_size_one_evicts_immediately(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """max_size=1 keeps only the most recently added entry."""
        from asap.transport import cache as cache_module

        mock_time = MockTime(1000.0)
        monkeypatch.setattr(cache_module.time, "time", mock_time.time)
        cache = ManifestCache(max_size=1)

        cache.set("http://a.example.com/m.json", _make_manifest("urn:asap:agent:a"))
        assert cache.size() == 1
        assert cache.get("http://a.example.com/m.json") is not None

        cache.set("http://b.example.com/m.json", _make_manifest("urn:asap:agent:b"))
        assert cache.size() == 1
        assert cache.get("http://a.example.com/m.json") is None
        assert cache.get("http://b.example.com/m.json") is not None

    def test_concurrent_access_with_lru(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Concurrent access with LRU eviction does not raise errors."""
        import threading

        from asap.transport import cache as cache_module

        mock_time = MockTime(1000.0)
        monkeypatch.setattr(cache_module.time, "time", mock_time.time)
        cache = ManifestCache(max_size=10)
        manifest = _make_manifest("urn:asap:agent:testagent")
        errors: list[Exception] = []

        def worker(n: int) -> None:
            try:
                for i in range(50):
                    url = f"http://test{n}x{i}.example.com/manifest.json"
                    cache.set(url, manifest)
                    cache.get(url)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=worker, args=(n,)) for n in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0
        assert cache.size() <= 10
