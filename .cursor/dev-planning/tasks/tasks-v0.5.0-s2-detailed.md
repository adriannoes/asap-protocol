# Tasks: ASAP v0.5.0 Sprint S2 (Detailed)

> **Sprint**: S2 - DoS Prevention & Rate Limiting
> **Duration**: Flexible (5-7 days)
> **Goal**: Implement rate limiting and request size validation

---

## Relevant Files

- `pyproject.toml` - Add slowapi dependency
- `src/asap/transport/middleware.py` - Rate limiting (extend existing)
- `src/asap/transport/server.py` - Integrate limiter and size validation
- `src/asap/models/constants.py` - Add MAX_REQUEST_SIZE
- `tests/transport/test_middleware.py` - Rate limit tests (extend)
- `tests/transport/test_server.py` - Size validation tests (extend)
- `docs/security.md` - DoS prevention docs (extend)

---

## Task 2.1: Add slowapi Dependency

- [ ] 2.1.1 Research slowapi compatibility
  - Check: https://github.com/laurentS/slowapi
  - Verify FastAPI 0.128+ support
  - Document target version (≥0.1.9)

- [ ] 2.1.2 Add dependency
  - Command: `uv add "slowapi>=0.1.9"`
  - Verify: `uv tree | grep slowapi`

- [ ] 2.1.3 Test import
  - Run: `python -c "from slowapi import Limiter; print('OK')"`

- [ ] 2.1.4 Commit
  - Command: `git commit -m "build(deps): add slowapi for rate limiting"`

**Acceptance**: slowapi ≥0.1.9 installed and importable

---

## Task 2.2: Implement Rate Limiting Middleware

- [ ] 2.2.1 Add sender extraction function to middleware.py
  - Function: `_get_sender_from_envelope(request: Request) -> str`
  - Logic: Extract sender from envelope, fallback to IP
  - Handle cases where envelope not yet parsed

- [ ] 2.2.2 Create rate limiter instance
  - Create limiter with sender-based key function
  - Default: 100 requests/minute
  - Storage: memory://

- [ ] 2.2.3 Add rate limit exception handler
  - Function: `rate_limit_handler(request, exc: RateLimitExceeded)`
  - Return: JSON-RPC formatted error with Retry-After header
  - Status: HTTP 429

- [ ] 2.2.4 Export from middleware module
  - Update __all__: Add limiter, rate_limit_handler

- [ ] 2.2.5 Run mypy
  - Command: `mypy --strict src/asap/transport/middleware.py`

- [ ] 2.2.6 Commit
  - Command: `git commit -m "feat(transport): add per-sender rate limiting middleware"`

**Acceptance**: Rate limiter created, exports work, mypy passes

---

## Task 2.3: Integrate Rate Limiter in Server

- [ ] 2.3.1 Import limiter in server.py
  - Add: `from .middleware import limiter, rate_limit_handler`

- [ ] 2.3.2 Add rate_limit parameter to create_app
  - Parameter: `rate_limit: str | None = None`
  - Default from env: ASAP_RATE_LIMIT or "100/minute"

- [ ] 2.3.3 Configure limiter in app
  - Set: `app.state.limiter = limiter`
  - Add exception handler for RateLimitExceeded

- [ ] 2.3.4 Apply to /asap endpoint
  - Add decorator: `@limiter.limit("100/minute")`
  - Make configurable via create_app parameter

- [ ] 2.3.5 Test locally
  - Start server, send 100+ rapid requests
  - Verify 101st request gets HTTP 429

- [ ] 2.3.6 Commit
  - Command: `git commit -m "feat(transport): integrate rate limiting in /asap endpoint"`

**Acceptance**: Rate limiting works, HTTP 429 after limit

---

## Task 2.4: Add Request Size Validation

- [ ] 2.4.1 Add constant
  - File: `src/asap/models/constants.py`
  - Add: `MAX_REQUEST_SIZE = 10 * 1024 * 1024  # 10MB`
  - Export in __all__

- [ ] 2.4.2 Add size validation function
  - File: `src/asap/transport/server.py`
  - Function: `_validate_request_size(request, max_size) -> None`
  - Check Content-Length header first
  - Raise HTTPException(413) if too large

- [ ] 2.4.3 Apply validation in endpoint
  - Call before reading body
  - Also validate actual body size after reading

- [ ] 2.4.4 Add max_request_size parameter to create_app
  - Parameter: `max_request_size: int | None = None`
  - Default from env or 10MB
  - Store in app.state

- [ ] 2.4.5 Test locally
  - Create 11MB file: `dd if=/dev/zero of=/tmp/large.bin bs=1M count=11`
  - Send: `curl -X POST http://localhost:8000/asap -d @/tmp/large.bin`
  - Expected: HTTP 413 or 400

- [ ] 2.4.6 Commit
  - Command: `git commit -m "feat(transport): add 10MB request size limit"`

**Acceptance**: Size validation rejects >10MB, normal requests work

---

## Task 2.5: Add Rate Limiting Tests

- [ ] 2.5.1 Add TestRateLimiting class to test_middleware.py
  - Test: Requests within limit succeed
  - Test: Exceeding limit returns 429
  - Test: Limit resets after window
  - Test: Different senders independent

- [ ] 2.5.2 Run tests
  - Command: `uv run pytest tests/transport/test_middleware.py::TestRateLimiting -v`
  - Expected: 4+ tests pass

- [ ] 2.5.3 Commit
  - Command: `git commit -m "test(transport): add rate limiting tests"`

**Acceptance**: 4+ tests, all pass

---

## Task 2.6: Add Payload Size Tests

- [ ] 2.6.1 Add TestPayloadSizeValidation class to test_server.py
  - Test: Requests <10MB accepted
  - Test: Requests >10MB rejected
  - Test: Content-Length validation
  - Test: Actual body size validation

- [ ] 2.6.2 Run tests
  - Command: `uv run pytest tests/transport/test_server.py::TestPayloadSizeValidation -v`
  - Expected: 4+ tests pass

- [ ] 2.6.3 Commit
  - Command: `git commit -m "test(transport): add payload size validation tests"`

**Acceptance**: 4+ tests, all pass

---

## Task 2.7: Update Security Documentation

- [ ] 2.7.1 Add Rate Limiting section to docs/security.md
  - Section: "## Rate Limiting"
  - Content: Configuration, defaults, production recommendations
  - Include: Response format example

- [ ] 2.7.2 Add Request Size Limits section
  - Section: "## Request Size Limits"
  - Content: Default limit, configuration, rationale
  - Include: Error response example

- [ ] 2.7.3 Update table of contents

- [ ] 2.7.4 Commit
  - Command: `git commit -m "docs(security): add rate limiting and size limit docs"`

**Acceptance**: Documentation complete with examples

---

**Sprint S2 Definition of Done**:
- [ ] Rate limiting: HTTP 429 works
- [ ] Size validation: 10MB limit enforced
- [ ] Test coverage >95%
- [ ] Documentation updated
- [ ] All tests passing

**Total Sub-tasks**: ~30
