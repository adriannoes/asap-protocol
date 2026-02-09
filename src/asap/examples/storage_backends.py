"""Storage backend selection example for ASAP protocol.

Demonstrates InMemory vs SQLite SnapshotStore and switching via environment:

    ASAP_STORAGE_BACKEND=memory  -> InMemorySnapshotStore (default, testing)
    ASAP_STORAGE_BACKEND=sqlite  -> SQLiteSnapshotStore (persistent)
    ASAP_STORAGE_PATH=/path/to/db  -> DB path when using sqlite

Run:
    uv run python -m asap.examples.storage_backends
    ASAP_STORAGE_BACKEND=sqlite ASAP_STORAGE_PATH=./demo.db uv run python -m asap.examples.storage_backends
"""

from __future__ import annotations

import os
from datetime import datetime, timezone

from asap.models.entities import StateSnapshot
from asap.state.stores import create_snapshot_store


def main() -> None:
    """Run a minimal save/get cycle with the configured store."""
    store = create_snapshot_store()
    task_id = "task_demo_01"
    snapshot = StateSnapshot(
        id="snap_demo_01",
        task_id=task_id,
        version=1,
        data={"example": True, "backend": os.environ.get("ASAP_STORAGE_BACKEND", "memory")},
        checkpoint=False,
        created_at=datetime.now(timezone.utc),
    )
    store.save(snapshot)
    retrieved = store.get(task_id, None)
    assert retrieved is not None
    print(f"Backend: {os.environ.get('ASAP_STORAGE_BACKEND', 'memory')}")
    print(f"Saved and retrieved task_id={task_id}, data={retrieved.data}")


if __name__ == "__main__":
    main()
