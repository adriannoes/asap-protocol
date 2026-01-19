"""Tests for ASAP snapshot store."""

import pytest
from datetime import datetime, timezone

from asap.models.entities import StateSnapshot
from asap.state.snapshot import InMemorySnapshotStore, SnapshotStore


@pytest.fixture
def snapshot_store() -> InMemorySnapshotStore:
    """Create a fresh InMemorySnapshotStore for each test."""
    return InMemorySnapshotStore()


@pytest.fixture
def sample_snapshot() -> StateSnapshot:
    """Create a sample snapshot for testing."""
    now = datetime.now(timezone.utc)
    return StateSnapshot(
        id="snap_01HX5K7R000000000000000000",
        task_id="task_01HX5K4N000000000000000000",
        version=1,
        data={"status": "working", "progress": 50},
        checkpoint=False,
        created_at=now,
    )


class TestSnapshotStoreInterface:
    """Test the SnapshotStore interface contract."""

    def test_snapshot_store_is_protocol(self) -> None:
        """Test that SnapshotStore is a Protocol."""
        from typing import runtime_checkable

        # Protocol should be runtime checkable
        assert hasattr(SnapshotStore, "__protocol_attrs__") or runtime_checkable(SnapshotStore)

    def test_protocol_methods_defined(self) -> None:
        """Test that protocol methods are properly defined."""
        # Check that the protocol methods exist
        assert hasattr(SnapshotStore, "save")
        assert hasattr(SnapshotStore, "get")
        assert hasattr(SnapshotStore, "list_versions")
        assert hasattr(SnapshotStore, "delete")

        # Check that concrete implementation implements protocol
        store = InMemorySnapshotStore()  # Use concrete implementation
        # These should work on concrete implementation
        assert callable(store.save)
        assert callable(store.get)
        assert callable(store.list_versions)
        assert callable(store.delete)

    def test_in_memory_store_implements_protocol(self) -> None:
        """Test that InMemorySnapshotStore implements SnapshotStore protocol."""
        store = InMemorySnapshotStore()
        # Runtime check should pass
        assert isinstance(store, SnapshotStore)


class TestInMemorySnapshotStore:
    """Test the InMemorySnapshotStore implementation."""

    def test_save_snapshot_stores_correctly(
        self, snapshot_store: InMemorySnapshotStore, sample_snapshot: StateSnapshot
    ) -> None:
        """Test that save() stores snapshots correctly."""
        snapshot_store.save(sample_snapshot)

        # Verify the snapshot was stored
        retrieved = snapshot_store.get(sample_snapshot.task_id, sample_snapshot.version)
        assert retrieved is not None
        assert retrieved.id == sample_snapshot.id
        assert retrieved.task_id == sample_snapshot.task_id
        assert retrieved.version == sample_snapshot.version
        assert retrieved.data == sample_snapshot.data
        assert retrieved.checkpoint == sample_snapshot.checkpoint

    def test_get_latest_snapshot_returns_most_recent(
        self, snapshot_store: InMemorySnapshotStore
    ) -> None:
        """Test that get(task_id) returns the latest snapshot."""
        task_id = "task_01HX5K4N000000000000000000"
        now = datetime.now(timezone.utc)

        # Create multiple snapshots for the same task
        snapshot_v1 = StateSnapshot(
            id="snap_01HX5K7R000000000000000001",
            task_id=task_id,
            version=1,
            data={"step": 1},
            created_at=now,
        )

        snapshot_v2 = StateSnapshot(
            id="snap_01HX5K7R000000000000000002",
            task_id=task_id,
            version=2,
            data={"step": 2},
            created_at=now,
        )

        snapshot_v3 = StateSnapshot(
            id="snap_01HX5K7R000000000000000003",
            task_id=task_id,
            version=3,
            data={"step": 3},
            created_at=now,
        )

        # Save them (not necessarily in order)
        snapshot_store.save(snapshot_v1)
        snapshot_store.save(snapshot_v3)
        snapshot_store.save(snapshot_v2)

        # Get latest (should be v3)
        latest = snapshot_store.get(task_id)
        assert latest is not None
        assert latest.version == 3
        assert latest.data["step"] == 3

    def test_get_specific_version_returns_correct_snapshot(
        self, snapshot_store: InMemorySnapshotStore
    ) -> None:
        """Test that get(task_id, version) returns the specific version."""
        task_id = "task_01HX5K4N000000000000000000"
        now = datetime.now(timezone.utc)

        # Create snapshots with different versions
        snapshot_v1 = StateSnapshot(
            id="snap_01HX5K7R000000000000000001",
            task_id=task_id,
            version=1,
            data={"step": 1},
            created_at=now,
        )

        snapshot_v2 = StateSnapshot(
            id="snap_01HX5K7R000000000000000002",
            task_id=task_id,
            version=2,
            data={"step": 2},
            created_at=now,
        )

        snapshot_store.save(snapshot_v1)
        snapshot_store.save(snapshot_v2)

        # Get specific versions
        retrieved_v1 = snapshot_store.get(task_id, 1)
        assert retrieved_v1 is not None
        assert retrieved_v1.version == 1
        assert retrieved_v1.data["step"] == 1

        retrieved_v2 = snapshot_store.get(task_id, 2)
        assert retrieved_v2 is not None
        assert retrieved_v2.version == 2
        assert retrieved_v2.data["step"] == 2

    def test_list_versions_returns_all_versions_for_task(
        self, snapshot_store: InMemorySnapshotStore
    ) -> None:
        """Test that list_versions(task_id) returns all versions."""
        task_id = "task_01HX5K4N000000000000000000"
        now = datetime.now(timezone.utc)

        # Create snapshots with versions 1, 3, 2 (out of order)
        snapshots = [
            StateSnapshot(
                id=f"snap_01HX5K7R00000000000000000{i}",
                task_id=task_id,
                version=version,
                data={"step": version},
                created_at=now,
            )
            for version, i in [(1, 1), (3, 3), (2, 2)]
        ]

        for snapshot in snapshots:
            snapshot_store.save(snapshot)

        # List versions should be sorted
        versions = snapshot_store.list_versions(task_id)
        assert versions == [1, 2, 3]

    def test_version_auto_increment_not_handled_by_store(
        self, snapshot_store: InMemorySnapshotStore
    ) -> None:
        """Test that the store doesn't auto-increment versions (that's handled by caller)."""
        task_id = "task_01HX5K4N000000000000000000"
        now = datetime.now(timezone.utc)

        # Save snapshots with manually set versions
        snapshot_v5 = StateSnapshot(
            id="snap_01HX5K7R000000000000000005",
            task_id=task_id,
            version=5,
            data={"manual_version": True},
            created_at=now,
        )

        snapshot_store.save(snapshot_v5)

        # Store just accepts whatever version is provided
        retrieved = snapshot_store.get(task_id, 5)
        assert retrieved is not None
        assert retrieved.version == 5

    def test_get_nonexistent_task_returns_none(self, snapshot_store: InMemorySnapshotStore) -> None:
        """Test that get() returns None for non-existent task."""
        nonexistent_task_id = "task_nonexistent"
        result = snapshot_store.get(nonexistent_task_id)
        assert result is None

    def test_get_nonexistent_version_returns_none(
        self, snapshot_store: InMemorySnapshotStore, sample_snapshot: StateSnapshot
    ) -> None:
        """Test that get() returns None for non-existent version."""
        snapshot_store.save(sample_snapshot)

        # Try to get a version that doesn't exist
        result = snapshot_store.get(sample_snapshot.task_id, 999)
        assert result is None

    def test_list_versions_empty_for_nonexistent_task(
        self, snapshot_store: InMemorySnapshotStore
    ) -> None:
        """Test that list_versions() returns empty list for non-existent task."""
        nonexistent_task_id = "task_nonexistent"
        versions = snapshot_store.list_versions(nonexistent_task_id)
        assert versions == []

    def test_multiple_tasks_isolation(self, snapshot_store: InMemorySnapshotStore) -> None:
        """Test that snapshots from different tasks are properly isolated."""
        now = datetime.now(timezone.utc)

        task_id_1 = "task_01HX5K4N000000000000000001"
        task_id_2 = "task_01HX5K4N000000000000000002"

        # Create snapshots for task 1
        snapshot_1 = StateSnapshot(
            id="snap_01HX5K7R000000000000000001",
            task_id=task_id_1,
            version=1,
            data={"task": 1},
            created_at=now,
        )

        # Create snapshots for task 2
        snapshot_2 = StateSnapshot(
            id="snap_01HX5K7R000000000000000002",
            task_id=task_id_2,
            version=1,
            data={"task": 2},
            created_at=now,
        )

        snapshot_store.save(snapshot_1)
        snapshot_store.save(snapshot_2)

        # Verify isolation
        retrieved_1 = snapshot_store.get(task_id_1)
        assert retrieved_1 is not None
        assert retrieved_1.data["task"] == 1

        retrieved_2 = snapshot_store.get(task_id_2)
        assert retrieved_2 is not None
        assert retrieved_2.data["task"] == 2

        # Versions should be separate
        versions_1 = snapshot_store.list_versions(task_id_1)
        versions_2 = snapshot_store.list_versions(task_id_2)
        assert versions_1 == [1]
        assert versions_2 == [1]

    def test_get_latest_when_no_snapshots_exist(
        self, snapshot_store: InMemorySnapshotStore, sample_snapshot: StateSnapshot
    ) -> None:
        """Test get() returns None when no snapshots exist for task."""
        # Save snapshot for one task
        snapshot_store.save(sample_snapshot)

        # Try to get latest for different task
        nonexistent_task_id = "task_nonexistent"
        result = snapshot_store.get(nonexistent_task_id)
        assert result is None

    def test_get_latest_when_task_has_no_versions(
        self, snapshot_store: InMemorySnapshotStore
    ) -> None:
        """Test get() returns None when task exists but has no versions."""
        # This edge case shouldn't happen in practice, but let's test it
        task_id = "task_empty"

        # Manually create empty dict for task (simulating corrupted state)
        snapshot_store._snapshots[task_id] = {}
        # But don't set latest version

        result = snapshot_store.get(task_id)
        assert result is None

    def test_list_versions_returns_empty_for_empty_task_dict(
        self, snapshot_store: InMemorySnapshotStore
    ) -> None:
        """Test list_versions() returns empty list when task dict exists but is empty."""
        task_id = "task_empty"
        snapshot_store._snapshots[task_id] = {}  # Empty dict

        versions = snapshot_store.list_versions(task_id)
        assert versions == []

    def test_delete_specific_version(
        self, snapshot_store: InMemorySnapshotStore, sample_snapshot: StateSnapshot
    ) -> None:
        """Test delete() removes specific version."""
        task_id = sample_snapshot.task_id
        now = datetime.now(timezone.utc)

        # Create multiple versions
        snapshot_v1 = StateSnapshot(
            id="snap_01HX5K7R000000000000000001",
            task_id=task_id,
            version=1,
            data={"step": 1},
            created_at=now,
        )
        snapshot_v2 = StateSnapshot(
            id="snap_01HX5K7R000000000000000002",
            task_id=task_id,
            version=2,
            data={"step": 2},
            created_at=now,
        )

        snapshot_store.save(snapshot_v1)
        snapshot_store.save(snapshot_v2)

        # Delete version 1
        result = snapshot_store.delete(task_id, version=1)
        assert result is True

        # Version 1 should be gone
        assert snapshot_store.get(task_id, version=1) is None
        # Version 2 should still exist
        assert snapshot_store.get(task_id, version=2) is not None
        # Latest should now be version 2
        assert snapshot_store.get(task_id).version == 2

    def test_delete_all_versions(
        self, snapshot_store: InMemorySnapshotStore, sample_snapshot: StateSnapshot
    ) -> None:
        """Test delete() removes all versions when version is None."""
        task_id = sample_snapshot.task_id
        now = datetime.now(timezone.utc)

        # Create multiple versions
        snapshot_v1 = StateSnapshot(
            id="snap_01HX5K7R000000000000000001",
            task_id=task_id,
            version=1,
            data={"step": 1},
            created_at=now,
        )
        snapshot_v2 = StateSnapshot(
            id="snap_01HX5K7R000000000000000002",
            task_id=task_id,
            version=2,
            data={"step": 2},
            created_at=now,
        )

        snapshot_store.save(snapshot_v1)
        snapshot_store.save(snapshot_v2)

        # Delete all versions
        result = snapshot_store.delete(task_id)
        assert result is True

        # All versions should be gone
        assert snapshot_store.get(task_id) is None
        assert snapshot_store.get(task_id, version=1) is None
        assert snapshot_store.get(task_id, version=2) is None
        assert snapshot_store.list_versions(task_id) == []

    def test_delete_nonexistent_task_returns_false(
        self, snapshot_store: InMemorySnapshotStore
    ) -> None:
        """Test delete() returns False for non-existent task."""
        result = snapshot_store.delete("task_nonexistent")
        assert result is False

    def test_delete_nonexistent_version_returns_false(
        self, snapshot_store: InMemorySnapshotStore, sample_snapshot: StateSnapshot
    ) -> None:
        """Test delete() returns False for non-existent version."""
        snapshot_store.save(sample_snapshot)

        result = snapshot_store.delete(sample_snapshot.task_id, version=999)
        assert result is False

        # Original snapshot should still exist
        assert snapshot_store.get(sample_snapshot.task_id) is not None

    def test_delete_preserves_other_tasks(self, snapshot_store: InMemorySnapshotStore) -> None:
        """Test delete() only affects the specified task."""
        now = datetime.now(timezone.utc)

        task_id_1 = "task_01HX5K4N000000000000000001"
        task_id_2 = "task_01HX5K4N000000000000000002"

        snapshot_1 = StateSnapshot(
            id="snap_01HX5K7R000000000000000001",
            task_id=task_id_1,
            version=1,
            data={"task": 1},
            created_at=now,
        )
        snapshot_2 = StateSnapshot(
            id="snap_01HX5K7R000000000000000002",
            task_id=task_id_2,
            version=1,
            data={"task": 2},
            created_at=now,
        )

        snapshot_store.save(snapshot_1)
        snapshot_store.save(snapshot_2)

        # Delete task 1
        snapshot_store.delete(task_id_1)

        # Task 1 should be gone
        assert snapshot_store.get(task_id_1) is None
        # Task 2 should still exist
        assert snapshot_store.get(task_id_2) is not None
        assert snapshot_store.get(task_id_2).data["task"] == 2
