"""ASAP Snapshot Store for task state persistence.

This module provides interfaces and implementations for storing and retrieving
task state snapshots, enabling state persistence across agent restarts.

Example:
    >>> store = InMemorySnapshotStore()
    >>> store.list_versions("task_01HX5K4N...")
    []
"""

from __future__ import annotations

import os
import warnings
from pathlib import Path
from typing import Protocol, runtime_checkable

from asap.models.entities import StateSnapshot
from asap.models.types import TaskID


@runtime_checkable
class AsyncSnapshotStore(Protocol):
    """Async snapshot storage (:class:`SnapshotStore` methods as ``async def``).

    Runtime :func:`isinstance` does not distinguish sync vs coroutine callables;
    use :func:`inspect.iscoroutinefunction` when you require native async.
    """

    async def save(self, snapshot: StateSnapshot) -> None:
        """Persist a snapshot asynchronously."""
        ...

    async def get(self, task_id: TaskID, version: int | None = None) -> StateSnapshot | None:
        """Retrieve a snapshot; ``version`` None means latest."""
        ...

    async def list_versions(self, task_id: TaskID) -> list[int]:
        """List version numbers for ``task_id`` in ascending order."""
        ...

    async def delete(self, task_id: TaskID, version: int | None = None) -> bool:
        """Delete one version or all snapshots for ``task_id``."""
        ...


@runtime_checkable
@warnings.deprecated(
    "Use AsyncSnapshotStore for new async code paths; sync SnapshotStore "
    "remains for synchronous in-memory or threaded bridges.",
    category=DeprecationWarning,
)
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


def create_async_snapshot_store(
    backend: str = "sqlite",
    *,
    db_path: str | Path | None = None,
) -> AsyncSnapshotStore:
    """Build an :class:`AsyncSnapshotStore` (default ``sqlite``; ``memory`` for tests).

    ``db_path`` applies to sqlite only; if omitted, uses ``ASAP_STORAGE_PATH`` or
    ``asap_state.db``.
    """
    from asap.state.stores.memory import AsyncInMemorySnapshotStore
    from asap.state.stores.sqlite import SQLiteAsyncSnapshotStore

    key = backend.strip().lower()
    if key == "memory":
        return AsyncInMemorySnapshotStore()
    if key == "sqlite":
        path = (
            Path(db_path)
            if db_path is not None
            else Path(os.environ.get("ASAP_STORAGE_PATH", "asap_state.db").strip())
        )
        return SQLiteAsyncSnapshotStore(db_path=path)
    raise ValueError(
        f"Unknown async snapshot backend {backend!r}. Use 'memory' or 'sqlite'.",
    )


# Backward compatibility: implementation moved to stores.memory in 2.5.3
from asap.state.stores.memory import InMemorySnapshotStore  # noqa: E402

__all__ = [
    "AsyncSnapshotStore",
    "SnapshotStore",
    "create_async_snapshot_store",
    "InMemorySnapshotStore",
]
