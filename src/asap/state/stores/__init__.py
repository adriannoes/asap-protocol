"""ASAP state storage backends.

This package provides SnapshotStore and MeteringStore implementations:
- InMemorySnapshotStore, AsyncInMemorySnapshotStore, InMemoryMeteringStore (from stores.memory)
- SQLiteAsyncSnapshotStore, SQLiteSnapshotStore, SQLiteMeteringStore (from stores.sqlite)

Factory:
- create_snapshot_store() — env ASAP_STORAGE_BACKEND / ASAP_STORAGE_PATH
- create_async_snapshot_store() — re-exported; default sqlite, optional memory
"""

import os
from pathlib import Path

from asap.state.snapshot import SnapshotStore, create_async_snapshot_store
from asap.state.stores.memory import (
    AsyncInMemorySnapshotStore,
    InMemoryMeteringStore,
    InMemorySnapshotStore,
)
from asap.state.stores.sqlite import (
    SQLiteAsyncSnapshotStore,
    SQLiteMeteringStore,
    SQLiteSnapshotStore,
)

ASAP_STORAGE_BACKEND_ENV = "ASAP_STORAGE_BACKEND"
ASAP_STORAGE_PATH_ENV = "ASAP_STORAGE_PATH"
DEFAULT_DB_PATH = "asap_state.db"


def create_snapshot_store() -> SnapshotStore:
    """Create a SnapshotStore from environment.

    Reads ASAP_STORAGE_BACKEND (default "memory") and ASAP_STORAGE_PATH
    (default "asap_state.db" for sqlite). Use "memory" for tests and
    "sqlite" for persistent state.

    Returns:
        Configured SnapshotStore instance.

    Raises:
        ValueError: If ASAP_STORAGE_BACKEND is not "memory" or "sqlite".
    """
    backend = os.environ.get(ASAP_STORAGE_BACKEND_ENV, "memory").strip().lower()
    path = os.environ.get(ASAP_STORAGE_PATH_ENV, DEFAULT_DB_PATH).strip()

    if backend == "memory":
        return InMemorySnapshotStore()
    if backend == "sqlite":
        return SQLiteSnapshotStore(db_path=Path(path))
    raise ValueError(f"Unknown {ASAP_STORAGE_BACKEND_ENV}={backend!r}. Use 'memory' or 'sqlite'.")


__all__ = [
    "AsyncInMemorySnapshotStore",
    "InMemorySnapshotStore",
    "InMemoryMeteringStore",
    "SQLiteAsyncSnapshotStore",
    "SQLiteSnapshotStore",
    "SQLiteMeteringStore",
    "create_async_snapshot_store",
    "create_snapshot_store",
]
