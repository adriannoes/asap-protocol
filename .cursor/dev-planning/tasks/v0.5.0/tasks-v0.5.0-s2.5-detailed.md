# Tasks: ASAP v0.5.0 Sprint S2.5 (Detailed)

> **Sprint**: S2.5 - Test Infrastructure Refactoring & Issue #17 Resolution
> **Goal**: Reorganize test structure and resolve rate limiting interference (33 failing tests)
> **Issue**: https://github.com/adriannoes/asap-protocol/issues/17

---

## Problem Statement

**Root Cause**: `slowapi.Limiter` maintains global state that persists across test executions, even with unique storage URIs. After ~18 tests using `testclient`, the accumulated request count triggers rate limiting (HTTP 429) in subsequent tests.

**Evidence**:
- Tests pass when run individually ✅
- Tests fail when run after rate limiting tests (HTTP 429) ❌
- Even with UUID-based storage isolation, interference occurs
- `slowapi` has internal state beyond storage URI

**Impact**: 33 tests failing in full suite, all pass individually

---

## Solution Strategy

### Three-Pronged Approach (All Required)

1. **Process Isolation**: Use `pytest-xdist` to run tests in separate processes
2. **Aggressive Monkeypatch**: Replace limiter module-level for complete isolation
3. **Strategic Organization**: Separate rate-limiting tests from others

This combination guarantees no interference while maintaining test quality.

---

## Relevant Files

**New Files to Create:**
- `tests/transport/conftest.py` - Transport-specific fixtures with aggressive isolation
- `tests/transport/unit/__init__.py` - Unit tests directory
- `tests/transport/unit/test_bounded_executor.py` - BoundedExecutor unit tests (8 tests)
- `tests/transport/integration/__init__.py` - Integration tests directory  
- `tests/transport/integration/test_rate_limiting.py` - Rate limiting tests ONLY (4 tests)
- `tests/transport/integration/test_request_size_limits.py` - Size validation (4 tests)
- `tests/transport/integration/test_thread_pool_bounds.py` - Thread pool tests (3 tests)
- `tests/transport/integration/test_metrics_cardinality.py` - Metrics tests (1 test)
- `tests/transport/integration/test_server_core.py` - Core server tests WITHOUT rate limiting
- `tests/transport/e2e/__init__.py` - E2E tests directory
- `tests/transport/e2e/test_full_agent_flow.py` - Full E2E flow (16 tests)

**Files to Modify:**
- `tests/conftest.py` - Remove global isolated_rate_limiter (move to transport/conftest.py)
- `tests/transport/test_server.py` - Extract classes to separate files, keep only core
- `tests/transport/test_middleware.py` - Remove TestRateLimiting, keep auth tests
- `tests/transport/test_executors.py` - Remove after migration OR delete if empty
- `tests/transport/test_integration.py` - Move to e2e/
- `pyproject.toml` - Add pytest-xdist dependency
- `.github/workflows/ci.yml` - Update pytest command with -n auto

**Documentation:**
- `docs/testing.md` - NEW: Testing strategy and organization guide
- `CONTRIBUTING.md` - Update with new test structure guidelines

---

## Task 2.5.1: Fix Critical Bug (UnboundLocalError)

**Issue**: Variable 'json' accessed before assignment in `ASAPRequestHandler.parse_json_body()`

- [x] 2.5.1.1 Investigate the bug
  - File: `src/asap/transport/server.py`
  - Method: `ASAPRequestHandler.parse_json_body()`
  - Issue: `import json` inside try block, accessed in except block
  - Status: ✅ **FIXED** - Moved import to top of file

- [x] 2.5.1.2 Fix by moving import
  - Move: `import json` to top of server.py (line ~43)
  - Remove: Duplicate import from parse_json_body method
  - Status: ✅ **DONE**

- [x] 2.5.1.3 Update test mocks for new streaming implementation
  - File: `tests/transport/test_server.py`
  - Class: `TestASAPRequestHandlerHelpers`
  - Update: Mock `request.stream()` instead of `request.json()`
  - Reason: Server now uses `request.stream()` for chunk-by-chunk validation
  - Status: ✅ **DONE** - All 3 tests updated and passing

- [x] 2.5.1.4 Run tests
  - Command: `pytest tests/transport/test_server.py::TestASAPRequestHandlerHelpers -v`
  - Expected: All tests pass
  - Result: ✅ **15/15 tests passing**

- [x] 2.5.1.5 Commit ✅
  - Command: `git commit -m "fix(test): resolve UnboundLocalError and update mocks for streaming"`
  - Status: ✅ **DONE** - Committed in 4199096

**Acceptance**: All TestASAPRequestHandlerHelpers tests pass ✅ **COMPLETE**

---

## Task 2.5.2: Add pytest-xdist

**Why First**: Provides process-level isolation that eliminates rate limiting interference

- [x] 2.5.2.1 Add dependency
  - File: `pyproject.toml`
  - Add: `pytest-xdist = ">=3.5.0"` in dev-dependencies
  - Command: `uv add --dev "pytest-xdist>=3.5.0"`
  - **Status**: ✅ Added to `pyproject.toml` in `[project.optional-dependencies].dev`
  - **Note**: User needs to run `uv sync --all-extras --dev` to install

- [x] 2.5.2.2 Verify installation
  - Command: `uv run pytest --version | grep xdist`
  - OR: `python -c "import xdist; print(xdist.__version__)"`
  - **Status**: ✅ Installed successfully
  - **Verification Results**: 
    - `import xdist` succeeds: xdist version: 3.8.0
    - pytest-xdist plugin is available and ready to use

- [x] 2.5.2.3 Test parallel execution
  - Command: `uv run pytest tests/transport/test_middleware.py -n 2 -v`
  - Expected: Tests pass in parallel (2 workers)
  - Verify: No interference between workers
  - **Status**: ✅ All tests passed in parallel
  - **Results**: 
    - 25 tests passed with 2 workers
    - Execution time: 2.47s
    - No failures or interference detected
    - Process isolation working correctly

- [x] 2.5.2.4 Update CI workflow
  - File: `.github/workflows/ci.yml`
  - Find: Line with `pytest` command
  - Update: Add `-n auto` flag
  - Example: `uv run pytest -n auto --tb=short --cov=src --cov-report=xml`
  - **Status**: ✅ Updated CI workflow with `-n auto` flag
  - **Verification**: CI workflow line 61 shows: `uv run pytest -n auto --tb=short --cov=src --cov-report=xml`

- [x] 2.5.2.5 Test full suite with xdist
  - Command: `PYTHONPATH=src uv run pytest -n auto --tb=no -q`
  - Expected: Significantly fewer failures (process isolation helps)
  - Note: Number of failures before/after
  - **Status**: ✅ Suite executed successfully with parallel workers
  - **Results**:
    - **575 passed** ✅
    - **2 failed** (down from previous failures - process isolation helping!)
    - **1 skipped**
    - **Execution time**: 4.21s (very fast with parallel execution)
    - **Coverage**: 89.16% overall
  - **Failures**:
    1. `test_metrics_updated_on_error_request` - assert 0.0 >= 1.0 (metrics issue)
    2. `test_authentication_missing_header_returns_error` - assert 429 == 200 (rate limiting interference - needs isolated limiter)
  - **Analysis**: Process isolation is working! Only 2 failures remain, likely due to missing isolated_rate_limiter in some tests

- [x] 2.5.2.6 Commit ✅
  - Command: `git commit -m "build(deps): add pytest-xdist for process-isolated testing"`
  - Status: ✅ **DONE** - Committed in 4e5d055

**Acceptance**: pytest-xdist installed, parallel execution working, CI updated
- ✅ Dependency added to pyproject.toml
- ✅ CI workflow updated
- ⏳ Installation pending (user needs to run `uv sync --all-extras --dev`)

**CRITICAL**: This alone may reduce failures significantly. Validate before proceeding.

---

## Task 2.5.3: Create Aggressive Monkeypatch Fixture

**Purpose**: For tests that can't use xdist, provide module-level limiter replacement

- [x] 2.5.3.1 Create tests/transport/conftest.py
  - File: New file
  - Docstring: Explain transport-specific fixtures and isolation strategy
  - Status: ✅ **DONE** - File created with comprehensive docstring explaining aggressive monkeypatch strategy

- [x] 2.5.3.2 Add isolated_limiter_factory fixture
  - Type: Factory fixture (returns function)
  - Returns: Function that creates Limiter with UUID storage
  - Status: ✅ **DONE** - Fixture created, accepts optional limits parameter, returns function that creates isolated limiters

- [x] 2.5.3.3 Add replace_global_limiter fixture
  - Type: Fixture with monkeypatch
  - Purpose: Replace module-level limiter completely
  - Status: ✅ **DONE** - Fixture created, replaces limiters in both middleware and server modules

- [x] 2.5.3.4 Add no_auth_manifest fixture
  - Purpose: Manifest without auth for simple tests
  - ID: "urn:asap:agent:test-transport"
  - Status: ✅ **DONE** - Fixture already existed, verified working

- [x] 2.5.3.5 Add create_isolated_app fixture
  - Type: Factory fixture
  - Purpose: Create app with completely isolated limiter
  - Parameters: manifest, rate_limit, max_request_size, max_threads, use_monkeypatch
  - Uses: replace_global_limiter if use_monkeypatch=True
  - Status: ✅ **DONE** - Fixture updated to accept use_monkeypatch parameter and use aggressive monkeypatch when enabled

- [x] 2.5.3.6 Test fixtures
  - Create: Temporary test file
  - Verify: All fixtures work
  - Verify: Limiter is actually isolated
  - Delete: Temporary test file
  - Status: ✅ **DONE** - All 6 tests passed, verified isolation between limiters, temporary file deleted

- [x] 2.5.3.7 Run mypy
  - Command: `mypy tests/transport/conftest.py`
  - Expected: Pass or only minor warnings
  - Status: ✅ **DONE** - Only expected warnings about missing stubs (import-untyped), no real errors

- [x] 2.5.3.8 Commit ✅
  - Command: `git commit -m "feat(test): add aggressive monkeypatch fixtures for limiter isolation"`
  - Status: ✅ **DONE** - Committed in f3f46e8

**Acceptance**: Fixtures created, tested, provide true isolation ✅ **COMPLETE**

---

## Task 2.5.4: Create Test Directory Structure

- [x] 2.5.4.1 Create directories
  - Command: `mkdir -p tests/transport/{unit,integration,e2e}`
  - Status: ✅ **DONE** - Directories already existed, verified structure

- [x] 2.5.4.2 Create __init__.py files
  - File: `tests/transport/unit/__init__.py`
  - Status: ✅ **DONE** - Updated with correct content explaining unit test purpose

- [x] 2.5.4.3 Create integration __init__.py
  - File: `tests/transport/integration/__init__.py`
  - Status: ✅ **DONE** - Updated with correct content including IMPORTANT note about fixtures

- [x] 2.5.4.4 Create e2e __init__.py
  - File: `tests/transport/e2e/__init__.py`
  - Status: ✅ **DONE** - Updated with correct content explaining E2E test purpose

- [x] 2.5.4.5 Verify structure
  - Command: `tree tests/transport -L 2 -I __pycache__`
  - Expected: See unit/, integration/, e2e/ with __init__.py
  - Status: ✅ **DONE** - Structure verified: all 3 directories exist with __init__.py files

- [x] 2.5.4.6 Commit ✅
  - Command: `git commit -m "feat(test): create unit/integration/e2e directory structure"`
  - Status: ✅ **DONE** - Committed in 77bd179

**Acceptance**: Directory structure created with documentation ✅ **COMPLETE**

---

## Task 2.5.5: Migrate BoundedExecutor to Unit Tests

- [x] 2.5.5.1 Create unit/test_bounded_executor.py
  - File: `tests/transport/unit/test_bounded_executor.py`
  - Copy: TestBoundedExecutor class from test_executors.py (8 tests)
  - Copy: All necessary imports
  - Note: NO HTTP, NO rate limiting - pure unit tests
  - Status: ✅ **DONE** - File already exists with all 8 tests migrated

- [x] 2.5.5.2 Run tests in isolation
  - Command: `pytest tests/transport/unit/test_bounded_executor.py -v`
  - Expected: 8/8 tests pass
  - Status: ✅ **DONE** - All 8 tests passed successfully

- [x] 2.5.5.3 Run with xdist
  - Command: `pytest tests/transport/unit/test_bounded_executor.py -n 2 -v`
  - Expected: 8/8 tests pass in parallel
  - Status: ✅ **DONE** - All 8 tests passed in parallel with 2 workers

- [x] 2.5.5.4 Remove from old location
  - File: `tests/transport/test_executors.py`
  - Remove: TestBoundedExecutor class
  - Keep: TestBoundedExecutorStarvation (moves to integration later)
  - Status: ✅ **DONE** - TestBoundedExecutor removed, only TestBoundedExecutorStarvation remains

- [x] 2.5.5.5 Commit ✅
  - Command: `git commit -m "refactor(test): migrate BoundedExecutor to unit tests"`
  - Status: ✅ **DONE** - Committed in ffedfaa

**Acceptance**: 8/8 unit tests passing, no HTTP dependencies ✅ **COMPLETE**

---

## Task 2.5.6: Migrate Rate Limiting Tests (ISOLATED FILE)

**CRITICAL**: Rate limiting tests MUST be in a separate file that runs in isolated process

- [x] 2.5.6.1 Create integration/test_rate_limiting.py
  - File: `tests/transport/integration/test_rate_limiting.py`
  - Copy: TestRateLimiting class from test_middleware.py (4 tests)
  - Update: Use replace_global_limiter fixture with monkeypatch
  - Status: ✅ **DONE** - File created with all 4 tests using aggressive monkeypatch pattern

- [x] 2.5.6.2 Add module-level pytest mark
  - Add at top of file:
    ```python
    pytestmark = pytest.mark.filterwarnings("ignore::DeprecationWarning")
    ```
  - Status: ✅ **DONE** - pytestmark added to filter deprecation warnings

- [x] 2.5.6.3 Run tests in isolation
  - Command: `pytest tests/transport/integration/test_rate_limiting.py -v`
  - Expected: 4/4 tests pass
  - Status: ✅ **DONE** - All 4 tests passed successfully

- [x] 2.5.6.4 Run with xdist (CRITICAL TEST)
  - Command: `pytest tests/transport/integration/test_rate_limiting.py -n 2 -v`
  - Expected: 4/4 tests pass in parallel
  - Verify: No "429 Too Many Requests" errors
  - Status: ✅ **DONE** - All 4 tests passed in parallel with 2 workers, no interference

- [x] 2.5.6.5 Run with OTHER tests (CRITICAL TEST)
  - Command: `pytest tests/transport/integration/test_rate_limiting.py tests/transport/unit/ -v`
  - Expected: All tests pass
  - Verify: No interference
  - Status: ✅ **DONE** - All 12 tests passed (4 rate limiting + 8 unit), zero interference

- [x] 2.5.6.6 Remove from old location
  - File: `tests/transport/test_middleware.py`
  - Remove: TestRateLimiting class (keep auth tests)
  - Status: ✅ **DONE** - TestRateLimiting class and related fixtures removed, 21 auth tests still passing

- [x] 2.5.6.7 Commit ✅
  - Command: `git commit -m "refactor(test): isolate rate limiting tests with aggressive monkeypatch"`
  - Status: ✅ **DONE** - Committed in 8aef1da

**Acceptance**: Rate limiting tests completely isolated, 4/4 passing with no interference ✅ **COMPLETE**

**CRITICAL VALIDATION**: ✅ All validation tests passed - monkeypatch is working correctly!

---

## Task 2.5.7: Create "No Rate Limiting" Test Base Class

**Purpose**: Provide base class for tests that should NOT use rate limiting

- [x] 2.5.7.1 Add to tests/transport/conftest.py
  - Add: `NoRateLimitTestBase` class
  - Purpose: Mixin that disables rate limiting completely
  - Status: ✅ **DONE** - Class added with autouse fixture that disables rate limiting

- [x] 2.5.7.2 Document usage
  - Add docstring example showing inheritance
  - Status: ✅ **DONE** - Docstring includes example showing how to inherit from the class

**Acceptance**: Base class created, ready for use in non-rate-limiting tests ✅ **COMPLETE**

---

## Task 2.5.8: Migrate Size Validation Tests

- [x] 2.5.8.1 Create integration/test_request_size_limits.py
  - File: `tests/transport/integration/test_request_size_limits.py`
  - Inherit: `NoRateLimitTestBase` (from conftest)
  - Copy: TestPayloadSizeValidation from test_server.py (4 tests)
  - Note: Rate limiting automatically disabled via base class
  - Status: ✅ **DONE** - File created with all 4 tests, inheriting from NoRateLimitTestBase

- [x] 2.5.8.2 Run tests in isolation
  - Command: `pytest tests/transport/integration/test_request_size_limits.py -v`
  - Expected: 4/4 tests pass
  - Status: ✅ **DONE** - All 4 tests passed successfully

- [x] 2.5.8.3 Run with rate limiting tests (CRITICAL)
  - Command:
    ```
    pytest \
      tests/transport/integration/test_rate_limiting.py \
      tests/transport/integration/test_request_size_limits.py \
      -v
    ```
  - Expected: 8/8 tests pass (4 rate + 4 size)
  - Verify: No 429 errors in size validation tests
  - Status: ✅ **DONE** - All 8 tests passed (4 rate limiting + 4 size validation), zero interference

- [x] 2.5.8.4 Remove from old location
  - File: `tests/transport/test_server.py`
  - Remove: TestPayloadSizeValidation class
  - Status: ✅ **DONE** - Class removed from test_server.py

- [x] 2.5.8.5 Commit ✅
  - Command: `git commit -m "refactor(test): migrate size validation with rate limiting disabled"`
  - Status: ✅ **DONE** - Included in 77bd179 (directory structure commit)

**Acceptance**: Size tests isolated, no rate limiting interference ✅ **COMPLETE**

---

## Task 2.5.9: Migrate Thread Pool Tests

- [x] 2.5.9.1 Create integration/test_thread_pool_bounds.py
  - File: `tests/transport/integration/test_thread_pool_bounds.py`
  - Inherit: `NoRateLimitTestBase`
  - Copy: TestThreadPoolExhaustion from test_server.py (2 tests - 1 skipped, 1 direct)
  - Copy: TestBoundedExecutorStarvation from test_executors.py (1 test)
  - Total: 3 tests (1 may remain skipped for HTTP test)
  - Status: ✅ **DONE** - File created with all 3 tests, inheriting from NoRateLimitTestBase

- [x] 2.5.9.2 Remove skip from HTTP test
  - Test: `test_thread_pool_exhaustion_returns_503`
  - Try: Remove @pytest.mark.skipif decorator
  - Reason: NoRateLimitTestBase should prevent interference
  - Status: ✅ **DONE** - Skip removed, test now runs without decorator

- [x] 2.5.9.3 Run tests in isolation
  - Command: `pytest tests/transport/integration/test_thread_pool_bounds.py -v`
  - Expected: 3/3 tests pass
  - Status: ✅ **DONE** - All 3 tests passed successfully

- [x] 2.5.9.4 Run with ALL other integration tests (CRITICAL)
  - Command: `pytest tests/transport/integration/ -v`
  - Expected: All integration tests pass
  - Verify: No 429 errors in thread pool tests
  - Status: ✅ **DONE** - All 11 integration tests passed (4 rate limiting + 4 size validation + 3 thread pool), zero interference

- [x] 2.5.9.5 Remove from old locations
  - File: `tests/transport/test_server.py` - Remove TestThreadPoolExhaustion
  - File: `tests/transport/test_executors.py` - Remove TestBoundedExecutorStarvation
  - Status: ✅ **DONE** - Both classes removed from old locations

- [x] 2.5.9.6 Commit ✅
  - Command: `git commit -m "refactor(test): migrate thread pool tests with rate limiting disabled"`
  - Status: ✅ **DONE** - Included in 77bd179 (directory structure commit)

**Acceptance**: 3/3 thread pool tests passing without interference ✅ **COMPLETE**

---

## Task 2.5.10: Migrate Metrics Cardinality Tests

- [x] 2.5.10.1 Create integration/test_metrics_cardinality.py
  - File: `tests/transport/integration/test_metrics_cardinality.py`
  - Inherit: `NoRateLimitTestBase`
  - Copy: TestMetricsCardinalityProtection from test_server.py (1 test)
  - Status: ✅ **DONE** - File created with test, inheriting from NoRateLimitTestBase

- [x] 2.5.10.2 Run test
  - Command: `pytest tests/transport/integration/test_metrics_cardinality.py -v`
  - Expected: 1/1 test passes
  - Status: ✅ **DONE** - Test passed successfully

- [x] 2.5.10.3 Remove from old location
  - File: `tests/transport/test_server.py`
  - Remove: TestMetricsCardinalityProtection class
  - Status: ✅ **DONE** - Class removed from test_server.py

- [x] 2.5.10.4 Commit ✅
  - Command: `git commit -m "refactor(test): migrate metrics cardinality with rate limiting disabled"`
  - Status: ✅ **DONE** - Included in 77bd179 (directory structure commit)

**Acceptance**: Metrics test isolated, passing ✅ **COMPLETE**

---

## Task 2.5.11: Migrate Core Server Tests (No Rate Limiting)

**Purpose**: Extract non-Sprint-S2 tests from test_server.py to new file

- [x] 2.5.11.1 Create integration/test_server_core.py
  - File: `tests/transport/integration/test_server_core.py`
  - Inherit: `NoRateLimitTestBase`
  - Copy: TestAsapEndpoint (11 tests)
  - Copy: TestHandlerRegistryIntegration (3 tests)
  - Copy: TestMetricsEndpoint (3 tests)
  - Copy: TestServerExceptionHandling (2 tests)
  - Total: ~19 tests

- [x] 2.5.11.2 Update all fixtures to use disable_rate_limiting
  - Since inheriting from NoRateLimitTestBase, rate limiting auto-disabled
  - Verify: No need for isolated_rate_limiter in fixtures
  - Simplify: Remove rate limiting configuration
  - Status: ✅ **DONE** - All classes inherit from NoRateLimitTestBase, fixtures simplified

- [x] 2.5.11.3 Fix TestAuthenticationIntegration rate limiting issue
  - File: `tests/transport/test_server.py`
  - Class: `TestAuthenticationIntegration`
  - Issue: `test_authentication_missing_header_returns_error` failing with 429 (rate limit)
  - Current: Already uses `isolated_rate_limiter` but still fails
  - Solution: Update to use `NoRateLimitTestBase` OR ensure complete isolation
  - Options:
    - Option A: Add TestAuthenticationIntegration to test_server_core.py with NoRateLimitTestBase
    - Option B: Create separate test file for auth tests with NoRateLimitTestBase
    - Option C: Verify isolated_rate_limiter is working correctly (may need different approach)
  - Action: Choose best approach (see our codebase for benchmark) and implement
  - Verify: `test_authentication_missing_header_returns_error` passes after fix
  - Status: ✅ **DONE** - TestAuthenticationIntegration migrated to test_server_core.py with NoRateLimitTestBase, test now passes!

- [x] 2.5.11.4 Run tests
  - Command: `pytest tests/transport/integration/test_server_core.py -v`
  - Expected: 19/19 tests pass (or more if TestAuthenticationIntegration included)
  - Status: ✅ **DONE** - 30/31 tests passed (1 test has pre-existing metrics issue, not related to migration)

- [x] 2.5.11.5 Run with rate limiting tests (CRITICAL)
  - Command: `pytest tests/transport/integration/ -v`
  - Expected: All integration tests pass
  - Verify: No interference
  - Verify: `test_authentication_missing_header_returns_error` passes
  - Status: ✅ **DONE** - 42/43 tests passed (only pre-existing metrics test fails), zero interference, authentication test passes!

- [x] 2.5.11.5a Investigate and fix metrics test failure
  - Test: `test_metrics_updated_on_error_request` in `TestMetricsEndpoint`
  - Issue: `assert 0.0 >= 1.0` - error metrics not being recorded
  - Location: `tests/transport/integration/test_server_core.py`
  - Root Cause: ✅ **FOUND** - `_normalize_payload_type_for_metrics` normalizes payload_type to "other" when no handler is registered
  - Solution: ✅ **FIXED** - Changed test to use `{"payload_type": "other", "error_type": "handler_not_found"}` instead of `{"payload_type": "task.request", ...}`
  - Investigation results:
    1. ✅ Metrics reset is working correctly (fixture `reset_metrics_before_test`)
    2. ✅ Error is being triggered correctly (handler not found)
    3. ✅ Metrics collector is recording the error correctly
    4. ✅ Metric key format issue: payload_type is normalized to "other" for unregistered handlers
    5. ✅ This is expected behavior (DoS protection via cardinality explosion prevention)
  - Status: ✅ **DONE** - Test fixed and passing, all 43 integration tests passing

- [x] 2.5.11.6 Remove from old location
  - **Prerequisite**: ✅ Task 2.5.11.5a completed (metrics test fixed)
  - File: `tests/transport/test_server.py`
  - Remove: All migrated classes:
    - TestAsapEndpoint ✅
    - TestHandlerRegistryIntegration ✅
    - TestMetricsEndpoint ✅
    - TestServerExceptionHandling ✅
    - TestAuthenticationIntegration ✅
  - Keep: TestAppFactory, TestManifestEndpoint, TestErrorHandling, TestASAPRequestHandlerHelpers ✅
  - Verify: All tests in test_server_core.py pass before removing (✅ 31/31 passing)
  - Verify: All remaining tests in test_server.py pass (✅ 23/23 passing)
  - Status: ✅ **DONE** - All classes removed, file cleaned up, tests passing

- [x] 2.5.11.7 Commit ✅
  - Command: `git commit -m "refactor(test): migrate core server tests with rate limiting disabled"`
  - Status: ✅ **DONE** - Included in 77bd179 (directory structure commit)

**Acceptance**: Core server tests isolated, TestAuthenticationIntegration fixed ✅ **COMPLETE**
- ✅ test_server_core.py created with all classes migrated
- ✅ All classes inherit from NoRateLimitTestBase
- ✅ TestAuthenticationIntegration now passes (was failing with 429)
- ✅ **43/43 integration tests passing** (zero interference, metrics test fixed!)
- ✅ Metrics test fixed (payload_type normalization issue resolved)
- ✅ All migrated classes removed from test_server.py (task 2.5.11.6)
- ✅ test_server.py cleaned up (only 4 classes remain, 23/23 tests passing)

---

## Task 2.5.12: Migrate E2E Tests

- [x] 2.5.12.1 Move entire file
  - Command: `git mv tests/transport/test_integration.py tests/transport/e2e/test_full_agent_flow.py`
  - Status: ✅ **DONE** - File moved and old file deleted

- [x] 2.5.12.2 Update class to inherit NoRateLimitTestBase
  - Open: `tests/transport/e2e/test_full_agent_flow.py`
  - Add: Import NoRateLimitTestBase
  - Update: All test classes to inherit from it
  - Example:
    ```python
    from ..conftest import NoRateLimitTestBase
    
    class TestFullRoundTrip(NoRateLimitTestBase):
        # Automatically gets rate limiting disabled
    ```
  - Status: ✅ **DONE** - All 6 classes now inherit from NoRateLimitTestBase, fixture simplified

- [x] 2.5.12.3 Run tests
  - Command: `pytest tests/transport/e2e/test_full_agent_flow.py -v`
  - Expected: 16/16 tests pass
  - Status: ✅ **DONE** - All 16/16 tests passed successfully

- [x] 2.5.12.4 Run with integration tests (CRITICAL)
  - Command: `pytest tests/transport/integration/ tests/transport/e2e/ -v`
  - Expected: All tests pass
  - Verify: No interference between integration and e2e
  - Status: ✅ **DONE** - All 59 tests passed (43 integration + 16 E2E), zero interference

- [x] 2.5.12.5 Commit ✅
  - Command: `git commit -m "refactor(test): migrate E2E tests to dedicated directory"`
  - Status: ✅ **DONE** - Committed in e3b568c

**Acceptance**: E2E tests in e2e/, 16/16 passing ✅ **COMPLETE**

---

## Task 2.5.13: Clean Up and Consolidate

- [x] 2.5.13.1 Check test_server.py remaining tests
  - File: `tests/transport/test_server.py`
  - Count: How many tests remain after migrations?
  - Decision: If < 10 tests, consider merging into integration/test_server_core.py
  - Status: ✅ **DONE** - 23 tests in 4 classes remain (keep as is, > 10 tests)

- [x] 2.5.13.2 Check test_executors.py
  - File: `tests/transport/test_executors.py`
  - If: Only TestBoundedExecutorStarvation remains
  - Action: Already moved to integration/test_thread_pool_bounds.py
  - Action: Delete file with `git rm tests/transport/test_executors.py`
  - Status: ✅ **DONE** - File deleted (was empty)

- [x] 2.5.13.3 Check test_middleware.py
  - File: `tests/transport/test_middleware.py`
  - After: TestRateLimiting removed
  - Remaining: Auth tests (should be fine, already use monkeypatch)
  - Action: Keep file for auth tests
  - Status: ✅ **DONE** - File kept (contains auth tests)

- [x] 2.5.13.4 Update global conftest.py
  - File: `tests/conftest.py`
  - Remove: isolated_rate_limiter fixture (moved to transport/conftest.py)
  - Keep: sample_manifest, sample_task_request, sample_envelope
  - Status: ✅ **DONE** - Fixture removed, test_server.py updated to not use it

- [x] 2.5.13.5 Run mypy on test files and fix errors/warnings
  - Command: `PYTHONPATH=src uv run mypy tests/transport/`
  - Focus: New test files created during migration
  - Files to check:
    - `tests/transport/conftest.py`
    - `tests/transport/unit/test_bounded_executor.py`
    - `tests/transport/integration/test_rate_limiting.py`
    - `tests/transport/integration/test_request_size_limits.py`
    - `tests/transport/integration/test_thread_pool_bounds.py`
    - `tests/transport/integration/test_metrics_cardinality.py`
    - `tests/transport/integration/test_server_core.py`
    - `tests/transport/e2e/test_full_agent_flow.py`
  - Action: Fix type errors and warnings (ignore import-untyped if from external libs)
  - Note: Some warnings about missing stubs are expected and can be ignored
  - Status: ✅ **DONE** - Fixed type annotations:
    - Fixed `isolated_limiter_factory` calls in conftest.py
    - Added type annotations to async generator functions in test_server.py
    - Fixed type annotations in test_rate_limiting.py
    - Fixed threading.atomic issue in test_handlers.py
    - Added type: ignore for create_app return type in test_server_core.py

- [x] 2.5.13.6 Commit ✅
  - Command: `git commit -m "refactor(test): clean up old test files and consolidate fixtures"`
  - Status: ✅ **DONE** - Committed in 9a4bc1d

**Acceptance**: No duplicate code, fixtures consolidated, mypy errors fixed ✅ **COMPLETE**
- ✅ test_executors.py deleted (was empty)
- ✅ isolated_rate_limiter removed from tests/conftest.py
- ✅ test_server.py updated to not use removed fixture
- ✅ All type errors fixed (only import-untyped warnings remain, which are expected)
- ✅ All tests passing (23/23 in test_server.py)

---

## Task 2.5.14: Validate All Sprint S2 Tests Together

**CRITICAL VALIDATION**: This is the true test of success

- [x] 2.5.14.1 Run ALL Sprint S2 tests together
  - Command:
    ```bash
    pytest \
      tests/transport/integration/test_rate_limiting.py \
      tests/transport/integration/test_request_size_limits.py \
      tests/transport/unit/test_bounded_executor.py \
      tests/transport/integration/test_thread_pool_bounds.py \
      tests/transport/integration/test_metrics_cardinality.py \
      -v
    ```
  - Expected: 20/20 tests pass
  - Track: Any failures
  - Status: ✅ **DONE** - All 20/20 tests passed successfully

- [x] 2.5.14.2 Run with pytest-xdist (parallel)
  - Command: Same as above + `-n auto`
  - Expected: 20/20 tests pass in parallel
  - Note: Execution time
  - Status: ✅ **DONE** - All 20/20 tests passed in parallel (8 workers, 3.39s)

- [x] 2.5.14.3 Run with ALL integration tests
  - Command: `pytest tests/transport/integration/ -v`
  - Expected: ~32+ tests pass (S2 + core server tests)
  - Verify: ZERO rate limiting interference
  - Status: ✅ **DONE** - All 43/43 integration tests passed, zero interference!

- [x] 2.5.14.4 If failures occur
  - STOP: Do not proceed
  - Investigate: Which test is failing and why
  - Check: Monkeypatch is actually replacing limiter
  - Check: NoRateLimitTestBase is being used
  - Fix: Before continuing
  - Status: ✅ **N/A** - No failures occurred

**Acceptance**: ALL Sprint S2 tests pass together with zero interference ✅ **COMPLETE**
- ✅ 20/20 Sprint S2 tests passing (sequential)
- ✅ 20/20 Sprint S2 tests passing (parallel with pytest-xdist)
- ✅ 43/43 integration tests passing (includes Sprint S2 + core server tests)
- ✅ Zero rate limiting interference detected
- ✅ Strategy validated successfully!

**BLOCKER**: ✅ **RESOLVED** - All tests passing, refactoring strategy successful!

---

## Task 2.5.15: Validate Full Test Suite

- [x] 2.5.15.1 Run complete test suite (sequential)
  - Command: `PYTHONPATH=src uv run pytest --tb=short -v`
  - Expected: 578+ tests
  - Target: 0 failures (was 33 failures before)
  - Track: Actual number of failures
  - Status: ✅ **DONE** - 578/578 tests passed, 0 failures, 3.43s execution time

- [x] 2.5.15.2 Run with pytest-xdist (parallel)
  - Command: `PYTHONPATH=src uv run pytest -n auto --tb=short -v`
  - Expected: Same results as sequential
  - Note: Execution time improvement
  - Status: ✅ **DONE** - 578/578 tests passed, 0 failures, 3.62s execution time

- [x] 2.5.15.3 Run CI checks
  - Lint: `uv run ruff check .`
  - Format: `uv run ruff format --check .`
  - Types: `uv run mypy src/`
  - Security: `uv run pip-audit`
  - Expected: All pass
  - Status: ✅ **DONE** - All checks passed:
    - ✅ Linting: Fixed 3 unused imports (AsyncMock)
    - ✅ Formatting: 76 files already formatted
    - ✅ Type checking: Success (31 source files)
    - ✅ Security: No known vulnerabilities found

- [x] 2.5.15.3a Fix mypy errors in test files
  - Command: `PYTHONPATH=src uv run mypy tests/transport/ tests/`
  - Action: Fix any type errors found (not just warnings)
  - Focus: Real type errors, not import-untyped warnings from external libs
  - Verify: Run mypy again to confirm fixes
  - Note: This ensures all test files have proper type annotations
  - Status: ✅ **DONE** - Removed 10 unused `# type: ignore` comments from test_jsonrpc.py

- [x] 2.5.15.4 Check test coverage
  - Command: `PYTHONPATH=src uv run pytest --cov=src --cov-report=term-missing --cov-fail-under=50`
  - Expected: Coverage ≥50% maintained
  - Note: Coverage percentage
  - Status: ✅ **DONE** - Coverage: 89.42% (well above 50% requirement)

- [x] 2.5.15.5 Document results
  - Tests passing: 578/578 ✅
  - Tests failing: 0 ✅
  - Coverage: 89.42% ✅ (well above 50% requirement)
  - Execution time: sequential 3.43s vs parallel 3.62s
  - CI checks: All passing ✅
    - Linting: ✅ (fixed 3 unused imports)
    - Formatting: ✅ (76 files formatted)
    - Type checking: ✅ (31 source files, no errors)
    - Security: ✅ (no vulnerabilities)
  - Status: ✅ **DONE** - Full validation complete!

**Acceptance**: Full suite passes, 0 failures, all CI checks pass ✅ **COMPLETE**
- ✅ 578/578 tests passing (sequential)
- ✅ 578/578 tests passing (parallel with pytest-xdist)
- ✅ 0 failures (down from 33 failures before refactoring!)
- ✅ Coverage: 89.42% (well above 50% requirement)
- ✅ All CI checks passing (lint, format, types, security)
- ✅ All mypy errors in test files fixed (removed unused type: ignore comments)

---

## Task 2.5.16: Update Documentation

- [x] 2.5.16.1 Create docs/testing.md
  - File: `docs/testing.md`
  - Sections:
    - "Test Organization" - Explain unit/integration/e2e structure ✅
    - "Rate Limiting in Tests" - Explain NoRateLimitTestBase ✅
    - "Test Isolation Strategy" - **NEW**: Explain our three-pronged approach ✅
      - Process isolation (pytest-xdist) ✅
      - Aggressive monkeypatch fixtures (for tests that can't use xdist) ✅
      - Strategic test organization (separate rate-limiting tests) ✅
      - **Why "Aggressive Monkeypatch"**: Explain decision to replace module-level limiters ✅
        - Problem: slowapi.Limiter maintains global state that persists across tests ✅
        - Solution: Fixtures that replace limiter at module level, not just app level ✅
        - Rationale: Ensures complete isolation even when code uses global limiter directly ✅
        - Example: Show how `replace_global_limiter` fixture works ✅
        - When to use: For tests that can't benefit from pytest-xdist process isolation ✅
    - "Pytest Fixtures Explained" - **NEW**: Educational section ✅
      - What are fixtures? (concept explanation) ✅
      - Factory fixtures vs regular fixtures ✅
      - How fixtures provide test isolation ✅
      - Our specific fixtures: `isolated_limiter_factory`, `replace_global_limiter`, `create_isolated_app` ✅
      - Why we created these: Decision rationale and trade-offs ✅
    - "Running Tests" - Commands for each test type ✅
    - "Writing New Tests" - Which directory, which base class ✅
    - "Parallel Execution" - pytest-xdist usage ✅
  - Status: ✅ **DONE** - Comprehensive documentation created with all required sections

- [x] 2.5.16.2 Update CONTRIBUTING.md
  - Section: Testing ✅
  - Add: Reference to docs/testing.md ✅
  - Add: Note about rate limiting interference ✅
  - Add: Requirement to use NoRateLimitTestBase or isolated_limiter_factory ✅
  - Add: Brief explanation of our test isolation strategy (three-pronged approach) ✅
  - Add: Link to "Test Isolation Strategy" section in docs/testing.md for details ✅
  - Status: ✅ **DONE** - Testing section added with all required information

- [x] 2.5.16.3 Update mkdocs.yml
  - Add: docs/testing.md to navigation ✅
  - Under: "Guides" section (moved from root level) ✅
  - Status: ✅ **DONE** - testing.md added to Guides section in navigation

- [x] 2.5.16.4 Commit ✅
  - Command: `git commit -m "docs(test): add comprehensive testing strategy documentation"`
  - Status: ✅ **DONE** - Committed in 8298453

**Acceptance**: Documentation complete, clear guidelines for contributors ✅ **COMPLETE**
- ✅ docs/testing.md created with comprehensive content
- ✅ CONTRIBUTING.md updated with testing section
- ✅ mkdocs.yml updated with testing.md in Guides section
- ✅ All sections include required information about test isolation strategy

---

## Task 2.5.17: Close Issue #17 and Update PR #16

- [x] 2.5.17.1 Update Issue #17 ✅
  - Action: Add comment explaining resolution ✅
  - Content: Added comprehensive resolution comment ✅
  - Action: Close issue ✅
  - Label: Add "resolved" label ✅
  - Status: ✅ **DONE** - Issue #17 closed with resolution comment and "resolved" label

- [x] 2.5.17.2 Update PR #16 description ✅
  - Add: Section about Issue #17 resolution ✅
  - Content: Added comment to PR #16 mentioning Issue #17 resolution ✅
  - Add: Link to Sprint S2.5 detailed tasks ✅
  - Status: ✅ **DONE** - Comment added to PR #16 (already merged)

- [x] 2.5.17.3 Update this task file ✅
  - Mark: All tasks as complete [x], especially those that need to be committed ✅
  - Add: Completion date and Final test counts ✅
  - **Completion Date**: January 26, 2026
  - **Final Test Counts**:
    - Total tests: 578/578 passing ✅
    - Failures: 0 (down from 33) ✅
    - Coverage: 89.42% ✅
    - Execution time: 3.43s (sequential), 3.62s (parallel)
  - **All Commits Completed**: ✅
    - 2.5.1.5: 4199096 ✅
    - 2.5.2.6: 4e5d055 ✅
    - 2.5.3.8: f3f46e8 ✅
    - 2.5.4.6: 77bd179 ✅
    - 2.5.5.5: ffedfaa ✅
    - 2.5.6.7: 8aef1da ✅
    - 2.5.8.5: Included in 77bd179 ✅
    - 2.5.9.6: Included in 77bd179 ✅
    - 2.5.10.4: Included in 77bd179 ✅
    - 2.5.11.7: Included in 77bd179 ✅
    - 2.5.12.5: e3b568c ✅
    - 2.5.13.6: 9a4bc1d ✅
    - 2.5.16.4: 8298453 ✅

- [x] 2.5.17.4 Update roadmap ✅
  - File: `tasks-v0.5.0-roadmap.md`
  - Mark: Sprint S2.5 as complete ✅
  - Update: Progress percentage ✅
  - Status: ✅ **DONE** - Roadmap updated, progress: 33/49 tasks (67.35%)

- [x] 2.5.17.5 Commit ✅
  - Command: `git commit -m "docs: mark Sprint S2.5 complete and close Issue #17"`
  - Status: ✅ **DONE** - Committed in b2e05ee

**Acceptance**: Issue closed, PR updated, documentation current

---

**Sprint S2.5 Definition of Done**:

- [x] All 33 failing tests now passing (Issue #17 resolved) ✅
  - Status: 578/578 tests passing, 0 failures (down from 33)
- [x] pytest-xdist installed and working ✅
  - Status: Installed in pyproject.toml, verified working with -n 2
- [x] NoRateLimitTestBase created and used in all non-rate-limiting tests ✅
  - Status: Created in conftest.py, used in 19 test classes
- [x] Test structure reorganized: unit/, integration/, e2e/ ✅
  - Status: All three directories created with __init__.py files
- [x] All 578+ tests passing with 0 failures ✅
  - Status: 578/578 tests passing, 89.42% coverage
- [x] Tests pass both sequentially AND in parallel (pytest-xdist) ✅
  - Status: Verified sequential (3.43s) and parallel (3.62s) execution
- [x] Documentation complete (docs/testing.md created) ✅
  - Status: Comprehensive 461-line testing guide created
- [x] CONTRIBUTING.md updated with test guidelines ✅
  - Status: Testing section added with references to docs/testing.md
- [x] Issue #17 closed with resolution notes ✅
  - Status: Closed with comprehensive resolution comment and "resolved" label
- [x] All CI checks passing (lint, format, mypy, security) ✅
  - Status: All checks passing (ruff, format, mypy, pip-audit)
- [x] No regressions introduced ✅
  - Status: 578/578 tests passing, all existing functionality preserved

**Critical Success Metric**: Run full suite 3 times in a row - all must pass with 0 failures

**Total Sub-tasks**: ~50 detailed steps across 11 main tasks

---

## Troubleshooting Guide

### If Rate Limiting Interference Persists

**Symptom**: Tests still getting HTTP 429 even with monkeypatch

**Debugging Steps**:

1. **Verify monkeypatch is applied**:
   ```python
   def test_something(self, monkeypatch):
       # Add debug print
       import asap.transport.middleware
       print(f"Limiter ID before: {id(asap.transport.middleware.limiter)}")
       
       # Apply monkeypatch
       new_limiter = create_isolated_limiter()
       monkeypatch.setattr(asap.transport.middleware, "limiter", new_limiter)
       
       print(f"Limiter ID after: {id(asap.transport.middleware.limiter)}")
       # IDs should be different
   ```

2. **Check if app.state.limiter is used**:
   - Server uses `app.state.limiter` at runtime
   - Ensure BOTH module limiter AND app.state.limiter are replaced

3. **Nuclear option - Disable globally**:
   ```python
   @pytest.fixture(autouse=True, scope="session")
   def disable_all_rate_limiting(monkeypatch_session):
       """Disable rate limiting for entire test session."""
       # This runs ONCE for all tests
       from slowapi import Limiter
       no_limit = Limiter(key_func=lambda r: "test", default_limits=[])
       monkeypatch_session.setattr("asap.transport.middleware.limiter", no_limit)
   ```

4. **Contact maintainer**:
   - If all else fails, this may be a slowapi bug
   - Consider: Opening issue with slowapi project
   - Workaround: Mock slowapi entirely for non-rate-limiting tests

---

## Notes

- **Incremental commits**: Commit after each successful task
- **Validation at each step**: Don't proceed if tests fail
- **Rollback strategy**: Keep old files until migration validated
- **Issue #17**: Link all commits to this issue for traceability
