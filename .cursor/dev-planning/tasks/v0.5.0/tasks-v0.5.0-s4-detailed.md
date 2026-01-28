# Tasks: ASAP v0.5.0 Sprint S4 (Detailed)

> **Sprint**: S4 - Retry Logic & Authorization
> **Goal**: Exponential backoff and authorization validation

---

## Relevant Files

- `src/asap/transport/client.py` - Retry logic with exponential backoff, CircuitBreaker class with thread-safety (RLock), integration in send() method
- `src/asap/models/entities.py` - Auth scheme validation function `_validate_auth_scheme()` and `@model_validator` on Manifest model
- `src/asap/models/constants.py` - Retry/backoff constants and SUPPORTED_AUTH_SCHEMES (bearer, basic) with docstring
- `src/asap/errors.py` - CircuitOpenError and UnsupportedAuthSchemeError added with proper error codes and details
- `tests/transport/unit/test_retry_backoff.py` - NEW: Backoff unit tests (S3 pattern) with 10 tests covering exponential delays, jitter, max delay, 4xx handling, and Retry-After header
- `tests/transport/unit/test_retry_edge_cases.py` - NEW: Edge case tests for backoff with 11 tests covering boundary conditions
- `tests/transport/unit/test_circuit_breaker.py` - NEW: Circuit breaker unit tests with 14 tests covering basic functionality, timeout transitions, integration, and thread-safety
- `tests/transport/test_client.py` - Integration tests (extend) - pending
- `tests/models/test_entities.py` - Auth validation tests extended with 8 new tests in TestManifestAuthSchemeValidation class
- `docs/transport.md` - Retry configuration documentation with exponential backoff, circuit breaker, and configuration examples
- `docs/security.md` - Authorization schemes documentation with supported schemes (bearer, basic), validation, and configuration examples
- `docs/error-handling.md` - Connection error troubleshooting guide with diagnostic steps, common errors, and best practices

---

## Learnings from Sprint S3 Applied

> These improvements are based on Code Review PR #19 patterns:
> - **Constants pattern**: Define defaults in `models/constants.py` with docstrings
> - **Thread-safety**: Use RLock for state management (like InMemoryNonceStore)
> - **Unit test structure**: Create dedicated files in `tests/transport/unit/`
> - **Edge case tests**: Add tests for boundary conditions

---

## Task 4.1: Implement Exponential Backoff

**Reference**: [Task 6.1-6.3](./tasks-security-review-report.md)

- [x] 4.1.1 Add backoff calculation method to client.py
  - Method: `_calculate_backoff(self, attempt: int) -> float`
  - Algorithm: `base_delay * (2 ** attempt) + jitter`
  - Cap: max_delay (60 seconds)
  - Return: Delay in seconds

- [x] 4.1.2 Add backoff configuration parameters
  - Add to __init__: `base_delay: float = DEFAULT_BASE_DELAY`
  - Add to __init__: `max_delay: float = DEFAULT_MAX_DELAY`
  - Add to __init__: `jitter: bool = True`

- [x] 4.1.2.1 Add retry constants to constants.py (S3 pattern)
  - File: `src/asap/models/constants.py`
  - Add: `DEFAULT_BASE_DELAY = 1.0` with docstring
  - Add: `DEFAULT_MAX_DELAY = 60.0` with docstring
  - Add: `DEFAULT_CIRCUIT_BREAKER_THRESHOLD = 5` with docstring
  - Add: `DEFAULT_CIRCUIT_BREAKER_TIMEOUT = 60.0` with docstring
  - Follow pattern from `MAX_ENVELOPE_AGE_SECONDS` docstrings

- [x] 4.1.3 Update retry loop in send()
  - Find retry loop (existing max_retries logic)
  - Replace immediate retry with backoff:
    - Calculate delay: `delay = self._calculate_backoff(attempt)`
    - Only for retriable errors (5xx, connection)
    - Sleep: `await asyncio.sleep(delay)`
    - Log: Retry attempt with delay

- [x] 4.1.4 Test locally
  - Mock server that returns 503
  - Send request, observe delays
  - Verify: 1s, 2s, 4s, 8s pattern (with jitter)
  - Added tests: `test_backoff_pattern_1s_2s_4s_8s_with_jitter` and `test_backoff_pattern_1s_2s_4s_8s_without_jitter`

- [x] 4.1.5 Commit
  - Command: `git commit -m "feat(transport): add exponential backoff with jitter to retry logic"`
  - Commit: bd6ad06 (combined with 4.2.6)

- [x] 4.1.6 Handle Retry-After header from 429 responses (S2 integration)
  - Parse `Retry-After` header if present in HTTP 429 response
  - If present: Use server-suggested delay instead of calculated backoff
  - Log: "Respecting server Retry-After: Xs"
  - Ensures proper integration with S2's rate limiting feature

**Acceptance**: Backoff working, delays exponential, capped at 60s, respects Retry-After

---

## Task 4.2: Implement Circuit Breaker

**Reference**: [Task 6.4](./tasks-security-review-report.md)

- [x] 4.2.1 Add CircuitBreaker class to client.py
  - States: CLOSED, OPEN, HALF_OPEN (use Enum)
  - Track: Consecutive failures per base_url
  - Threshold: Default `DEFAULT_CIRCUIT_BREAKER_THRESHOLD` (5 failures)
  - Add: `CircuitOpenError` to errors.py for when circuit is open

- [x] 4.2.2 Add circuit breaker parameters to ASAPClient
  - Parameter: `circuit_breaker_enabled: bool = False`
  - Parameter: `circuit_breaker_threshold: int = DEFAULT_CIRCUIT_BREAKER_THRESHOLD`
  - Parameter: `circuit_breaker_timeout: float = DEFAULT_CIRCUIT_BREAKER_TIMEOUT`

- [x] 4.2.3 Integrate in retry logic
  - Check circuit state before sending
  - If OPEN: Raise `CircuitOpenError` immediately (don't retry)
  - Track failures, open circuit at threshold
  - Half-open after timeout, close on success

- [x] 4.2.4 Add logging for circuit state changes
  - Log WARNING when opening circuit
  - Log INFO when closing circuit

- [x] 4.2.5 Test circuit breaker
  - Mock 5 consecutive failures
  - Verify circuit opens
  - Verify subsequent requests fail immediately

- [x] 4.2.6 Commit
  - Command: `git commit -m "feat(transport): add optional circuit breaker pattern"`
  - Commit: bd6ad06 (combined with 4.1.5)

- [x] 4.2.7 Ensure thread-safe circuit state transitions (S3 pattern)
  - Use `threading.RLock` for state changes (like InMemoryNonceStore)
  - Implement atomic check-and-update pattern
  - Avoid TOCTOU race conditions in HALF_OPEN → CLOSED transition
  - Pattern: `with self._lock: check state and update atomically`

**Acceptance**: Circuit breaker optional, opens after 5 failures, thread-safe

---

## Task 4.3: Add Authorization Scheme Validation

**Issue**: [#13](https://github.com/adriannoes/asap-protocol/issues/13)

- [x] 4.3.1 Add UnsupportedAuthSchemeError to errors.py
  - Class: Inherits from ASAPError
  - Code: "asap:auth/unsupported_scheme"
  - Message: Include scheme name and supported list

- [x] 4.3.2 Define supported schemes
  - File: `src/asap/models/constants.py`
  - Add: `SUPPORTED_AUTH_SCHEMES = frozenset({"bearer", "basic"})`
  - Note: oauth2, hmac planned for future

- [x] 4.3.3 Add validation function to entities.py
  - Function: `_validate_auth_scheme(auth: AuthScheme | None) -> None`
  - Check each scheme in auth.schemes against SUPPORTED_AUTH_SCHEMES
  - Raise UnsupportedAuthSchemeError if invalid

- [x] 4.3.4 Add validator to Manifest model
  - Use Pydantic's @model_validator
  - Call _validate_auth_scheme(self.auth)
  - Validation runs on model creation

- [x] 4.3.5 Test validation
  - Create Manifest with bearer: works
  - Create Manifest with unsupported scheme: raises
  - Create Manifest without auth: works
  - Tests implemented in task 4.4.3 (TestManifestAuthSchemeValidation)

- [x] 4.3.6 Commit
  - Command: `git commit -m "feat(models): add authorization scheme validation"`
  - Commit: 9501297 - Closes #13

**Acceptance**: Unsupported schemes rejected at Manifest creation

---

## Task 4.4: Add Retry and Auth Tests

> **Note**: Follow S3 test structure pattern - create dedicated files in `tests/transport/unit/`

- [x] 4.4.1 Create backoff unit tests (S3 pattern)
  - File: `tests/transport/unit/test_retry_backoff.py`
  - Test: Delays increase exponentially (1s, 2s, 4s, 8s...)
  - Test: Jitter applied correctly (random component)
  - Test: Max delay respected (60s cap)
  - Test: No backoff for 4xx errors
  - Test: Retry-After header is respected for 429

- [x] 4.4.1.1 Add edge case tests for backoff (S3 pattern)
  - File: `tests/transport/unit/test_retry_edge_cases.py`
  - Test: Zero attempts edge case
  - Test: Negative base_delay (should clamp to 0 or raise)
  - Test: Very large max_delay values
  - Test: Jitter distribution is within expected range

- [x] 4.4.2 Create circuit breaker unit tests (S3 pattern)
  - File: `tests/transport/unit/test_circuit_breaker.py`
  - Test: Opens after threshold failures
  - Test: Half-opens after timeout
  - Test: Closes on success
  - Test: Raises CircuitOpenError immediately when open
  - Test: Thread-safety (concurrent requests)

- [x] 4.4.3 Add auth scheme tests to test_entities.py
  - Test: Valid schemes (bearer, basic) accepted
  - Test: Invalid schemes rejected with UnsupportedAuthSchemeError
  - Test: Empty schemes list handled gracefully
  - Test: Missing auth works (optional)

- [x] 4.4.4 Run all tests
  - Command: `uv run pytest tests/transport/unit/test_retry*.py tests/transport/unit/test_circuit*.py tests/models/test_entities.py -v`
  - Expected: 29 new tests pass (10 backoff + 11 edge cases + 8 auth validation)

- [x] 4.4.5 Commit
  - Command: `git commit -m "test(transport): add retry, backoff, circuit breaker, and auth validation tests"`
  - Commit: c7d7936 - 4 files changed, 1161 insertions(+)

**Acceptance**: 29+ tests, all pass, coverage >95%, follows S3 file structure

---

## Task 4.4.5: Improve Connection Error Messages (User Feedback)

**Feedback Source**: v0.3.0 testing - "Connection errors are handled gracefully"

- [x] 4.4.5.1 Enhance error messages for connection failures
  - File: `src/asap/transport/client.py`
  - Improve `ASAPConnectionError` messages to be more user-friendly
  - Include: Suggested troubleshooting steps (check URL, verify agent is running)
  - Example: "Connection failed to {url}. Verify the agent is running and accessible."
  - Added URL attribute to ASAPConnectionError for better error context

- [x] 4.4.5.2 Add connection validation helper
  - Method: `_validate_connection(self) -> bool`
  - Optional: Pre-flight check before sending (can be disabled for performance)
  - Check: Agent manifest endpoint is accessible
  - Log: Clear message if validation fails

- [x] 4.4.5.3 Add connection error context to logs
  - Enhance logging in `send()` method
  - Include: URL, attempt number, total retries, error type
  - Add: Suggested actions in log messages
  - Improved logging for connection errors, timeouts, and server errors

- [x] 4.4.5.4 Test improved error messages
  - Verify: Error messages are clear and actionable
  - Verify: Logs provide sufficient context for debugging
  - Added 6 new tests in TestImprovedConnectionErrorMessages class

- [x] 4.4.5.5 Commit
  - Command: `git commit -m "feat(transport): improve connection error messages and user guidance"`
  - Commit: 39a161a - 2 files changed, 316 insertions(+), 17 deletions(-)

**Acceptance**: Error messages are clear, actionable, and include troubleshooting hints

---

## Task 4.5: Update Documentation

- [x] 4.5.1 Add Retry Configuration section to docs/transport.md
  - Content: Backoff strategy, configuration
  - Examples: Default vs custom settings
  - Guidance: When to use circuit breaker

- [x] 4.5.2 Add Authorization Schemes section to docs/security.md
  - Content: Supported schemes (bearer, basic)
  - Configuration: How to set up each
  - Future: oauth2, hmac roadmap

- [x] 4.5.3 Add Connection Error Troubleshooting section
  - File: `docs/error-handling.md` or `docs/transport.md`
  - Content: Common connection errors and solutions
  - Include: How to diagnose connection issues
  - Include: Best practices for error handling in user code
  - Examples: Checking agent status, verifying URLs, network issues

- [ ] 4.5.4 Commit
  - Command: `git commit -m "docs: add retry, authorization, and connection troubleshooting documentation"`

**Acceptance**: Documentation complete with examples including troubleshooting guide

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
- [ ] Exponential backoff working with jitter
- [ ] Max delay 60s cap enforced
- [ ] Retry-After header respected (S2 integration)
- [ ] Circuit breaker optional and thread-safe (S3 pattern)
- [ ] Auth schemes validated with UnsupportedAuthSchemeError
- [ ] Connection error messages improved (user feedback addressed)
- [ ] Constants defined in models/constants.py (S3 pattern)
- [ ] 16+ new tests pass (in unit/ directory per S3 structure)
- [ ] Coverage >95%
- [ ] Docs updated (including troubleshooting)
- [ ] Issue #13 closed
- [ ] Progress tracked in both files

**Total Sub-tasks**: ~42 (added S3-inspired improvements)

---

## Appendix: S3 Patterns Applied

| Pattern | S3 Implementation | S4 Application |
|---------|-------------------|----------------|
| Constants module | `MAX_ENVELOPE_AGE_SECONDS` | `DEFAULT_BASE_DELAY`, `DEFAULT_MAX_DELAY` |
| Thread-safety | `InMemoryNonceStore` with RLock | `CircuitBreaker` with RLock |
| Unit test structure | `tests/transport/unit/test_validators.py` | `tests/transport/unit/test_retry_backoff.py` |
| Edge case tests | `test_validators_edge_cases.py` | `test_retry_edge_cases.py` |
| Protocol pattern | `NonceStore` Protocol | Consider `CircuitBreakerStore` Protocol for future |
