"""Tests for MeteringStorage interface and implementations."""

from datetime import datetime, timedelta, timezone

import pytest

from asap.economics import (
    InMemoryMeteringStorage,
    MeteringQuery,
    SQLiteMeteringStorage,
    UsageMetrics,
)


@pytest.fixture
def in_memory_storage() -> InMemoryMeteringStorage:
    """Fresh InMemoryMeteringStorage for each test."""
    return InMemoryMeteringStorage()


@pytest.fixture
def sqlite_storage(tmp_path) -> SQLiteMeteringStorage:
    """Fresh SQLiteMeteringStorage for each test (isolated DB)."""
    return SQLiteMeteringStorage(db_path=str(tmp_path / "test_usage.db"))


@pytest.fixture
def sample_metrics() -> UsageMetrics:
    """Sample UsageMetrics for testing."""
    return UsageMetrics(
        task_id="task_01",
        agent_id="agent_01",
        consumer_id="consumer_01",
        tokens_in=10,
        tokens_out=20,
        duration_ms=100,
        api_calls=1,
        timestamp=datetime(2026, 2, 17, 12, 0, 0, tzinfo=timezone.utc),
    )


class TestMeteringStorageProtocol:
    """Test MeteringStorage protocol contract."""

    def test_in_memory_implements_protocol(self) -> None:
        """InMemoryMeteringStorage conforms to MeteringStorage."""
        from asap.economics.storage import MeteringStorage

        store = InMemoryMeteringStorage()
        assert isinstance(store, MeteringStorage)

    def test_sqlite_implements_protocol(self, sqlite_storage: SQLiteMeteringStorage) -> None:
        """SQLiteMeteringStorage conforms to MeteringStorage."""
        from asap.economics.storage import MeteringStorage

        assert isinstance(sqlite_storage, MeteringStorage)


class TestInMemoryMeteringStorageRecordAndQuery:
    """Test InMemoryMeteringStorage record and query."""

    def test_record_and_query_returns_metrics(
        self,
        in_memory_storage: InMemoryMeteringStorage,
        sample_metrics: UsageMetrics,
    ) -> None:
        """Record stores metrics; query returns them in range."""
        in_memory_storage.record(sample_metrics)
        start = datetime(2026, 2, 17, 11, 0, 0, tzinfo=timezone.utc)
        end = datetime(2026, 2, 17, 14, 0, 0, tzinfo=timezone.utc)
        results = in_memory_storage.query(MeteringQuery(start=start, end=end))
        assert len(results) == 1
        assert results[0].task_id == sample_metrics.task_id
        assert results[0].tokens_in == 10
        assert results[0].tokens_out == 20

    def test_query_filters_by_agent_id(
        self,
        in_memory_storage: InMemoryMeteringStorage,
        sample_metrics: UsageMetrics,
    ) -> None:
        """Query filters by agent_id when provided."""
        in_memory_storage.record(sample_metrics)
        start = datetime(2026, 2, 17, 0, 0, 0, tzinfo=timezone.utc)
        end = datetime(2026, 2, 18, 0, 0, 0, tzinfo=timezone.utc)
        assert (
            len(in_memory_storage.query(MeteringQuery(agent_id="agent_01", start=start, end=end)))
            == 1
        )
        assert (
            len(in_memory_storage.query(MeteringQuery(agent_id="other", start=start, end=end))) == 0
        )

    def test_query_filters_by_consumer_id(
        self,
        in_memory_storage: InMemoryMeteringStorage,
        sample_metrics: UsageMetrics,
    ) -> None:
        """Query filters by consumer_id when provided."""
        in_memory_storage.record(sample_metrics)
        start = datetime(2026, 2, 17, 0, 0, 0, tzinfo=timezone.utc)
        end = datetime(2026, 2, 18, 0, 0, 0, tzinfo=timezone.utc)
        assert (
            len(
                in_memory_storage.query(
                    MeteringQuery(consumer_id="consumer_01", start=start, end=end)
                )
            )
            == 1
        )
        assert (
            len(in_memory_storage.query(MeteringQuery(consumer_id="other", start=start, end=end)))
            == 0
        )

    def test_query_filters_by_task_id(
        self,
        in_memory_storage: InMemoryMeteringStorage,
        sample_metrics: UsageMetrics,
    ) -> None:
        """Query filters by task_id when provided."""
        in_memory_storage.record(sample_metrics)
        in_memory_storage.record(
            UsageMetrics(
                task_id="task_02",
                agent_id="agent_01",
                consumer_id="consumer_01",
                timestamp=datetime(2026, 2, 17, 13, 0, 0, tzinfo=timezone.utc),
            )
        )
        results = in_memory_storage.query(MeteringQuery(task_id="task_01"))
        assert len(results) == 1
        assert results[0].task_id == "task_01"
        assert len(in_memory_storage.query(MeteringQuery(task_id="nonexistent"))) == 0

    def test_query_pagination_limit_offset(
        self,
        in_memory_storage: InMemoryMeteringStorage,
    ) -> None:
        """Query respects limit and offset."""
        base = datetime(2026, 2, 17, 12, 0, 0, tzinfo=timezone.utc)
        for i in range(5):
            in_memory_storage.record(
                UsageMetrics(
                    task_id=f"t{i}",
                    agent_id="a1",
                    consumer_id="c1",
                    timestamp=base + timedelta(minutes=i),
                )
            )
        start = datetime(2026, 2, 17, 0, 0, 0, tzinfo=timezone.utc)
        end = datetime(2026, 2, 18, 0, 0, 0, tzinfo=timezone.utc)
        all_results = in_memory_storage.query(MeteringQuery(start=start, end=end))
        assert len(all_results) == 5
        limited = in_memory_storage.query(MeteringQuery(start=start, end=end, limit=2))
        assert len(limited) == 2
        offset_results = in_memory_storage.query(
            MeteringQuery(start=start, end=end, limit=2, offset=2)
        )
        assert len(offset_results) == 2
        assert offset_results[0].task_id == "t2"


class TestInMemoryMeteringStorageAggregate:
    """Test InMemoryMeteringStorage aggregation."""

    def test_aggregate_by_agent(
        self,
        in_memory_storage: InMemoryMeteringStorage,
        sample_metrics: UsageMetrics,
    ) -> None:
        """Aggregate by agent returns UsageAggregateByAgent."""
        in_memory_storage.record(sample_metrics)
        in_memory_storage.record(
            UsageMetrics(
                task_id="task_02",
                agent_id="agent_01",
                consumer_id="consumer_01",
                tokens_in=5,
                tokens_out=5,
                api_calls=2,
                timestamp=datetime(2026, 2, 17, 13, 0, 0, tzinfo=timezone.utc),
            )
        )
        aggs = in_memory_storage.aggregate("agent")
        assert len(aggs) == 1
        assert aggs[0].agent_id == "agent_01"
        assert aggs[0].total_tokens == 10 + 20 + 5 + 5
        assert aggs[0].total_tasks == 2
        assert aggs[0].total_api_calls == 3

    def test_aggregate_by_consumer(
        self,
        in_memory_storage: InMemoryMeteringStorage,
        sample_metrics: UsageMetrics,
    ) -> None:
        """Aggregate by consumer returns UsageAggregateByConsumer."""
        in_memory_storage.record(sample_metrics)
        in_memory_storage.record(
            UsageMetrics(
                task_id="task_02",
                agent_id="agent_02",
                consumer_id="consumer_01",
                tokens_in=1,
                tokens_out=1,
                timestamp=datetime(2026, 2, 17, 13, 0, 0, tzinfo=timezone.utc),
            )
        )
        aggs = in_memory_storage.aggregate("consumer")
        assert len(aggs) == 1
        assert aggs[0].consumer_id == "consumer_01"
        assert aggs[0].total_tokens == 10 + 20 + 1 + 1
        assert aggs[0].total_tasks == 2

    def test_aggregate_by_day(
        self,
        in_memory_storage: InMemoryMeteringStorage,
    ) -> None:
        """Aggregate by day groups by date."""
        in_memory_storage.record(
            UsageMetrics(
                task_id="t1",
                agent_id="a1",
                consumer_id="c1",
                tokens_in=10,
                tokens_out=10,
                timestamp=datetime(2026, 2, 17, 10, 0, 0, tzinfo=timezone.utc),
            )
        )
        in_memory_storage.record(
            UsageMetrics(
                task_id="t2",
                agent_id="a1",
                consumer_id="c1",
                tokens_in=20,
                tokens_out=20,
                timestamp=datetime(2026, 2, 17, 14, 0, 0, tzinfo=timezone.utc),
            )
        )
        in_memory_storage.record(
            UsageMetrics(
                task_id="t3",
                agent_id="a1",
                consumer_id="c1",
                tokens_in=5,
                tokens_out=5,
                timestamp=datetime(2026, 2, 18, 10, 0, 0, tzinfo=timezone.utc),
            )
        )
        aggs = in_memory_storage.aggregate("day")
        assert len(aggs) == 2
        by_period = {a.period: a for a in aggs}
        assert "2026-02-17" in by_period
        assert "2026-02-18" in by_period
        assert by_period["2026-02-17"].total_tokens == 60  # 10+10 + 20+20
        assert by_period["2026-02-18"].total_tokens == 10  # 5+5

    def test_aggregate_with_filters_scopes_by_time_range(
        self,
        in_memory_storage: InMemoryMeteringStorage,
    ) -> None:
        """Aggregate with start/end filters only includes events in range."""
        in_memory_storage.record(
            UsageMetrics(
                task_id="t1",
                agent_id="a1",
                consumer_id="c1",
                tokens_in=10,
                tokens_out=10,
                timestamp=datetime(2026, 2, 17, 12, 0, 0, tzinfo=timezone.utc),
            )
        )
        in_memory_storage.record(
            UsageMetrics(
                task_id="t2",
                agent_id="a1",
                consumer_id="c1",
                tokens_in=20,
                tokens_out=20,
                timestamp=datetime(2026, 2, 19, 12, 0, 0, tzinfo=timezone.utc),
            )
        )
        start = datetime(2026, 2, 17, 0, 0, 0, tzinfo=timezone.utc)
        end = datetime(2026, 2, 18, 0, 0, 0, tzinfo=timezone.utc)
        filters = MeteringQuery(start=start, end=end)
        aggs = in_memory_storage.aggregate("agent", filters=filters)
        assert len(aggs) == 1
        assert aggs[0].total_tokens == 20
        assert aggs[0].total_tasks == 1

    def test_aggregate_invalid_group_by_raises(
        self,
        in_memory_storage: InMemoryMeteringStorage,
    ) -> None:
        """Aggregate with invalid group_by raises ValueError."""
        with pytest.raises(ValueError, match="group_by must be one of"):
            in_memory_storage.aggregate("invalid")


class TestInMemoryMeteringStorageSummary:
    """Test InMemoryMeteringStorage summary."""

    def test_summary_empty_returns_zeros(
        self,
        in_memory_storage: InMemoryMeteringStorage,
    ) -> None:
        """Summary with no events returns all zeros."""
        s = in_memory_storage.summary()
        assert s.total_tasks == 0
        assert s.total_tokens == 0
        assert s.total_duration_ms == 0
        assert s.unique_agents == 0
        assert s.unique_consumers == 0
        assert s.total_api_calls == 0

    def test_summary_aggregates_totals(
        self,
        in_memory_storage: InMemoryMeteringStorage,
        sample_metrics: UsageMetrics,
    ) -> None:
        """Summary returns total_tasks, total_tokens, total_duration_ms, etc."""
        in_memory_storage.record(sample_metrics)
        in_memory_storage.record(
            UsageMetrics(
                task_id="task_02",
                agent_id="agent_02",
                consumer_id="consumer_01",
                tokens_in=5,
                tokens_out=15,
                duration_ms=200,
                api_calls=2,
                timestamp=datetime(2026, 2, 17, 13, 0, 0, tzinfo=timezone.utc),
            )
        )
        s = in_memory_storage.summary()
        assert s.total_tasks == 2
        assert s.total_tokens == 10 + 20 + 5 + 15
        assert s.total_duration_ms == 100 + 200
        assert s.unique_agents == 2
        assert s.unique_consumers == 1
        assert s.total_api_calls == 1 + 2

    def test_summary_with_filters_scopes_by_time_range(
        self,
        in_memory_storage: InMemoryMeteringStorage,
    ) -> None:
        """Summary with start/end filters only includes events in range."""
        in_memory_storage.record(
            UsageMetrics(
                task_id="t1",
                agent_id="a1",
                consumer_id="c1",
                tokens_in=10,
                tokens_out=20,
                duration_ms=100,
                timestamp=datetime(2026, 2, 17, 12, 0, 0, tzinfo=timezone.utc),
            )
        )
        in_memory_storage.record(
            UsageMetrics(
                task_id="t2",
                agent_id="a2",
                consumer_id="c1",
                tokens_in=5,
                tokens_out=5,
                duration_ms=50,
                timestamp=datetime(2026, 2, 19, 12, 0, 0, tzinfo=timezone.utc),
            )
        )
        start = datetime(2026, 2, 17, 0, 0, 0, tzinfo=timezone.utc)
        end = datetime(2026, 2, 18, 0, 0, 0, tzinfo=timezone.utc)
        s = in_memory_storage.summary(filters=MeteringQuery(start=start, end=end))
        assert s.total_tasks == 1
        assert s.total_tokens == 30
        assert s.total_duration_ms == 100
        assert s.unique_agents == 1
        assert s.unique_consumers == 1


class TestInMemoryMeteringStorageStats:
    """Test InMemoryMeteringStorage stats."""

    def test_stats_empty_returns_zeros(
        self,
        in_memory_storage: InMemoryMeteringStorage,
    ) -> None:
        """Stats with no events returns total_events=0, oldest_timestamp=None."""
        s = in_memory_storage.stats()
        assert s.total_events == 0
        assert s.oldest_timestamp is None
        assert s.retention_ttl_seconds is None

    def test_stats_with_events_returns_totals(
        self,
        in_memory_storage: InMemoryMeteringStorage,
        sample_metrics: UsageMetrics,
    ) -> None:
        """Stats returns total_events and oldest_timestamp."""
        in_memory_storage.record(sample_metrics)
        s = in_memory_storage.stats()
        assert s.total_events == 1
        assert s.oldest_timestamp == sample_metrics.timestamp

    def test_stats_with_retention_returns_ttl(
        self,
    ) -> None:
        """Stats returns retention_ttl_seconds when configured."""
        store = InMemoryMeteringStorage(retention_ttl_seconds=86400)
        s = store.stats()
        assert s.retention_ttl_seconds == 86400


class TestInMemoryMeteringStorageRetention:
    """Test InMemoryMeteringStorage retention policy."""

    def test_purge_expired_removes_old_events(self) -> None:
        """purge_expired removes events older than TTL."""
        store = InMemoryMeteringStorage(retention_ttl_seconds=3600)
        now = datetime.now(timezone.utc)
        old = now - timedelta(seconds=7200)
        store.record(UsageMetrics(task_id="old", agent_id="a1", consumer_id="c1", timestamp=old))
        store.record(UsageMetrics(task_id="new", agent_id="a1", consumer_id="c1", timestamp=now))
        removed = store.purge_expired()
        assert removed == 1
        results = store.query(MeteringQuery())
        assert len(results) == 1
        assert results[0].task_id == "new"

    def test_purge_expired_no_retention_returns_zero(self) -> None:
        """purge_expired with no retention configured returns 0."""
        store = InMemoryMeteringStorage()
        store.record(
            UsageMetrics(
                task_id="t1",
                agent_id="a1",
                consumer_id="c1",
                timestamp=datetime.now(timezone.utc),
            )
        )
        assert store.purge_expired() == 0


class TestSQLiteMeteringStorage:
    """Test SQLiteMeteringStorage operations."""

    def test_record_and_query(
        self,
        sqlite_storage: SQLiteMeteringStorage,
        sample_metrics: UsageMetrics,
    ) -> None:
        """Record then query returns metrics."""
        sqlite_storage.record(sample_metrics)
        start = datetime(2026, 2, 17, 11, 0, 0, tzinfo=timezone.utc)
        end = datetime(2026, 2, 17, 14, 0, 0, tzinfo=timezone.utc)
        results = sqlite_storage.query(MeteringQuery(start=start, end=end))
        assert len(results) == 1
        assert results[0].task_id == sample_metrics.task_id
        assert results[0].tokens_in == 10

    def test_aggregate_sums_metrics(
        self,
        sqlite_storage: SQLiteMeteringStorage,
        sample_metrics: UsageMetrics,
    ) -> None:
        """Aggregate returns correct totals."""
        sqlite_storage.record(sample_metrics)
        sqlite_storage.record(
            UsageMetrics(
                task_id="task_02",
                agent_id="agent_01",
                consumer_id="c1",
                tokens_in=5,
                tokens_out=5,
                api_calls=2,
                timestamp=datetime(2026, 2, 17, 13, 0, 0, tzinfo=timezone.utc),
            )
        )
        aggs = sqlite_storage.aggregate("agent")
        assert len(aggs) == 1
        assert aggs[0].total_tokens == 40
        assert aggs[0].total_tasks == 2
        assert aggs[0].total_api_calls == 3

    def test_query_empty_returns_empty_list(
        self,
        sqlite_storage: SQLiteMeteringStorage,
    ) -> None:
        """Query on empty store returns []."""
        results = sqlite_storage.query(MeteringQuery())
        assert results == []

    def test_aggregate_with_filters(
        self,
        sqlite_storage: SQLiteMeteringStorage,
    ) -> None:
        """SQLite aggregate with start/end filters scopes correctly."""
        sqlite_storage.record(
            UsageMetrics(
                task_id="t1",
                agent_id="a1",
                consumer_id="c1",
                tokens_in=10,
                tokens_out=10,
                timestamp=datetime(2026, 2, 17, 12, 0, 0, tzinfo=timezone.utc),
            )
        )
        sqlite_storage.record(
            UsageMetrics(
                task_id="t2",
                agent_id="a1",
                consumer_id="c1",
                tokens_in=20,
                tokens_out=20,
                timestamp=datetime(2026, 2, 19, 12, 0, 0, tzinfo=timezone.utc),
            )
        )
        start = datetime(2026, 2, 17, 0, 0, 0, tzinfo=timezone.utc)
        end = datetime(2026, 2, 18, 0, 0, 0, tzinfo=timezone.utc)
        filters = MeteringQuery(start=start, end=end)
        aggs = sqlite_storage.aggregate("agent", filters=filters)
        assert len(aggs) == 1
        assert aggs[0].total_tokens == 20
        assert aggs[0].total_tasks == 1

    def test_query_filters_by_task_id(
        self,
        sqlite_storage: SQLiteMeteringStorage,
        sample_metrics: UsageMetrics,
    ) -> None:
        """SQLite query filters by task_id."""
        sqlite_storage.record(sample_metrics)
        sqlite_storage.record(
            UsageMetrics(
                task_id="task_02",
                agent_id="agent_01",
                consumer_id="consumer_01",
                timestamp=datetime(2026, 2, 17, 13, 0, 0, tzinfo=timezone.utc),
            )
        )
        results = sqlite_storage.query(MeteringQuery(task_id="task_01"))
        assert len(results) == 1
        assert results[0].task_id == "task_01"

    def test_summary_returns_totals(
        self,
        sqlite_storage: SQLiteMeteringStorage,
        sample_metrics: UsageMetrics,
    ) -> None:
        """SQLite summary returns correct totals."""
        sqlite_storage.record(sample_metrics)
        sqlite_storage.record(
            UsageMetrics(
                task_id="task_02",
                agent_id="agent_02",
                consumer_id="consumer_01",
                tokens_in=5,
                tokens_out=15,
                duration_ms=200,
                api_calls=2,
                timestamp=datetime(2026, 2, 17, 13, 0, 0, tzinfo=timezone.utc),
            )
        )
        s = sqlite_storage.summary()
        assert s.total_tasks == 2
        assert s.total_tokens == 50
        assert s.total_duration_ms == 300
        assert s.unique_agents == 2
        assert s.unique_consumers == 1
        assert s.total_api_calls == 3

    def test_stats_returns_totals(
        self,
        sqlite_storage: SQLiteMeteringStorage,
        sample_metrics: UsageMetrics,
    ) -> None:
        """SQLite stats returns total_events and oldest_timestamp."""
        sqlite_storage.record(sample_metrics)
        s = sqlite_storage.stats()
        assert s.total_events == 1
        assert s.oldest_timestamp == sample_metrics.timestamp

    def test_purge_expired_removes_old_events(
        self,
        tmp_path,
    ) -> None:
        """purge_expired removes events older than TTL."""
        store = SQLiteMeteringStorage(
            db_path=str(tmp_path / "purge_test.db"),
            retention_ttl_seconds=3600,
        )
        now = datetime.now(timezone.utc)
        old = now - timedelta(seconds=7200)
        store.record(UsageMetrics(task_id="old", agent_id="a1", consumer_id="c1", timestamp=old))
        store.record(UsageMetrics(task_id="new", agent_id="a1", consumer_id="c1", timestamp=now))
        removed = store.purge_expired()
        assert removed == 1
        results = store.query(MeteringQuery())
        assert len(results) == 1
        assert results[0].task_id == "new"
