# Best Practices: Agent Failover & Migration

> Formal patterns for transferring task state between agents and recovering from failures.  
> **Purpose**: Ensure interoperability so all ASAP implementations handle handover and failover consistently.

---

## Overview

ASAP provides protocol primitives for state persistence and transfer:

- **StateSnapshot**: Checkpoint of task state (versioned, JSON-portable).
- **StateQuery**: Request to obtain a task's state snapshot from an agent.
- **StateRestore**: Request to restore a task from a snapshot (by snapshot ID).

Without a common approach, implementations diverge and failover/migration breaks across vendors. This document is **prescriptive**: follow these patterns for interoperable agent failover and migration.

**Related**: [State Management Guide](../state-management.md), [state_migration example](../../src/asap/examples/state_migration.py), [agent_failover example](../../src/asap/examples/agent_failover.py).

---

## 1. Context Handover Pattern (StateQuery → StateRestore)

Use this pattern whenever task ownership or location changes: handover, failover, or migration.

### Flow

1. **Obtain state** from the current holder:
   - **Option A (protocol)**: Send a `StateQuery` envelope to the agent that holds the task. It responds with the snapshot (or you read from a shared store it uses).
   - **Option B (shared storage)**: If both agents use the same store (e.g. shared SQLite path or Redis), the coordinator (or new agent) reads the snapshot directly with `store.get(task_id, version)`.
2. **Restore on the new agent**:
   - **Option A (protocol)**: Ensure the snapshot is available to the target agent (e.g. save it to the target’s store or a shared store), then send a `StateRestore` envelope to the target with `task_id` and `snapshot_id`.
   - **Option B (shared storage)**: If the target uses the same store, it can load by `task_id`/version; no `StateRestore` needed if you only need to “point” the worker at the same store.

For **cross-process / cross-host** handover, use the protocol: send `StateQuery` (or read from shared storage), then send `StateRestore` (or write snapshot to a store the target can read).

### Envelope construction

```python
from asap.models.envelope import Envelope
from asap.models.payloads import StateQuery, StateRestore
from asap.models.ids import generate_id

# Request state from Agent A (e.g. primary)
def build_state_query(task_id: str, version: int | None = None) -> Envelope:
    return Envelope(
        asap_version="0.1",
        sender="urn:asap:agent:coordinator",
        recipient="urn:asap:agent:primary",
        payload_type="state_query",
        payload=StateQuery(task_id=task_id, version=version).model_dump(),
        trace_id=generate_id(),
    )

# Tell Agent B (backup) to restore from a snapshot
def build_state_restore(task_id: str, snapshot_id: str) -> Envelope:
    return Envelope(
        asap_version="0.1",
        sender="urn:asap:agent:coordinator",
        recipient="urn:asap:agent:backup",
        payload_type="state_restore",
        payload=StateRestore(task_id=task_id, snapshot_id=snapshot_id).model_dump(),
        trace_id=generate_id(),
    )
```

The agent that receives `StateQuery` must respond with the snapshot (e.g. from its `SnapshotStore`). The agent that receives `StateRestore` must load the snapshot by `snapshot_id` from its store and resume the task from that state.

---

## 2. Failover Scenario (Primary Fails, Backup Takes Over)

**Scenario**: Agent A (primary) is processing a task; Agent A fails (crash, OOM, network). A coordinator or orchestrator must move the task to Agent B (backup) so work can resume.

### Steps

1. **Detect failure**  
   Use the ASAP health endpoint (e.g. `GET /.well-known/asap/health`) or your orchestration layer to detect that Agent A is unhealthy (SD-10).

2. **Obtain latest state**  
   - If Agent A is still reachable: send `StateQuery` to A, get the snapshot from the response.  
   - If Agent A is down but state is in **shared storage** (e.g. Redis, shared SQLite): read `store.get(task_id)` (latest) or `store.get(task_id, version=version)` from that store.

3. **Make snapshot available to Agent B**  
   - If B uses the same shared store and the snapshot is already there: no copy needed.  
   - Otherwise: push the snapshot to B’s store (e.g. via an API that accepts a snapshot, or by sending the snapshot in a message and B saves it), or write it to a store B can read.

4. **Restore on Agent B**  
   - Send `StateRestore(task_id=..., snapshot_id=...)` to B (so B loads that snapshot and continues), **or**  
   - If B reads from shared store, ensure B is told to resume `task_id` (and optionally which version). B then calls `store.get(task_id)` and resumes.

5. **Route new work to B**  
   Update routing so subsequent requests for that task (or conversation) go to Agent B.

### Coordinator responsibilities

- Poll or subscribe to health (e.g. `/.well-known/asap/health`).
- On primary failure, decide which task(s) to fail over.
- For each task: get snapshot (StateQuery or shared store), provide snapshot to backup (StateRestore or shared store), then route traffic to backup.

---

## 3. Migration Scenario (Different Host or Version)

**Scenario**: You are moving an agent to a new host or upgrading to a new version; you want to move in-flight task state to the new process.

### Steps

1. **Drain / pause**  
   Stop assigning new work to the old agent (or mark it draining). Let in-flight tasks reach a checkpoint if possible.

2. **Export state**  
   For each active task, get the latest snapshot:
   - From the old agent via `StateQuery`, or  
   - From the old agent’s store (e.g. read from its DB or shared store).

3. **Import into new agent**  
   - Write snapshots into the new agent’s store (or shared store the new agent uses).  
   - Optionally send `StateRestore` to the new agent for each task so it loads the snapshot and resumes.

4. **Switch traffic**  
   Point clients/coordinators to the new agent. Retire the old agent.

### Version compatibility

- `StateSnapshot.data` is a JSON-serializable `dict`. Keep schema stable across versions so old snapshots can be restored by new code.
- Prefer adding optional fields and ignoring unknown fields when restoring.

---

## 4. Artifact Portability Conventions

Task state (e.g. `StateSnapshot.data`) often references artifacts by URI (files, blobs, outputs). Whether those references remain valid after failover or migration depends on the URI scheme. Follow these conventions so artifacts behave correctly when the task moves to another agent.

### 4.1 URI schemes and portability

| Scheme     | Portable across agents? | Use case |
|-----------|--------------------------|----------|
| `https://` | **Yes**                  | Shared object storage (S3, GCS, Azure Blob), CDN URLs, presigned URLs. Resolvable by any agent with network access. **Use for any artifact that may need to survive failover.** |
| `asap://`  | **No** (agent-local)     | References local to a single agent instance (e.g. `asap://artifact/abc`). The new agent cannot resolve them after failover unless you copy the resource and expose it (e.g. via `https://`) or replicate it locally. |
| `data:`    | **Yes**                  | Inline small payloads (e.g. `data:application/json;base64,...`). No network or local storage required; always portable. |

### 4.2 What happens during failover

- **`https://`**: After failover, the backup agent (or any other agent) can fetch the artifact using the same URL. No extra step required as long as the URL remains valid (e.g. presigned URL not expired).
- **`asap://`**: After failover, the URL points to the old (possibly dead) agent. The backup cannot resolve it. Either avoid `asap://` for state that may fail over, or ensure the coordinator (or old agent before shutdown) copies the artifact to shared storage and rewrites the reference to `https://` before handing over.
- **`data:`**: The payload is embedded in the state; it moves with the snapshot. No change in behavior after failover.

### 4.3 Recommendation

- For tasks that might be failed over or migrated, **store artifact references as `https://`** (or `data:` for small inline data).
- **Avoid relying on `asap://`** for any state that must move to another agent. Reserve `asap://` for agent-local references that will never be transferred (e.g. transient scratch paths).
- When generating artifact URIs in task handlers, prefer writing to object storage (or a shared volume) and storing the resulting `https://` (or presigned) URL in `StateSnapshot.data`, so that failover and migration work without extra copy steps.

---

## 5. State Export Convention

To export `StateSnapshot` for external systems (backups, analytics, or another platform):

- **Format**: JSON. Use `StateSnapshot.model_dump()` (Pydantic v2) for a dict, or `StateSnapshot.model_dump_json()` for a string.
- **Fields**: `id`, `task_id`, `version`, `data`, `checkpoint`, `created_at`. All are JSON-serializable; `data` is already `dict[str, Any]`.
- **Idempotency**: When re-importing, use the same `id` and `task_id`/`version` if you need to avoid duplicates. New IDs can be generated for “copy” migrations.

Example:

```python
from asap.models.entities import StateSnapshot

snapshot: StateSnapshot = store.get(task_id)
if snapshot:
    export_dict = snapshot.model_dump()
    # Persist export_dict to file, blob store, or send over the wire
    # Later: snapshot = StateSnapshot.model_validate(export_dict); store.save(snapshot)
```

---

## 6. Code Examples

### 6.1 Moving state between two stores (in-process)

This mirrors the official [state_migration](../../src/asap/examples/state_migration.py) example: export from one store, import into another (e.g. primary vs backup store).

```python
from datetime import datetime, timezone
from asap.models.entities import StateSnapshot
from asap.models.ids import generate_id
from asap.state import InMemorySnapshotStore, SnapshotStore

def move_state(
    source: SnapshotStore,
    target: SnapshotStore,
    task_id: str,
    version: int | None = None,
    new_task_id: str | None = None,
) -> StateSnapshot | None:
    snapshot = source.get(task_id, version=version)
    if not snapshot:
        return None
    target_task_id = new_task_id or task_id
    migrated = StateSnapshot(
        id=generate_id(),
        task_id=target_task_id,
        version=snapshot.version,
        data=dict(snapshot.data),
        checkpoint=snapshot.checkpoint,
        created_at=snapshot.created_at,
    )
    target.save(migrated)
    return migrated
```

Run the full demo:

```bash
uv run python -m asap.examples.state_migration
```

### 6.2 Coordinator: detect failure and trigger handover

Pseudocode for a coordinator that uses health checks and shared storage (conceptual; adapt to your transport).

```python
# 1. Periodically check health
primary_healthy = await check_health(primary_url)  # GET /.well-known/asap/health

# 2. If primary unhealthy, for each in-flight task_id:
if not primary_healthy:
    for task_id in in_flight_tasks:
        # 3. Get snapshot from shared store (primary wrote there)
        snapshot = shared_store.get(task_id)
        if not snapshot:
            continue  # or try StateQuery to primary as last resort
        # 4. Ensure backup has the snapshot (if different store)
        if backup_store != shared_store:
            backup_store.save(snapshot)  # or send snapshot to backup via API
        # 5. Tell backup to restore
        await send_envelope_to_agent(backup_url, build_state_restore(task_id, snapshot.id))
        # 6. Update routing: task_id -> backup
        routing[task_id] = backup_url
```

### 6.3 Worker: save checkpoints and resume from store

Worker agents should save snapshots at checkpoints and, on startup or when receiving `StateRestore`, load from the store and resume.

```python
from asap.models.entities import StateSnapshot
from asap.state import SnapshotStore

def resume_or_start(store: SnapshotStore, task_id: str) -> dict:
    snapshot = store.get(task_id)
    if snapshot:
        return snapshot.data  # Resume from this state
    return {}  # Fresh start

# In task handler: periodically
def on_checkpoint(store: SnapshotStore, task_id: str, state: dict) -> None:
    snapshot = StateSnapshot(
        id=generate_id(),
        task_id=task_id,
        version=state["step"],
        data=state,
        checkpoint=True,
        created_at=datetime.now(timezone.utc),
    )
    store.save(snapshot)
```

---

## Summary

| Scenario        | Obtain state              | Restore on new agent      |
|----------------|---------------------------|----------------------------|
| Failover       | StateQuery or shared store | StateRestore or shared store |
| Migration      | Export from old store      | Import into new store + StateRestore (optional) |
| Handover       | StateQuery or shared store | StateRestore or shared store |

- Use **StateQuery** / **StateRestore** (or shared storage) so state transfer is consistent across implementations.
- Use **https://** (or **data:**) for artifact URIs that must survive failover.
- Export **StateSnapshot** as JSON via `model_dump()` / `model_dump_json()` for backups or external systems.
- Run the [state_migration](../../src/asap/examples/state_migration.py) example to validate the pattern end-to-end.
