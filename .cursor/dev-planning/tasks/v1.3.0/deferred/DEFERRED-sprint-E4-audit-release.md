> [!CAUTION]
> **DEFERRED (2026-02-12, Lean Marketplace Pivot)**: Audit logging deferred to v2.1+. Release tasks merged into Sprint E3 (SLA Framework & Release). See [deferred-backlog.md](../../../../product-specs/strategy/deferred-backlog.md#4-audit-logging-originally-v13-sprint-e4).
>
> This sprint file is preserved for reference. Audit content captured in deferred backlog.

# Sprint E4: Audit Logging & Release (DEFERRED)

> **Goal**: Tamper-evident audit logs and v1.3.0 release
> **Prerequisites**: Sprint E3 completed (SLA Framework)
> **Parent Roadmap**: [tasks-v1.3.0-roadmap.md](../tasks-v1.3.0-roadmap.md)

---

## Relevant Files

- `src/asap/economics/audit.py` - Audit logging
- `tests/economics/test_audit.py` - Audit tests
- `pyproject.toml` - Version bump
- `CHANGELOG.md` - Release notes
- `README.md` - Quick start updates
- `AGENTS.md` - AI agent instructions

---

## Context

Sprint E4 implements tamper-evident audit logging for compliance and prepares the v1.3.0 release.

---

## Task 4.1: Audit Log Format

**Goal**: Append-only, tamper-evident logging

### Sub-tasks

- [ ] 4.1.1 Create audit module
  - **File**: `src/asap/economics/audit.py`

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

**Acceptance Criteria**:
- [ ] Audit log format defined

---

## Task 4.2: Log All Billable Events

**Goal**: Comprehensive audit trail

### Sub-tasks

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

**Acceptance Criteria**:
- [ ] All billable events logged

---

## Task 4.3: Audit Query API

**Goal**: Query audit logs

### Sub-tasks

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

**Acceptance Criteria**:
- [ ] Audit API functional

---

## Task 4.4: Comprehensive Testing

**Goal**: All v1.3.0 tests pass

### Sub-tasks

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

**Acceptance Criteria**:
- [ ] All tests pass

---

## Task 4.5: Release Preparation

**Goal**: v1.3.0 ready for publish

### Sub-tasks

- [ ] 4.5.1 Update CHANGELOG.md
  - **Section**: [1.3.0] - YYYY-MM-DD
  - **Features**: Metering, Delegation, SLA, Audit

- [ ] 4.5.2 Bump version
  - `pyproject.toml` → `1.3.0`

- [ ] 4.5.3 Update documentation
  - Economics module docs
  - SLA definition guide
  - Delegation tutorial

- [ ] 4.5.4 Update AGENTS.md
  - **Add**: Metering patterns and usage tracking
  - **Add**: Delegation token handling
  - **Add**: SLA configuration and breach detection

- [ ] 4.5.5 Tag and publish
  - `git tag v1.3.0`
  - `uv publish`

- [ ] 4.5.6 Update Docker images

- [ ] 4.5.7 Create GitHub release

- [ ] 4.5.8 Complete checkpoint CP-3
  - **File**: [checkpoints.md](../../../checkpoints.md#cp-3-post-v130-release)
  - Review learnings and update velocity tracking

**Acceptance Criteria**:
- [ ] v1.3.0 published

---

## Sprint E4 Definition of Done

- [ ] Audit logs all events
- [ ] Hash chain integrity verified
- [ ] All tests pass
- [ ] v1.3.0 published
- [ ] Docker image available

**Total Sub-tasks**: ~30
