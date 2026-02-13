# Sprint E3: SLA Framework

> **Goal**: Service guarantees and breach detection
> **Prerequisites**: Sprints E1-E2 completed (Metering, Delegation)
> **Parent Roadmap**: [tasks-v1.3.0-roadmap.md](./tasks-v1.3.0-roadmap.md)

---

## Relevant Files

- `src/asap/economics/sla.py` - SLA implementation
- `src/asap/models/manifest.py` - SLA schema addition
- `tests/economics/test_sla.py` - SLA tests

---

## Context

SLAs (Service Level Agreements) define guarantees agents commit to - availability, latency, error rates. This enables consumers to choose agents based on reliability commitments. Breach detection alerts when agents fail to meet their SLAs.

---

## Task 3.1: SLA Schema in Manifest

**Goal**: Add SLA definition to manifest

### Sub-tasks

- [ ] 3.1.1 Create SLA module
  - **File**: `src/asap/economics/sla.py`

- [ ] 3.1.2 Define SLADefinition model
  ```python
  class SLADefinition(BaseModel):
      availability: Optional[str]  # "99.5%"
      max_latency_p95_ms: Optional[int]
      max_error_rate: Optional[str]  # "1%"
      support_hours: Optional[str]  # "24/7", "business"
  ```

- [ ] 3.1.3 Add SLA field to Manifest
  - Optional field
  - Validated on manifest parse

- [ ] 3.1.4 Update manifest examples
  - Add SLA to example manifests

- [ ] 3.1.5 Write tests
  - Schema validation
  - Optional field handling

- [ ] 3.1.6 Commit
  - **Command**: `git commit -m "feat(economics): add SLA schema to manifest"`

**Acceptance Criteria**:
- [ ] SLA schema in manifest

---

## Task 3.2: SLA Tracking

**Goal**: Measure actual vs promised SLA

### Sub-tasks

- [ ] 3.2.1 Define SLAMetrics model
  ```python
  class SLAMetrics(BaseModel):
      agent: str
      period_start: datetime
      period_end: datetime
      uptime_percent: float
      latency_p95_ms: int
      error_rate_percent: float
      tasks_completed: int
      tasks_failed: int
  ```

- [ ] 3.2.2 Implement metrics collection
  - Calculate uptime from health checks
  - Calculate latency from task metrics
  - Calculate error rate from outcomes

- [ ] 3.2.3 Implement rolling windows
  - Last hour, day, week, month
  - Efficient calculation

- [ ] 3.2.4 Store SLA history
  - Use metering storage pattern
  - Indexed by agent, period

- [ ] 3.2.5 Write tests
  - Metrics calculation accuracy
  - Rolling window correctness

- [ ] 3.2.6 Commit
  - **Command**: `git commit -m "feat(economics): implement SLA metrics tracking"`

**Acceptance Criteria**:
- [ ] SLA metrics tracked accurately

---

## Task 3.3: SLA Breach Detection

**Goal**: Real-time breach alerts

### Sub-tasks

- [ ] 3.3.1 Define breach conditions
  - Uptime below threshold
  - Latency above threshold
  - Error rate above threshold

- [ ] 3.3.2 Implement breach detector
  - Compare actual vs defined SLA
  - Trigger on threshold cross

- [ ] 3.3.3 Implement alert hooks
  - Callback interface for alerts
  - Default: log warning

- [ ] 3.3.4 Add WebSocket notification
  - Real-time breach events
  - Optional subscription

- [ ] 3.3.5 Write tests
  - Breach detection accuracy
  - Alert delivery

- [ ] 3.3.6 Commit
  - **Command**: `git commit -m "feat(economics): add SLA breach detection and alerts"`

**Acceptance Criteria**:
- [ ] Breach detection working

---

## Task 3.4: SLA API

**Goal**: Query SLA history and current status

### Sub-tasks

- [ ] 3.4.1 Implement GET /agents/{id}/sla
  - Current SLA status
  - Compliance percentage

- [ ] 3.4.2 Implement GET /agents/{id}/sla/history
  - Historical SLA data
  - Pagination, time filtering

- [ ] 3.4.3 Implement GET /agents/{id}/sla/breaches
  - List of breaches
  - Severity, timestamp, duration

- [ ] 3.4.4 Add SLA to Registry search
  - Filter by min_availability
  - Sort by SLA score

- [ ] 3.4.5 Write integration tests

- [ ] 3.4.6 Commit
  - **Command**: `git commit -m "feat(economics): expose SLA metrics via API"`

**Acceptance Criteria**:
- [ ] SLA API functional

---

## Sprint E3 Definition of Done

- [ ] SLA schema in manifests
- [ ] Metrics tracking accurate
- [ ] Breach detection working
- [ ] API endpoints functional
- [ ] Test coverage >95%

**Total Sub-tasks**: ~24
