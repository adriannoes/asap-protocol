# Tasks: ASAP v0.5.0 Sprint S2.5 (Detailed)

> **Sprint**: S2.5 - Test Infrastructure Refactoring & Issue #17 Resolution
> **Goal**: Reorganize test structure and resolve rate limiting interference (33 failing tests)
> **Issue**: https://github.com/adriannoes/asap-protocol/issues/17

---

## Problem Statement

**Root Cause**: `slowapi.Limiter` maintains global state that persists across test executions, even with unique storage URIs. After a sequence of tests, the accumulated request count triggers rate limiting (HTTP 429) in subsequent tests.

**Impact**: 33 tests failing in full suite, all pass individually.

---

## Solution Strategy

### Three-Pronged Approach

1. **Process Isolation**: Use `pytest-xdist` to run tests in separate processes.
2. **Aggressive Monkeypatch**: Replace limiter module-level for complete isolation.
3. **Strategic Organization**: Separate rate-limiting tests from others.

---

## Relevant Files

**New Files:**
- `tests/transport/conftest.py` - Transport-specific fixtures with isolation.
- `tests/transport/unit/test_bounded_executor.py` - BoundedExecutor unit tests.
- `tests/transport/integration/test_rate_limiting.py` - Rate limiting tests ONLY.
- `tests/transport/integration/test_request_size_limits.py` - Size validation tests.
- `tests/transport/integration/test_thread_pool_bounds.py` - Thread pool bounds tests.
- `tests/transport/integration/test_metrics_cardinality.py` - Metrics cardinality tests.
- `tests/transport/integration/test_server_core.py` - Core server tests without rate limiting.
- `tests/transport/e2e/test_full_agent_flow.py` - Full E2E flow tests.

**Modified Files:**
- `tests/conftest.py` - Moved global isolated fixtures.
- `tests/transport/test_server.py` - Refactored into smaller files.
- `pyproject.toml` - Added `pytest-xdist`.
- `.github/workflows/ci.yml` - Updated CI to use parallel execution.
- `docs/testing.md` - NEW: Testing strategy guide.

---

## Task 2.5.1: Fix Critical Bug (UnboundLocalError)

- [x] 2.5.1.1 Investigate UnboundLocalError in `parse_json_body()`
- [x] 2.5.1.2 Resolve by moving import to top level
- [x] 2.5.1.3 Update test mocks for new streaming implementation
- [x] 2.5.1.4 Verify all server helper tests pass

**Acceptance**: All request handler helper tests passing and bug resolved.

---

## Task 2.5.2: Implement Process Isolation (pytest-xdist)

- [x] 2.5.2.1 Add `pytest-xdist` dependency
- [x] 2.5.2.2 Verify installation and plugin status
- [x] 2.5.2.3 Test parallel execution of transport tests
- [x] 2.5.2.4 Update CI workflow with `-n auto` flag
- [x] 2.5.2.5 Validate full suite with parallel workers

**Acceptance**: Parallel execution working correctly across local and CI environments.

---

## Task 2.5.3: Implement Resource Isolation Fixtures

- [x] 2.5.3.1 Create transport-level `conftest.py`
- [x] 2.5.3.2 Implement `isolated_limiter_factory`
- [x] 2.5.3.3 Implement aggressive `replace_global_limiter` monkeypatch
- [x] 2.5.3.4 Add `create_isolated_app` fixture for easy testing
- [x] 2.5.3.5 Verify isolation between concurrent limiters

**Acceptance**: Fixtures provide complete isolation between test cases.

---

## Task 2.5.4: Reorganize Test Directory Structure

- [x] 2.5.4.1 Create `unit/`, `integration/`, and `e2e/` directories
- [x] 2.5.4.2 Add `__init__.py` files with documentation for each level
- [x] 2.5.4.3 Verify the new logical structure

**Acceptance**: New test hierarchy established and documented.

---

## Task 2.5.5: Migrate BoundedExecutor to Unit Tests

- [x] 2.5.5.1 Create `unit/test_bounded_executor.py`
- [x] 2.5.5.2 Migrate pure logic tests (no HTTP dependencies)
- [x] 2.5.5.3 Verify unit tests pass in isolation and parallel

**Acceptance**: BoundedExecutor logic fully covered by unit tests.

---

## Task 2.5.6: Migrate Rate Limiting Tests

- [x] 2.5.6.1 Create `integration/test_rate_limiting.py`
- [x] 2.5.6.2 Apply aggressive monkeypatch pattern for the limiter
- [x] 2.5.6.3 Verify tests pass without interference from other suites

**Acceptance**: Rate limiting tests isolated and passing without 429 noise.

---

## Task 2.5.7: Create "No Rate Limiting" Base Class

- [x] 2.5.7.1 Implement `NoRateLimitTestBase` mixin in `conftest.py`
- [x] 2.5.7.2 Add auto-use fixture to disable limiting for inherited classes

**Acceptance**: Reusable base class available for non-rate-limiting tests.

---

## Task 2.5.8: Migrate Integration Tests

- [x] 2.5.8.1 Migrate Size Validation tests
- [x] 2.5.8.2 Migrate Thread Pool Bounds tests
- [x] 2.5.8.3 Migrate Metrics Cardinality tests
- [x] 2.5.8.4 Migrate Core Server integration tests
- [x] 2.5.8.5 Migrate Authentication integration tests

**Acceptance**: All sub-suites migrated and passing with rate limiting disabled.

---

## Task 2.5.9: Migrate E2E Tests

- [x] 2.5.9.1 Create `e2e/test_full_agent_flow.py`
- [x] 2.5.9.2 Migrate multi-agent round-trip scenarios
- [x] 2.5.9.3 Verify full flow passes with new infrastructure

**Acceptance**: End-to-end scenarios verified and passing.

---

## Task 2.5.10: Final Cleanup and Documentation

- [x] 2.5.10.1 Remove empty/obsolete test files
- [x] 2.5.10.2 Consolidate fixtures in the global `conftest.py`
- [x] 2.5.10.3 Create `docs/testing.md` guide
- [x] 2.5.10.4 Update `CONTRIBUTING.md` with new test guidelines

**Acceptance**: Clean test environment and comprehensive documentation.

---

## Task 2.5.11: Sprint Validation

- [x] 2.5.11.1 Run 578/578 tests sequentially (0 failures)
- [x] 2.5.11.2 Run 578/578 tests in parallel (0 failures)
- [x] 2.5.11.3 Verify overall coverage (89.42%)
- [x] 2.5.11.4 Pass all CI checks (lint, format, types, security)

**Acceptance**: Reached zero test failures and full quality gate pass.

---

**Sprint S2.5 Definition of Done**:
- [x] Issues #17 resolved (0 failing tests) ✅
- [x] Test infrastructure refactored into unit/integration/e2e ✅
- [x] pytest-xdist integrated for parallel and isolated testing ✅
- [x] Aggressive monkeypatch fixtures for limiter isolation ✅
- [x] Comprehensive testing documentation created ✅
- [x] Full quality gate pass (lint, mypy, security) ✅

**Total Sub-tasks**: ~60
