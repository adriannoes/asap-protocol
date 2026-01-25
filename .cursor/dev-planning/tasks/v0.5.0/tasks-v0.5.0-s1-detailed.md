# Tasks: ASAP v0.5.0 Sprint S1 (Detailed)

> **Sprint**: S1 - Quick Wins & Dependency Setup
> **Duration**: Flexible (3-5 days)
> **Goal**: Resolve low-hanging fruit and establish dependency monitoring

---

## Relevant Files

- `src/asap/transport/handlers.py` - Remove type: ignore
- `src/asap/transport/server.py` - Refactor handle_message
- `tests/transport/test_handlers.py` - Handler tests
- `tests/transport/test_server.py` - Server tests
- `pyproject.toml` - FastAPI upgrade
- `.github/dependabot.yml` - NEW: Dependency monitoring
- `CONTRIBUTING.md` - Dependency process
- `SECURITY.md` - Update policy

---

## Task 1.1: Remove `type: ignore` in handlers.py

**Issue**: [#10](https://github.com/adriannoes/asap-protocol/issues/10)

- [x] 1.1.1 Identify type: ignore locations
  - Command: `grep -n "type: ignore" src/asap/transport/handlers.py`
  - Document why each suppression exists
  - **Found**: 1 location at line 342
  - **Reason**: `result` is typed as `object` from `run_in_executor`, but after checking it's not awaitable, we know it's `Envelope` for sync handlers. Mypy can't narrow the type automatically.

- [x] 1.1.2 Analyze type errors
  - Run: `mypy --strict src/asap/transport/handlers.py`
  - Understand what types are mismatched
  - **Error**: `result` (type `object`) cannot be assigned to `response` (type `Envelope`)

- [x] 1.1.3 Fix type annotations
  - Refactor handler signatures with proper generics/protocols
  - Update return types as needed
  - Remove type: ignore comments
  - **Solution**: Used `cast(Envelope, result)` for explicit type narrowing

- [x] 1.1.4 Verify mypy compliance
  - Run: `mypy --strict src/asap/transport/handlers.py`
  - Expected: Success, no issues
  - **Result**: ✅ Success, no issues found

- [x] 1.1.5 Run existing tests
  - Run: `uv run pytest tests/transport/test_handlers.py -v`
  - Expected: All 20 tests pass
  - **Result**: ✅ All 35 tests passed

- [ ] 1.1.6 Commit
  - Command: `git commit -m "fix(transport): remove type: ignore in handlers.py"`
  - Close issue #10

**Acceptance**: Zero type: ignore, mypy passes, tests pass

---

## Task 1.2: Refactor handle_message into smaller helpers

**Issue**: [#9](https://github.com/adriannoes/asap-protocol/issues/9)

- [ ] 1.2.1 Analyze current function
  - Open: `src/asap/transport/server.py`
  - Find handle_message (likely 50-100 lines)
  - Identify distinct sections: parse, dispatch, error handling

- [ ] 1.2.2 Extract _validate_envelope helper
  - Create function: `_validate_envelope(body: bytes) -> Envelope`
  - Move envelope parsing and validation logic
  - Add docstring with Args/Returns/Raises

- [ ] 1.2.3 Extract _dispatch_to_handler helper
  - Create function: `async def _dispatch_to_handler(...) -> Envelope`
  - Move handler lookup and execution logic
  - Handle both sync and async handlers

- [ ] 1.2.4 Extract _create_error_response helper
  - Create function: `_create_error_response(error, request_id) -> JsonRpcErrorResponse`
  - Move exception-to-JSON-RPC mapping
  - Support all error types

- [ ] 1.2.5 Simplify handle_message
  - Rewrite as orchestrator using helpers
  - Target: <20 lines total
  - Keep try/except for top-level error handling

- [ ] 1.2.6 Add unit tests for helpers
  - File: `tests/transport/test_server.py`
  - Test each helper independently
  - Target: 10+ new tests

- [ ] 1.2.7 Run integration tests
  - Run: `uv run pytest tests/transport/test_integration.py -v`
  - Expected: All 16 tests pass

- [ ] 1.2.8 Commit
  - Command: `git commit -m "refactor(transport): extract handle_message into smaller helpers"`
  - Close issue #9

**Acceptance**: handle_message <20 lines, 10+ new tests, all tests pass

---

## Task 1.3: Upgrade FastAPI to 0.128.0+

**Issue**: [#7](https://github.com/adriannoes/asap-protocol/issues/7)

- [ ] 1.3.1 Review FastAPI changelog
  - Visit: https://fastapi.tiangolo.com/release-notes/
  - Check 0.124 → 0.128 breaking changes
  - Document anything affecting our code

- [ ] 1.3.2 Update pyproject.toml
  - Change `"fastapi>=0.124"` to `"fastapi>=0.128.0"`

- [ ] 1.3.3 Update dependencies
  - Command: `uv lock --upgrade-package fastapi`
  - Verify: `uv tree | grep fastapi`

- [ ] 1.3.4 Run full test suite
  - Command: `uv run pytest -v`
  - Expected: All 543+ tests pass

- [ ] 1.3.5 Test examples
  - Run: `uv run python -m asap.examples.run_demo`
  - Verify no errors

- [ ] 1.3.6 Run benchmarks
  - Run: `uv run pytest benchmarks/ -v`
  - Compare to v0.1.0 baseline
  - Ensure <5% regression

- [ ] 1.3.7 Commit
  - Command: `git commit -m "build(deps): upgrade FastAPI from 0.124 to 0.128.0"`
  - Close issue #7

**Acceptance**: FastAPI ≥0.128, all tests pass, no regression

---

## Task 1.4: Configure Dependabot

**Reference**: [Task 2.0](./tasks-security-review-report.md)

- [ ] 1.4.1 Create .github/dependabot.yml
  - Add pip ecosystem configuration
  - Set daily schedule, 5 PR limit
  - Labels: dependencies, security

- [ ] 1.4.2 Commit and push
  - Command: `git commit -m "ci(deps): add Dependabot for security monitoring"`
  - Push to activate Dependabot

- [ ] 1.4.3 Verify activation
  - Visit: github.com/adriannoes/asap-protocol/network/updates
  - Check: "Last checked" shows recent time

**Acceptance**: Dependabot active, daily checks configured

---

## Task 1.5: Document Dependency Process

- [ ] 1.5.1 Update CONTRIBUTING.md
  - Add section: "Reviewing Dependabot PRs"
  - Document review workflow
  - Define SLA timelines

- [ ] 1.5.2 Update SECURITY.md
  - Add "Security Update Policy" section
  - Document response times by severity
  - Link to GitHub Security Advisories

- [ ] 1.5.3 Commit documentation
  - Command: `git commit -m "docs: add dependency update review process"`

**Acceptance**: Both files updated with clear process

---

## Task 1.6: Verify CI Integration

- [ ] 1.6.1 Check pip-audit in CI
  - Review: `.github/workflows/ci.yml`
  - Verify pip-audit step exists

- [ ] 1.6.2 Test locally
  - Run: `uv run pip-audit`
  - Expected: No vulnerabilities

- [ ] 1.6.3 Create test PR
  - Make trivial change, create PR
  - Verify CI runs automatically
  - Close test PR

**Acceptance**: pip-audit runs on all PRs

---

## Task 1.7: Mark Sprint S1 Complete

- [ ] 1.7.1 Update roadmap progress
  - Open: `tasks-v0.5.0-roadmap.md`
  - Mark: Tasks 1.2-1.6 as complete `[x]`
  - Update: S1 progress to 6/6 (100%)

- [ ] 1.7.2 Update this detailed file
  - Mark: All sub-tasks 1.1.1-1.6.X as complete `[x]`
  - Add: Completion date at top

- [ ] 1.7.3 Document sprint learnings
  - Note: Challenges, adjustments needed for S2-S5

**Acceptance**: Both files marked complete, learnings noted

---

**Sprint S1 Definition of Done**:
- [ ] All tasks 1.1-1.7 completed
- [ ] Issues #7, #9, #10 closed
- [ ] Dependabot configured
- [ ] All 543+ tests passing
- [ ] mypy --strict passes
- [ ] Documentation updated
- [ ] Progress tracked in roadmap and detailed

**Total Sub-tasks**: ~45
