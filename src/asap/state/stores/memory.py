"""In-memory SnapshotStore and MeteringStore implementations.

InMemorySnapshotStore lives here; InMemoryMeteringStore is re-exported from
metering.py so that metering models stay in one place and avoid circular imports.
"""

from __future__ import annotations

import threading

from asap.models.entities import StateSnapshot
from asap.models.types import TaskID

from asap.state.metering import InMemoryMeteringStore


class InMemorySnapshotStore:
    """In-memory implementation of SnapshotStore.

    Stores snapshots in memory using dictionaries. Useful for testing
    and simple applications that don't require persistence across restarts.

    This implementation is thread-safe using RLock for concurrent access.
    """

    def __init__(self) -> None:
        """Initialize the in-memory snapshot store."""
        self._lock = threading.RLock()
        self._snapshots: dict[TaskID, dict[int, StateSnapshot]] = {}
        self._latest_versions: dict[TaskID, int] = {}

    def save(self, snapshot: StateSnapshot) -> None:
        """Save a snapshot to the in-memory store."""
        with self._lock:
            task_id = snapshot.task_id
            if task_id not in self._snapshots:
                self._snapshots[task_id] = {}
            self._snapshots[task_id][snapshot.version] = snapshot
            self._latest_versions[task_id] = max(
                self._latest_versions.get(task_id, 0), snapshot.version
            )

    def get(
        self,
        task_id: TaskID,
        version: int | None = None,
    ) -> StateSnapshot | None:
        """Retrieve a snapshot from the in-memory store."""
        with self._lock:
            if task_id not in self._snapshots:
                return None
            if version is None:
                latest_version = self._latest_versions.get(task_id)
                if latest_version is None:
                    return None
                return self._snapshots[task_id].get(latest_version)
            return self._snapshots[task_id].get(version)

    def list_versions(self, task_id: TaskID) -> list[int]:
        """List all available versions for a task."""
        with self._lock:
            if task_id not in self._snapshots:
                return []
            return sorted(self._snapshots[task_id].keys())

    def delete(self, task_id: TaskID, version: int | None = None) -> bool:
        """Delete snapshot(s) for a task."""
        with self._lock:
            if task_id not in self._snapshots:
                return False
            if version is None:
                del self._snapshots[task_id]
                if task_id in self._latest_versions:
                    del self._latest_versions[task_id]
                return True
            if version in self._snapshots[task_id]:
                del self._snapshots[task_id][version]
                if self._latest_versions.get(task_id) == version:
                    if self._snapshots[task_id]:
                        self._latest_versions[task_id] = max(self._snapshots[task_id].keys())
                    else:
                        del self._latest_versions[task_id]
                if not self._snapshots[task_id]:
                    del self._snapshots[task_id]
                    if task_id in self._latest_versions:
                        del self._latest_versions[task_id]
                return True
            return False


__all__ = [
    "InMemorySnapshotStore",
    "InMemoryMeteringStore",
]
