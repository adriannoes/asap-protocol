# ADR-009: Snapshot vs Event-Sourced State Persistence

## Context and Problem Statement

Long-running tasks need state persistence for resume after crash or restart. We must choose between snapshot-based and event-sourced persistence.

## Decision Drivers

* Resume from last known good state
* Storage efficiency
* Implementation complexity
* Debugging and audit trail needs

## Considered Options

* Snapshot-based (periodic full state save)
* Event-sourced (append-only event log, replay to restore)
* Hybrid (snapshot + incremental events)

## Decision Outcome

Chosen option: "Snapshot-based", because it is simpler to implement and use. StateSnapshot stores versioned snapshots; `InMemorySnapshotStore` and custom stores (Redis, PostgreSQL) implement the SnapshotStore protocol. Event-sourcing deferred for future consideration.

### Consequences

* Good, because simple API: save snapshot, get latest, resume
* Good, because flexible data shape (JSON-serializable dict)
* Bad, because no full audit trail; only checkpoints
* Neutral, because event-sourcing could be added later for audit

### Confirmation

`asap.models.entities.StateSnapshot` and `asap.state.snapshot.InMemorySnapshotStore`. See [State Management Guide](../state-management.md).

## Pros and Cons of the Options

### Snapshot-based

* Good, because simple; easy to reason about
* Good, because checkpoint flag for significant states
* Bad, because no replay; no full history

### Event-sourced

* Good, because full audit trail; replay for debugging
* Bad, because more complex; storage growth
* Bad, because schema evolution harder

### Hybrid

* Good, because best of both
* Bad, because higher complexity

## More Information

* `asap.models.entities.StateSnapshot`
* `asap.state.snapshot.InMemorySnapshotStore`, `SnapshotStore` protocol
* [State Management Guide](../state-management.md)
* [Stateful Workflows tutorial](../tutorials/stateful-workflows.md)
