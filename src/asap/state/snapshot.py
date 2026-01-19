"""ASAP Snapshot Store for task state persistence.

This module provides interfaces and implementations for storing and retrieving
task state snapshots, enabling state persistence across agent restarts.
"""

import threading
from typing import Protocol, runtime_checkable

from asap.models.entities import StateSnapshot
from asap.models.types import TaskID


@runtime_checkable
class SnapshotStore(Protocol):
    """Protocol for snapshot storage implementations.

    Provides the interface for storing and retrieving task state snapshots.
    Implementations can use various backends (memory, database, file system, etc.).
    This uses Protocol for duck typing, allowing any class that implements
    these methods to be used as a SnapshotStore.
    """

    def save(self, snapshot: StateSnapshot) -> None:
        """Save a snapshot to the store.

        Args:
            snapshot: The snapshot to save
        """
        ...

    def get(self, task_id: TaskID, version: int | None = None) -> StateSnapshot | None:
        """Retrieve a snapshot for the given task.

        Args:
            task_id: The task ID to retrieve snapshots for
            version: Optional specific version to retrieve. If None, returns latest.

        Returns:
            The snapshot if found, None otherwise
        """
        ...

    def list_versions(self, task_id: TaskID) -> list[int]:
        """List all available versions for a task.

        Args:
            task_id: The task ID to list versions for

        Returns:
            List of version numbers in ascending order
        """
        ...

    def delete(self, task_id: TaskID, version: int | None = None) -> bool:
        """Delete snapshot(s) for a task.

        Args:
            task_id: The task ID
            version: If provided, delete only this version. Otherwise delete all.

        Returns:
            True if any snapshots were deleted, False otherwise
        """
        ...


class InMemorySnapshotStore:
    """In-memory implementation of SnapshotStore.

    Stores snapshots in memory using dictionaries. Useful for testing
    and simple applications that don't require persistence across restarts.

    This implementation is thread-safe using RLock for concurrent access.
    """

    def __init__(self) -> None:
        """Initialize the in-memory snapshot store."""
        self._lock = threading.RLock()
        # task_id -> version -> snapshot
        self._snapshots: dict[TaskID, dict[int, StateSnapshot]] = {}
        # task_id -> latest version
        self._latest_versions: dict[TaskID, int] = {}

    def save(self, snapshot: StateSnapshot) -> None:
        """Save a snapshot to the in-memory store.

        Args:
            snapshot: The snapshot to save
        """
        with self._lock:
            task_id = snapshot.task_id

            # Initialize storage for this task if needed
            if task_id not in self._snapshots:
                self._snapshots[task_id] = {}

            # Store the snapshot
            self._snapshots[task_id][snapshot.version] = snapshot

            # Update latest version
            self._latest_versions[task_id] = max(
                self._latest_versions.get(task_id, 0), snapshot.version
            )

    def get(self, task_id: TaskID, version: int | None = None) -> StateSnapshot | None:
        """Retrieve a snapshot from the in-memory store.

        Args:
            task_id: The task ID to retrieve snapshots for
            version: Optional specific version to retrieve. If None, returns latest.

        Returns:
            The snapshot if found, None otherwise
        """
        with self._lock:
            if task_id not in self._snapshots:
                return None

            if version is None:
                # Return latest version
                latest_version = self._latest_versions.get(task_id)
                if latest_version is None:
                    return None
                return self._snapshots[task_id].get(latest_version)

            # Return specific version
            return self._snapshots[task_id].get(version)

    def list_versions(self, task_id: TaskID) -> list[int]:
        """List all available versions for a task.

        Args:
            task_id: The task ID to list versions for

        Returns:
            List of version numbers in ascending order
        """
        with self._lock:
            if task_id not in self._snapshots:
                return []

            return sorted(self._snapshots[task_id].keys())

    def delete(self, task_id: TaskID, version: int | None = None) -> bool:
        """Delete snapshot(s) for a task.

        Args:
            task_id: The task ID
            version: If provided, delete only this version. Otherwise delete all.

        Returns:
            True if any snapshots were deleted, False otherwise
        """
        with self._lock:
            if task_id not in self._snapshots:
                return False

            if version is None:
                # Delete all versions for this task
                if task_id in self._snapshots:
                    del self._snapshots[task_id]
                    if task_id in self._latest_versions:
                        del self._latest_versions[task_id]
                    return True
                return False

            # Delete specific version
            if version in self._snapshots[task_id]:
                del self._snapshots[task_id][version]

                # Update latest version if needed
                if self._latest_versions.get(task_id) == version:
                    if self._snapshots[task_id]:
                        self._latest_versions[task_id] = max(self._snapshots[task_id].keys())
                    else:
                        del self._latest_versions[task_id]

                # Clean up empty task dict
                if not self._snapshots[task_id]:
                    del self._snapshots[task_id]
                    if task_id in self._latest_versions:
                        del self._latest_versions[task_id]

                return True

            return False
