# Tasks: ASAP v1.3.0 SLA Framework & Release (E3-E4) - Detailed

> **Sprints**: E3-E4 - SLA Framework, Audit Logging, and Release
> **Goal**: Service guarantees and compliance, then release v1.3.0
> **Prerequisites**: E1-E2 completed (Metering, Delegation)
> **Estimated Duration**: 2 weeks

---

## Relevant Files

### Sprint E3: SLA Framework
- `src/asap/economics/sla.py` - SLA implementation
- `src/asap/models/manifest.py` - SLA schema addition
- `tests/economics/test_sla.py` - SLA tests

### Sprint E4: Audit & Release
- `src/asap/economics/audit.py` - Audit logging
- `tests/economics/test_audit.py` - Audit tests
- CHANGELOG, docs, release materials

---

## Sprint E3: SLA Framework

**Context**: SLAs (Service Level Agreements) define guarantees agents commit to - availability, latency, error rates. This enables consumers to choose agents based on reliability commitments. Breach detection alerts when agents fail to meet their SLAs.

### Task 3.1: SLA Schema in Manifest

**Goal**: Add SLA definition to manifest

- [ ] 3.1.1 Create SLA module
  - File: `src/asap/economics/sla.py`

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

---

### Task 3.2: SLA Tracking

**Goal**: Measure actual vs promised SLA

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

---

### Task 3.3: SLA Breach Detection

**Goal**: Real-time breach alerts

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

---

### Task 3.4: SLA API

**Goal**: Query SLA history and current status

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

---

## Sprint E4: Audit Logging & Release

### Task 4.1: Audit Log Format

**Goal**: Append-only, tamper-evident logging

- [ ] 4.1.1 Create audit module
  - File: `src/asap/economics/audit.py`

- [ ] 4.1.2 Define AuditEntry model
  ```python
  class AuditEntry(BaseModel):
      id: str  # ULID
      timestamp: datetime
      event_type: AuditEventType
      actor: str  # Agent URN
      subject: str  # Task ID or target
      details: Dict[str, Any]
      previous_hash: str
      hash: str
  ```

- [ ] 4.1.3 Implement hash chain
  - Each entry includes hash of previous
  - SHA-256 for integrity

- [ ] 4.1.4 Implement append-only storage
  - No updates or deletes
  - Only append allowed

- [ ] 4.1.5 Write tests
  - Hash chain integrity
  - Append-only enforced

- [ ] 4.1.6 Commit

---

### Task 4.2: Log All Billable Events

**Goal**: Comprehensive audit trail

- [ ] 4.2.1 Define event types
  ```python
  class AuditEventType(str, Enum):
      TASK_STARTED = "task.started"
      TASK_COMPLETED = "task.completed"
      TASK_FAILED = "task.failed"
      USAGE_RECORDED = "usage.recorded"
      DELEGATION_CREATED = "delegation.created"
      DELEGATION_REVOKED = "delegation.revoked"
      SLA_BREACH = "sla.breach"
  ```

- [ ] 4.2.2 Integrate with task lifecycle
  - Emit audit entries automatically

- [ ] 4.2.3 Integrate with metering
  - Log usage reports

- [ ] 4.2.4 Integrate with delegation
  - Log token creation/revocation

- [ ] 4.2.5 Write tests
  - All events logged
  - No gaps

- [ ] 4.2.6 Commit

---

### Task 4.3: Audit Query API

**Goal**: Query audit logs

- [ ] 4.3.1 Implement GET /audit/logs
  - Query params: actor, subject, event_type, start, end
  - Pagination

- [ ] 4.3.2 Implement GET /audit/logs/{id}
  - Single entry with full details

- [ ] 4.3.3 Implement integrity verification
  - GET /audit/verify
  - Returns chain validity

- [ ] 4.3.4 Add export endpoint
  - GET /audit/export?format=json
  - For compliance reports

- [ ] 4.3.5 Write integration tests

- [ ] 4.3.6 Commit

---

### Task 4.4: Comprehensive Testing

**Goal**: All v1.3.0 tests pass

- [ ] 4.4.1 Run unit tests
  - All economics module tests

- [ ] 4.4.2 Run integration tests
  - Full flow: task → metering → SLA → audit

- [ ] 4.4.3 Run property tests
  - Delegation constraints
  - Audit integrity

- [ ] 4.4.4 Verify benchmarks
  - Metering overhead <5ms
  - Delegation validation <10ms

- [ ] 4.4.5 Fix any issues found

---

### Task 4.5: Release Preparation

**Goal**: v1.3.0 ready for publish

- [ ] 4.5.1 Update CHANGELOG.md
  - Section: [1.3.0] - YYYY-MM-DD
  - Features: Metering, Delegation, SLA, Audit

- [ ] 4.5.2 Bump version
  - pyproject.toml → 1.3.0

- [ ] 4.5.3 Update documentation
  - Economics module docs
  - SLA definition guide
  - Delegation tutorial

- [ ] 4.5.4 Update AGENTS.md
  - Add: Metering patterns and usage tracking
  - Add: Delegation token handling
  - Add: SLA configuration and breach detection

- [ ] 4.5.5 Tag and publish
  - git tag v1.3.0
  - uv publish

- [ ] 4.5.6 Update Docker images

- [ ] 4.5.7 Create GitHub release

- [ ] 4.5.8 Complete checkpoint CP-3
  - File: [checkpoints.md](../../checkpoints.md#cp-3-post-v130-release)
  - Review learnings and update velocity tracking

---

**E3-E4 Definition of Done**:
- [ ] SLA schema in manifests
- [ ] Breach detection working
- [ ] Audit logs all events
- [ ] Hash chain integrity verified
- [ ] v1.3.0 published

**Total Sub-tasks**: ~40
