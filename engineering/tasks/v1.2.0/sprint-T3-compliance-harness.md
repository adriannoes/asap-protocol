# Sprint T3: ASAP Compliance Harness

> **Goal**: Protocol compliance testing suite
> **Prerequisites**: Sprints T1-T2 completed (PKI, Trust Levels)
> **Parent Roadmap**: [tasks-v1.2.0-roadmap.md](./tasks-v1.2.0-roadmap.md)
>
> **Note**: This sprint replaces the deferred Registry API sprints. It was previously numbered T5.

---

## Relevant Files

- `asap-compliance/` - Separate package for compliance testing
- `asap-compliance/pyproject.toml` - Package setup
- `asap-compliance/asap_compliance/__init__.py` - Package init
- `asap-compliance/asap_compliance/harness.py` - Test harness
- `asap-compliance/asap_compliance/config.py` - Configuration
- `asap-compliance/asap_compliance/pytest_plugin.py` - Pytest plugin (fixture, marker)
- `asap-compliance/asap_compliance/validators/handshake.py` - Handshake validator
- `asap-compliance/asap_compliance/validators/schema.py` - Schema validator
- `asap-compliance/asap_compliance/validators/state.py` - State machine validator
- `asap-compliance/asap_compliance/validators/sla.py` - SLA validator (timeout, progress)
- `asap-compliance/asap_compliance/validators/` - Validators
- `asap-compliance/tests/test_state.py` - State validator unit tests
- `asap-compliance/tests/test_sla.py` - SLA validator tests
- `asap-compliance/tests/test_state_integration.py` - Integration tests (lifecycle, failures)

---

## Context

The Compliance Harness validates that ASAP implementations follow the protocol specification. It's a separate package that third parties can use to certify their agents are ASAP-compliant. This enables ecosystem interoperability.

---

## Task 3.1: Compliance Suite Structure

**Goal**: Create pytest-based compliance test package

### Sub-tasks

- [x] 3.1.1 Create package structure
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

- [x] 3.1.2 Define configuration
  ```python
  class ComplianceConfig(BaseModel):
      agent_url: str
      timeout_seconds: float = 30.0
      test_categories: List[str] = ["handshake", "schema", "state"]
  ```

- [x] 3.1.3 Create pytest plugin
  - **Plugin**: `pytest-asap-compliance`
  - **Fixture**: `compliance_harness`
  - **Marker**: `@pytest.mark.asap_compliance`

- [x] 3.1.4 Write package setup
  - **File**: `pyproject.toml`
  - **Dependencies**: pytest, httpx, asap-protocol

- [x] 3.1.5 Commit
  - **Command**: `git commit -m "feat(evals): create compliance package structure"`

**Acceptance Criteria**:
- [x] Package structure ready for validators

---

## Task 3.2: Handshake Validation

**Goal**: Validate agent handshake correctness

### Sub-tasks

- [x] 3.2.1 Create handshake validator
  - **File**: `validators/handshake.py`

- [x] 3.2.2 Implement connection test
  - Test: Agent responds to health check
  - Test: Correct content-type

- [x] 3.2.3 Implement manifest test
  - Test: Manifest endpoint exists
  - Test: Manifest schema valid
  - Test: Signature valid (using JCS and Strict Verification)

- [x] 3.2.4 Implement version negotiation test
  - Test: Agent reports version
  - Test: Rejects unsupported versions

- [x] 3.2.5 Write test for validator
  - Test: Against known-good agent
  - Test: Against known-bad agent

- [x] 3.2.6 Commit
  - **Command**: `git commit -m "feat(compliance): add handshake validator"`

**Acceptance Criteria**:
- [x] Handshake tests detect issues

---

## Task 3.3: Schema Validation

**Goal**: Verify Pydantic schema compliance

### Sub-tasks

- [x] 3.3.1 Create schema validator
  - **File**: `validators/schema.py`

- [x] 3.3.2 Implement envelope validation
  - Test: Envelope structure correct
  - Test: Required fields present
  - Test: Types correct

- [x] 3.3.3 Implement payload validation
  - Test: TaskRequest schema
  - Test: TaskResponse schema
  - Test: Error schema (MessageAck, McpToolResult)

- [x] 3.3.4 Implement extension handling
  - Test: Unknown fields rejected (extra='forbid')
  - Test: Extensions passed through

- [x] 3.3.5 Write comprehensive tests
  - Edge cases from property tests
  - Known-bad payloads rejected

- [x] 3.3.6 Commit
  - **Command**: `git commit -m "feat(evals): add schema validation"`

**Acceptance Criteria**:
- [x] Schema validation catches errors

---

## Task 3.4: State Machine Validation

**Goal**: Verify correct state transitions

### Sub-tasks

- [x] 3.4.1 Create state validator
  - **File**: `validators/state.py`

- [x] 3.4.2 Implement transition tests
  - Test: PENDING → RUNNING allowed
  - Test: COMPLETED → RUNNING rejected
  - Test: All valid paths work

- [x] 3.4.3 Implement terminal state tests
  - Test: COMPLETED is terminal
  - Test: FAILED is terminal
  - Test: No transitions from terminal

- [x] 3.4.4 Implement SLA validation
  - Test: Task completes within timeout
  - Test: Progress updates sent

- [x] 3.4.5 Write integration tests
  - Full task lifecycle
  - Various failure scenarios

- [x] 3.4.6 Commit
  - **Command**: `git commit -m "feat(evals): add state machine validation"`

**Acceptance Criteria**:
- [x] State machine correctness verified

---

## Sprint T3 Definition of Done

- [x] Compliance package structure ready
- [x] Handshake validation working
- [x] Schema validation working
- [x] State machine validation working
- [x] Test coverage >95%

**Total Sub-tasks**: ~22

## Documentation Updates
- [x] **Update Roadmap**: Mark completed items in [v1.2.0 Roadmap](./tasks-v1.2.0-roadmap.md)
