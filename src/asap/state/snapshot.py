"""ASAP Snapshot Store for task state persistence.

This module provides interfaces and implementations for storing and retrieving
task state snapshots, enabling state persistence across agent restarts.

Example:
    >>> store = InMemorySnapshotStore()
    >>> store.list_versions("task_01HX5K4N...")
    []
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

    Example:
        >>> class CustomStore:
        ...     def save(self, snapshot: StateSnapshot) -> None:
        ...         pass
        ...     def get(self, task_id: TaskID, version: int | None = None) -> StateSnapshot | None:
        ...         return None
        ...     def list_versions(self, task_id: TaskID) -> list[int]:
        ...         return []
        ...     def delete(self, task_id: TaskID, version: int | None = None) -> bool:
        ...         return False
        >>> isinstance(CustomStore(), SnapshotStore)
        True
    """

    def save(self, snapshot: StateSnapshot) -> None:
        """Save a snapshot to the store.

        Args:
            snapshot: The snapshot to save

        Example:
            >>> from datetime import datetime, timezone
            >>> store = InMemorySnapshotStore()
            >>> snapshot = StateSnapshot(
            ...     id="snap_01HX5K7R...",
            ...     task_id="task_01HX5K4N...",
            ...     version=1,
            ...     data={"status": "submitted"},
            ...     created_at=datetime.now(timezone.utc),
            ... )
            >>> store.save(snapshot)
        """
        ...

    def get(self, task_id: TaskID, version: int | None = None) -> StateSnapshot | None:
        """Retrieve a snapshot for the given task.

        Args:
            task_id: The task ID to retrieve snapshots for
            version: Optional specific version to retrieve. If None, returns latest.

        Returns:
            The snapshot if found, None otherwise

        Example:
            >>> store = InMemorySnapshotStore()
            >>> store.get("task_01HX5K4N...")
            None
        """
        ...

    def list_versions(self, task_id: TaskID) -> list[int]:
        """List all available versions for a task.

        Args:
            task_id: The task ID to list versions for

        Returns:
            List of version numbers in ascending order

        Example:
            >>> store = InMemorySnapshotStore()
            >>> store.list_versions("task_01HX5K4N...")
            []
        """
        ...

    def delete(self, task_id: TaskID, version: int | None = None) -> bool:
        """Delete snapshot(s) for a task.

        Args:
            task_id: The task ID
            version: If provided, delete only this version. Otherwise delete all.

        Returns:
            True if any snapshots were deleted, False otherwise

        Example:
            >>> store = InMemorySnapshotStore()
            >>> store.delete("task_01HX5K4N...")
            False
        """
        ...


class InMemorySnapshotStore:
    """In-memory implementation of SnapshotStore.

    Stores snapshots in memory using dictionaries. Useful for testing
    and simple applications that don't require persistence across restarts.

    This implementation is thread-safe using RLock for concurrent access.
    """

    def __init__(self) -> None:
        """Initialize the in-memory snapshot store.

        Example:
            >>> store = InMemorySnapshotStore()
            >>> isinstance(store, InMemorySnapshotStore)
            True
        """
        self._lock = threading.RLock()
        # task_id -> version -> snapshot
        self._snapshots: dict[TaskID, dict[int, StateSnapshot]] = {}
        # task_id -> latest version
        self._latest_versions: dict[TaskID, int] = {}

    def save(self, snapshot: StateSnapshot) -> None:
        """Save a snapshot to the in-memory store.

        Args:
            snapshot: The snapshot to save

        Example:
            >>> from datetime import datetime, timezone
            >>> store = InMemorySnapshotStore()
            >>> snapshot = StateSnapshot(
            ...     id="snap_01HX5K7R...",
            ...     task_id="task_01HX5K4N...",
            ...     version=1,
            ...     data={"status": "submitted"},
            ...     created_at=datetime.now(timezone.utc),
            ... )
            >>> store.save(snapshot)
        """
        with self._lock:
            task_id = snapshot.task_id

            if task_id not in self._snapshots:
                self._snapshots[task_id] = {}

            self._snapshots[task_id][snapshot.version] = snapshot
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

        Example:
            >>> store = InMemorySnapshotStore()
            >>> store.get("task_01HX5K4N...")
            None
        """
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
        """List all available versions for a task.

        Args:
            task_id: The task ID to list versions for

        Returns:
            List of version numbers in ascending order

        Example:
            >>> store = InMemorySnapshotStore()
            >>> store.list_versions("task_01HX5K4N...")
            []
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

        Example:
            >>> store = InMemorySnapshotStore()
            >>> store.delete("task_01HX5K4N...")
            False
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
