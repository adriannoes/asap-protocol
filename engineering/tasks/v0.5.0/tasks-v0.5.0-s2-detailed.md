# Tasks: ASAP v0.5.0 Sprint S2 (Detailed)

> **Sprint**: S2 - DoS Prevention & Rate Limiting
> **Duration**: Flexible (5-7 days)
> **Goal**: Implement rate limiting and request size validation
> **Completed**: 2026-01-25

---

## Relevant Files

- `pyproject.toml` - Add slowapi dependency
- `src/asap/transport/middleware.py` - Rate limiting
- `src/asap/transport/server.py` - Integrate limiter, size validation, and thread pool
- `src/asap/models/constants.py` - Add MAX_REQUEST_SIZE
- `src/asap/transport/executors.py` - BoundedExecutor for thread pool limiting
- `src/asap/errors.py` - Add ThreadPoolExhaustedError
- `src/asap/observability/metrics.py` - Add thread pool metrics
- `src/asap/transport/handlers.py` - Integrate bounded executor
- `tests/transport/test_middleware.py` - Rate limit tests
- `tests/transport/test_server.py` - Size validation and metrics tests
- `tests/transport/test_executors.py` - BoundedExecutor tests
- `docs/security.md` - DoS prevention documentation

---

## Task 2.1: Add slowapi Dependency

- [x] 2.1.1 Research slowapi compatibility
  - Check: slowapi documentation
  - Verify FastAPI 0.128+ support

- [x] 2.1.2 Add dependency
  - Command: `uv add "slowapi>=0.1.9"`

- [x] 2.1.3 Test import
  - Run: `python -c "from slowapi import Limiter; print('OK')"`

- [x] 2.1.4 Commit ✅

**Acceptance**: slowapi ≥0.1.9 installed and importable

---

## Task 2.2: Implement Rate Limiting Middleware

- [x] 2.2.1 Add sender extraction function to middleware.py
  - Function: `_get_sender_from_envelope(request: Request) -> str`
  - Logic: Extract sender from envelope, fallback to IP

- [x] 2.2.2 Create rate limiter instance
  - Create limiter with sender-based key function
  - Default: 100 requests/minute
  - Storage: memory://

- [x] 2.2.3 Add rate limit exception handler
  - Function: `rate_limit_handler(request, exc: RateLimitExceeded)`
  - Return: JSON-RPC formatted error with Retry-After header
  - Status: HTTP 429

- [x] 2.2.4 Export from middleware module
  - Update __all__: Add limiter, rate_limit_handler

- [x] 2.2.5 Run mypy

- [x] 2.2.6 Commit ✅

**Acceptance**: Rate limiter created, exports work, mypy passes

---

## Task 2.3: Integrate Rate Limiter in Server

- [x] 2.3.1 Import limiter in server.py
  - Add: `from .middleware import limiter, rate_limit_handler`

- [x] 2.3.2 Add rate_limit parameter to create_app
  - Parameter: `rate_limit: str | None = None`
  - Default from env: ASAP_RATE_LIMIT or "100/minute"

- [x] 2.3.3 Configure limiter in app
  - Set: `app.state.limiter = limiter`
  - Add exception handler for RateLimitExceeded

- [x] 2.3.4 Apply to /asap endpoint
  - Add decorator: `@limiter.limit(rate_limit_str)`
  - Make configurable via create_app parameter

- [x] 2.3.5 Test locally
  - Start server, send rapid requests
  - Verify 101st request gets HTTP 429

- [x] 2.3.6 Commit ✅

**Acceptance**: Rate limiting works, HTTP 429 after limit

---

## Task 2.4: Add Request Size Validation

- [x] 2.4.1 Add constant
  - File: `src/asap/models/constants.py`
  - Add: `MAX_REQUEST_SIZE = 10 * 1024 * 1024  # 10MB`

- [x] 2.4.2 Add size validation function
  - File: `src/asap/transport/server.py`
  - Function: `_validate_request_size(request, max_size) -> None`
  - Check Content-Length header first
  - Raise HTTPException(413) if too large

- [x] 2.4.3 Apply validation in endpoint
  - Call before reading body
  - Also validate actual body size after reading

- [x] 2.4.4 Add max_request_size parameter to create_app
  - Parameter: `max_request_size: int | None = None`
  - Default from env or 10MB

- [x] 2.4.5 Test locally
  - Send requests under and over 10MB
  - Verify rejection of large files

- [x] 2.4.6 Commit ✅

**Acceptance**: Size validation rejects >10MB, normal requests work

---

## Task 2.5: Add Rate Limiting Tests

- [x] 2.5.1 Add TestRateLimiting class to test_middleware.py
  - Test: Requests within limit succeed
  - Test: Exceeding limit returns 429
  - Test: Limit resets after window
  - Test: Different senders independent

- [x] 2.5.2 Run tests
  - Command: `uv run pytest tests/transport/test_middleware.py::TestRateLimiting -v`

- [x] 2.5.3 Commit ✅

**Acceptance**: All rate limiting tests passing

---

## Task 2.6: Add Payload Size Tests

- [x] 2.6.1 Add TestPayloadSizeValidation class to test_server.py
  - Test: Requests <10MB accepted
  - Test: Requests >10MB rejected
  - Test: Content-Length validation
  - Test: Actual body size validation

- [x] 2.6.2 Run tests
  - Command: `uv run pytest tests/transport/test_server.py::TestPayloadSizeValidation -v`

- [x] 2.6.3 Commit ✅

**Acceptance**: All payload size validation tests passing

---

## Task 2.7: Update Security Documentation

- [x] 2.7.1 Add Rate Limiting section to docs/security.md
  - Section: "## Rate Limiting"
  - Content: Configuration, defaults, recommendations

- [x] 2.7.2 Add Request Size Limits section
  - Section: "## Request Size Limits"
  - Content: Default limit, configuration, rationale

- [x] 2.7.3 Update table of contents and checklist

- [x] 2.7.4 Commit ✅

**Acceptance**: Documentation complete with configuration examples

---

## Task 2.8: Harden Thread Pool Execution

- [x] 2.8.1 Create bounded executor class
  - File: `src/asap/transport/executors.py`
  - Class: `BoundedExecutor`
  - Implementation: Semaphore-based thread pool limiting

- [x] 2.8.2 Implement queue depth rejection
  - Rejection: Raise `ThreadPoolExhaustedError` (503 Service Unavailable)
  - Metrics: `asap_thread_pool_exhausted_total`

- [x] 2.8.3 Integrate with HandlerRegistry
  - Update: `dispatch_async` using bounded executor
  - Parameter: `max_threads` in `create_app`

- [x] 2.8.4 Add starvation test
  - Test: Submit multiple synchronous tasks to verify rejection

- [x] 2.8.5 Commit ✅

**Acceptance**: Synchronous handlers cannot consume infinite threads

---

## Task 2.9: Protect Metrics Cardinality

- [x] 2.9.1 Implement payload type whitelist logic
  - Logic: Only record specific metric labels for registered handlers
  - Fallback: Use `payload_type="other"` for unknowns

- [x] 2.9.2 Update server metrics recording
  - Update error and success metrics normalization

- [x] 2.9.3 Add DoS test case
  - Test: Send requests with random `payload_type` values
  - Assert: Prometheus labels count remains constant

- [x] 2.9.4 Commit ✅

**Acceptance**: High cardinality payload types do not impact memory

---

## Task 2.10: Mark Sprint S2 Complete

- [x] 2.10.1 Update roadmap progress
  - Mark Tasks 2.1-2.9 as complete

- [x] 2.10.2 Update this detailed file
  - Completion date: 2026-01-25

- [x] 2.10.3 Verify DoD checklist
  - All acceptance criteria met and verified through automated testing.

**Acceptance**: Both roadmap and detailed tasks marked complete

---

## Sprint S2 Summary

Sprint S2 introduced robust protection against Denial of Service (DoS) attacks. Key features include per-sender rate limiting, strict request size enforcement, and bounded thread execution for synchronous handlers. Metrics cardinality protection was also implemented to prevent memory exhaustion from random payload types.

---

**Sprint S2 Definition of Done**:
- [x] All tasks 2.1-2.10 completed ✅
- [x] Rate limiting: HTTP 429 enforced ✅
- [x] Size validation: 10MB limit enforced ✅
- [x] Test coverage ≥95% maintained ✅
- [x] Security documentation updated ✅
- [x] All transport tests passing ✅

**Total Sub-tasks**: ~35
