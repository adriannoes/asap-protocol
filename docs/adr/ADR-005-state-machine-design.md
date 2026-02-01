# ADR-005: State Machine Design for Task Lifecycle

## Context and Problem Statement

Tasks in ASAP have a lifecycle (submitted → working → completed/failed/cancelled). We need explicit states and valid transitions to avoid invalid state changes and support resumable workflows.

## Decision Drivers

* Prevent invalid transitions (e.g., submitted → completed without working)
* Support observable task lifecycle for UI and debugging
* Enable state persistence and recovery
* Clear semantics for terminal states

## Considered Options

* Free-form status string
* Enum with validation
* State machine with explicit transition rules
* Event-sourced state (replay events)

## Decision Outcome

Chosen option: "State machine with explicit transition rules", because it enforces valid transitions via `can_transition()` and `transition()`, provides `TaskStatus` enum, and supports snapshot-based persistence.

### Consequences

* Good, because invalid transitions raise `InvalidTransitionError`
* Good, because terminal states (COMPLETED, FAILED, CANCELLED) are explicit
* Good, because integrates with StateSnapshot for resumable tasks
* Bad, because requires discipline; new states need transition matrix updates

### Confirmation

`asap.state.machine` defines transitions. Tests in `tests/state/` verify valid and invalid transitions.

## Pros and Cons of the Options

### Free-form status string

* Good, because flexible
* Bad, because no validation; prone to invalid states

### State machine with transitions

* Good, because validated transitions; clear lifecycle
* Good, because immutable transitions (return new Task)
* Bad, because more code to maintain

## More Information

* `asap.models.enums.TaskStatus`
* `asap.state.machine.transition`, `can_transition`
* [State Management Guide](../state-management.md)
