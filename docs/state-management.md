# State Management Guide

> Task lifecycle, state machine, and snapshot persistence in the ASAP protocol.

---

## Overview

ASAP provides first-class state management through:

- **Task State Machine**: Defines valid task statuses and transitions
- **State Snapshots**: Persistent checkpoints for resumable tasks
- **Versioned History**: Track state evolution over time

This addresses a key limitation in other agent protocols where task state is often ephemeral.

---

## Task Lifecycle

### Task Statuses

Every task in ASAP has a well-defined status from the `TaskStatus` enum:

| Status | Description | Terminal |
|--------|-------------|----------|
| `SUBMITTED` | Task received, awaiting processing | No |
| `WORKING` | Task actively being processed | No |
| `INPUT_REQUIRED` | Waiting for additional input from requester | No |
| `COMPLETED` | Task finished successfully | Yes |
| `FAILED` | Task encountered an error | Yes |
| `CANCELLED` | Task was cancelled by request | Yes |

```python
from asap.models.enums import TaskStatus

# Check if task is in a terminal state
status = TaskStatus.COMPLETED
print(status.is_terminal())  # True

# Get all terminal states
terminal = TaskStatus.terminal_states()
print(terminal)  # frozenset({COMPLETED, FAILED, CANCELLED})
```

### State Transition Diagram

```
                    ┌─────────────────────────────────────────────────────┐
                    │                                                     │
                    ▼                                                     │
┌─────────────┐ ──────────► ┌─────────────┐ ──────────► ┌─────────────┐  │
│  SUBMITTED  │             │   WORKING   │             │  COMPLETED  │  │
└─────────────┘             └─────────────┘             └─────────────┘  │
       │                           │                                      │
       │                           ├────────────► ┌─────────────┐        │
       │                           │              │    FAILED   │        │
       │                           │              └─────────────┘        │
       │                           │                                      │
       │                           ├────────────► ┌─────────────────┐    │
       │                           │              │ INPUT_REQUIRED  │────┘
       │                           │              └─────────────────┘
       │                           │                      │
       │                           ▼                      │
       │                    ┌─────────────┐               │
       └──────────────────► │  CANCELLED  │ ◄─────────────┘
                            └─────────────┘
```

### Valid Transitions

The state machine enforces these transition rules:

| From Status | Valid Target Statuses |
|-------------|----------------------|
| `SUBMITTED` | `WORKING`, `CANCELLED` |
| `WORKING` | `COMPLETED`, `FAILED`, `CANCELLED`, `INPUT_REQUIRED` |
| `INPUT_REQUIRED` | `WORKING`, `CANCELLED` |
| `COMPLETED` | *(none - terminal)* |
| `FAILED` | *(none - terminal)* |
| `CANCELLED` | *(none - terminal)* |

---

## Using the State Machine

### Checking Transition Validity

Before transitioning, check if the transition is valid:

```python
from asap.state.machine import can_transition
from asap.models.enums import TaskStatus

# Valid transition
can_transition(TaskStatus.SUBMITTED, TaskStatus.WORKING)  # True

# Invalid transition (skipping WORKING state)
can_transition(TaskStatus.SUBMITTED, TaskStatus.COMPLETED)  # False

# Terminal state cannot transition
can_transition(TaskStatus.COMPLETED, TaskStatus.WORKING)  # False
```

### Transitioning Tasks

Use the `transition()` function for validated state changes:

```python
from datetime import datetime, timezone
from asap.state.machine import transition
from asap.models.entities import Task
from asap.models.enums import TaskStatus
from asap.errors import InvalidTransitionError

# Create a task
task = Task(
    id="task_01HX5K4N...",
    conversation_id="conv_01HX5K3M...",
    status=TaskStatus.SUBMITTED,
    created_at=datetime.now(timezone.utc),
    updated_at=datetime.now(timezone.utc),
)

# Valid transition - returns new Task instance
working_task = transition(task, TaskStatus.WORKING)
print(working_task.status)  # TaskStatus.WORKING
print(working_task.updated_at)  # Automatically updated

# Invalid transition - raises exception
try:
    transition(task, TaskStatus.COMPLETED)  # Skip WORKING!
except InvalidTransitionError as e:
    print(e.message)  # "Invalid transition from 'submitted' to 'completed'"
    print(e.from_state)  # "submitted"
    print(e.to_state)  # "completed"
```

### Immutability

Task transitions are immutable - they return a new Task instance:

```python
original = Task(
    id="task_123",
    conversation_id="conv_456",
    status=TaskStatus.SUBMITTED,
    created_at=datetime.now(timezone.utc),
    updated_at=datetime.now(timezone.utc),
)

updated = transition(original, TaskStatus.WORKING)

# Original is unchanged
print(original.status)  # TaskStatus.SUBMITTED

# Updated is a new instance
print(updated.status)  # TaskStatus.WORKING
print(original is updated)  # False
```

### Task Helper Methods

The `Task` model provides convenient helper methods:

```python
task = Task(
    id="task_123",
    conversation_id="conv_456",
    status=TaskStatus.WORKING,
    created_at=datetime.now(timezone.utc),
    updated_at=datetime.now(timezone.utc),
)

# Check if task is in terminal state
task.is_terminal()  # False

# Check if task can be cancelled
task.can_be_cancelled()  # True (SUBMITTED or WORKING only)

# After completion
completed_task = transition(task, TaskStatus.COMPLETED)
completed_task.is_terminal()  # True
completed_task.can_be_cancelled()  # False
```

---

## State Snapshots

Snapshots enable task state persistence, allowing tasks to be resumed after interruptions.

### Snapshot Model

```python
from datetime import datetime, timezone
from asap.models.entities import StateSnapshot

snapshot = StateSnapshot(
    id="snap_01HX5K7R...",
    task_id="task_01HX5K4N...",
    version=1,
    data={
        "search_completed": True,
        "sources_analyzed": 15,
        "partial_results": ["result1", "result2"],
        "current_step": "synthesis"
    },
    checkpoint=True,  # Mark as significant checkpoint
    created_at=datetime.now(timezone.utc),
)
```

### Storage Backend Configuration

You can switch backends without code changes using environment variables or the factory:

| Variable | Description | Default |
|----------|-------------|---------|
| `ASAP_STORAGE_BACKEND` | `memory` or `sqlite` | `memory` |
| `ASAP_STORAGE_PATH` | Database file path when using `sqlite` | `asap_state.db` |

```python
from asap.state.stores import create_snapshot_store

# Uses ASAP_STORAGE_BACKEND and ASAP_STORAGE_PATH
store = create_snapshot_store()
```

- **memory**: In-memory store (default). Best for tests and single-process dev; state is lost on restart.
- **sqlite**: File-based persistent store. Use for development or single-instance production; state survives restarts.

When using `create_app()`, if you do not pass `snapshot_store`, the server uses `create_snapshot_store()` and attaches the store to `app.state.snapshot_store` for handlers to use.

**Migration from InMemory to SQLite**: Set `ASAP_STORAGE_BACKEND=sqlite` and optionally `ASAP_STORAGE_PATH=/path/to/db`. No code change required; existing handlers that read `app.state.snapshot_store` will use the SQLite backend. Data in the previous in-memory store is not migrated; start with an empty DB or restore from backup if needed.

### Snapshot Store Interface

The `SnapshotStore` protocol defines the storage interface:

```python
from asap.state import InMemorySnapshotStore, SnapshotStore

# Create a store (use InMemorySnapshotStore for development)
store = InMemorySnapshotStore()

# Save a snapshot
store.save(snapshot)

# Get latest snapshot for a task
latest = store.get("task_01HX5K4N...")

# Get specific version
v2 = store.get("task_01HX5K4N...", version=2)

# List all versions
versions = store.list_versions("task_01HX5K4N...")
print(versions)  # [1, 2, 3]

# Delete specific version
store.delete("task_01HX5K4N...", version=1)

# Delete all snapshots for a task
store.delete("task_01HX5K4N...")
```

### Creating Custom Stores

Implement the `SnapshotStore` protocol for custom backends:

```python
from asap.state.snapshot import SnapshotStore
from asap.models.entities import StateSnapshot
from asap.models.types import TaskID

class RedisSnapshotStore:
    """Redis-backed snapshot storage."""
    
    def __init__(self, redis_client):
        self.redis = redis_client
    
    def save(self, snapshot: StateSnapshot) -> None:
        key = f"snapshot:{snapshot.task_id}:{snapshot.version}"
        self.redis.set(key, snapshot.model_dump_json())
    
    def get(self, task_id: TaskID, version: int | None = None) -> StateSnapshot | None:
        if version is None:
            version = self._get_latest_version(task_id)
        if version is None:
            return None
        
        key = f"snapshot:{task_id}:{version}"
        data = self.redis.get(key)
        return StateSnapshot.model_validate_json(data) if data else None
    
    def list_versions(self, task_id: TaskID) -> list[int]:
        pattern = f"snapshot:{task_id}:*"
        keys = self.redis.keys(pattern)
        return sorted(int(k.split(":")[-1]) for k in keys)
    
    def delete(self, task_id: TaskID, version: int | None = None) -> bool:
        if version is None:
            pattern = f"snapshot:{task_id}:*"
            keys = self.redis.keys(pattern)
            if keys:
                self.redis.delete(*keys)
                return True
            return False
        
        key = f"snapshot:{task_id}:{version}"
        return bool(self.redis.delete(key))

# Usage - works with SnapshotStore protocol
store: SnapshotStore = RedisSnapshotStore(redis_client)
store.save(snapshot)
```

---

## Snapshot Usage Patterns

### Pattern 1: Periodic Checkpoints

Save snapshots at regular intervals during long-running tasks:

```python
async def process_with_checkpoints(task: Task, store: SnapshotStore):
    """Process task with periodic checkpoints."""
    state = {"step": 0, "results": []}
    
    for i, item in enumerate(items_to_process):
        # Process item
        result = await process_item(item)
        state["results"].append(result)
        state["step"] = i + 1
        
        # Checkpoint every 10 items
        if (i + 1) % 10 == 0:
            snapshot = StateSnapshot(
                id=generate_id(),
                task_id=task.id,
                version=state["step"],
                data=state,
                checkpoint=True,
                created_at=datetime.now(timezone.utc),
            )
            store.save(snapshot)
```

### Pattern 2: Resume from Failure

Restore state after task interruption:

```python
async def resume_task(task_id: str, store: SnapshotStore):
    """Resume task from latest snapshot."""
    # Get latest snapshot
    snapshot = store.get(task_id)
    
    if snapshot is None:
        # No snapshot - start fresh
        return await start_fresh(task_id)
    
    # Restore state
    state = snapshot.data
    start_step = state.get("step", 0)
    results = state.get("results", [])
    
    print(f"Resuming from step {start_step}")
    
    # Continue processing
    for i, item in enumerate(items_to_process[start_step:], start=start_step):
        result = await process_item(item)
        results.append(result)
        # ... continue with checkpoints
```

### Pattern 3: State Rollback

Rollback to a previous known-good state:

```python
async def rollback_to_checkpoint(task_id: str, store: SnapshotStore):
    """Rollback to the last checkpoint."""
    versions = store.list_versions(task_id)
    
    # Find last checkpoint
    for version in reversed(versions):
        snapshot = store.get(task_id, version)
        if snapshot and snapshot.checkpoint:
            print(f"Rolling back to version {version}")
            return snapshot.data
    
    raise ValueError("No checkpoint found")
```

---

## Versioning and Consistency

### Version Numbers

Snapshot versions are positive integers starting at 1:

```python
snapshot = StateSnapshot(
    id="snap_123",
    task_id="task_456",
    version=1,  # Must be >= 1
    data={"key": "value"},
    created_at=datetime.now(timezone.utc),
)
```

### Version Auto-Tracking

The `InMemorySnapshotStore` tracks the latest version:

```python
store = InMemorySnapshotStore()

# Save version 1
store.save(StateSnapshot(
    id="snap_1", task_id="task_123", version=1,
    data={}, created_at=datetime.now(timezone.utc)
))

# Save version 2
store.save(StateSnapshot(
    id="snap_2", task_id="task_123", version=2,
    data={}, created_at=datetime.now(timezone.utc)
))

# Get latest returns version 2
latest = store.get("task_123")
print(latest.version)  # 2
```

### Thread Safety

The `InMemorySnapshotStore` is thread-safe:

```python
from asap.state import InMemorySnapshotStore
import threading

store = InMemorySnapshotStore()

def worker(task_id: str, version: int):
    snapshot = StateSnapshot(
        id=f"snap_{version}",
        task_id=task_id,
        version=version,
        data={"version": version},
        created_at=datetime.now(timezone.utc),
    )
    store.save(snapshot)

# Concurrent writes are safe
threads = [
    threading.Thread(target=worker, args=("task_123", i))
    for i in range(1, 11)
]
for t in threads:
    t.start()
for t in threads:
    t.join()

# All versions saved
print(store.list_versions("task_123"))  # [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
```

### Consistency Expectations

| Operation | Guarantee |
|-----------|-----------|
| `save()` | Atomic write |
| `get()` | Read-your-writes consistency |
| `list_versions()` | Eventually consistent |
| `delete()` | Atomic delete |

For production deployments with multiple instances, use a distributed store (Redis, PostgreSQL) with appropriate consistency guarantees.

---

## Best Practices

### 1. Checkpoint Strategically

Save snapshots at meaningful boundaries, not after every operation:

```python
# Good: Checkpoint at logical boundaries
if phase_complete or items_processed % 100 == 0:
    save_snapshot(state, checkpoint=True)

# Avoid: Too frequent checkpoints
for item in items:
    process(item)
    save_snapshot(state)  # Too expensive!
```

### 2. Keep Snapshots Lean

Store only essential state, not derived data:

```python
# Good: Essential state only
snapshot_data = {
    "step": current_step,
    "item_ids_processed": processed_ids,
    "config": task_config,
}

# Avoid: Storing derived/reconstructable data
snapshot_data = {
    "step": current_step,
    "all_results": huge_results_list,  # Can be reconstructed
    "cache": in_memory_cache,  # Not serializable
}
```

### 3. Mark Critical Checkpoints

Use the `checkpoint` flag for important states:

```python
# Mark significant milestones
snapshot = StateSnapshot(
    id=generate_id(),
    task_id=task.id,
    version=version,
    data=state,
    checkpoint=True,  # After phase completion
    created_at=datetime.now(timezone.utc),
)
```

### 4. Clean Up Old Snapshots

Remove unnecessary snapshots to manage storage:

```python
async def cleanup_old_snapshots(task_id: str, store: SnapshotStore, keep_last: int = 5):
    """Keep only recent snapshots plus checkpoints."""
    versions = store.list_versions(task_id)
    
    for version in versions[:-keep_last]:
        snapshot = store.get(task_id, version)
        if snapshot and not snapshot.checkpoint:
            store.delete(task_id, version)
```

---

## Related Documentation

- [Error Handling](error-handling.md) - `InvalidTransitionError` and other exceptions
- [API Reference](api-reference.md) - Complete API documentation
- [Testing](testing.md) - Testing state management
- [Best Practices: Agent Failover & Migration](best-practices/agent-failover-migration.md) - State handover, failover, and migration patterns
