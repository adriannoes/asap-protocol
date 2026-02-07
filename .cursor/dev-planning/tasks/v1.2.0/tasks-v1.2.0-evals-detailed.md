# Tasks: ASAP v1.2.0 Evals & Release (T5-T6) - Detailed

> **Sprints**: T5-T6 - Compliance Harness and Release
> **Goal**: Protocol compliance testing and v1.2.0 release
> **Prerequisites**: T1-T4 completed (PKI, Registry)
> **Estimated Duration**: 2 weeks

---

## Relevant Files

### Sprint T5: Compliance Harness
- `asap-compliance/` - Separate package for compliance testing
- `asap-compliance/asap_compliance/__init__.py` - Package init
- `asap-compliance/asap_compliance/harness.py` - Test harness
- `asap-compliance/asap_compliance/validators/` - Validators
- `asap-compliance/tests/` - Self-tests

### Sprint T6: DeepEval & Release
- `asap-compliance/asap_compliance/deepeval_adapter.py` - DeepEval integration
- Documentation updates
- Release materials

---

## Sprint T5: ASAP Compliance Harness

**Context**: The Compliance Harness validates that ASAP implementations follow the protocol specification. It's a separate package that third parties can use to certify their agents are ASAP-compliant. This enables ecosystem interoperability.

### Task 5.1: Compliance Suite Structure

**Goal**: Create pytest-based compliance test package

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
  - Plugin: `pytest-asap-compliance`
  - Fixture: `compliance_harness`
  - Marker: `@pytest.mark.asap_compliance`

- [ ] 5.1.4 Write package setup
  - File: `pyproject.toml`
  - Dependencies: pytest, httpx, asap-protocol

- [ ] 5.1.5 Commit
  - Command: `git commit -m "feat(evals): create compliance package structure"`

**Acceptance**: Package structure ready for validators

---

### Task 5.2: Handshake Validation

**Goal**: Validate agent handshake correctness

- [ ] 5.2.1 Create handshake validator
  - File: `validators/handshake.py`

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
  - Command: `git commit -m "feat(evals): add handshake validation"`

**Acceptance**: Handshake tests detect issues

---

### Task 5.3: Schema Validation

**Goal**: Verify Pydantic schema compliance

- [ ] 5.3.1 Create schema validator
  - File: `validators/schema.py`

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
  - Command: `git commit -m "feat(evals): add schema validation"`

**Acceptance**: Schema validation catches errors

---

### Task 5.4: State Machine Validation

**Goal**: Verify correct state transitions

- [ ] 5.4.1 Create state validator
  - File: `validators/state.py`

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
  - Command: `git commit -m "feat(evals): add state machine validation"`

**Acceptance**: State machine correctness verified

---

## Sprint T6: DeepEval Integration & Release

### Task 6.1: DeepEval Integration (Optional)

**Goal**: Brain evaluation for intelligence metrics

- [ ] 6.1.1 Spike: DeepEval Adapter Prototype
  - Goal: Validate async compatibility and API key injection
  - Output: `prototypes/deepeval_adapter.py`
  - Validation:
    - Must use `AsyncConfig(run_async=True)` in `evaluate()`
    - Must handle `RuntimeError: This event loop is already running` via `nest_asyncio.apply()` or `loop.run_in_executor`
    - Verify `pytest-asyncio` integration works with ASAP's loop

- [ ] 6.1.2 Define Configuration Schema
  - Goal: Design `pyproject.toml` configuration for metrics
  - Example: `[tool.asap.evals] hallucination_threshold = 0.5`
  - Output: Schema definition in `asap_compliance/config.py`

- [ ] 6.1.3 Add DeepEval dependency (optional)
  - Command: `uv add --optional "deepeval>=0.21"`

- [ ] 6.1.4 Create adapter
  - File: `asap_compliance/deepeval_adapter.py`

- [ ] 6.1.5 Implement G-Eval integration
  - Metric: Custom logic assessment
  - Use: Evaluate agent reasoning

- [ ] 6.1.6 Implement safety metrics
  - Metric: Hallucination detection
  - Metric: Bias detection
  - Metric: Toxicity detection

- [ ] 6.1.7 Create Evaluation Guide
  - File: `docs/guides/evaluating-intelligence.md`
  - Content:
    - "Why evaluate?" (Verified Badge requirements)
    - Cost analysis (LLM token usage)
    - Interpreting metrics (Bias, Toxicity, Hallucination)
    - Configuration reference

- [ ] 6.1.8 Write documentation
  - How to enable DeepEval
  - Interpreting results
  - Cost considerations (LLM calls)

- [ ] 6.1.9 Commit
  - Command: `git commit -m "feat(evals): add DeepEval integration and docs"`

**Acceptance**: Intelligence metrics available

---

### Task 6.2: Comprehensive Testing

**Goal**: Validate all v1.2.0 features

- [ ] 6.2.1 Run unit tests
  - Command: `uv run pytest tests/ -v`
  - Target: 100% pass

- [ ] 6.2.2 Run integration tests
  - Registry + PKI + Discovery flow
  - Compliance harness against test agent

- [ ] 6.2.3 Run property tests
  - New crypto properties
  - Registry query properties

- [ ] 6.2.4 Run compliance harness on ASAP Server
  - Self-validate: Our server passes

- [ ] 6.2.5 Verify benchmarks
  - Signing performance
  - Registry query latency

**Acceptance**: All tests pass

---

### Task 6.3: Release Preparation

**Goal**: Prepare v1.2.0 release materials

- [ ] 6.3.1 Update CHANGELOG.md
  - Section: [1.2.0] - YYYY-MM-DD
  - Features: PKI, Registry, Evals, mTLS

- [ ] 6.3.2 Bump version
  - File: `pyproject.toml` → `1.2.0`

- [ ] 6.3.3 Update README
  - Add: Signing quick start
  - Add: Registry usage

- [ ] 6.3.4 Write migration guide
  - v1.1.0 → v1.2.0 changes
  - New recommended practices

- [ ] 6.3.5 Generate API docs
  - Crypto API
  - Registry API

- [ ] 6.3.6 Update AGENTS.md
  - Add: Crypto/signing patterns and key management
  - Add: Registry client SDK usage
  - Add: Trust levels and verification info

- [ ] 6.3.7 Complete checkpoint CP-2
  - File: [checkpoints.md](../../checkpoints.md#cp-2-post-v120-release)
  - Review learnings and update velocity tracking

**Acceptance**: Documentation complete

---

### Task 6.4: Build and Publish

**Goal**: Release v1.2.0

- [ ] 6.4.1 Create release branch
  - Branch: `release/v1.2.0`

- [ ] 6.4.2 Run CI pipeline
  - Verify: All checks pass

- [ ] 6.4.3 Tag release
  - Command: `git tag v1.2.0`

- [ ] 6.4.4 Publish main package
  - Command: `uv publish`
  - PyPI: asap-protocol==1.2.0

- [ ] 6.4.5 Publish compliance package
  - Command: `cd asap-compliance && uv publish`
  - PyPI: asap-compliance==1.2.0

- [ ] 6.4.6 Create GitHub release
  - Tag: v1.2.0
  - Notes: From CHANGELOG

- [ ] 6.4.7 Update Docker images
  - Push: `ghcr.io/adriannoes/asap-protocol:v1.2.0`

**Acceptance**: v1.2.0 published

---

## Task 6.5: Mark v1.2.0 Complete

- [ ] 6.5.1 Update roadmap to 100%
- [ ] 6.5.2 Create retrospective
- [ ] 6.5.3 Plan v1.3.0 kickoff

**Acceptance**: v1.2.0 released, ready for v1.3.0

---

**T5-T6 Definition of Done**:
- [ ] Compliance harness published
- [ ] All validators working
- [ ] DeepEval integration documented
- [ ] All tests pass
- [ ] v1.2.0 on PyPI
- [ ] asap-compliance on PyPI

**Total Sub-tasks**: ~35
