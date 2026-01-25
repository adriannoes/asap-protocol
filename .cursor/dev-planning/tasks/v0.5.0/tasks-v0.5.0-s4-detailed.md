# Tasks: ASAP v0.5.0 Sprint S4 (Detailed)

> **Sprint**: S4 - Retry Logic & Authorization
> **Duration**: Flexible (3-5 days)
> **Goal**: Exponential backoff and authorization validation

---

## Relevant Files

- `src/asap/transport/client.py` - Retry logic and circuit breaker
- `src/asap/models/entities.py` - Auth scheme validation
- `src/asap/errors.py` - Add UnsupportedAuthSchemeError
- `tests/transport/test_client.py` - Backoff tests (extend)
- `tests/models/test_entities.py` - Auth validation tests (extend)
- `docs/transport.md` - Retry docs (extend)
- `docs/security.md` - Auth scheme docs (extend)

---

## Task 4.1: Implement Exponential Backoff

**Reference**: [Task 6.1-6.3](./tasks-security-review-report.md)

- [ ] 4.1.1 Add backoff calculation method to client.py
  - Method: `_calculate_backoff(self, attempt: int) -> float`
  - Algorithm: `base_delay * (2 ** attempt) + jitter`
  - Cap: max_delay (60 seconds)
  - Return: Delay in seconds

- [ ] 4.1.2 Add backoff configuration parameters
  - Add to __init__: `base_delay: float = 1.0`
  - Add to __init__: `max_delay: float = 60.0`
  - Add to __init__: `jitter: bool = True`

- [ ] 4.1.3 Update retry loop in send()
  - Find retry loop (existing max_retries logic)
  - Replace immediate retry with backoff:
    - Calculate delay: `delay = self._calculate_backoff(attempt)`
    - Only for retriable errors (5xx, connection)
    - Sleep: `await asyncio.sleep(delay)`
    - Log: Retry attempt with delay

- [ ] 4.1.4 Test locally
  - Mock server that returns 503
  - Send request, observe delays
  - Verify: 1s, 2s, 4s, 8s pattern (with jitter)

- [ ] 4.1.5 Commit
  - Command: `git commit -m "feat(transport): add exponential backoff with jitter to retry logic"`

**Acceptance**: Backoff working, delays exponential, capped at 60s

---

## Task 4.2: Implement Circuit Breaker (Optional)

**Reference**: [Task 6.4](./tasks-security-review-report.md)

- [ ] 4.2.1 Add CircuitBreaker class to client.py
  - States: CLOSED, OPEN, HALF_OPEN
  - Track: Consecutive failures per base_url
  - Threshold: Default 5 failures

- [ ] 4.2.2 Add circuit breaker parameters to ASAPClient
  - Parameter: `circuit_breaker_enabled: bool = False`
  - Parameter: `circuit_breaker_threshold: int = 5`
  - Parameter: `circuit_breaker_timeout: float = 60.0`

- [ ] 4.2.3 Integrate in retry logic
  - Check circuit state before sending
  - If OPEN: Raise immediately (don't retry)
  - Track failures, open circuit at threshold
  - Half-open after timeout, close on success

- [ ] 4.2.4 Add logging for circuit state changes
  - Log WARNING when opening circuit
  - Log INFO when closing circuit

- [ ] 4.2.5 Test circuit breaker
  - Mock 5 consecutive failures
  - Verify circuit opens
  - Verify subsequent requests fail immediately

- [ ] 4.2.6 Commit
  - Command: `git commit -m "feat(transport): add optional circuit breaker pattern"`

**Acceptance**: Circuit breaker optional, opens after 5 failures

---

## Task 4.3: Add Authorization Scheme Validation

**Issue**: [#13](https://github.com/adriannoes/asap-protocol/issues/13)

- [ ] 4.3.1 Add UnsupportedAuthSchemeError to errors.py
  - Class: Inherits from ASAPError
  - Code: "asap:auth/unsupported_scheme"
  - Message: Include scheme name and supported list

- [ ] 4.3.2 Define supported schemes
  - File: `src/asap/models/constants.py`
  - Add: `SUPPORTED_AUTH_SCHEMES = frozenset({"bearer", "basic"})`
  - Note: oauth2, hmac planned for future

- [ ] 4.3.3 Add validation function to entities.py
  - Function: `_validate_auth_scheme(auth: AuthScheme | None) -> None`
  - Check each scheme in auth.schemes against SUPPORTED_AUTH_SCHEMES
  - Raise UnsupportedAuthSchemeError if invalid

- [ ] 4.3.4 Add validator to Manifest model
  - Use Pydantic's @model_validator
  - Call _validate_auth_scheme(self.auth)
  - Validation runs on model creation

- [ ] 4.3.5 Test validation
  - Create Manifest with bearer: works
  - Create Manifest with unsupported scheme: raises
  - Create Manifest without auth: works

- [ ] 4.3.6 Commit
  - Command: `git commit -m "feat(models): add authorization scheme validation"`
  - Close issue #13

**Acceptance**: Unsupported schemes rejected at Manifest creation

---

## Task 4.4: Add Retry and Auth Tests

- [ ] 4.4.1 Add backoff tests to test_client.py
  - Test: Delays increase exponentially
  - Test: Jitter applied correctly
  - Test: Max delay respected (60s)
  - Test: No backoff for 4xx errors

- [ ] 4.4.2 Add circuit breaker tests
  - Test: Opens after threshold failures
  - Test: Half-opens after timeout
  - Test: Closes on success
  - Test: Rejects immediately when open

- [ ] 4.4.3 Add auth scheme tests to test_entities.py
  - Test: Valid schemes (bearer, basic) accepted
  - Test: Invalid schemes rejected
  - Test: Empty schemes list rejected
  - Test: Missing auth works (optional)

- [ ] 4.4.4 Run all tests
  - Command: `uv run pytest tests/transport/test_client.py tests/models/test_entities.py -v`
  - Expected: 12+ new tests pass

- [ ] 4.4.5 Commit
  - Command: `git commit -m "test(transport): add retry, backoff, and auth validation tests"`

**Acceptance**: 12+ tests, all pass, coverage >95%

---

## Task 4.5: Update Documentation

- [ ] 4.5.1 Add Retry Configuration section to docs/transport.md
  - Content: Backoff strategy, configuration
  - Examples: Default vs custom settings
  - Guidance: When to use circuit breaker

- [ ] 4.5.2 Add Authorization Schemes section to docs/security.md
  - Content: Supported schemes (bearer, basic)
  - Configuration: How to set up each
  - Future: oauth2, hmac roadmap

- [ ] 4.5.3 Commit
  - Command: `git commit -m "docs: add retry and authorization scheme documentation"`

**Acceptance**: Documentation complete with examples

---

## Task 4.6: Mark Sprint S4 Complete

- [ ] 4.6.1 Update roadmap progress
  - Open: `tasks-v0.5.0-roadmap.md`
  - Mark: Tasks 4.1-4.5 as complete `[x]`
  - Update: S4 progress to 5/5 (100%)

- [ ] 4.6.2 Update this detailed file
  - Mark: All sub-tasks as complete `[x]`
  - Add: Completion date

- [ ] 4.6.3 Verify issue #13 closed
  - Confirm: Closed on GitHub
  - Confirm: Commit references issue

**Acceptance**: Both files complete, issue #13 resolved

---

**Sprint S4 Definition of Done**:
- [ ] All tasks 4.1-4.6 completed
- [ ] Exponential backoff working
- [ ] Max delay 60s
- [ ] Auth schemes validated
- [ ] 12+ new tests pass
- [ ] Coverage >95%
- [ ] Docs updated
- [ ] Issue #13 closed
- [ ] Progress tracked in both files

**Total Sub-tasks**: ~30
