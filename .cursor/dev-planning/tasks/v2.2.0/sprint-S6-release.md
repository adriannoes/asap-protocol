# Sprint S6: Release v2.2.0

**Branch**: `release/v2.2.0`
**PR Scope**: Version bump, changelog, docs update, CI verification, tag & publish
**Depends on**: All previous sprints (S0-S5)

---

## Tasks

### 1.0 Pre-Release Verification

- [ ] 1.1 Full CI verification
  - **What**: Run complete CI suite:
    ```bash
    uv run ruff check .
    uv run ruff format --check .
    uv run mypy src/ scripts/ tests/
    PYTHONPATH=src uv run pytest --cov=src --cov-report=xml
    uv run pip-audit
    ```
  - **Verify**: All commands exit 0

- [ ] 1.2 Review test coverage
  - **What**: Ensure >= 90% coverage for all new v2.2 code (auth/identity, auth/capabilities, auth/lifecycle, auth/approval, auth/self_auth, auth/agent_jwt, models/payloads TaskStream, transport/server new endpoints, economics/audit).
  - **Verify**: Coverage report confirms

### 2.0 Version & Documentation

- [ ] 2.1 Bump version to 2.2.0
  - **Files**: `pyproject.toml`, `src/asap/__init__.py`
  - **What**: Change version to `2.2.0`.
  - **Verify**: `uv run python -c "import asap; print(asap.__version__)"` shows 2.2.0

- [ ] 2.2 Update CHANGELOG.md
  - **File**: `CHANGELOG.md`
  - **What**: Add `## [2.2.0]` section documenting all changes:
    - **Identity & Auth**: Per-runtime-agent identity, capability-based authz with constraints, agent lifecycle, approval flows, self-auth prevention
    - **Streaming**: SSE endpoint, TaskStream payload, client streaming
    - **Errors**: RecoverableError/FatalError, recovery hints, error code registry
    - **Versioning**: ASAP-Version header, content negotiation
    - **Async**: AsyncSnapshotStore/AsyncMeteringStore protocols
    - **Batch**: JSON-RPC batch operations
    - **Audit**: Tamper-evident audit logging with hash chain
    - **Compliance**: Harness v2 with expanded checks

- [ ] 2.3 Update AGENTS.md
  - **File**: `AGENTS.md`
  - **What**: Update project context with v2.2 features. Add Identity & Auth to architecture description.
  - **Verify**: AGENTS.md reflects current state

- [ ] 2.4 Update migration guide
  - **File**: `docs/migration.md` (modify)
  - **What**: Add v2.1 → v2.2 migration section covering: adopting per-agent identity (optional), defining capabilities, migrating to AsyncSnapshotStore, adding ASAP-Version header.
  - **Verify**: Migration steps are accurate

### 3.0 Tag & Publish

- [ ] 3.1 Create git tag
  - **What**: `git tag -a v2.2.0 -m "Release v2.2.0 — Protocol Hardening"` and push
  - **Verify**: Tag triggers release workflow

- [ ] 3.2 Verify PyPI publication
  - **What**: Confirm `pip install asap-protocol==2.2.0` works
  - **Verify**: Package available on PyPI

---

## Definition of Done

- [ ] All CI checks pass (ruff, mypy, pytest, pip-audit)
- [ ] Test coverage >= 90% for new code
- [ ] Version 2.2.0 in pyproject.toml and __init__.py
- [ ] CHANGELOG.md complete
- [ ] AGENTS.md updated
- [ ] Migration guide updated
- [ ] v2.2.0 tagged and published to PyPI
