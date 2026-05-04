# Tasks: ASAP v0.5.0 Sprint S4 (Detailed)

> **Sprint**: S4 - Retry Logic & Authorization
> **Goal**: Exponential backoff and authorization validation
> **Status**: ✅ **COMPLETE** (2026-01-27)

---

## Relevant Files

- `src/asap/transport/client.py` - Retry logic, CircuitBreaker implementation, and integration.
- `src/asap/models/entities.py` - Authorization scheme validation in the Manifest model.
- `src/asap/models/constants.py` - Retry/backoff constants and supported auth schemes.
- `src/asap/errors.py` - New error classes for circuit breaker and auth validation.
- `tests/transport/unit/` - New unit test suites for retry, backoff, and circuit breaker.
- `docs/transport.md` - Retry and circuit breaker documentation.
- `docs/security.md` - Authorization scheme documentation.
- `docs/error-handling.md` - Connection troubleshooting guide.

---

## Task 4.1: Implement Exponential Backoff

- [x] 4.1.1 Add `_calculate_backoff()` method to `ASAPClient`
  - Implement exponential delay with jitter
  - Cap maximum delay at 60 seconds
- [x] 4.1.2 Define retry constants in `models/constants.py`
- [x] 4.1.3 Update retry loop to apply calculated backoff for retriable errors
- [x] 4.1.4 Support `Retry-After` header for HTTP 429 (Rate Limited) responses
- [x] 4.1.5 Verify backoff pattern through unit testing

**Acceptance**: Client properly backs off on transient failures and respects server-suggested retry delays.

---

## Task 4.2: Implement Circuit Breaker

- [x] 4.2.1 Add `CircuitBreaker` class with CLOSED, OPEN, and HALF_OPEN states
- [x] 4.2.2 Implement failure tracking per base URL
- [x] 4.2.3 Ensure thread-safe state transitions using `RLock`
- [x] 4.2.4 Integrate circuit breaker into the client's request sending logic
- [x] 4.2.5 Implement immediate rejection with `CircuitOpenError` when open
- [x] 4.2.6 Verify state transitions and timeout recovery through tests

**Acceptance**: Circuit breaker prevents cascading failures and provides rapid recovery paths.

---

## Task 4.3: Add Authorization Scheme Validation

- [x] 4.3.1 Define supported auth schemes (Bearer, Basic) in `constants.py`
- [x] 4.3.2 Implement `UnsupportedAuthSchemeError` in `errors.py`
- [x] 4.3.3 Add validation logic to the `Manifest` model using Pydantic validators
- [x] 4.3.4 Ensure invalid schemes are rejected at model creation time (fail-fast)
- [x] 4.3.5 Verify validation with supported and unsupported schemes

**Acceptance**: Agents can only be configured with supported authorization protocols.

---

## Task 4.4: Enhance Testing Infrastructure

- [x] 4.4.1 Create dedicated unit tests for exponential backoff logic
- [x] 4.4.2 Implement edge-case tests for boundary retry conditions
- [x] 4.4.3 Create comprehensive circuit breaker state tests
- [x] 4.4.4 Extend manifest tests to cover authorization validation
- [x] 4.4.5 Improve connection error messages based on user feedback

**Acceptance**: Solid test suite covering all new transport and model hardening logic.

---

## Task 4.5: Update Developer Documentation

- [x] 4.5.1 Document Retry Configuration and strategies in `transport.md`
- [x] 4.5.2 Document supported Authorization Schemes in `security.md`
- [x] 4.5.3 Add Troubleshooting Guide for connection errors in `error-handling.md`
- [x] 4.5.4 Update all examples and configuration guides

**Acceptance**: Clear, actionable documentation for developers implementing the protocol.

---

## Task 4.6: Milestone Completion

- [x] 4.6.1 Update high-level roadmap and sprint progress
- [x] 4.6.2 Finalize issue tracking on GitHub
- [x] 4.6.3 Verify all S4 deliverables meet the Definition of Done

**Acceptance**: Sprint S4 closed and all goals achieved.

---

## Sprint S4 Summary

Sprint S4 significantly improved the resilience and security of the ASAP transport layer. The introduction of exponential backoff makes the client more robust to transient network issues, while the circuit breaker prevents overwhelming failing services. Authorization validation ensures that agents are configured correctly from the start.

---

**Sprint S4 Definition of Done**:
- [x] Exponential backoff with jitter implemented and tested ✅
- [x] Circuit breaker pattern implemented with thread-safety ✅
- [x] Authorization schemes validated at model level ✅
- [x] Connection error messages improved for better UX ✅
- [x] Test coverage ≥95% maintained ✅
- [x] All developer guides updated ✅

**Total Sub-tasks**: ~42
