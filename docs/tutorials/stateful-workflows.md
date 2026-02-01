# Stateful Workflows

**Time:** ~20 minutes | **Level:** Intermediate

This tutorial shows how to build long-running tasks that save state and resume after crashes. You will use `StateSnapshot` and `SnapshotStore` to persist progress and pick up where you left off.

**Prerequisites:** [Building Your First Agent](first-agent.md)

---

## Why Stateful Workflows?

Long-running tasks (e.g. batch processing, multi-step pipelines) can fail or be interrupted:

- Process crash or restart
- Pod eviction in Kubernetes
- Network timeout or connection drop

Without state persistence, you restart from scratch. With snapshots, you save progress at checkpoints and resume from the last known good state.

---

## Concepts

### StateSnapshot

A `StateSnapshot` captures task state at a point in time:

```python
from datetime import datetime, timezone
from asap.models.entities import StateSnapshot
from asap.models.ids import generate_id

snapshot = StateSnapshot(
    id=generate_id(),
    task_id="task_01HX5K4N...",
    version=1,
    data={"step": 2, "results": ["item_1", "item_2"], "completed": False},
    checkpoint=True,  # Mark significant milestone
    created_at=datetime.now(timezone.utc),
)
```

- **version**: Monotonically increasing; used for ordering and rollback.
- **data**: JSON-serializable dict with your task state.
- **checkpoint**: Flag for important states (e.g. phase completion).

### SnapshotStore

The store persists snapshots. ASAP provides `InMemorySnapshotStore` for development:

```python
from asap.state.snapshot import InMemorySnapshotStore

store = InMemorySnapshotStore()
store.save(snapshot)
latest = store.get("task_01HX5K4N...")
versions = store.list_versions("task_01HX5K4N...")
```

For production, implement the `SnapshotStore` protocol with Redis, PostgreSQL, or your backend. See [State Management Guide](../state-management.md#creating-custom-stores).

---

## Step 1: Run the Long-Running Demo

ASAP includes a demo that simulates a crash and resume:

```bash
uv run python -m asap.examples.long_running --num-steps 5 --crash-after 2
```

**What happens:**

1. Task runs 5 steps; a snapshot is saved after each step.
2. After step 2, the demo "crashes" (exits).
3. The process restarts and resumes from the last snapshot (step 2).
4. Steps 3–5 run and the task completes.

Check the logs to see checkpoint saves and the resume.

---

## Step 2: Build a Simple Stateful Task

Create `my_long_task.py`:

```python
from datetime import datetime, timezone

from asap.models.entities import StateSnapshot
from asap.models.ids import generate_id
from asap.state.snapshot import InMemorySnapshotStore


def run_task(store: InMemorySnapshotStore, task_id: str, num_steps: int) -> StateSnapshot | None:
    """Run a multi-step task, saving a snapshot after each step."""
    partial = {"items": [], "step": 0}

    for step in range(1, num_steps + 1):
        # Simulate work
        partial["items"].append(f"result_{step}")
        partial["step"] = step
        completed = step == num_steps

        snapshot = StateSnapshot(
            id=generate_id(),
            task_id=task_id,
            version=step,
            data={**partial, "completed": completed},
            checkpoint=True,
            created_at=datetime.now(timezone.utc),
        )
        store.save(snapshot)

    return store.get(task_id)


if __name__ == "__main__":
    store = InMemorySnapshotStore()
    task_id = generate_id()
    run_task(store, task_id, 5)
    latest = store.get(task_id)
    print("Final state:", latest.data if latest else None)
```

Run it: `uv run python my_long_task.py`

---

## Step 3: Simulate Crash and Resume

Extend the script to stop after a step (simulate crash) and resume:

```python
def run_task(
    store: InMemorySnapshotStore,
    task_id: str,
    num_steps: int,
    crash_after: int | None = None,
) -> StateSnapshot | None:
    """Run steps 1..num_steps; stop after crash_after (simulate crash)."""
    partial = {"items": [], "step": 0}

    for step in range(1, num_steps + 1):
        partial["items"].append(f"result_{step}")
        partial["step"] = step
        completed = step == num_steps

        snapshot = StateSnapshot(
            id=generate_id(),
            task_id=task_id,
            version=step,
            data={**partial, "completed": completed},
            checkpoint=True,
            created_at=datetime.now(timezone.utc),
        )
        store.save(snapshot)

        if crash_after is not None and step >= crash_after:
            print(f"Simulated crash after step {step}")
            break

    return store.get(task_id)


def resume_task(
    store: InMemorySnapshotStore,
    task_id: str,
    num_steps: int,
) -> StateSnapshot | None:
    """Resume from the latest snapshot and complete remaining steps."""
    latest = store.get(task_id)
    if latest is None:
        return None

    last_step = latest.data.get("step", 0)
    if last_step >= num_steps:
        return latest

    partial = {
        "items": list(latest.data.get("items", [])),
        "step": last_step,
    }

    for step in range(last_step + 1, num_steps + 1):
        partial["items"].append(f"result_{step}")
        partial["step"] = step
        completed = step == num_steps

        snapshot = StateSnapshot(
            id=generate_id(),
            task_id=task_id,
            version=step,
            data={**partial, "completed": completed},
            checkpoint=True,
            created_at=datetime.now(timezone.utc),
        )
        store.save(snapshot)

    return store.get(task_id)


if __name__ == "__main__":
    store = InMemorySnapshotStore()
    task_id = generate_id()

    # Phase 1: run until crash
    run_task(store, task_id, 5, crash_after=2)

    # Phase 2: resume and complete
    final = resume_task(store, task_id, 5)
    print("Final state:", final.data if final else None)
```

This pattern: **save after each step → simulate crash → resume from latest snapshot** is the core of stateful workflows.

---

## Step 4: Use the Built-in Example

The `long_running` example uses the same pattern with structured helpers:

```python
from asap.examples.long_running import run_steps, resume_from_store
from asap.state.snapshot import InMemorySnapshotStore

store = InMemorySnapshotStore()
task_id = "task_01HX5K4N..."

# Run until step 2, then "crash"
run_steps(store, task_id, num_steps=5, crash_after_step=2)

# Resume and complete
final = resume_from_store(store, task_id, num_steps=5)
```

---

## Best Practices

1. **Checkpoint at logical boundaries** — After each phase or batch, not every tiny operation.
2. **Keep snapshots lean** — Store only essential state; avoid large or derived data.
3. **Use version numbers** — Increment versions so you can reason about ordering and rollback.
4. **Use a persistent store in production** — `InMemorySnapshotStore` loses data on restart; use Redis, PostgreSQL, etc.

---

## Next Steps

- [Multi-Agent Orchestration](multi-agent.md) — Coordinate multiple agents
- [Building Resilient Agents](resilience.md) — Retries, circuit breakers, recovery
- [State Management Guide](../state-management.md) — Task lifecycle, custom stores
