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
from asap.economics.sla_storage import _parse_iso


def _metrics(
    agent_id: str = "urn:asap:agent:test",
    period_start: datetime | None = None,
    period_end: datetime | None = None,
) -> SLAMetrics:
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
        detected_at=detected_at or datetime(2026, 2, 18, 12, 0, 0, tzinfo=timezone.utc),
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
        """InMemorySLAStorage conforms to SLAStorage."""
        store = InMemorySLAStorage()
        assert isinstance(store, SLAStorage)

    def test_sqlite_implements_protocol(self, sqlite_sla_storage: SQLiteSLAStorage) -> None:
        """SQLiteSLAStorage conforms to SLAStorage."""
        assert isinstance(sqlite_sla_storage, SLAStorage)


class TestInMemorySLAStorage:
    """InMemorySLAStorage record, query, stats."""

    @pytest.mark.asyncio
    async def test_record_and_query_metrics(
        self, in_memory_sla_storage: InMemorySLAStorage
    ) -> None:
        """Record metrics; query returns them."""
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
        """query_metrics filters by agent_id."""
        await in_memory_sla_storage.record_metrics(_metrics(agent_id="urn:asap:agent:a"))
        await in_memory_sla_storage.record_metrics(_metrics(agent_id="urn:asap:agent:b"))
        results = await in_memory_sla_storage.query_metrics(agent_id="urn:asap:agent:a")
        assert len(results) == 1
        assert results[0].agent_id == "urn:asap:agent:a"

    @pytest.mark.asyncio
    async def test_query_metrics_filter_time(
        self, in_memory_sla_storage: InMemorySLAStorage
    ) -> None:
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
    async def test_record_and_query_breaches(
        self, in_memory_sla_storage: InMemorySLAStorage
    ) -> None:
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
        """query_breaches filters by agent_id."""
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
    async def test_persistence_across_connections(
        self, sqlite_sla_storage: SQLiteSLAStorage
    ) -> None:
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
        """query_metrics with start and end filters by overlapping periods."""
        s1 = datetime(2026, 2, 18, 0, 0, 0, tzinfo=timezone.utc)
        e1 = datetime(2026, 2, 18, 1, 0, 0, tzinfo=timezone.utc)
        s2 = datetime(2026, 2, 18, 4, 0, 0, tzinfo=timezone.utc)
        e2 = datetime(2026, 2, 18, 5, 0, 0, tzinfo=timezone.utc)
        await sqlite_sla_storage.record_metrics(_metrics(period_start=s1, period_end=e1))
        await sqlite_sla_storage.record_metrics(_metrics(period_start=s2, period_end=e2))

        # Query window 0:30-1:30 should only match first period
        results = await sqlite_sla_storage.query_metrics(
            start=datetime(2026, 2, 18, 0, 30, 0, tzinfo=timezone.utc),
            end=datetime(2026, 2, 18, 1, 30, 0, tzinfo=timezone.utc),
        )
        assert len(results) == 1

    @pytest.mark.asyncio
    async def test_query_breaches_filter_time_range(
        self, sqlite_sla_storage: SQLiteSLAStorage
    ) -> None:
        """query_breaches with start and end filters by detected_at."""
        early = datetime(2026, 2, 18, 6, 0, 0, tzinfo=timezone.utc)
        late = datetime(2026, 2, 18, 18, 0, 0, tzinfo=timezone.utc)
        await sqlite_sla_storage.record_breach(_breach(breach_id="b1", detected_at=early))
        await sqlite_sla_storage.record_breach(_breach(breach_id="b2", detected_at=late))

        results = await sqlite_sla_storage.query_breaches(
            start=datetime(2026, 2, 18, 5, 0, 0, tzinfo=timezone.utc),
            end=datetime(2026, 2, 18, 12, 0, 0, tzinfo=timezone.utc),
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
        """Breach with resolved_at persists and roundtrips correctly."""
        resolved = datetime(2026, 2, 18, 14, 0, 0, tzinfo=timezone.utc)
        await sqlite_sla_storage.record_breach(_breach(breach_id="b1", resolved_at=resolved))
        results = await sqlite_sla_storage.query_breaches()
        assert len(results) == 1
        assert results[0].resolved_at is not None

    @pytest.mark.asyncio
    async def test_query_breaches_filter_start_only(
        self, sqlite_sla_storage: SQLiteSLAStorage
    ) -> None:
        """query_breaches with only start filter."""
        early = datetime(2026, 2, 18, 6, 0, 0, tzinfo=timezone.utc)
        late = datetime(2026, 2, 18, 18, 0, 0, tzinfo=timezone.utc)
        await sqlite_sla_storage.record_breach(_breach(breach_id="b1", detected_at=early))
        await sqlite_sla_storage.record_breach(_breach(breach_id="b2", detected_at=late))
        results = await sqlite_sla_storage.query_breaches(
            start=datetime(2026, 2, 18, 12, 0, 0, tzinfo=timezone.utc),
        )
        assert len(results) == 1
        assert results[0].id == "b2"

    @pytest.mark.asyncio
    async def test_query_metrics_filter_start_only(
        self, sqlite_sla_storage: SQLiteSLAStorage
    ) -> None:
        """query_metrics with only start filter."""
        s1 = datetime(2026, 2, 18, 0, 0, 0, tzinfo=timezone.utc)
        e1 = datetime(2026, 2, 18, 1, 0, 0, tzinfo=timezone.utc)
        s2 = datetime(2026, 2, 18, 4, 0, 0, tzinfo=timezone.utc)
        e2 = datetime(2026, 2, 18, 5, 0, 0, tzinfo=timezone.utc)
        await sqlite_sla_storage.record_metrics(_metrics(period_start=s1, period_end=e1))
        await sqlite_sla_storage.record_metrics(_metrics(period_start=s2, period_end=e2))
        results = await sqlite_sla_storage.query_metrics(
            start=datetime(2026, 2, 18, 3, 0, 0, tzinfo=timezone.utc),
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
    """Cover query_breaches with time filters (start/end)."""

    @pytest.mark.asyncio
    async def test_query_breaches_filter_time_range(self) -> None:
        store = InMemorySLAStorage()
        early = datetime(2026, 2, 18, 6, 0, 0, tzinfo=timezone.utc)
        late = datetime(2026, 2, 18, 18, 0, 0, tzinfo=timezone.utc)
        await store.record_breach(_breach(breach_id="b1", detected_at=early))
        await store.record_breach(_breach(breach_id="b2", detected_at=late))

        results = await store.query_breaches(
            start=datetime(2026, 2, 18, 5, 0, 0, tzinfo=timezone.utc),
            end=datetime(2026, 2, 18, 12, 0, 0, tzinfo=timezone.utc),
        )
        assert len(results) == 1
        assert results[0].id == "b1"
