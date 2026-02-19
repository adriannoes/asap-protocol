"""Tests for SLAStorage implementations (InMemory, SQLite)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

import pytest

from asap.economics import (
    InMemorySLAStorage,
    SLABreach,
    SLAMetrics,
    SLAStorage,
    SQLiteSLAStorage,
)
from asap.economics.sla_storage import _parse_iso


def _metrics(
    agent_id: str = "urn:asap:agent:test",
    period_start: datetime | None = None,
    period_end: datetime | None = None,
) -> SLAMetrics:
    now = datetime.now(timezone.utc)
    start = period_start or (now - timedelta(hours=1))
    end = period_end or now
    return SLAMetrics(
        agent_id=agent_id,
        period_start=start,
        period_end=end,
        uptime_percent=99.5,
        latency_p95_ms=120,
        error_rate_percent=0.5,
        tasks_completed=100,
        tasks_failed=1,
    )


def _breach(
    breach_id: str = "breach_01",
    agent_id: str = "urn:asap:agent:test",
    detected_at: datetime | None = None,
    resolved_at: datetime | None = None,
) -> SLABreach:
    return SLABreach(
        id=breach_id,
        agent_id=agent_id,
        breach_type="latency",
        threshold="500ms",
        actual="600ms",
        severity="warning",
        detected_at=detected_at or datetime.now(timezone.utc),
        resolved_at=resolved_at,
    )


@pytest.fixture
def in_memory_sla_storage() -> InMemorySLAStorage:
    """Fresh InMemorySLAStorage per test."""
    return InMemorySLAStorage()


@pytest.fixture
def sqlite_sla_storage(tmp_path: Path) -> SQLiteSLAStorage:
    """Fresh SQLiteSLAStorage per test (isolated DB)."""
    return SQLiteSLAStorage(db_path=str(tmp_path / "sla.db"))


class TestSLAStorageProtocol:
    """SLAStorage protocol conformance."""

    def test_in_memory_implements_protocol(self) -> None:
        store = InMemorySLAStorage()
        assert isinstance(store, SLAStorage)

    def test_sqlite_implements_protocol(self, sqlite_sla_storage: SQLiteSLAStorage) -> None:
        assert isinstance(sqlite_sla_storage, SLAStorage)


class TestInMemorySLAStorage:
    """InMemorySLAStorage record, query, stats."""

    @pytest.mark.asyncio
    async def test_record_and_query_metrics(
        self, in_memory_sla_storage: InMemorySLAStorage
    ) -> None:
        m = _metrics()
        await in_memory_sla_storage.record_metrics(m)
        results = await in_memory_sla_storage.query_metrics()
        assert len(results) == 1
        assert results[0].agent_id == m.agent_id
        assert results[0].latency_p95_ms == 120

    @pytest.mark.asyncio
    async def test_query_metrics_filter_agent(
        self, in_memory_sla_storage: InMemorySLAStorage
    ) -> None:
        await in_memory_sla_storage.record_metrics(_metrics(agent_id="urn:asap:agent:a"))
        await in_memory_sla_storage.record_metrics(_metrics(agent_id="urn:asap:agent:b"))
        results = await in_memory_sla_storage.query_metrics(agent_id="urn:asap:agent:a")
        assert len(results) == 1
        assert results[0].agent_id == "urn:asap:agent:a"

    @pytest.mark.asyncio
    async def test_query_metrics_filter_time(
        self, in_memory_sla_storage: InMemorySLAStorage
    ) -> None:
        now = datetime.now(timezone.utc)
        start1 = now - timedelta(hours=5)
        end1 = now - timedelta(hours=4)
        start2 = now - timedelta(hours=3)
        end2 = now - timedelta(hours=2)
        await in_memory_sla_storage.record_metrics(_metrics(period_start=start1, period_end=end1))
        await in_memory_sla_storage.record_metrics(_metrics(period_start=start2, period_end=end2))
        # Query window 4:00-5:00: no metric overlaps (both periods end before 4:00) -> 0 results
        results_none = await in_memory_sla_storage.query_metrics(
            start=now - timedelta(hours=1),
            end=now,
        )
        assert len(results_none) == 0
        # Query window 0:30-1:30: only first period (0:00-1:00) overlaps
        results_one = await in_memory_sla_storage.query_metrics(
            start=now - timedelta(hours=4, minutes=30),
            end=now - timedelta(hours=3, minutes=30),
        )
        assert len(results_one) == 1
        assert results_one[0].period_start == start1

    @pytest.mark.asyncio
    async def test_query_metrics_pagination(
        self, in_memory_sla_storage: InMemorySLAStorage
    ) -> None:
        now = datetime.now(timezone.utc)
        for i in range(5):
            await in_memory_sla_storage.record_metrics(
                _metrics(period_start=now - timedelta(hours=5 - i))
            )

        # Page 1: limit=2, offset=0
        page1 = await in_memory_sla_storage.query_metrics(limit=2, offset=0)
        assert len(page1) == 2
        # Verify order: oldest first (now-5h, now-4h)
        assert page1[0].period_start < page1[1].period_start

        # Page 2: limit=2, offset=2
        page2 = await in_memory_sla_storage.query_metrics(limit=2, offset=2)
        assert len(page2) == 2
        assert page2[0].period_start > page1[1].period_start

        # Page 3: limit=2, offset=4 (partial page)
        page3 = await in_memory_sla_storage.query_metrics(limit=2, offset=4)
        assert len(page3) == 1
        assert page3[0].period_start > page2[1].period_start
        """Record breach; query_breaches returns it."""
        b = _breach()
        await in_memory_sla_storage.record_breach(b)
        results = await in_memory_sla_storage.query_breaches()
        assert len(results) == 1
        assert results[0].id == b.id
        assert results[0].breach_type == "latency"

    @pytest.mark.asyncio
    async def test_query_breaches_filter_agent(
        self, in_memory_sla_storage: InMemorySLAStorage
    ) -> None:
        await in_memory_sla_storage.record_breach(
            _breach(breach_id="b1", agent_id="urn:asap:agent:x")
        )
        await in_memory_sla_storage.record_breach(
            _breach(breach_id="b2", agent_id="urn:asap:agent:y")
        )
        results = await in_memory_sla_storage.query_breaches(agent_id="urn:asap:agent:x")
        assert len(results) == 1
        assert results[0].agent_id == "urn:asap:agent:x"

    @pytest.mark.asyncio
    async def test_stats(self, in_memory_sla_storage: InMemorySLAStorage) -> None:
        await in_memory_sla_storage.record_metrics(_metrics())
        await in_memory_sla_storage.record_breach(_breach())
        s = await in_memory_sla_storage.stats()
        assert s.total_events == 2
        assert s.oldest_timestamp is not None

    @pytest.mark.asyncio
    async def test_stats_empty(self, in_memory_sla_storage: InMemorySLAStorage) -> None:
        s = await in_memory_sla_storage.stats()
        assert s.total_events == 0
        assert s.oldest_timestamp is None


class TestSQLiteSLAStorage:
    """SQLiteSLAStorage record, query, stats (persistent)."""

    @pytest.mark.asyncio
    async def test_record_and_query_metrics(self, sqlite_sla_storage: SQLiteSLAStorage) -> None:
        m = _metrics()
        await sqlite_sla_storage.record_metrics(m)
        results = await sqlite_sla_storage.query_metrics()
        assert len(results) == 1
        assert results[0].agent_id == m.agent_id

    @pytest.mark.asyncio
    async def test_query_metrics_pagination(self, sqlite_sla_storage: SQLiteSLAStorage) -> None:
        now = datetime.now(timezone.utc)
        for i in range(5):
            await sqlite_sla_storage.record_metrics(
                _metrics(period_start=now - timedelta(hours=5 - i))
            )

        # Page 1: limit=2, offset=0
        page1 = await sqlite_sla_storage.query_metrics(limit=2, offset=0)
        assert len(page1) == 2
        assert page1[0].period_start < page1[1].period_start

        # Page 2: limit=2, offset=2
        page2 = await sqlite_sla_storage.query_metrics(limit=2, offset=2)
        assert len(page2) == 2
        assert page2[0].period_start > page1[1].period_start

        # Page 3: limit=2, offset=4 (partial page)
        page3 = await sqlite_sla_storage.query_metrics(limit=2, offset=4)
        assert len(page3) == 1
        assert page3[0].period_start > page2[1].period_start
        """Record breach; query_breaches returns it."""
        b = _breach()
        await sqlite_sla_storage.record_breach(b)
        results = await sqlite_sla_storage.query_breaches()
        assert len(results) == 1
        assert results[0].id == b.id

    @pytest.mark.asyncio
    async def test_persistence_across_connections(
        self, sqlite_sla_storage: SQLiteSLAStorage
    ) -> None:
        await sqlite_sla_storage.record_metrics(_metrics(agent_id="urn:asap:agent:persist"))
        # Same path, new instance
        store2 = SQLiteSLAStorage(db_path=sqlite_sla_storage._db_path)
        results = await store2.query_metrics(agent_id="urn:asap:agent:persist")
        assert len(results) == 1
        assert results[0].agent_id == "urn:asap:agent:persist"

    @pytest.mark.asyncio
    async def test_stats(self, sqlite_sla_storage: SQLiteSLAStorage) -> None:
        await sqlite_sla_storage.record_metrics(_metrics())
        await sqlite_sla_storage.record_breach(_breach())
        s = await sqlite_sla_storage.stats()
        assert s.total_events == 2
        assert s.oldest_timestamp is not None

    @pytest.mark.asyncio
    async def test_count_metrics(self, sqlite_sla_storage: SQLiteSLAStorage) -> None:
        await sqlite_sla_storage.record_metrics(_metrics(agent_id="a"))
        await sqlite_sla_storage.record_metrics(_metrics(agent_id="b"))
        assert await sqlite_sla_storage.count_metrics() == 2
        assert await sqlite_sla_storage.count_metrics(agent_id="a") == 1

        # Test time filters
        now = datetime.now(timezone.utc)
        # Filter that excludes everything (start in future)
        assert await sqlite_sla_storage.count_metrics(start=now + timedelta(hours=1)) == 0
        # Filter that includes everything
        assert await sqlite_sla_storage.count_metrics(end=now + timedelta(hours=1)) == 2

    @pytest.mark.asyncio
    async def test_query_metrics_offset_only(self, sqlite_sla_storage: SQLiteSLAStorage) -> None:
        now = datetime.now(timezone.utc)
        for i in range(5):
            await sqlite_sla_storage.record_metrics(
                _metrics(period_start=now - timedelta(hours=5 - i))
            )

        # skip first 2, expect remaining 3
        results = await sqlite_sla_storage.query_metrics(offset=2)
        assert len(results) == 3

    @pytest.mark.asyncio
    async def test_db_connection_error(self, sqlite_sla_storage: SQLiteSLAStorage) -> None:
        # Patch the aiosqlite.connect being used in sla_storage module
        with (
            patch("asap.economics.sla_storage.aiosqlite.connect", side_effect=OSError("DB Error")),
            pytest.raises(OSError, match="DB Error"),
        ):
            await sqlite_sla_storage.record_metrics(_metrics())


# ---------------------------------------------------------------------------
# SQLiteSLAStorage — additional coverage (filter paths)
# ---------------------------------------------------------------------------


class TestSQLiteSLAStorageCoverage:
    """Cover query_metrics/query_breaches with time filters and edge cases."""

    @pytest.mark.asyncio
    async def test_query_metrics_filter_agent(self, sqlite_sla_storage: SQLiteSLAStorage) -> None:
        await sqlite_sla_storage.record_metrics(_metrics(agent_id="urn:a"))
        await sqlite_sla_storage.record_metrics(_metrics(agent_id="urn:b"))
        results = await sqlite_sla_storage.query_metrics(agent_id="urn:a")
        assert len(results) == 1
        assert results[0].agent_id == "urn:a"

    @pytest.mark.asyncio
    async def test_query_metrics_filter_time_range(
        self, sqlite_sla_storage: SQLiteSLAStorage
    ) -> None:
        now = datetime.now(timezone.utc)
        s1 = now - timedelta(hours=5)
        e1 = now - timedelta(hours=4)
        s2 = now - timedelta(hours=2)
        e2 = now - timedelta(hours=1)
        await sqlite_sla_storage.record_metrics(_metrics(period_start=s1, period_end=e1))
        await sqlite_sla_storage.record_metrics(_metrics(period_start=s2, period_end=e2))

        # Query window 0:30-1:30 should only match first period
        results = await sqlite_sla_storage.query_metrics(
            start=now - timedelta(hours=4, minutes=30),
            end=now - timedelta(hours=3, minutes=30),
        )
        assert len(results) == 1

    @pytest.mark.asyncio
    async def test_query_breaches_filter_time_range(
        self, sqlite_sla_storage: SQLiteSLAStorage
    ) -> None:
        now = datetime.now(timezone.utc)
        early = now - timedelta(hours=12)
        late = now - timedelta(hours=1)
        await sqlite_sla_storage.record_breach(_breach(breach_id="b1", detected_at=early))
        await sqlite_sla_storage.record_breach(_breach(breach_id="b2", detected_at=late))

        results = await sqlite_sla_storage.query_breaches(
            start=now - timedelta(hours=13),
            end=now - timedelta(hours=6),
        )
        assert len(results) == 1
        assert results[0].id == "b1"

    @pytest.mark.asyncio
    async def test_query_breaches_filter_agent(self, sqlite_sla_storage: SQLiteSLAStorage) -> None:
        await sqlite_sla_storage.record_breach(_breach(breach_id="b1", agent_id="urn:x"))
        await sqlite_sla_storage.record_breach(_breach(breach_id="b2", agent_id="urn:y"))
        results = await sqlite_sla_storage.query_breaches(agent_id="urn:x")
        assert len(results) == 1
        assert results[0].agent_id == "urn:x"

    @pytest.mark.asyncio
    async def test_stats_empty(self, sqlite_sla_storage: SQLiteSLAStorage) -> None:
        s = await sqlite_sla_storage.stats()
        assert s.total_events == 0
        assert s.oldest_timestamp is None

    @pytest.mark.asyncio
    async def test_breach_with_resolved_at(self, sqlite_sla_storage: SQLiteSLAStorage) -> None:
        resolved = datetime.now(timezone.utc)
        await sqlite_sla_storage.record_breach(_breach(breach_id="b1", resolved_at=resolved))
        results = await sqlite_sla_storage.query_breaches()
        assert len(results) == 1
        assert results[0].resolved_at is not None

    @pytest.mark.asyncio
    async def test_query_breaches_filter_start_only(
        self, sqlite_sla_storage: SQLiteSLAStorage
    ) -> None:
        now = datetime.now(timezone.utc)
        early = now - timedelta(hours=12)
        late = now - timedelta(hours=1)
        await sqlite_sla_storage.record_breach(_breach(breach_id="b1", detected_at=early))
        await sqlite_sla_storage.record_breach(_breach(breach_id="b2", detected_at=late))
        results = await sqlite_sla_storage.query_breaches(
            start=now - timedelta(hours=6),
        )
        assert len(results) == 1
        assert results[0].id == "b2"

    @pytest.mark.asyncio
    async def test_query_metrics_filter_start_only(
        self, sqlite_sla_storage: SQLiteSLAStorage
    ) -> None:
        now = datetime.now(timezone.utc)
        s1 = now - timedelta(hours=6)
        e1 = now - timedelta(hours=5)
        s2 = now - timedelta(hours=2)
        e2 = now - timedelta(hours=1)
        await sqlite_sla_storage.record_metrics(_metrics(period_start=s1, period_end=e1))
        await sqlite_sla_storage.record_metrics(_metrics(period_start=s2, period_end=e2))
        results = await sqlite_sla_storage.query_metrics(
            start=now - timedelta(hours=3),
        )
        assert len(results) == 1


# ---------------------------------------------------------------------------
# _parse_iso edge cases
# ---------------------------------------------------------------------------


class TestParseIso:
    """Cover _parse_iso helper edge cases."""

    def test_parse_iso_none(self) -> None:
        assert _parse_iso(None) is None

    def test_parse_iso_empty(self) -> None:
        assert _parse_iso("") is None

    def test_parse_iso_invalid(self) -> None:
        assert _parse_iso("not-a-date") is None

    def test_parse_iso_z_suffix(self) -> None:
        result = _parse_iso("2026-01-01T00:00:00Z")
        assert result is not None

    def test_parse_iso_with_offset(self) -> None:
        result = _parse_iso("2026-01-01T00:00:00+00:00")
        assert result is not None


# ---------------------------------------------------------------------------
# InMemorySLAStorage — additional coverage (breach time filters)
# ---------------------------------------------------------------------------


class TestInMemorySLAStorageCoverage:
    @pytest.mark.asyncio
    async def test_query_breaches_filter_time_range(self) -> None:
        store = InMemorySLAStorage()
        now = datetime.now(timezone.utc)
        early = now - timedelta(hours=12)
        late = now - timedelta(hours=1)
        await store.record_breach(_breach(breach_id="b1", detected_at=early))
        await store.record_breach(_breach(breach_id="b2", detected_at=late))

        results = await store.query_breaches(
            start=now - timedelta(hours=5),
            end=now,
        )
        assert len(results) == 1
        assert results[0].id == "b2"
