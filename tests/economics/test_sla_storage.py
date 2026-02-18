"""Tests for SLAStorage implementations (InMemory, SQLite)."""

from datetime import datetime, timezone
from pathlib import Path

import pytest

from asap.economics import (
    InMemorySLAStorage,
    SLABreach,
    SLAMetrics,
    SLAStorage,
    SQLiteSLAStorage,
)


def _metrics(agent_id: str = "urn:asap:agent:test", period_start: datetime | None = None, period_end: datetime | None = None) -> SLAMetrics:
    start = period_start or datetime(2026, 2, 18, 0, 0, 0, tzinfo=timezone.utc)
    end = period_end or datetime(2026, 2, 18, 1, 0, 0, tzinfo=timezone.utc)
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


def _breach(breach_id: str = "breach_01", agent_id: str = "urn:asap:agent:test") -> SLABreach:
    return SLABreach(
        id=breach_id,
        agent_id=agent_id,
        breach_type="latency",
        threshold="500ms",
        actual="600ms",
        severity="warning",
        detected_at=datetime(2026, 2, 18, 12, 0, 0, tzinfo=timezone.utc),
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
        """InMemorySLAStorage conforms to SLAStorage."""
        store = InMemorySLAStorage()
        assert isinstance(store, SLAStorage)

    def test_sqlite_implements_protocol(self, sqlite_sla_storage: SQLiteSLAStorage) -> None:
        """SQLiteSLAStorage conforms to SLAStorage."""
        assert isinstance(sqlite_sla_storage, SLAStorage)


class TestInMemorySLAStorage:
    """InMemorySLAStorage record, query, stats."""

    @pytest.mark.asyncio
    async def test_record_and_query_metrics(self, in_memory_sla_storage: InMemorySLAStorage) -> None:
        """Record metrics; query returns them."""
        m = _metrics()
        await in_memory_sla_storage.record_metrics(m)
        results = await in_memory_sla_storage.query_metrics()
        assert len(results) == 1
        assert results[0].agent_id == m.agent_id
        assert results[0].latency_p95_ms == 120

    @pytest.mark.asyncio
    async def test_query_metrics_filter_agent(self, in_memory_sla_storage: InMemorySLAStorage) -> None:
        """query_metrics filters by agent_id."""
        await in_memory_sla_storage.record_metrics(_metrics(agent_id="urn:asap:agent:a"))
        await in_memory_sla_storage.record_metrics(_metrics(agent_id="urn:asap:agent:b"))
        results = await in_memory_sla_storage.query_metrics(agent_id="urn:asap:agent:a")
        assert len(results) == 1
        assert results[0].agent_id == "urn:asap:agent:a"

    @pytest.mark.asyncio
    async def test_query_metrics_filter_time(self, in_memory_sla_storage: InMemorySLAStorage) -> None:
        """query_metrics filters by start/end (overlapping periods included)."""
        start1 = datetime(2026, 2, 18, 0, 0, 0, tzinfo=timezone.utc)
        end1 = datetime(2026, 2, 18, 1, 0, 0, tzinfo=timezone.utc)
        start2 = datetime(2026, 2, 18, 2, 0, 0, tzinfo=timezone.utc)
        end2 = datetime(2026, 2, 18, 3, 0, 0, tzinfo=timezone.utc)
        await in_memory_sla_storage.record_metrics(_metrics(period_start=start1, period_end=end1))
        await in_memory_sla_storage.record_metrics(_metrics(period_start=start2, period_end=end2))
        # Query window 4:00-5:00: no metric overlaps (both periods end before 4:00) -> 0 results
        results_none = await in_memory_sla_storage.query_metrics(
            start=datetime(2026, 2, 18, 4, 0, 0, tzinfo=timezone.utc),
            end=datetime(2026, 2, 18, 5, 0, 0, tzinfo=timezone.utc),
        )
        assert len(results_none) == 0
        # Query window 0:30-1:30: only first period (0:00-1:00) overlaps
        results_one = await in_memory_sla_storage.query_metrics(
            start=datetime(2026, 2, 18, 0, 30, 0, tzinfo=timezone.utc),
            end=datetime(2026, 2, 18, 1, 30, 0, tzinfo=timezone.utc),
        )
        assert len(results_one) == 1
        assert results_one[0].period_start == start1

    @pytest.mark.asyncio
    async def test_record_and_query_breaches(self, in_memory_sla_storage: InMemorySLAStorage) -> None:
        """Record breach; query_breaches returns it."""
        b = _breach()
        await in_memory_sla_storage.record_breach(b)
        results = await in_memory_sla_storage.query_breaches()
        assert len(results) == 1
        assert results[0].id == b.id
        assert results[0].breach_type == "latency"

    @pytest.mark.asyncio
    async def test_query_breaches_filter_agent(self, in_memory_sla_storage: InMemorySLAStorage) -> None:
        """query_breaches filters by agent_id."""
        await in_memory_sla_storage.record_breach(_breach(breach_id="b1", agent_id="urn:asap:agent:x"))
        await in_memory_sla_storage.record_breach(_breach(breach_id="b2", agent_id="urn:asap:agent:y"))
        results = await in_memory_sla_storage.query_breaches(agent_id="urn:asap:agent:x")
        assert len(results) == 1
        assert results[0].agent_id == "urn:asap:agent:x"

    @pytest.mark.asyncio
    async def test_stats(self, in_memory_sla_storage: InMemorySLAStorage) -> None:
        """stats returns total_events and oldest_timestamp."""
        await in_memory_sla_storage.record_metrics(_metrics())
        await in_memory_sla_storage.record_breach(_breach())
        s = await in_memory_sla_storage.stats()
        assert s.total_events == 2
        assert s.oldest_timestamp is not None

    @pytest.mark.asyncio
    async def test_stats_empty(self, in_memory_sla_storage: InMemorySLAStorage) -> None:
        """stats with no data returns zeros."""
        s = await in_memory_sla_storage.stats()
        assert s.total_events == 0
        assert s.oldest_timestamp is None


class TestSQLiteSLAStorage:
    """SQLiteSLAStorage record, query, stats (persistent)."""

    @pytest.mark.asyncio
    async def test_record_and_query_metrics(self, sqlite_sla_storage: SQLiteSLAStorage) -> None:
        """Record metrics; query returns them."""
        m = _metrics()
        await sqlite_sla_storage.record_metrics(m)
        results = await sqlite_sla_storage.query_metrics()
        assert len(results) == 1
        assert results[0].agent_id == m.agent_id

    @pytest.mark.asyncio
    async def test_record_and_query_breaches(self, sqlite_sla_storage: SQLiteSLAStorage) -> None:
        """Record breach; query_breaches returns it."""
        b = _breach()
        await sqlite_sla_storage.record_breach(b)
        results = await sqlite_sla_storage.query_breaches()
        assert len(results) == 1
        assert results[0].id == b.id

    @pytest.mark.asyncio
    async def test_persistence_across_connections(self, sqlite_sla_storage: SQLiteSLAStorage) -> None:
        """Data persists; new instance sees same data (same db path)."""
        await sqlite_sla_storage.record_metrics(_metrics(agent_id="urn:asap:agent:persist"))
        # Same path, new instance
        store2 = SQLiteSLAStorage(db_path=sqlite_sla_storage._db_path)
        results = await store2.query_metrics(agent_id="urn:asap:agent:persist")
        assert len(results) == 1
        assert results[0].agent_id == "urn:asap:agent:persist"

    @pytest.mark.asyncio
    async def test_stats(self, sqlite_sla_storage: SQLiteSLAStorage) -> None:
        """stats returns counts and oldest timestamp."""
        await sqlite_sla_storage.record_metrics(_metrics())
        await sqlite_sla_storage.record_breach(_breach())
        s = await sqlite_sla_storage.stats()
        assert s.total_events == 2
        assert s.oldest_timestamp is not None
