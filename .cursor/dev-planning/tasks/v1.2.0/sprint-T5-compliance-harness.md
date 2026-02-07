# Sprint T5: ASAP Compliance Harness

> **Goal**: Protocol compliance testing suite
> **Prerequisites**: Sprints T1-T4 completed (PKI, Registry)
> **Parent Roadmap**: [tasks-v1.2.0-roadmap.md](./tasks-v1.2.0-roadmap.md)

---

## Relevant Files

- `asap-compliance/` - Separate package for compliance testing
- `asap-compliance/pyproject.toml` - Package setup
- `asap-compliance/asap_compliance/__init__.py` - Package init
- `asap-compliance/asap_compliance/harness.py` - Test harness
- `asap-compliance/asap_compliance/config.py` - Configuration
- `asap-compliance/asap_compliance/validators/` - Validators
- `asap-compliance/tests/` - Self-tests

---

## Context

The Compliance Harness validates that ASAP implementations follow the protocol specification. It's a separate package that third parties can use to certify their agents are ASAP-compliant. This enables ecosystem interoperability.

---

## Task 5.1: Compliance Suite Structure

**Goal**: Create pytest-based compliance test package

### Sub-tasks

- [ ] 5.1.1 Create package structure
  ```
  asap-compliance/
  ├── pyproject.toml
  ├── asap_compliance/
  │   ├── __init__.py
  │   ├── harness.py
  │   ├── config.py
  │   └── validators/
  │       ├── __init__.py
  │       ├── handshake.py
  │       ├── schema.py
  │       ├── state.py
  │       └── sla.py
  └── tests/
  ```

- [ ] 5.1.2 Define configuration
  ```python
  class ComplianceConfig(BaseModel):
      agent_url: str
      timeout_seconds: float = 30.0
      test_categories: List[str] = ["handshake", "schema", "state"]
  ```

- [ ] 5.1.3 Create pytest plugin
  - **Plugin**: `pytest-asap-compliance`
  - **Fixture**: `compliance_harness`
  - **Marker**: `@pytest.mark.asap_compliance`

- [ ] 5.1.4 Write package setup
  - **File**: `pyproject.toml`
  - **Dependencies**: pytest, httpx, asap-protocol

- [ ] 5.1.5 Commit
  - **Command**: `git commit -m "feat(evals): create compliance package structure"`

**Acceptance Criteria**:
- [ ] Package structure ready for validators

---

## Task 5.2: Handshake Validation

**Goal**: Validate agent handshake correctness

### Sub-tasks

- [ ] 5.2.1 Create handshake validator
  - **File**: `validators/handshake.py`

- [ ] 5.2.2 Implement connection test
  - Test: Agent responds to health check
  - Test: Correct content-type

- [ ] 5.2.3 Implement manifest test
  - Test: Manifest endpoint exists
  - Test: Manifest schema valid
  - Test: Signature valid (if signed)

- [ ] 5.2.4 Implement version negotiation test
  - Test: Agent reports version
  - Test: Rejects unsupported versions

- [ ] 5.2.5 Write test for validator
  - Test: Against known-good agent
  - Test: Against known-bad agent

- [ ] 5.2.6 Commit
  - **Command**: `git commit -m "feat(evals): add handshake validation"`

**Acceptance Criteria**:
- [ ] Handshake tests detect issues

---

## Task 5.3: Schema Validation

**Goal**: Verify Pydantic schema compliance

### Sub-tasks

- [ ] 5.3.1 Create schema validator
  - **File**: `validators/schema.py`

- [ ] 5.3.2 Implement envelope validation
  - Test: Envelope structure correct
  - Test: Required fields present
  - Test: Types correct

- [ ] 5.3.3 Implement payload validation
  - Test: TaskRequest schema
  - Test: TaskResponse schema
  - Test: Error schema

- [ ] 5.3.4 Implement extension handling
  - Test: Unknown fields ignored
  - Test: Extensions passed through

- [ ] 5.3.5 Write comprehensive tests
  - Edge cases from property tests
  - Known-bad payloads rejected

- [ ] 5.3.6 Commit
  - **Command**: `git commit -m "feat(evals): add schema validation"`

**Acceptance Criteria**:
- [ ] Schema validation catches errors

---

## Task 5.4: State Machine Validation

**Goal**: Verify correct state transitions

### Sub-tasks

- [ ] 5.4.1 Create state validator
  - **File**: `validators/state.py`

- [ ] 5.4.2 Implement transition tests
  - Test: PENDING → RUNNING allowed
  - Test: COMPLETED → RUNNING rejected
  - Test: All valid paths work

- [ ] 5.4.3 Implement terminal state tests
  - Test: COMPLETED is terminal
  - Test: FAILED is terminal
  - Test: No transitions from terminal

- [ ] 5.4.4 Implement SLA validation
  - Test: Task completes within timeout
  - Test: Progress updates sent

- [ ] 5.4.5 Write integration tests
  - Full task lifecycle
  - Various failure scenarios

- [ ] 5.4.6 Commit
  - **Command**: `git commit -m "feat(evals): add state machine validation"`

**Acceptance Criteria**:
- [ ] State machine correctness verified

---

## Sprint T5 Definition of Done

- [ ] Compliance package structure ready
- [ ] Handshake validation working
- [ ] Schema validation working
- [ ] State machine validation working
- [ ] Test coverage >95%

**Total Sub-tasks**: ~22
