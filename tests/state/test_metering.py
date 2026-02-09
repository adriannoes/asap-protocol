"""Tests for ASAP metering store (MeteringStore protocol and InMemoryMeteringStore)."""

import threading
from datetime import datetime, timezone

import pytest

from asap.state.metering import (
    InMemoryMeteringStore,
    MeteringStore,
    UsageAggregate,
    UsageEvent,
    UsageMetrics,
)


@pytest.fixture
def metering_store() -> InMemoryMeteringStore:
    """Create a fresh InMemoryMeteringStore for each test."""
    return InMemoryMeteringStore()


@pytest.fixture
def sample_event() -> UsageEvent:
    """Create a sample usage event for testing."""
    return UsageEvent(
        task_id="task_01",
        agent_id="agent_01",
        consumer_id="consumer_01",
        metrics=UsageMetrics(
            tokens_in=10,
            tokens_out=20,
            duration_ms=100,
            api_calls=1,
        ),
        timestamp=datetime(2025, 2, 8, 12, 0, 0, tzinfo=timezone.utc),
    )


class TestMeteringStoreProtocol:
    """Test MeteringStore protocol contract."""

    def test_metering_store_is_runtime_checkable(self) -> None:
        """MeteringStore is runtime_checkable for isinstance."""
        store = InMemoryMeteringStore()
        assert isinstance(store, MeteringStore)

    def test_protocol_methods_defined(self) -> None:
        """Protocol defines record, query, aggregate."""
        assert hasattr(MeteringStore, "record")
        assert hasattr(MeteringStore, "query")
        assert hasattr(MeteringStore, "aggregate")
        store = InMemoryMeteringStore()
        assert callable(store.record)
        assert callable(store.query)
        assert callable(store.aggregate)


class TestInMemoryMeteringStoreRecordAndQuery:
    """Test record and query behavior."""

    def test_record_and_query_returns_event(
        self,
        metering_store: InMemoryMeteringStore,
        sample_event: UsageEvent,
    ) -> None:
        """Record stores event; query returns it in range."""
        metering_store.record(sample_event)
        start = datetime(2025, 2, 8, 11, 0, 0, tzinfo=timezone.utc)
        end = datetime(2025, 2, 8, 14, 0, 0, tzinfo=timezone.utc)
        events = metering_store.query("agent_01", start, end)
        assert len(events) == 1
        assert events[0].task_id == sample_event.task_id
        assert events[0].metrics.tokens_in == 10
        assert events[0].metrics.tokens_out == 20

    def test_query_excludes_out_of_range(
        self,
        metering_store: InMemoryMeteringStore,
        sample_event: UsageEvent,
    ) -> None:
        """Query returns empty when time range does not include events."""
        metering_store.record(sample_event)
        start = datetime(2026, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
        end = datetime(2026, 1, 2, 0, 0, 0, tzinfo=timezone.utc)
        events = metering_store.query("agent_01", start, end)
        assert events == []

    def test_query_filters_by_agent_id(
        self,
        metering_store: InMemoryMeteringStore,
        sample_event: UsageEvent,
    ) -> None:
        """Query returns only events for the given agent_id."""
        metering_store.record(sample_event)
        start = datetime(2025, 2, 8, 0, 0, 0, tzinfo=timezone.utc)
        end = datetime(2025, 2, 9, 0, 0, 0, tzinfo=timezone.utc)
        assert len(metering_store.query("agent_01", start, end)) == 1
        assert len(metering_store.query("other_agent", start, end)) == 0

    def test_query_returns_sorted_by_timestamp(
        self,
        metering_store: InMemoryMeteringStore,
    ) -> None:
        """Query returns events ordered by timestamp ascending."""
        base = datetime(2025, 2, 8, 12, 0, 0, tzinfo=timezone.utc)
        metering_store.record(
            UsageEvent(
                task_id="t2",
                agent_id="a1",
                consumer_id="c1",
                timestamp=base,
                metrics=UsageMetrics(),
            )
        )
        metering_store.record(
            UsageEvent(
                task_id="t1",
                agent_id="a1",
                consumer_id="c1",
                timestamp=datetime(2025, 2, 8, 11, 0, 0, tzinfo=timezone.utc),
                metrics=UsageMetrics(),
            )
        )
        start = datetime(2025, 2, 8, 10, 0, 0, tzinfo=timezone.utc)
        end = datetime(2025, 2, 8, 14, 0, 0, tzinfo=timezone.utc)
        events = metering_store.query("a1", start, end)
        assert len(events) == 2
        assert events[0].task_id == "t1" and events[1].task_id == "t2"


class TestInMemoryMeteringStoreAggregate:
    """Test aggregation by period."""

    def test_aggregate_sums_metrics(
        self,
        metering_store: InMemoryMeteringStore,
        sample_event: UsageEvent,
    ) -> None:
        """Aggregate returns correct totals for the agent."""
        metering_store.record(sample_event)
        metering_store.record(
            UsageEvent(
                task_id="task_02",
                agent_id="agent_01",
                consumer_id="consumer_01",
                metrics=UsageMetrics(tokens_in=5, tokens_out=5, api_calls=2),
                timestamp=datetime(2025, 2, 8, 13, 0, 0, tzinfo=timezone.utc),
            )
        )
        agg = metering_store.aggregate("agent_01", "day")
        assert isinstance(agg, UsageAggregate)
        assert agg.agent_id == "agent_01"
        assert agg.period == "day"
        assert agg.total_tokens == 10 + 20 + 5 + 5
        assert agg.total_tasks == 2
        assert agg.total_api_calls == 1 + 2

    def test_aggregate_hour_period_label(
        self,
        metering_store: InMemoryMeteringStore,
        sample_event: UsageEvent,
    ) -> None:
        """Aggregate accepts period label 'hour'."""
        metering_store.record(sample_event)
        agg = metering_store.aggregate("agent_01", "hour")
        assert agg.period == "hour"
        assert agg.total_tasks == 1


class TestInMemoryMeteringStoreEmpty:
    """Test empty store behavior."""

    def test_query_empty_store_returns_empty_list(
        self,
        metering_store: InMemoryMeteringStore,
    ) -> None:
        """Query on empty store returns []."""
        start = datetime(2025, 1, 1, tzinfo=timezone.utc)
        end = datetime(2025, 12, 31, tzinfo=timezone.utc)
        assert metering_store.query("any_agent", start, end) == []

    def test_aggregate_empty_store_returns_zero_totals(
        self,
        metering_store: InMemoryMeteringStore,
    ) -> None:
        """Aggregate for agent with no events returns zero totals."""
        agg = metering_store.aggregate("no_events_agent", "day")
        assert agg.agent_id == "no_events_agent"
        assert agg.total_tokens == 0
        assert agg.total_tasks == 0
        assert agg.total_duration == 0
        assert agg.total_api_calls == 0


class TestInMemoryMeteringStoreThreadSafety:
    """Test thread-safe concurrent access."""

    def test_concurrent_record_and_query(
        self,
        metering_store: InMemoryMeteringStore,
    ) -> None:
        """Multiple threads can record and query without corruption."""
        errors: list[Exception] = []
        n_events = 50

        def record_events() -> None:
            try:
                for i in range(n_events):
                    metering_store.record(
                        UsageEvent(
                            task_id=f"t{i}",
                            agent_id="a1",
                            consumer_id="c1",
                            timestamp=datetime(2025, 2, 8, 12, i % 24, 0, tzinfo=timezone.utc),
                            metrics=UsageMetrics(tokens_in=i, tokens_out=i),
                        )
                    )
            except Exception as e:
                errors.append(e)

        def query_events() -> None:
            try:
                start = datetime(2025, 2, 8, 0, 0, 0, tzinfo=timezone.utc)
                end = datetime(2025, 2, 9, 0, 0, 0, tzinfo=timezone.utc)
                for _ in range(20):
                    metering_store.query("a1", start, end)
                    metering_store.aggregate("a1", "day")
            except Exception as e:
                errors.append(e)

        threads = [
            threading.Thread(target=record_events),
            threading.Thread(target=record_events),
            threading.Thread(target=query_events),
            threading.Thread(target=query_events),
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert not errors
        agg = metering_store.aggregate("a1", "day")
        assert agg.total_tasks == n_events * 2
