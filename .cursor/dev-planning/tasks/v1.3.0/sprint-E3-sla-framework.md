# Sprint E3: SLA Framework

> **Goal**: Service guarantees, breach detection, and v1.3.0 release
> **Prerequisites**: Sprints E1-E2 completed (Metering, Delegation)
> **Parent Roadmap**: [tasks-v1.3.0-roadmap.md](./tasks-v1.3.0-roadmap.md)

---

## Relevant Files

- `src/asap/examples/v1_3_0_showcase.py` - v1.3.0 E2E showcase (Task 3.6.1)
- `src/asap/models/entities.py` - SLADefinition model (Task 3.1.1)
- `tests/fixtures/manifest_with_sla.json` - Example manifest with SLA (Task 3.1.5)
- `tests/models/test_entities.py` - TestSLADefinition, TestManifest SLA tests, TestManifestSLAFixture (Task 3.1.6)
- `src/asap/economics/sla.py` - SLAMetrics, SLABreach, metrics collection, rolling windows, breach conditions (BreachConditionResult, parse_percentage, evaluate_breach_conditions) (Task 3.2, 3.3.1)
- `src/asap/economics/sla_storage.py` - SLAStorage Protocol, InMemorySLAStorage, SQLiteSLAStorage (Task 3.2)
- `tests/economics/test_sla.py` - SLA models, helpers, and breach condition tests (Task 3.2.9, 3.3.1)
- `tests/economics/test_sla_storage.py` - SLAStorage InMemory + SQLite tests (Task 3.2.9)
- `src/asap/models/entities.py` - SLADefinition model (added to Manifest)
- `src/asap/transport/sla_api.py` - SLA REST API routes (create_sla_router) (Task 3.4)
- `src/asap/transport/server.py` - create_app(..., sla_storage=...) (Task 3.4.5)
- `tests/economics/test_sla.py` - SLA unit tests
- `tests/economics/test_sla_storage.py` - SLAStorage tests
- `tests/economics/test_sla_api.py` - SLA API integration tests (Task 3.4.6)
- `tests/integration/test_v1_3_cross_feature.py` - Cross-feature integration tests (Task 3.5)
- `tests/transport/test_sla_websocket.py` - SLA WebSocket subscribe/unsubscribe and broadcast tests (Task 3.3.5)

---

## Context

SLAs (Service Level Agreements) define guarantees agents commit to — availability, latency, error rates. In the "Lean Marketplace" (v2.0), these serve as **Trust Signals** to help users separate high-quality agents from experimental ones. Breach detection alerts usage, but does not trigger financial penalties in v2.0.

---

## Task 3.1: SLA Schema in Manifest

**Goal**: Add SLA definition to manifest

### Sub-tasks

- [x] 3.1.1 Define SLADefinition model in `src/asap/models/entities.py`
  ```python
  class SLADefinition(ASAPBaseModel):
      availability: str | None = None  # "99.5%"
      max_latency_p95_ms: int | None = None
      max_error_rate: str | None = None  # "1%"
      support_hours: str | None = None  # "24/7", "business"
  ```
  - Lives in `entities.py` alongside Manifest (same pattern as AuthScheme)

- [x] 3.1.2 Add SLA field to Manifest
  - `sla: SLADefinition | None = Field(default=None, ...)`
  - Validated on manifest parse

- [x] 3.1.3 Create SLA module `src/asap/economics/sla.py`

- [x] 3.1.4 Export SLADefinition in `src/asap/economics/__init__.py`

- [x] 3.1.5 Update manifest examples
  - Add SLA to example manifests

- [x] 3.1.6 Write tests
  - Schema validation
  - Optional field handling
  - Manifest with and without SLA

- [x] 3.1.7 Commit
  - **Command**: `git commit -m "feat(economics): add SLA schema to manifest"`

**Acceptance Criteria**:
- [x] SLA schema defined in Manifest
- [x] SLADefinition exported from economics module

---

## Task 3.2: SLA Tracking & Storage

**Goal**: Measure actual vs promised SLA, with persistent storage

### Sub-tasks

- [x] 3.2.1 Define SLAMetrics model
  ```python
  class SLAMetrics(BaseModel):
      agent_id: str
      period_start: datetime
      period_end: datetime
      uptime_percent: float
      latency_p95_ms: int
      error_rate_percent: float
      tasks_completed: int
      tasks_failed: int
  ```

- [x] 3.2.2 Define SLABreach model
  ```python
  class SLABreach(BaseModel):
      id: str
      agent_id: str
      breach_type: str  # "availability", "latency", "error_rate"
      threshold: str
      actual: str
      severity: str  # "warning", "critical"
      detected_at: datetime
      resolved_at: datetime | None = None
  ```

- [x] 3.2.3 Implement `SLAStorage` Protocol
  - **File**: `src/asap/economics/sla_storage.py`
  ```python
  class SLAStorage(Protocol):
      async def record_metrics(self, metrics: SLAMetrics) -> None: ...
      async def query_metrics(self, agent_id: str | None, start: datetime | None, end: datetime | None) -> list[SLAMetrics]: ...
      async def record_breach(self, breach: SLABreach) -> None: ...
      async def query_breaches(self, agent_id: str | None, start: datetime | None, end: datetime | None) -> list[SLABreach]: ...
      async def stats(self) -> StorageStats: ...
  ```
  - Follows same pattern as `MeteringStorage` and `DelegationStorage`

- [x] 3.2.4 Implement `InMemorySLAStorage`
  - For development/testing
  - Async-safe via `asyncio.Lock`

- [x] 3.2.5 Implement `SQLiteSLAStorage`
  - Tables: `sla_metrics`, `sla_breaches`
  - Indexed by agent_id, period_start, detected_at
  - Same SQLite file (`asap_state.db`) shared with metering/delegation

- [x] 3.2.6 Implement metrics collection
  - Calculate uptime from health checks (uses `health.py`)
  - Calculate latency from task metrics (uses `MeteringStorage`)
  - Calculate error rate from task outcomes

- [x] 3.2.7 Implement rolling windows
  - Last hour, day, week, month
  - Efficient calculation

- [x] 3.2.8 Export SLAStorage, SLAMetrics, SLABreach in `__init__.py`

- [x] 3.2.9 Write tests
  - Storage operations (InMemory + SQLite)
  - Metrics calculation accuracy
  - Rolling window correctness

- [x] 3.2.10 Commit
  - **Command**: `git commit -m "feat(economics): implement SLA metrics tracking and storage"`

**Acceptance Criteria**:
- [x] SLA metrics tracked accurately
- [x] Storage persistent via SQLite

---

## Task 3.3: SLA Breach Detection

**Goal**: Real-time breach alerts with WebSocket notifications

### Sub-tasks

- [x] 3.3.1 Define breach conditions
  - Uptime below threshold
  - Latency above threshold
  - Error rate above threshold

- [x] 3.3.2 Implement breach detector
  - Compare actual vs defined SLA
  - Trigger on threshold cross

- [x] 3.3.3 Implement alert hooks (callback interface)
  - Callback interface for alerts
  - Default: log warning

- [x] 3.3.4 Add WebSocket notification for breach alerts
  - Real-time breach events via WebSocket
  - Subscribe/unsubscribe mechanism
  - Integration with existing `/asap/ws` transport

- [x] 3.3.5 Write tests
  - Breach detection accuracy
  - Alert delivery (callback)
  - WebSocket notification delivery

- [x] 3.3.6 Commit
  - **Command**: `git commit -m "feat(economics): add SLA breach detection and alerts"`

**Acceptance Criteria**:
- [x] Breach detection working
- [x] Alerts delivered via callback and WebSocket

---

## Task 3.4: SLA API

**Goal**: Query SLA history and current status via REST API

### Sub-tasks

- [x] 3.4.1 Implement `create_sla_router()` in `src/asap/transport/sla_api.py`
  - Follows same pattern as `create_usage_router()` and `create_delegation_router()`

- [x] 3.4.2 Implement GET /sla
  - Current SLA status per agent
  - Query params: `agent_id`
  - Compliance percentage

- [x] 3.4.3 Implement GET /sla/history
  - Historical SLA data
  - Query params: `agent_id`, `start`, `end`
  - Pagination support

- [x] 3.4.4 Implement GET /sla/breaches
  - List of breaches
  - Query params: `agent_id`, `severity`, `start`, `end`

- [x] 3.4.5 Integrate SLA router with `create_app`
  - Add `sla_storage: object | None = None` parameter to `create_app`
  - `app.state.sla_storage = sla_storage`
  - `app.include_router(create_sla_router())`
  - Log warning for unauthenticated access (same pattern as usage API)

- [x] 3.4.6 Write integration tests

- [x] 3.4.7 Commit
  - **Command**: `git commit -m "feat(economics): expose SLA metrics via API"`

**Acceptance Criteria**:
- [x] SLA API functional with feature-centric paths (`/sla/*`)
- [x] Integrated with `create_app`

---

## Task 3.5: Comprehensive Testing (Cross-Feature Integration)

**Goal**: Validate SLA integrates correctly with Metering (E1), Delegation (E2), and Health (v1.1)

### Sub-tasks

- [x] 3.5.1 Integration test: SLA + Metering
  - SLA metrics derived from metering data
  - Latency p95 from task metrics matches SLA calculation

- [x] 3.5.2 Integration test: SLA + Health endpoint
  - Uptime calculation uses health check data
  - Simulated downtime triggers correct availability breach

- [x] 3.5.3 Integration test: SLA + Delegation
  - Delegated agent SLA tracked separately
  - Breach on delegated agent reflects on delegation context

- [x] 3.5.4 Full integration test: all v1.3 features
  - Create delegation → execute tasks (metering) → check SLA → trigger breach
  - End-to-end flow through API

- [x] 3.5.5 Commit
  - **Command**: `git commit -m "test: add cross-feature integration tests for v1.3.0"`

**Acceptance Criteria**:
- [x] All integration tests pass
- [x] Test coverage >95%

---

## Task 3.6: End-to-End Showcase (Verify "It Works")

**Goal**: A runnable script demonstrating all v1.3.0 features working together.

### Sub-tasks

- [x] 3.6.1 Create `examples/v1_3_0_showcase.py`
  - Scenario:
    1. **Delegation**: Agent A generates a token for Agent B with `max_tasks=5`.
    2. **Metering**: Agent B performs tasks; usage is logged locally.
    3. **Transparency**: Agent A queries `GET /usage` to see Agent B's consumption.
    4. **Trust/SLA**: Agent B artificially injects a delay -> Agent A receives an SLA breach alert (via WebSocket).

- [x] 3.6.2 Verify Output
  - Ensure updated `README` instructions work.
  - "One command to run them all".

- [ ] 3.6.3 Commit
  - **Command**: `git commit -m "docs: add v1.3.0 end-to-end showcase"`

**Acceptance Criteria**:
- [ ] Demo script runs without errors
- [ ] Prints clear, narrative output for the user
- [ ] WebSocket breach alert visible in showcase output

---

## Task 3.7: Release Preparation

**Goal**: CHANGELOG, docs, version bump, v1.3.0 release

### Sub-tasks

- [ ] 3.7.1 Version bump
  - `pyproject.toml` version field
  - `src/asap/__init__.py` __version__

- [ ] 3.7.2 CHANGELOG.md update
  - List all features from E1, E2, E3
  - Breaking changes (if any)
  - Migration notes

- [ ] 3.7.3 README.md update
  - Add SLA section
  - Update feature list
  - Ensure example commands work

- [ ] 3.7.4 Update v1.3.0 Roadmap
  - Mark all E3 tasks as [x]
  - Update progress counter
  - Add change log entry

- [ ] 3.7.5 CI verification
  - All tests pass
  - Linting clean
  - Type checking clean

- [ ] 3.7.6 PR creation
  - Create PR for E3 sprint
  - Code review pass

- [ ] 3.7.7 Git tag v1.3.0

- [ ] 3.7.8 Commit
  - **Command**: `git commit -m "chore: prepare v1.3.0 release"`

**Acceptance Criteria**:
- [ ] v1.3.0 version in all files
- [ ] CHANGELOG complete
- [ ] CI passes
- [ ] Tag created

---

## Sprint E3 Definition of Done

- [ ] SLA schema in manifests
- [ ] SLA metrics tracked accurately (with SLAStorage)
- [ ] Breaches detected and alerted (callback + WebSocket)
- [ ] API endpoints functional (`/sla/*`)
- [ ] Cross-feature integration tested
- [ ] End-to-End demo runs successfully
- [ ] v1.3.0 release prepared
- [ ] Test coverage >95%

**Total Sub-tasks**: ~37

## Documentation Updates
- [ ] **Update Roadmap**: Mark completed items in [v1.3.0 Roadmap](./tasks-v1.3.0-roadmap.md)
