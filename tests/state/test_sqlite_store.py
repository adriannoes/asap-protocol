"""Tests for SQLite SnapshotStore and MeteringStore."""

import threading
from datetime import datetime, timezone

import pytest

from asap.models.entities import StateSnapshot
from asap.state.metering import (
    MeteringStore,
    UsageAggregate,
    UsageEvent,
    UsageMetrics,
)
from asap.state.snapshot import SnapshotStore
from asap.state.stores.sqlite import SQLiteMeteringStore, SQLiteSnapshotStore


@pytest.fixture
def db_path(tmp_path):
    """Isolated DB file per test."""
    return tmp_path / "test_asap.db"


@pytest.fixture
def sqlite_snapshot_store(db_path) -> SQLiteSnapshotStore:
    """Fresh SQLiteSnapshotStore for each test."""
    return SQLiteSnapshotStore(db_path=db_path)


@pytest.fixture
def sqlite_metering_store(db_path) -> SQLiteMeteringStore:
    """Fresh SQLiteMeteringStore for each test (same DB path as snapshot store)."""
    return SQLiteMeteringStore(db_path=db_path)


@pytest.fixture
def sample_snapshot() -> StateSnapshot:
    """Sample StateSnapshot for tests."""
    return StateSnapshot(
        id="snap_01HX5K7R000000000000000000",
        task_id="task_01HX5K4N000000000000000000",
        version=1,
        data={"status": "working", "progress": 50},
        checkpoint=False,
        created_at=datetime.now(timezone.utc),
    )


@pytest.fixture
def sample_usage_event() -> UsageEvent:
    """Sample UsageEvent for tests."""
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


class TestSQLiteSnapshotStoreProtocol:
    """SQLiteSnapshotStore conforms to SnapshotStore protocol."""

    def test_implements_snapshot_store_protocol(
        self,
        sqlite_snapshot_store: SQLiteSnapshotStore,
    ) -> None:
        """SQLiteSnapshotStore is a SnapshotStore."""
        assert isinstance(sqlite_snapshot_store, SnapshotStore)


class TestSQLiteSnapshotStoreCRUD:
    """CRUD operations for SQLiteSnapshotStore."""

    def test_save_and_get(
        self,
        sqlite_snapshot_store: SQLiteSnapshotStore,
        sample_snapshot: StateSnapshot,
    ) -> None:
        """Save then get returns the same snapshot."""
        sqlite_snapshot_store.save(sample_snapshot)
        retrieved = sqlite_snapshot_store.get(
            sample_snapshot.task_id,
            sample_snapshot.version,
        )
        assert retrieved is not None
        assert retrieved.id == sample_snapshot.id
        assert retrieved.data == sample_snapshot.data
        assert retrieved.checkpoint == sample_snapshot.checkpoint

    def test_get_latest_when_no_version_specified(
        self,
        sqlite_snapshot_store: SQLiteSnapshotStore,
        sample_snapshot: StateSnapshot,
    ) -> None:
        """get(task_id) returns latest version."""
        sqlite_snapshot_store.save(sample_snapshot)
        v2 = StateSnapshot(
            id="snap_01HX5K7R000000000000000002",
            task_id=sample_snapshot.task_id,
            version=2,
            data={"step": 2},
            created_at=datetime.now(timezone.utc),
        )
        sqlite_snapshot_store.save(v2)
        latest = sqlite_snapshot_store.get(sample_snapshot.task_id, None)
        assert latest is not None
        assert latest.version == 2

    def test_list_versions(
        self,
        sqlite_snapshot_store: SQLiteSnapshotStore,
        sample_snapshot: StateSnapshot,
    ) -> None:
        """list_versions returns sorted version numbers."""
        sqlite_snapshot_store.save(sample_snapshot)
        v2 = StateSnapshot(
            id="snap_02",
            task_id=sample_snapshot.task_id,
            version=2,
            data={},
            created_at=datetime.now(timezone.utc),
        )
        sqlite_snapshot_store.save(v2)
        versions = sqlite_snapshot_store.list_versions(sample_snapshot.task_id)
        assert versions == [1, 2]

    def test_delete_specific_version(
        self,
        sqlite_snapshot_store: SQLiteSnapshotStore,
        sample_snapshot: StateSnapshot,
    ) -> None:
        """delete(task_id, version) removes only that version."""
        sqlite_snapshot_store.save(sample_snapshot)
        v2 = StateSnapshot(
            id="snap_02",
            task_id=sample_snapshot.task_id,
            version=2,
            data={},
            created_at=datetime.now(timezone.utc),
        )
        sqlite_snapshot_store.save(v2)
        deleted = sqlite_snapshot_store.delete(sample_snapshot.task_id, 1)
        assert deleted is True
        assert sqlite_snapshot_store.get(sample_snapshot.task_id, 1) is None
        assert sqlite_snapshot_store.get(sample_snapshot.task_id, 2) is not None

    def test_delete_all_versions(
        self,
        sqlite_snapshot_store: SQLiteSnapshotStore,
        sample_snapshot: StateSnapshot,
    ) -> None:
        """delete(task_id) removes all versions."""
        sqlite_snapshot_store.save(sample_snapshot)
        deleted = sqlite_snapshot_store.delete(sample_snapshot.task_id, None)
        assert deleted is True
        assert sqlite_snapshot_store.list_versions(sample_snapshot.task_id) == []

    def test_get_nonexistent_task_returns_none(
        self,
        sqlite_snapshot_store: SQLiteSnapshotStore,
    ) -> None:
        """get for unknown task_id returns None."""
        assert sqlite_snapshot_store.get("nonexistent_task", None) is None

    def test_list_versions_empty_for_nonexistent_task(
        self,
        sqlite_snapshot_store: SQLiteSnapshotStore,
    ) -> None:
        """list_versions for unknown task returns []."""
        assert sqlite_snapshot_store.list_versions("nonexistent") == []

    def test_delete_nonexistent_returns_false(
        self,
        sqlite_snapshot_store: SQLiteSnapshotStore,
    ) -> None:
        """delete for unknown task returns False."""
        assert sqlite_snapshot_store.delete("nonexistent", None) is False

    def test_sequential_operations_do_not_spawn_excessive_threads(
        self,
        sqlite_snapshot_store: SQLiteSnapshotStore,
        sample_snapshot: StateSnapshot,
    ) -> None:
        """Multiple sequential DB operations reuse shared executor; no per-call thread explosion."""
        initial_count = threading.active_count()
        for i in range(15):
            snap = StateSnapshot(
                id=f"snap_{i:02d}",
                task_id=sample_snapshot.task_id,
                version=sample_snapshot.version + i,
                data={"seq": i},
                checkpoint=False,
                created_at=datetime.now(timezone.utc),
            )
            sqlite_snapshot_store.save(snap)
            _ = sqlite_snapshot_store.get(snap.task_id, snap.version)
        final_count = threading.active_count()
        # Shared executor has max 4 workers; delta should be bounded (not 15+ new threads)
        assert final_count - initial_count <= 8


class TestSQLiteSnapshotStorePersistence:
    """Data persists across store re-creation (same db file)."""

    def test_data_survives_store_recreation(
        self,
        db_path,
        sample_snapshot: StateSnapshot,
    ) -> None:
        """Re-opening the same DB file returns saved data."""
        store1 = SQLiteSnapshotStore(db_path=db_path)
        store1.save(sample_snapshot)
        store2 = SQLiteSnapshotStore(db_path=db_path)
        retrieved = store2.get(sample_snapshot.task_id, sample_snapshot.version)
        assert retrieved is not None
        assert retrieved.id == sample_snapshot.id
        assert retrieved.data == sample_snapshot.data


class TestSQLiteMeteringStore:
    """SQLiteMeteringStore conforms to MeteringStore and record/query/aggregate work."""

    def test_implements_metering_store_protocol(
        self,
        sqlite_metering_store: SQLiteMeteringStore,
    ) -> None:
        """SQLiteMeteringStore is a MeteringStore."""
        assert isinstance(sqlite_metering_store, MeteringStore)

    def test_record_and_query(
        self,
        sqlite_metering_store: SQLiteMeteringStore,
        sample_usage_event: UsageEvent,
    ) -> None:
        """Record then query returns events in range."""
        sqlite_metering_store.record(sample_usage_event)
        start = datetime(2025, 2, 8, 11, 0, 0, tzinfo=timezone.utc)
        end = datetime(2025, 2, 8, 14, 0, 0, tzinfo=timezone.utc)
        events = sqlite_metering_store.query("agent_01", start, end)
        assert len(events) == 1
        assert events[0].task_id == sample_usage_event.task_id
        assert events[0].metrics.tokens_in == 10

    def test_aggregate_sums_metrics(
        self,
        sqlite_metering_store: SQLiteMeteringStore,
        sample_usage_event: UsageEvent,
    ) -> None:
        """Aggregate returns correct totals."""
        sqlite_metering_store.record(sample_usage_event)
        sqlite_metering_store.record(
            UsageEvent(
                task_id="task_02",
                agent_id="agent_01",
                consumer_id="c1",
                metrics=UsageMetrics(tokens_in=5, tokens_out=5, api_calls=2),
                timestamp=datetime(2025, 2, 8, 13, 0, 0, tzinfo=timezone.utc),
            )
        )
        agg = sqlite_metering_store.aggregate("agent_01", "day")
        assert isinstance(agg, UsageAggregate)
        assert agg.agent_id == "agent_01"
        assert agg.total_tokens == 10 + 20 + 5 + 5
        assert agg.total_tasks == 2
        assert agg.total_api_calls == 3

    def test_query_empty_returns_empty_list(
        self,
        sqlite_metering_store: SQLiteMeteringStore,
    ) -> None:
        """Query on empty store returns []."""
        start = datetime(2025, 1, 1, tzinfo=timezone.utc)
        end = datetime(2025, 12, 31, tzinfo=timezone.utc)
        assert sqlite_metering_store.query("any_agent", start, end) == []

    def test_aggregate_empty_returns_zeros(
        self,
        sqlite_metering_store: SQLiteMeteringStore,
    ) -> None:
        """Aggregate for agent with no events returns zero totals."""
        agg = sqlite_metering_store.aggregate("no_events", "day")
        assert agg.total_tokens == 0
        assert agg.total_tasks == 0
        assert agg.total_api_calls == 0
