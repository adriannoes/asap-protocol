# Tasks: Sprint 3 PR Feedback - Improvements & Enhancements

> Task list generated from [sprint3-code-review.md](../sprint3-code-review.md)
> 
> **Context**: This task list addresses the feedback and recommendations identified during the Sprint 3 code review (PR #3). These are incremental improvements to enhance code quality, coverage, and production-readiness.

---

## Relevant Files

### Sprint 3 Improvements
- `src/asap/transport/client.py` - Async HTTP client (✅ 100% coverage, added pragma comments)
- `tests/transport/test_client.py` - Client unit tests (✅ added 7 new retry edge case tests)
- `src/asap/transport/handlers.py` - Handler registry (✅ thread-safe with RLock)
- `src/asap/transport/server.py` - FastAPI server (✅ integrated HandlerRegistry, 100% coverage)
- `tests/transport/test_server.py` - Server tests (✅ added 5 registry integration tests)
- `tests/transport/test_handlers.py` - Handler tests (✅ added 5 thread safety tests)

### Sprint 4 Integration
- `src/asap/transport/server.py` - Integrate HandlerRegistry
- `src/asap/examples/echo_agent.py` - Echo agent implementation
- `src/asap/examples/coordinator.py` - Coordinator agent implementation
- `src/asap/examples/run_demo.py` - Demo runner script
- `src/asap/examples/README.md` - Examples documentation

### Observability
- `src/asap/observability/__init__.py` - Observability module (✅ implemented)
- `src/asap/observability/logging.py` - Structured logging configuration (✅ implemented)
- `src/asap/observability/metrics.py` - Prometheus metrics (optional, pending)
- `tests/observability/__init__.py` - Test package (✅ created)
- `tests/observability/test_logging.py` - Logging tests (✅ 16 tests)

### Notes

- **Test runner**: Use `uv run pytest` for faster execution
- **Specific tests**: `uv run pytest tests/transport/` to run transport tests
- **Coverage target**: 95%+ for all transport modules

---

## Tasks

### Phase 1: High-Level Tasks

- [x] 1.0 Improve Client Test Coverage (87% → 95%) ✅
- [x] 2.0 Add Thread Safety to HandlerRegistry ✅
- [x] 3.0 Integrate HandlerRegistry into Server ✅
- [x] 4.0 Implement Structured Logging ✅
- [x] 5.0 Add Observability & Metrics (Optional)
- [x] 6.0 Enhance Client Retry Configuration

---

## Task Breakdown

### 1.0 Improve Client Test Coverage (87% → 95%) 🟡 Medium Priority

**Goal**: Increase test coverage for `client.py` from 87% to 95%+ by testing retry edge cases and error scenarios.

- [x] 1.1 Analyze current coverage gaps ✅
  - Run `uv run pytest tests/transport/test_client.py --cov=asap.transport.client --cov-report=html`
  - Identify uncovered lines (200, 256, 278-285)
  - Document which scenarios are missing
  
  **Analysis Results** (2026-01-20):
  - Coverage: 87% (82 stmts, 7 miss, 18 branches, 4 partial)
  - Line 200: `send()` called outside context manager
  - Line 256: Response missing envelope in result
  - Lines 278-280: Unexpected exceptions wrapped
  - Lines 282-285: Max retries exceeded edge case
  - Branch 178→exit: `__aexit__` when not connected
  
- [x] 1.2 Add test for max retries exceeded ✅
  - Create test that simulates network failures exceeding `max_retries`
  - Verify `ASAPConnectionError` is raised with appropriate message
  - Verify all retry attempts were made
  
- [x] 1.3 Add test for intermittent network errors ✅
  - Mock transport to fail first N requests, then succeed
  - Verify client retries successfully
  - Verify final request succeeds and returns correct envelope
  
- [x] 1.4 Add test for retry timing validation ✅
  - Note: Current implementation doesn't have exponential backoff delays
  - Tested retry count behavior instead
  - Backoff configuration will be added in Task 6.0
  
- [x] 1.5 Add test for idempotency key usage ✅
  - Verify idempotency key is included in retried requests
  - Verify key remains consistent across retry attempts (both in params and header)
  
- [x] 1.6 Verify coverage improvement ✅
  - Run coverage report again
  - Confirm coverage is ≥95%
  - Update documentation if needed
  
  **Final Results** (2026-01-20):
  - Coverage: **100%** (79 stmts, 0 miss, 14 branches, 0 partial)
  - Added 7 new tests in `TestASAPClientRetryEdgeCases` class
  - Defensive code (lines 283-285) marked with `# pragma: no cover`
  - All linting checks passed (ruff, mypy --strict)

**Definition of Done**:
- ✅ Coverage ≥95% for `client.py` → **Achieved 100%**
- ✅ All retry edge cases tested
- ✅ Tests pass in CI

---

### 2.0 Add Thread Safety to HandlerRegistry 🟢 Low Priority ✅

**Goal**: Make `HandlerRegistry` thread-safe for potential multi-threaded environments.

- [x] 2.1 Add threading support ✅
  - Import `threading.RLock`
  - Add `self._lock = RLock()` to `__init__`
  - Document thread-safety in class docstring
  
- [x] 2.2 Protect `register()` method ✅
  - Wrap dict write operation with `with self._lock:`
  - Add docstring note about thread safety
  
- [x] 2.3 Protect `dispatch()` method ✅
  - Wrap dict read operation with `with self._lock:`
  - Ensure handler lookup is atomic
  - Execute handler outside lock for better concurrency
  
- [x] 2.4 Protect `has_handler()` method ✅
  - Wrap dict read with lock
  
- [x] 2.5 Protect `list_handlers()` method ✅
  - Wrap dict keys access with lock
  - Return copy of keys list (not view)
  
- [x] 2.6 Add thread safety tests ✅
  - Create test with concurrent registrations from multiple threads
  - Create test with concurrent dispatches
  - Create test with mixed register/dispatch operations
  - Verify no race conditions or exceptions
  
  **Implementation Results** (2026-01-20):
  - Added 5 new tests in `TestHandlerRegistryThreadSafety` class
  - Tests verify concurrent operations with 10+ threads and 100+ operations each
  - All linting checks passed (ruff, mypy --strict)
  - Coverage: 100% for `handlers.py`

**Definition of Done**:
- ✅ All registry operations are thread-safe
- ✅ Concurrent access tests passing (5 new tests)
- ✅ Documentation updated (docstrings + module docs)

---

### 3.0 Integrate HandlerRegistry into Server 🟡 Medium Priority ✅

**Goal**: Replace temporary `_process_envelope()` function with proper `HandlerRegistry` dispatch.

- [x] 3.1 Refactor `create_app()` signature ✅
  - Add optional `registry: HandlerRegistry | None = None` parameter
  - If `None`, use `registry = create_default_registry()`
  - Update docstring with registry parameter
  
- [x] 3.2 Update `handle_asap_message()` endpoint ✅
  - Remove `_process_envelope()` call
  - Replace with `response_envelope = registry.dispatch(envelope, manifest)`
  - Add error handling for `HandlerNotFoundError`
  
- [x] 3.3 Map `HandlerNotFoundError` to JSON-RPC error ✅
  - Catch `HandlerNotFoundError` in endpoint
  - Return `JsonRpcErrorResponse` with `METHOD_NOT_FOUND` code
  - Include payload_type in error data
  
- [x] 3.4 Remove deprecated `_process_envelope()` function ✅
  - Delete function definition (56 lines removed)
  - Verify no other references exist
  
- [x] 3.5 Update default app instance ✅
  - `app = create_app(_create_default_manifest(), create_default_registry())`
  
- [x] 3.6 Update server tests ✅
  - Added `TestHandlerRegistryIntegration` class with 5 new tests
  - Test for custom handler registration
  - Test for unknown payload type error
  - All 21 server tests passing

  **Implementation Results** (2026-01-20):
  - `server.py` reduced from 304 to 288 lines (removed deprecated code)
  - Coverage: **100%** for `server.py`
  - All 121 transport tests passing
  - All linting checks passed (ruff, mypy --strict)

**Definition of Done**:
- ✅ HandlerRegistry fully integrated
- ✅ `_process_envelope()` removed
- ✅ All tests passing (121 tests)
- ✅ Custom handlers can be registered

---

### 4.0 Implement Structured Logging 🟡 Medium Priority ✅

**Goal**: Add structured logging with trace_id and correlation_id throughout the transport layer.

- [x] 4.1 Create observability module ✅
  - Create `src/asap/observability/__init__.py`
  - Create `src/asap/observability/logging.py`
  
- [x] 4.2 Configure structlog ✅
  - Add `structlog>=24.1` to `pyproject.toml` dependencies (installed v25.5.0)
  - Configure structlog with JSON renderer for production
  - Configure console renderer for development
  - Set up log levels (INFO for production, DEBUG for dev)
  
- [x] 4.3 Create logger factory ✅
  - Implement `get_logger(name: str) -> BoundLogger`
  - Bind common context (service_name, environment)
  - Export from `observability/__init__.py`
  - Added `bind_context()` and `clear_context()` helpers
  
- [x] 4.4 Add logging to server endpoints ✅
  - Log `asap.request.received` with envelope_id, trace_id, payload_type
  - Log `asap.request.processed` with duration_ms
  - Log `asap.request.error` for exceptions
  - Log `asap.request.invalid_*` for validation errors
  
- [x] 4.5 Add logging to client ✅
  - Log `asap.client.send` with target URL, envelope_id
  - Log `asap.client.retry` for retry attempts
  - Log `asap.client.response` with duration_ms
  - Log `asap.client.error` for failures
  
- [x] 4.6 Add logging to handlers ✅
  - Log `asap.handler.registered` when handler is registered
  - Log `asap.handler.dispatch` with payload_type
  - Log `asap.handler.completed` with duration_ms
  - Log `asap.handler.error` for handler exceptions
  
- [x] 4.7 Add tests for logging ✅
  - Created `tests/observability/test_logging.py`
  - Test log configuration (console/json, log levels)
  - Test context binding and clearing
  - Test logger integration with transport modules
  
- [x] 4.8 Update documentation ✅
  - Docstrings added to all logging functions
  - Environment variables documented (ASAP_LOG_FORMAT, ASAP_LOG_LEVEL, ASAP_SERVICE_NAME)

  **Implementation Results** (2026-01-20):
  - Added `structlog>=24.1` dependency
  - Created `src/asap/observability/` module with 2 files
  - Added structured logging to server, client, handlers
  - Created 16 tests for logging functionality
  - All 333 tests passing with 97.52% coverage
  - All linting checks passed (ruff, mypy --strict)

**Definition of Done**:
- ✅ Structured logging configured
- ✅ All transport operations logged
- ✅ trace_id included in all logs
- ✅ Tests capture and verify logs (16 new tests)

---

### 5.0 Add Observability & Metrics (Optional) 🟢 Low Priority

**Goal**: Add Prometheus metrics for monitoring production deployments.

- [x] 5.1 Add Prometheus dependencies
  - Add `prometheus-fastapi-instrumentator>=7.0` to pyproject.toml
  - Add `prometheus-client>=0.20` for custom metrics
  
- [x] 5.2 Create metrics module
  - Create `src/asap/observability/metrics.py`
  - Define metrics: request_latency_seconds (Histogram), request_total (Counter), active_connections (Gauge)
  
- [x] 5.3 Instrument FastAPI server
  - Use `Instrumentator()` to auto-instrument FastAPI
  - Add custom `/metrics` endpoint
  - Instrument `/asap` endpoint specifically
  
- [x] 5.4 Add custom metrics
  - Counter: `asap_requests_total{payload_type, status}`
  - Histogram: `asap_request_duration_seconds{payload_type}`
  - Gauge: `asap_active_handlers{payload_type}`
  
- [x] 5.5 Instrument client
  - Counter: `asap_client_requests_total{target, status}`
  - Histogram: `asap_client_duration_seconds{target}`
  - Counter: `asap_client_retries_total{target}`
  
- [x] 5.6 Add metrics tests
  - Test metrics endpoint returns Prometheus format
  - Test counters increment correctly
  - Test histograms record durations
  
- [x] 5.7 Add Grafana dashboard example
  - Create `src/asap/examples/grafana-dashboard.json`
  - Include panels for latency, throughput, errors
  - Document dashboard setup in README
  - Test for all CI (Lint, Security, etc) before commit.

**Definition of Done**:
- ✅ Prometheus metrics exposed
- ✅ `/metrics` endpoint available
- ✅ Key metrics tracked (latency, throughput, errors)
- ✅ Example dashboard provided

---

### 6.0 Enhance Client Retry Configuration 🟢 Low Priority

**Goal**: Make retry backoff parameters configurable for production flexibility.

- [x] 6.1 Update `ASAPClient.__init__()` signature
  - Add `retry_backoff_factor: float = 2.0` parameter
  - Add `retry_backoff_max: float = 60.0` parameter
  - Store as instance attributes
  
- [x] 6.2 Create `RetryConfig` dataclass
  - Define `@dataclass RetryConfig` with max_retries, backoff_factor, backoff_max
  - Add factory method `RetryConfig.default()`
  - Use in `ASAPClient.__init__(retry_config: RetryConfig | None = None)`
  
- [x] 6.3 Update retry logic in `send()`
  - Use `self.retry_config.backoff_factor` for exponential backoff
  - Use `self.retry_config.backoff_max` to cap delay
  - Calculate: `delay = min(backoff_factor ** attempt, backoff_max)`
  
- [x] 6.4 Add retry configuration tests
  - Test custom backoff_factor (e.g., 1.5)
  - Test custom backoff_max (e.g., 30.0)
  - Test delay calculations are correct
  - Test configuration via `RetryConfig` dataclass
  
- [x] 6.5 Update client documentation
  - Document retry configuration in docstring
  - Add example with custom retry settings
  - Explain backoff algorithm
  
- [x] 6.6 Add configuration example
  - Create `src/asap/examples/client_with_custom_retry.py`
  - Show different retry configurations for different scenarios

**Definition of Done**:
- ✅ Retry parameters configurable
- ✅ `RetryConfig` dataclass implemented
- ✅ Tests verify custom configurations
- ✅ Documentation updated

---

## Priority Summary

| Priority | Tasks | Total Sub-tasks |
|----------|-------|-----------------|
| 🟡 Medium | 1.0, 3.0, 4.0 | 22 |
| 🟢 Low | 2.0, 5.0, 6.0 | 20 |

**Recommended Order**:
1. Task 1.0 - Client coverage (quick win)
2. Task 3.0 - HandlerRegistry integration (architectural improvement)
3. Task 4.0 - Structured logging (production readiness)
4. Task 2.0 - Thread safety (future-proofing)
5. Task 6.0 - Retry config (flexibility)
6. Task 5.0 - Metrics (nice-to-have)

---

**Total Tasks**: 6 parent tasks, 42 sub-tasks  
**Estimated Effort**: ~3-4 days for all improvements  
**Quick Wins**: Tasks 1.0 (1 day) and 2.0 (0.5 day) can be completed first
