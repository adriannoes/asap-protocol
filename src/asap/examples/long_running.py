"""Long-running task with checkpoints example for ASAP protocol.

This module demonstrates saving task state as snapshots and resuming after
a "crash" (e.g. process exit, failure). Use StateSnapshot and a SnapshotStore
to persist progress so work can continue from the last checkpoint.

Scenario:
    - A task runs in multiple steps (e.g. step 1, 2, 3, ...).
    - After each step we save a StateSnapshot to the store.
    - If the process crashes or stops, we can resume by loading the latest
      snapshot and continuing from the next step.

Run:
    uv run python -m asap.examples.long_running
    uv run python -m asap.examples.long_running --crash-after 2  # Simulate crash after step 2
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
from typing import Any, Protocol, Sequence, runtime_checkable

from asap.models.entities import StateSnapshot
from asap.models.ids import generate_id
from asap.models.types import TaskID
from asap.observability import get_logger
from asap.state.snapshot import InMemorySnapshotStore

logger = get_logger(__name__)

__all__ = [
    "KEY_COMPLETED",
    "KEY_PARTIAL_RESULT",
    "KEY_PROGRESS_PCT",
    "KEY_STEP",
    "InMemorySnapshotStore",
    "SnapshotStoreLike",
    "create_snapshot",
    "resume_from_store",
    "run_demo",
    "run_steps",
]

# Keys used in snapshot data for this example
KEY_STEP = "step"
KEY_PROGRESS_PCT = "progress_pct"
KEY_PARTIAL_RESULT = "partial_result"
KEY_COMPLETED = "completed"


@runtime_checkable
class SnapshotStoreLike(Protocol):
    """Minimal protocol for snapshot save/get (for type hints in this example)."""

    def save(self, snapshot: StateSnapshot) -> None: ...
    def get(self, task_id: TaskID, version: int | None = None) -> StateSnapshot | None: ...
    def list_versions(self, task_id: TaskID) -> list[int]: ...


def create_snapshot(
    task_id: str,
    version: int,
    step: int,
    progress_pct: int,
    partial_result: dict[str, Any],
    completed: bool = False,
    checkpoint: bool = True,
) -> StateSnapshot:
    """Build a StateSnapshot for the long-running task progress.

    Args:
        task_id: Parent task ID.
        version: Snapshot version (monotonically increasing).
        step: Current step number (1-based).
        progress_pct: Progress percentage (0–100).
        partial_result: Result data accumulated so far.
        completed: Whether the task is fully completed.
        checkpoint: Whether this snapshot is a significant checkpoint.

    Returns:
        StateSnapshot ready to save to a store.
    """
    return StateSnapshot(
        id=generate_id(),
        task_id=task_id,
        version=version,
        data={
            KEY_STEP: step,
            KEY_PROGRESS_PCT: progress_pct,
            KEY_PARTIAL_RESULT: partial_result,
            KEY_COMPLETED: completed,
        },
        checkpoint=checkpoint,
        created_at=datetime.now(timezone.utc),
    )


def run_steps(
    store: SnapshotStoreLike,
    task_id: str,
    num_steps: int,
    crash_after_step: int | None = None,
) -> StateSnapshot | None:
    """Run the long-running task: execute steps 1..num_steps and save a snapshot after each.

    If crash_after_step is set, stop after that step (simulating a crash).
    The latest snapshot remains in the store so the task can be resumed.

    Args:
        store: Snapshot store to persist state.
        task_id: Task identifier.
        num_steps: Total number of steps (e.g. 5).
        crash_after_step: If set, stop after this step (1-based). None = no crash.

    Returns:
        Latest snapshot after the run, or None if no step was executed.
    """
    partial_result: dict[str, Any] = {"items": [], "last_step": 0}
    last_snapshot: StateSnapshot | None = None

    for step in range(1, num_steps + 1):
        progress_pct = (step * 100) // num_steps
        partial_result["items"].append(f"result_step_{step}")
        partial_result["last_step"] = step

        completed = step == num_steps
        version = step
        snapshot = create_snapshot(
            task_id=task_id,
            version=version,
            step=step,
            progress_pct=progress_pct,
            partial_result=dict(partial_result),
            completed=completed,
            checkpoint=True,
        )
        store.save(snapshot)
        last_snapshot = snapshot
        logger.info(
            "asap.long_running.checkpoint",
            task_id=task_id,
            step=step,
            version=version,
            progress_pct=progress_pct,
        )

        if crash_after_step is not None and step >= crash_after_step:
            logger.warning(
                "asap.long_running.crash_simulated",
                task_id=task_id,
                after_step=step,
            )
            break

    return last_snapshot


def resume_from_store(
    store: SnapshotStoreLike,
    task_id: str,
    num_steps: int,
) -> StateSnapshot | None:
    """Resume a long-running task from the latest snapshot in the store.

    Loads the latest StateSnapshot for task_id, reads the last completed step,
    and runs from (step + 1) to num_steps, saving a snapshot after each step.

    Args:
        store: Snapshot store where state was persisted.
        task_id: Task identifier.
        num_steps: Total number of steps (must match original task).

    Returns:
        Latest snapshot after resume, or None if no previous snapshot or nothing left to do.
    """
    latest = store.get(task_id, version=None)
    if latest is None:
        logger.warning("asap.long_running.no_snapshot", task_id=task_id)
        return None

    data = latest.data
    last_step = data.get(KEY_STEP, 0)
    partial_result = dict(data.get(KEY_PARTIAL_RESULT, {"items": [], "last_step": 0}))

    if last_step >= num_steps:
        logger.info("asap.long_running.already_complete", task_id=task_id)
        return latest

    logger.info(
        "asap.long_running.resuming",
        task_id=task_id,
        from_step=last_step + 1,
        num_steps=num_steps,
    )

    last_snapshot: StateSnapshot | None = latest
    for step in range(last_step + 1, num_steps + 1):
        progress_pct = (step * 100) // num_steps
        partial_result["items"].append(f"result_step_{step}")
        partial_result["last_step"] = step
        completed = step == num_steps
        version = step
        snapshot = create_snapshot(
            task_id=task_id,
            version=version,
            step=step,
            progress_pct=progress_pct,
            partial_result=dict(partial_result),
            completed=completed,
            checkpoint=True,
        )
        store.save(snapshot)
        last_snapshot = snapshot
        logger.info(
            "asap.long_running.checkpoint",
            task_id=task_id,
            step=step,
            version=version,
            progress_pct=progress_pct,
        )

    return last_snapshot


def run_demo(
    num_steps: int = 5,
    crash_after_step: int | None = 2,
) -> None:
    """Run a full demo: execute until crash, then resume and complete.

    Args:
        num_steps: Total number of steps.
        crash_after_step: Step after which to simulate a crash (1-based). None = no crash.
    """
    store: InMemorySnapshotStore = InMemorySnapshotStore()
    task_id = generate_id()

    run_steps(store, task_id, num_steps, crash_after_step=crash_after_step)

    final = resume_from_store(store, task_id, num_steps)
    if final is None:
        raise SystemExit(1)
    if not final.data.get(KEY_COMPLETED, False):
        raise SystemExit(1)
    logger.info("asap.long_running.demo_complete", task_id=task_id, final_step=final.data[KEY_STEP])


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    """Parse command-line arguments for the long-running demo.

    Args:
        argv: Optional list of CLI arguments for testing.

    Returns:
        Parsed argparse namespace.
    """
    parser = argparse.ArgumentParser(
        description="Long-running task with checkpoints (save snapshot, resume after crash)."
    )
    parser.add_argument(
        "--num-steps",
        type=int,
        default=5,
        help="Total number of steps in the task.",
    )
    parser.add_argument(
        "--crash-after",
        type=int,
        default=2,
        metavar="N",
        help="Simulate crash after step N (1-based). Use 0 to disable crash.",
    )
    args = parser.parse_args(argv)
    if args.crash_after == 0:
        args.crash_after = None
    return args


def main(argv: Sequence[str] | None = None) -> None:
    """Run the long-running task demo: checkpoint, crash, resume."""
    args = parse_args(argv)
    run_demo(num_steps=args.num_steps, crash_after_step=args.crash_after)


if __name__ == "__main__":
    main()
