# Sprint T6: DeepEval Integration & Release

> **Goal**: Intelligence metrics and v1.2.0 release
> **Prerequisites**: Sprint T5 completed (Compliance Harness)
> **Parent Roadmap**: [tasks-v1.2.0-roadmap.md](./tasks-v1.2.0-roadmap.md)

---

## Relevant Files

- `asap-compliance/asap_compliance/deepeval_adapter.py` - DeepEval integration
- `docs/guides/evaluating-intelligence.md` - Evaluation guide
- `pyproject.toml` - Version bump
- `CHANGELOG.md` - Release notes
- `README.md` - Quick start updates
- `AGENTS.md` - AI agent instructions

---

## Context

Sprint T6 adds optional intelligence metrics via DeepEval and prepares the v1.2.0 release.

---

## Task 6.1: DeepEval Integration (Optional)

**Goal**: Brain evaluation for intelligence metrics

### Sub-tasks

- [ ] 6.1.1 Spike: DeepEval Adapter Prototype
  - **Goal**: Validate async compatibility and API key injection
  - **Output**: `prototypes/deepeval_adapter.py`
  - **Validation**:
    - Must use `AsyncConfig(run_async=True)`
    - Handle async event loop issues

- [ ] 6.1.2 Define Configuration Schema
  - **Goal**: Design `pyproject.toml` configuration for metrics
  - **Example**: `[tool.asap.evals] hallucination_threshold = 0.5`

- [ ] 6.1.3 Add DeepEval dependency (optional)
  - **Command**: `uv add --optional "deepeval>=0.21"`

- [ ] 6.1.4 Create adapter
  - **File**: `asap_compliance/deepeval_adapter.py`

- [ ] 6.1.5 Implement G-Eval integration
  - **Metric**: Custom logic assessment
  - **Use**: Evaluate agent reasoning

- [ ] 6.1.6 Implement safety metrics
  - **Metric**: Hallucination detection
  - **Metric**: Bias detection
  - **Metric**: Toxicity detection

- [ ] 6.1.7 Create Evaluation Guide
  - **File**: `docs/guides/evaluating-intelligence.md`
  - **Content**: Why evaluate, cost analysis, interpreting metrics

- [ ] 6.1.8 Write documentation
  - How to enable DeepEval
  - Interpreting results
  - Cost considerations (LLM calls)

- [ ] 6.1.9 Commit
  - **Command**: `git commit -m "feat(evals): add DeepEval integration and docs"`

**Acceptance Criteria**:
- [ ] Intelligence metrics available
- [ ] Documentation complete

---

## Task 6.2: Comprehensive Testing

**Goal**: Validate all v1.2.0 features

### Sub-tasks

- [ ] 6.2.1 Run unit tests
  - **Command**: `uv run pytest tests/ -v`
  - **Target**: 100% pass

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

**Acceptance Criteria**:
- [ ] All tests pass
- [ ] Coverage >95%

---

## Task 6.3: Release Preparation

**Goal**: Prepare v1.2.0 release materials

### Sub-tasks

- [ ] 6.3.1 Update CHANGELOG.md
  - **Section**: [1.2.0] - YYYY-MM-DD
  - **Features**: PKI, Registry, Evals, mTLS

- [ ] 6.3.2 Bump version
  - **File**: `pyproject.toml` → `1.2.0`

- [ ] 6.3.3 Update README
  - **Add**: Signing quick start
  - **Add**: Registry usage

- [ ] 6.3.4 Write migration guide
  - v1.1.0 → v1.2.0 changes
  - New recommended practices

- [ ] 6.3.5 Generate API docs
  - Crypto API
  - Registry API

- [ ] 6.3.6 Update AGENTS.md
  - **Add**: Crypto/signing patterns and key management
  - **Add**: Registry client SDK usage
  - **Add**: Trust levels and verification info

- [ ] 6.3.7 Complete checkpoint CP-2
  - **File**: [checkpoints.md](../../checkpoints.md#cp-2-post-v120-release)
  - Review learnings and update velocity tracking

**Acceptance Criteria**:
- [ ] Documentation complete

---

## Task 6.4: Build and Publish

**Goal**: Release v1.2.0

### Sub-tasks

- [ ] 6.4.1 Create release branch
  - **Branch**: `release/v1.2.0`

- [ ] 6.4.2 Run CI pipeline
  - **Verify**: All checks pass

- [ ] 6.4.3 Tag release
  - **Command**: `git tag v1.2.0`

- [ ] 6.4.4 Publish main package
  - **Command**: `uv publish`
  - **PyPI**: asap-protocol==1.2.0

- [ ] 6.4.5 Publish compliance package
  - **Command**: `cd asap-compliance && uv publish`
  - **PyPI**: asap-compliance==1.2.0

- [ ] 6.4.6 Create GitHub release
  - **Tag**: v1.2.0
  - **Notes**: From CHANGELOG

- [ ] 6.4.7 Update Docker images
  - **Push**: `ghcr.io/adriannoes/asap-protocol:v1.2.0`

**Acceptance Criteria**:
- [ ] v1.2.0 published
- [ ] asap-compliance published

---

## Task 6.5: Mark v1.2.0 Complete

### Sub-tasks

- [ ] 6.5.1 Update roadmap to 100%
- [ ] 6.5.2 Create retrospective
- [ ] 6.5.3 Plan v1.3.0 kickoff

**Acceptance Criteria**:
- [ ] v1.2.0 released, ready for v1.3.0

---

## Sprint T6 Definition of Done

- [ ] DeepEval integration documented
- [ ] All tests pass
- [ ] v1.2.0 on PyPI
- [ ] asap-compliance on PyPI
- [ ] Docker image published

**Total Sub-tasks**: ~28
