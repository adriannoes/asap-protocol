# Sprint S2.5: State Storage Interface

> **Goal**: Implement persistent state storage with SQLite reference implementation
> **Prerequisites**: Sprint S1 completed (auth module structure as reference)
> **Parent Roadmap**: [tasks-v1.1.0-roadmap.md](./tasks-v1.1.0-roadmap.md)
> **Strategic Decision**: [SD-9 (State Management Hybrid)](../../../product-specs/roadmap-to-marketplace.md), [ADR-13](../../../product-specs/ADR.md)

---

## Relevant Files

- `src/asap/state/__init__.py` - State module init (exists)
- `src/asap/state/snapshot.py` - SnapshotStore Protocol + InMemorySnapshotStore (exists)
- `src/asap/state/metering.py` - MeteringStore Protocol (new)
- `src/asap/state/stores/__init__.py` - Storage backends package (new)
- `src/asap/state/stores/memory.py` - InMemorySnapshotStore (refactored)
- `src/asap/state/stores/sqlite.py` - SQLiteSnapshotStore (new)
- `tests/state/test_snapshot.py` - Existing snapshot tests
- `tests/state/test_metering.py` - Metering store tests (new)
- `tests/state/test_sqlite_store.py` - SQLite store tests (new)

---

## Context

The v0 spec (Section 13.2) recommended "Option 2 (interface) for interoperability" for state storage. The `SnapshotStore` Protocol already exists in v1.0, but only `InMemorySnapshotStore` is implemented — state is lost on restart. This sprint:

1. Defines the `MeteringStore` interface (foundation for v1.3 Economics Layer)
2. Provides a production-ready SQLite implementation of `SnapshotStore`
3. Refactors `InMemorySnapshotStore` into the `stores/` subpackage
4. Adds environment-based storage backend selection

This is critical for the marketplace vision: without persistent storage, v1.3 metering, audit logging, and v2.0 reputation are impossible.

---

## Task 2.5.1: MeteringStore Protocol

**Goal**: Define abstract interface for usage metering data storage.

**Context**: v1.3.0 will implement Usage Metering (METER-001 to METER-006). The storage interface must be defined now so that v1.3 can focus on metering logic, not storage plumbing.

**Prerequisites**: None (can start immediately)

### Sub-tasks

- [ ] 2.5.1.1 Define MeteringStore Protocol
  - **File**: `src/asap/state/metering.py` (create new)
  - **What**: Create `MeteringStore` Protocol with methods:
    - `record(event: UsageEvent) -> None` — Record a usage event
    - `query(agent_id: str, start: datetime, end: datetime) -> list[UsageEvent]` — Query events
    - `aggregate(agent_id: str, period: str) -> UsageAggregate` — Aggregate by period
  - **Why**: v1.3 Economics Layer needs a defined storage contract
  - **Pattern**: Follow `SnapshotStore` Protocol pattern in `snapshot.py`
  - **Verify**: `isinstance(InMemoryMeteringStore(), MeteringStore)` is True

- [ ] 2.5.1.2 Define UsageEvent and UsageAggregate models
  - **File**: `src/asap/state/metering.py` (modify)
  - **What**: Pydantic v2 models:
    - `UsageEvent`: task_id, agent_id, consumer_id, metrics (tokens_in, tokens_out, duration_ms, api_calls), timestamp
    - `UsageAggregate`: agent_id, period, total_tokens, total_duration, total_tasks, total_api_calls
  - **Why**: Typed models ensure consistency across storage backends
  - **Pattern**: Follow `StateSnapshot` model pattern in `models/entities.py`
  - **Verify**: Models validate with Pydantic, serialize to JSON

- [ ] 2.5.1.3 Implement InMemoryMeteringStore
  - **File**: `src/asap/state/stores/memory.py` (modify after 2.5.3)
  - **What**: In-memory implementation for testing:
    - Thread-safe with RLock (same pattern as InMemorySnapshotStore)
    - Simple dict-based storage
  - **Why**: Testing and development use case
  - **Verify**: All MeteringStore Protocol methods work

- [ ] 2.5.1.4 Write tests
  - **File**: `tests/state/test_metering.py` (create new)
  - **What**: Test scenarios:
    - Protocol compliance (isinstance check)
    - Record and query events
    - Aggregation by period (hour, day)
    - Empty store returns empty results
    - Thread safety
  - **Verify**: `pytest tests/state/test_metering.py -v` all pass

- [ ] 2.5.1.5 Commit milestone
  - **Command**: `git commit -m "feat(state): add MeteringStore protocol and models"`
  - **Scope**: metering.py, test_metering.py
  - **Verify**: `git log -1` shows correct message

**Acceptance Criteria**:
- [ ] MeteringStore Protocol defined with type annotations
- [ ] UsageEvent and UsageAggregate models validated by Pydantic
- [ ] InMemoryMeteringStore passes all tests
- [ ] Protocol is runtime_checkable

---

## Task 2.5.2: SQLiteSnapshotStore

**Goal**: Implement persistent SnapshotStore using SQLite via aiosqlite.

**Context**: SQLite is the ideal first persistent backend: zero-config, file-based, suitable for single-agent deployments and development. It uses `aiosqlite` for async compatibility with ASAP's async-first architecture.

**Prerequisites**: Task 2.5.3 completed (stores/ package exists)

### Sub-tasks

- [ ] 2.5.2.1 Add aiosqlite dependency
  - **File**: `pyproject.toml` (modify)
  - **What**: Add to dependencies: `aiosqlite>=0.20`
  - **Command**: `uv add "aiosqlite>=0.20"`
  - **Verify**: `uv run python -c "import aiosqlite"` works

- [ ] 2.5.2.2 Implement SQLiteSnapshotStore
  - **File**: `src/asap/state/stores/sqlite.py` (create new)
  - **What**: Async SQLite implementation:
    - `__init__(db_path: str | Path = "asap_state.db")` — configurable path
    - `async def initialize() -> None` — create tables if not exists
    - `save(snapshot)` — INSERT OR REPLACE
    - `get(task_id, version)` — SELECT with optional version
    - `list_versions(task_id)` — SELECT DISTINCT versions
    - `delete(task_id, version)` — DELETE with optional version filter
    - Table schema: `snapshots(task_id TEXT, version INT, data JSON, created_at TEXT, PRIMARY KEY(task_id, version))`
  - **Why**: Production-ready persistence with zero external dependencies
  - **Pattern**: Same interface as InMemorySnapshotStore, but async-aware
  - **Note**: Since `SnapshotStore` Protocol uses sync methods, the SQLite impl wraps async calls. Consider making the Protocol async-aware (breaking change analysis needed).
  - **Verify**: Store survives process restart

- [ ] 2.5.2.3 Implement SQLiteMeteringStore
  - **File**: `src/asap/state/stores/sqlite.py` (modify)
  - **What**: SQLite implementation of MeteringStore:
    - Table: `usage_events(id TEXT PK, task_id TEXT, agent_id TEXT, consumer_id TEXT, metrics JSON, timestamp TEXT)`
    - Indexed on: `(agent_id, timestamp)` for efficient queries
    - Aggregation via SQL GROUP BY
  - **Why**: Unified SQLite backend for both snapshot and metering storage
  - **Verify**: Record/query/aggregate operations work

- [ ] 2.5.2.4 Write comprehensive tests
  - **File**: `tests/state/test_sqlite_store.py` (create new)
  - **What**: Test scenarios:
    - **CRUD**: Save, get, list, delete snapshots
    - **Persistence**: Data survives store re-creation (same db file)
    - **Concurrency**: Multiple concurrent writes don't corrupt
    - **Metering**: Record, query, aggregate usage events
    - **Edge cases**: Empty DB, non-existent task_id, duplicate versions
    - **Cleanup**: Use tmp_path fixture for isolated DB files
  - **Verify**: `pytest tests/state/test_sqlite_store.py -v` all pass

- [ ] 2.5.2.5 Add storage example
  - **File**: `src/asap/examples/storage_backends.py` (create new)
  - **What**: Example showing:
    - InMemory store for testing
    - SQLite store for development/production
    - How to switch backends via environment variable
  - **Verify**: Example runs successfully

- [ ] 2.5.2.6 Commit milestone
  - **Command**: `git commit -m "feat(state): add SQLite persistent storage backend"`
  - **Scope**: sqlite.py, test_sqlite_store.py, storage_backends.py, pyproject.toml
  - **Verify**: `git log -1` shows correct message

**Acceptance Criteria**:
- [ ] SQLite store passes all SnapshotStore tests
- [ ] Data persists across process restarts
- [ ] Metering store records and aggregates usage data
- [ ] No data corruption under concurrent access
- [ ] Example demonstrates backend switching

---

## Task 2.5.3: Refactor InMemorySnapshotStore

**Goal**: Move InMemorySnapshotStore to stores/ subpackage while maintaining backward compatibility.

**Context**: The current InMemorySnapshotStore lives in `snapshot.py` alongside the Protocol definition. Moving it to `stores/memory.py` creates a clean separation between interface and implementation.

**Prerequisites**: None (can start immediately, before 2.5.2)

### Sub-tasks

- [ ] 2.5.3.1 Create stores subpackage
  - **File**: `src/asap/state/stores/__init__.py` (create new)
  - **What**: Create package with re-exports:
    - `from asap.state.stores.memory import InMemorySnapshotStore`
    - `from asap.state.stores.memory import InMemoryMeteringStore` (after 2.5.1)
  - **Verify**: `from asap.state.stores import InMemorySnapshotStore` works

- [ ] 2.5.3.2 Move InMemorySnapshotStore
  - **File**: `src/asap/state/stores/memory.py` (create new)
  - **File**: `src/asap/state/snapshot.py` (modify)
  - **What**:
    - Move `InMemorySnapshotStore` class to `stores/memory.py`
    - Keep `SnapshotStore` Protocol in `snapshot.py`
    - Add backward-compat re-export in `snapshot.py`: `from asap.state.stores.memory import InMemorySnapshotStore`
  - **Why**: Clean separation of interface (Protocol) from implementation (stores/)
  - **Verify**: All existing imports still work, no test failures

- [ ] 2.5.3.3 Update state module __init__.py
  - **File**: `src/asap/state/__init__.py` (modify)
  - **What**: Update exports to include new package structure:
    - Export `SnapshotStore` from `snapshot.py`
    - Export `InMemorySnapshotStore` from `stores.memory`
    - Export `SQLiteSnapshotStore` from `stores.sqlite` (after 2.5.2)
  - **Verify**: `from asap.state import SnapshotStore, InMemorySnapshotStore` works

- [ ] 2.5.3.4 Verify backward compatibility
  - **Command**: `pytest tests/ -v`
  - **What**: Run full test suite to ensure no regressions:
    - All existing snapshot tests pass
    - All imports from `asap.state.snapshot` still work
    - No deprecation warnings unless intentional
  - **Verify**: Zero test failures

- [ ] 2.5.3.5 Commit milestone
  - **Command**: `git commit -m "refactor(state): move InMemorySnapshotStore to stores/ subpackage"`
  - **Scope**: snapshot.py, stores/__init__.py, stores/memory.py, __init__.py
  - **Verify**: `git log -1` shows correct message

**Acceptance Criteria**:
- [ ] InMemorySnapshotStore lives in `stores/memory.py`
- [ ] SnapshotStore Protocol stays in `snapshot.py`
- [ ] All existing tests pass without modification
- [ ] Backward-compatible imports maintained

---

## Task 2.5.4: Storage Configuration

**Goal**: Enable environment-based storage backend selection.

**Context**: Agents should be able to switch storage backends without code changes, using environment variables or configuration.

**Prerequisites**: Tasks 2.5.2 and 2.5.3 completed

### Sub-tasks

- [ ] 2.5.4.1 Implement storage factory
  - **File**: `src/asap/state/stores/__init__.py` (modify)
  - **What**: Create `create_snapshot_store()` factory:
    - Reads `ASAP_STORAGE_BACKEND` env var (default: `"memory"`)
    - `"memory"` → `InMemorySnapshotStore()`
    - `"sqlite"` → `SQLiteSnapshotStore(path=ASAP_STORAGE_PATH or "asap_state.db")`
    - Returns configured store instance
  - **Why**: Zero-code backend switching for different environments
  - **Pattern**: Factory pattern, similar to logging configuration
  - **Verify**: Setting env var changes storage backend

- [ ] 2.5.4.2 Integrate with ASAPServer
  - **File**: `src/asap/transport/server.py` (modify)
  - **What**: If no explicit store provided, use `create_snapshot_store()`:
    - `ASAPServer(store=my_store)` → use provided store
    - `ASAPServer()` → use factory (env-based)
  - **Why**: Seamless integration with existing server setup
  - **Verify**: Server uses SQLite when env var set

- [ ] 2.5.4.3 Update documentation
  - **What**: Add to README/docs:
    - Storage backend configuration guide
    - Environment variables reference
    - Migration from InMemory to SQLite
  - **Verify**: Documentation is clear and accurate

- [ ] 2.5.4.4 Write tests
  - **File**: `tests/state/test_storage_factory.py` (create new)
  - **What**: Test scenarios:
    - Default returns InMemorySnapshotStore
    - `ASAP_STORAGE_BACKEND=sqlite` returns SQLiteSnapshotStore
    - Invalid backend raises clear error
    - Custom path via `ASAP_STORAGE_PATH`
  - **Verify**: `pytest tests/state/test_storage_factory.py -v` all pass

- [ ] 2.5.4.5 Commit milestone
  - **Command**: `git commit -m "feat(state): add storage backend configuration and factory"`
  - **Scope**: stores/__init__.py, server.py, tests
  - **Verify**: `git log -1` shows correct message

**Acceptance Criteria**:
- [ ] Storage backend selectable via environment variable
- [ ] ASAPServer auto-detects storage backend
- [ ] Documentation covers configuration
- [ ] Factory handles errors gracefully

---

## Task 2.5.5: Best Practices — Agent Failover & Migration

**Goal**: Create formal documentation for agent failover and state migration patterns.

**Context**: The protocol primitives (`StateQuery`/`StateRestore`) already exist and work. `StateSnapshot.data` is `dict[str, Any]` — JSON-portable by design. However, without formal documentation as a "Best Practice", implementations will diverge and interoperability will fail. This is NOT buried in examples — it's a first-class pattern document. See context discussion in strategic review.

**Prerequisites**: Tasks 2.5.1-2.5.3 completed (storage interfaces and implementations defined)

### Sub-tasks

- [ ] 2.5.5.1 Create Best Practices document
  - **File**: `docs/best-practices/agent-failover-migration.md` (create new)
  - **What**: Formal pattern document covering:
    - **Context Handover Pattern**: Using `StateQuery` → `StateRestore` for transferring task state between agents
    - **Failover Scenario**: Agent A (Primary) fails, Agent B (Backup) takes over
    - **Migration Scenario**: Agent moves to different host/version
    - **Artifact Portability**: Use `https://` URIs for portable artifacts, `asap://` for local-only
    - **State Export Convention**: How to serialize `StateSnapshot` for external systems
    - **Code Examples**: Complete working examples with both coordinator and worker agents
  - **Why**: Without formal documentation, each implementation does handover differently — breaking interoperability
  - **Pattern**: Similar to Kubernetes "Migration Guides" — prescriptive, not just descriptive
  - **Verify**: Document is clear, examples are runnable

- [ ] 2.5.5.2 Add failover example to examples/
  - **File**: `src/asap/examples/agent_failover.py` (create new)
  - **What**: Working example demonstrating:
    - Agent A starts a task and saves snapshots
    - Agent A becomes unhealthy (simulated crash)
    - Coordinator detects via health endpoint (SD-10)
    - Coordinator sends `StateQuery` to Agent A (or reads from shared storage)
    - Coordinator sends `StateRestore` to Agent B
    - Agent B resumes the task
  - **Why**: Executable documentation — proves the pattern works end-to-end
  - **Verify**: Example runs successfully

- [ ] 2.5.5.3 Document artifact portability conventions
  - **File**: `docs/best-practices/agent-failover-migration.md` (modify)
  - **What**: Add section on artifact URIs:
    - `https://` — portable across agents (S3 presigned URLs, CDN, etc.)
    - `asap://` — agent-local only, NOT portable after failover
    - `data:` — inline small files, always portable
    - Recommendation: Use `https://` for any artifact that may need to survive failover
  - **Why**: Clarifies what happens to artifacts during agent replacement
  - **Verify**: Conventions are clear and actionable

- [ ] 2.5.5.4 Commit milestone
  - **Command**: `git commit -m "docs(state): add Best Practices for Agent Failover & Migration"`
  - **Scope**: best-practices doc, failover example
  - **Verify**: `git log -1` shows correct message

**Acceptance Criteria**:
- [ ] Best Practices document covers all failover/migration scenarios
- [ ] Working example demonstrates the pattern end-to-end
- [ ] Artifact portability conventions are clearly documented
- [ ] Document is discoverable (linked from README and AGENTS.md)

---

## Task 2.5.6: Mark Sprint S2.5 Complete

**Goal**: Finalize Sprint S2.5 deliverables.

**Context**: Checkpoint task to verify all S2.5 deliverables are complete and update tracking.

**Prerequisites**: All tasks 2.5.1-2.5.5 completed

### Sub-tasks

- [ ] 2.5.6.1 Update roadmap progress
  - **File**: `tasks-v1.1.0-roadmap.md` (modify)
  - **What**: Mark S2.5 tasks as complete `[x]`, update progress percentage
  - **Verify**: Progress shows 100% for S2.5

- [ ] 2.5.6.2 Run full test suite
  - **Command**: `pytest tests/state -v --cov`
  - **What**: Verify all new tests pass with >95% coverage
  - **Verify**: No failures, coverage target met

- [ ] 2.5.6.3 Commit checkpoint
  - **Command**: `git commit -m "chore: mark v1.1.0 S2.5 complete"`
  - **Verify**: Clean commit with progress updates

**Acceptance Criteria**:
- [ ] All S2.5 tasks complete
- [ ] Test suite passes
- [ ] Best Practices document complete and linked
- [ ] Progress tracked in roadmap

---

## Sprint S2.5 Definition of Done

- [ ] MeteringStore Protocol defined
- [ ] SQLiteSnapshotStore implemented and tested
- [ ] InMemorySnapshotStore refactored to stores/ package
- [ ] Storage backend configurable via environment
- [ ] Best Practices: Agent Failover & Migration documented
- [ ] Failover example runs end-to-end
- [ ] Backward compatibility maintained
- [ ] Test coverage >95%
- [ ] Progress tracked in roadmap

**Total Sub-tasks**: ~26
