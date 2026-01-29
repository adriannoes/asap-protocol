# Tasks: ASAP v0.5.0 Sprint S3 (Detailed)

> **Sprint**: S3 - Replay Attack Prevention & HTTPS
> **Goal**: Timestamp validation and HTTPS enforcement
> **Completed**: 2026-01-27

---

## Relevant Files

- `src/asap/models/constants.py` - Timestamp constants
- `src/asap/transport/validators.py` - NEW: Validators module
- `src/asap/transport/server.py` - Integrate validation
- `src/asap/transport/client.py` - HTTPS enforcement
- `src/asap/models/envelope.py` - Document nonce
- `src/asap/errors.py` - Add InvalidTimestampError, InvalidNonceError
- `tests/transport/unit/test_validators.py` - NEW: Unit tests for validation
- `tests/transport/test_client.py` - HTTPS validation tests
- `docs/security.md` - Security documentation

---

## Task 3.1: Add Timestamp Constants

- [x] 3.1.1 Add to constants.py
  - Add: `MAX_ENVELOPE_AGE_SECONDS = 300  # 5 minutes`
  - Add: `MAX_FUTURE_TOLERANCE_SECONDS = 30  # 30 seconds`
  - Include docstrings explaining rationale

- [x] 3.1.2 Verify constants are importable

- [x] 3.1.3 Commit ✅

**Acceptance**: Constants defined, documented, and properly exported.

---

## Task 3.2: Create Validators Module

- [x] 3.2.1 Add `InvalidTimestampError` to `errors.py`
- [x] 3.2.2 Create `src/asap/transport/validators.py` with necessary imports
- [x] 3.2.3 Implement `validate_envelope_timestamp(envelope: Envelope) -> None`
  - Check envelope age against window limits
  - Support future tolerance window
- [x] 3.2.4 Verify with older and future envelopes
- [x] 3.2.5 Ensure mypy compliance in strict mode
- [x] 3.2.6 Commit ✅

**Acceptance**: Validation function correctly rejects expired or future-dated envelopes.

---

## Task 3.3: Implement Nonce Support

- [x] 3.3.1 Document nonce usage in `envelope.py`
- [x] 3.3.2 Add `NonceStore` Protocol to `validators.py`
- [x] 3.3.3 Implement `InMemoryNonceStore` with thread-safe `RLock`
- [x] 3.3.4 Implement `validate_envelope_nonce(envelope: Envelope, store: NonceStore) -> None`
- [x] 3.3.5 Verify duplicate nonce detection
- [x] 3.3.6 Commit ✅

**Acceptance**: Optional nonce validation detects and prevents replay attacks.

---

## Task 3.4: Integrate Validation in Server

- [x] 3.4.1 Import validation utilities in `server.py`
- [x] 3.4.2 Add `require_nonce` parameter to `create_app()`
- [x] 3.4.3 Apply timestamp and nonce validation in the ASAP message handler
- [x] 3.4.4 Test integration with local server delivery
- [x] 3.4.5 Commit ✅

**Acceptance**: Server rejects malformed or replayed messages before dispatching to handlers.

---

## Task 3.5: Add HTTPS Enforcement to Client

- [x] 3.5.1 Add localhost detection capability to `ASAPClient`
- [x] 3.5.2 Add `require_https` parameter (default: True)
- [x] 3.5.3 raise errors for HTTP production URLs while allowing localhost development
- [x] 3.5.4 Verify enforcement logic across different URL patterns
- [x] 3.5.5 Commit ✅

**Acceptance**: HTTPS enforced for all production traffic; clear error messages for developers.

---

## Task 3.6: Add Comprehensive Validation Tests

- [x] 3.6.1 Create `tests/transport/unit/test_validators.py`
- [x] 3.6.2 Implement unit tests for timestamp windows and tolerances
- [x] 3.6.3 Implement unit tests for nonce lifecycle and duplicate detection
- [x] 3.6.4 Add HTTPS validation tests to `tests/transport/test_client.py`
- [x] 3.6.5 Commit ✅

**Acceptance**: High test coverage achieved for all new security validation logic.

---

## Task 3.7: Update Security Documentation

- [x] 3.7.1 Document Replay Attack Prevention in `docs/security.md`
- [x] 3.7.2 Document HTTPS Enforcement for production and dev environments
- [x] 3.7.3 Update README examples to reflect secure patterns
- [x] 3.7.4 Commit ✅

**Acceptance**: Documentation accurately reflects the v0.5.0 security model.

---

## Task 3.8: Roadmapping & Review

- [x] 3.8.1 Review PRD open questions regarding HMAC signing and encryption
- [x] 3.8.2 Document design decisions in the PRD roadmap
- [x] 3.8.3 Consolidate learnings from S1-S3 for final release prep
- [x] 3.8.4 Update PRD changelog to version 1.3

**Acceptance**: Roadmap aligned with implemented security features and future plans.

---

## Task 3.9: Mark Sprint S3 Complete

- [x] 3.9.1 Update high-level roadmap file
- [x] 3.9.2 Finalize status in this detailed task list

**Acceptance**: All S3 deliverables verified and marked complete.

---

## Sprint S3 Summary

Sprint S3 focused on protecting the protocol against replay attacks and ensuring transport security. Timestamp validation (5-minute window) and optional nonce tracking provide multiple layers of defense. The client now enforces HTTPS for production endpoints by default, significantly reducing the risk of credential leakage.

---

**Sprint S3 Definition of Done**:
- [x] Replay attack prevention: Old/future envelopes rejected ✅
- [x] Transport security: HTTPS enforced by default ✅
- [x] Test coverage: >95% maintained on critical modules ✅
- [x] Documentation: Security and Transport guides updated ✅
- [x] Static Analysis: 0 mypy/ruff issues ✅

**Total Sub-tasks**: ~40
