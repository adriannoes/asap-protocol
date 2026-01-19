"""ASAP Snapshot Store for task state persistence.

This module provides interfaces and implementations for storing and retrieving
task state snapshots, enabling state persistence across agent restarts.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional

from asap.models.entities import StateSnapshot
from asap.models.types import TaskID


class SnapshotStore(ABC):
    """Abstract base class for snapshot storage implementations.

    Provides the interface for storing and retrieving task state snapshots.
    Implementations can use various backends (memory, database, file system, etc.).
    """

    @abstractmethod
    def save(self, snapshot: StateSnapshot) -> None:
        """Save a snapshot to the store.

        Args:
            snapshot: The snapshot to save

        Raises:
            NotImplementedError: If not implemented by subclass
        """
        raise NotImplementedError

    @abstractmethod
    def get(self, task_id: TaskID, version: Optional[int] = None) -> Optional[StateSnapshot]:
        """Retrieve a snapshot for the given task.

        Args:
            task_id: The task ID to retrieve snapshots for
            version: Optional specific version to retrieve. If None, returns latest.

        Returns:
            The snapshot if found, None otherwise

        Raises:
            NotImplementedError: If not implemented by subclass
        """
        raise NotImplementedError

    @abstractmethod
    def list_versions(self, task_id: TaskID) -> List[int]:
        """List all available versions for a task.

        Args:
            task_id: The task ID to list versions for

        Returns:
            List of version numbers in ascending order

        Raises:
            NotImplementedError: If not implemented by subclass
        """
        raise NotImplementedError


class InMemorySnapshotStore(SnapshotStore):
    """In-memory implementation of SnapshotStore.

    Stores snapshots in memory using dictionaries. Useful for testing
    and simple applications that don't require persistence across restarts.
    """

    def __init__(self) -> None:
        """Initialize the in-memory snapshot store."""
        # task_id -> version -> snapshot
        self._snapshots: Dict[TaskID, Dict[int, StateSnapshot]] = {}
        # task_id -> latest version
        self._latest_versions: Dict[TaskID, int] = {}

    def save(self, snapshot: StateSnapshot) -> None:
        """Save a snapshot to the in-memory store.

        Args:
            snapshot: The snapshot to save
        """
        task_id = snapshot.task_id

        # Initialize storage for this task if needed
        if task_id not in self._snapshots:
            self._snapshots[task_id] = {}

        # Store the snapshot
        self._snapshots[task_id][snapshot.version] = snapshot

        # Update latest version
        self._latest_versions[task_id] = max(
            self._latest_versions.get(task_id, 0),
            snapshot.version
        )

    def get(self, task_id: TaskID, version: Optional[int] = None) -> Optional[StateSnapshot]:
        """Retrieve a snapshot from the in-memory store.

        Args:
            task_id: The task ID to retrieve snapshots for
            version: Optional specific version to retrieve. If None, returns latest.

        Returns:
            The snapshot if found, None otherwise
        """
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

    def list_versions(self, task_id: TaskID) -> List[int]:
        """List all available versions for a task.

        Args:
            task_id: The task ID to list versions for

        Returns:
            List of version numbers in ascending order
        """
        if task_id not in self._snapshots:
            return []

        return sorted(self._snapshots[task_id].keys())