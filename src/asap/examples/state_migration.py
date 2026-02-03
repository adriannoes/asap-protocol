"""State migration example for ASAP protocol.

This module demonstrates moving task state between agents: export state
from one agent's SnapshotStore and import it into another, using
StateSnapshot, StateQuery, and StateRestore.

Scenario:
    - Agent A holds task state in its SnapshotStore.
    - We query/export the snapshot (get from store A).
    - We save it to Agent B's store (or send StateRestore to B if B has
      the snapshot by ID).

Run:
    uv run python -m asap.examples.state_migration
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
from typing import Any, Protocol, Sequence, runtime_checkable

from asap.models.entities import StateSnapshot
from asap.models.envelope import Envelope
from asap.models.ids import generate_id
from asap.models.payloads import StateQuery, StateRestore
from asap.models.types import TaskID
from asap.observability import get_logger
from asap.state.snapshot import InMemorySnapshotStore

logger = get_logger(__name__)

# URNs for source and target agents in the example
AGENT_A_ID = "urn:asap:agent:source"
AGENT_B_ID = "urn:asap:agent:target"


@runtime_checkable
class SnapshotStoreLike(Protocol):
    """Minimal protocol for get/save (for type hints in this example)."""

    def get(self, task_id: TaskID, version: int | None = None) -> StateSnapshot | None: ...
    def save(self, snapshot: StateSnapshot) -> None: ...


def build_state_query_envelope(
    task_id: str,
    version: int | None = None,
    sender_id: str = AGENT_B_ID,
    recipient_id: str = AGENT_A_ID,
) -> Envelope:
    """Build an ASAP envelope containing a StateQuery (request state from an agent).

    Args:
        task_id: Task whose state to query.
        version: Optional snapshot version; None = latest.
        sender_id: URN of the agent requesting state (e.g. target).
        recipient_id: URN of the agent that holds the state (e.g. source).

    Returns:
        Envelope with payload_type "state_query" and StateQuery payload.
    """
    payload = StateQuery(task_id=task_id, version=version)
    return Envelope(
        asap_version="0.1",
        sender=sender_id,
        recipient=recipient_id,
        payload_type="state_query",
        payload=payload.model_dump(),
        trace_id=generate_id(),
    )


def build_state_restore_envelope(
    task_id: str,
    snapshot_id: str,
    sender_id: str = AGENT_B_ID,
    recipient_id: str = AGENT_B_ID,
) -> Envelope:
    """Build an ASAP envelope containing a StateRestore (restore task from snapshot).

    Args:
        task_id: Task to restore.
        snapshot_id: Snapshot ID to restore from (must exist in recipient's store).
        sender_id: URN of the agent requesting restore.
        recipient_id: URN of the agent that will restore (e.g. target agent).

    Returns:
        Envelope with payload_type "state_restore" and StateRestore payload.
    """
    payload = StateRestore(task_id=task_id, snapshot_id=snapshot_id)
    return Envelope(
        asap_version="0.1",
        sender=sender_id,
        recipient=recipient_id,
        payload_type="state_restore",
        payload=payload.model_dump(),
        trace_id=generate_id(),
    )


def create_snapshot(
    task_id: str,
    version: int,
    data: dict[str, Any],
    checkpoint: bool = True,
) -> StateSnapshot:
    """Create a StateSnapshot for the example."""
    return StateSnapshot(
        id=generate_id(),
        task_id=task_id,
        version=version,
        data=data,
        checkpoint=checkpoint,
        created_at=datetime.now(timezone.utc),
    )


def move_state_between_agents(
    source_store: SnapshotStoreLike,
    target_store: SnapshotStoreLike,
    task_id: str,
    version: int | None = None,
    new_task_id: str | None = None,
) -> StateSnapshot | None:
    """Move task state from source agent's store to target agent's store.

    Exports the snapshot from source (get) and imports it into target (save).
    If new_task_id is set, the snapshot is saved under that task_id on the target
    (e.g. for "migrated" task identity); otherwise the same task_id is used.

    Args:
        source_store: Snapshot store of the source agent (Agent A).
        target_store: Snapshot store of the target agent (Agent B).
        task_id: Task ID to export from source.
        version: Snapshot version to export; None = latest.
        new_task_id: If set, save on target under this task_id; else use task_id.

    Returns:
        The snapshot that was saved to the target store, or None if not found on source.
    """
    snapshot = source_store.get(task_id, version=version)
    if snapshot is None:
        logger.warning(
            "asap.state_migration.no_snapshot",
            task_id=task_id,
            version=version,
        )
        return None

    target_task_id = new_task_id if new_task_id is not None else task_id
    # New snapshot instance for target (new id, same data) so target has its own record
    migrated = StateSnapshot(
        id=generate_id(),
        task_id=target_task_id,
        version=snapshot.version,
        data=dict(snapshot.data),
        checkpoint=snapshot.checkpoint,
        created_at=snapshot.created_at,
    )
    target_store.save(migrated)
    logger.info(
        "asap.state_migration.moved",
        source_task_id=task_id,
        target_task_id=target_task_id,
        snapshot_version=snapshot.version,
    )
    return migrated


def run_demo() -> None:
    """Run state migration demo: save state on agent A, move to agent B, verify."""
    source_store: InMemorySnapshotStore = InMemorySnapshotStore()
    target_store: InMemorySnapshotStore = InMemorySnapshotStore()

    task_id = generate_id()
    snapshot = create_snapshot(
        task_id=task_id,
        version=1,
        data={"step": "processing", "items_processed": 42, "agent": "A"},
    )
    source_store.save(snapshot)
    logger.info(
        "asap.state_migration.saved_on_source",
        task_id=task_id,
        snapshot_id=snapshot.id,
    )

    # Build StateQuery envelope (protocol-level: request state from Agent A)
    query_envelope = build_state_query_envelope(task_id=task_id)
    logger.info(
        "asap.state_migration.state_query_envelope",
        payload_type=query_envelope.payload_type,
        task_id=query_envelope.payload.get("task_id"),
    )

    # Move state from A to B (in-process: get from source, save to target)
    migrated = move_state_between_agents(source_store, target_store, task_id)
    if migrated is None:
        raise RuntimeError("State migration failed: no snapshot on source")

    # Build StateRestore envelope (protocol-level: tell Agent B to restore from snapshot)
    restore_envelope = build_state_restore_envelope(
        task_id=task_id,
        snapshot_id=migrated.id,
        recipient_id=AGENT_B_ID,
    )
    logger.info(
        "asap.state_migration.state_restore_envelope",
        payload_type=restore_envelope.payload_type,
        task_id=restore_envelope.payload.get("task_id"),
        snapshot_id=restore_envelope.payload.get("snapshot_id"),
    )

    restored = target_store.get(migrated.task_id, version=migrated.version)
    assert restored is not None
    assert restored.data == snapshot.data
    logger.info(
        "asap.state_migration.demo_complete",
        task_id=task_id,
        target_has_state=restored is not None,
    )


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    """Parse command-line arguments for the state migration demo."""
    parser = argparse.ArgumentParser(
        description="Move task state between agents (StateSnapshot, StateQuery, StateRestore)."
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> None:
    """Run the state migration demo."""
    parse_args(argv)
    run_demo()


if __name__ == "__main__":
    main()
