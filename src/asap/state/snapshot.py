"""ASAP Snapshot Store for task state persistence.

This module provides interfaces and implementations for storing and retrieving
task state snapshots, enabling state persistence across agent restarts.

Example:
    >>> store = InMemorySnapshotStore()
    >>> store.list_versions("task_01HX5K4N...")
    []
"""

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


# Backward compatibility: implementation moved to stores.memory in 2.5.3
from asap.state.stores.memory import InMemorySnapshotStore  # noqa: E402

__all__ = ["SnapshotStore", "InMemorySnapshotStore"]
