# Tasks: ASAP v0.5.0 Sprint S3 (Detailed)

> **Sprint**: S3 - Replay Attack Prevention & HTTPS
> **Duration**: Flexible (4-6 days)
> **Goal**: Timestamp validation and HTTPS enforcement

---

## Relevant Files

- `src/asap/models/constants.py` - Timestamp constants
- `src/asap/transport/validators.py` - NEW: Validators module
- `src/asap/transport/server.py` - Integrate validation
- `src/asap/transport/client.py` - HTTPS enforcement
- `src/asap/models/envelope.py` - Document nonce
- `src/asap/errors.py` - Add InvalidTimestampError
- `tests/transport/test_validators.py` - NEW: Validation tests
- `tests/transport/test_client.py` - HTTPS tests (extend)
- `docs/security.md` - Update docs (extend)

---

## Task 3.1: Add Timestamp Constants

- [ ] 3.1.1 Add to constants.py
  - Add: `MAX_ENVELOPE_AGE_SECONDS = 300  # 5 minutes`
  - Add: `MAX_FUTURE_TOLERANCE_SECONDS = 30  # 30 seconds`
  - Include docstrings explaining rationale
  - Export in __all__

- [ ] 3.1.2 Verify import
  - Run: `python -c "from asap.models.constants import MAX_ENVELOPE_AGE_SECONDS; print(MAX_ENVELOPE_AGE_SECONDS)"`

- [ ] 3.1.3 Commit
  - Command: `git commit -m "feat(models): add timestamp validation constants"`

**Acceptance**: Constants defined, documented, importable

---

## Task 3.2: Create Validators Module

- [ ] 3.2.1 Add InvalidTimestampError to errors.py
  - Class: Inherits from ASAPError
  - Code: "asap:protocol/invalid_timestamp"
  - Export in __all__

- [ ] 3.2.2 Create validators.py
  - File: `src/asap/transport/validators.py`
  - Add module docstring
  - Import: Envelope, constants, errors

- [ ] 3.2.3 Implement validate_envelope_timestamp
  - Function: `validate_envelope_timestamp(envelope: Envelope) -> None`
  - Logic: Check age against MAX_ENVELOPE_AGE_SECONDS
  - Logic: Check future tolerance against MAX_FUTURE_TOLERANCE_SECONDS
  - Raise: InvalidTimestampError with detailed message

- [ ] 3.2.4 Test in REPL
  - Test recent envelope: passes
  - Test old envelope (10 min): raises
  - Test future envelope (1 hour): raises

- [ ] 3.2.5 Run mypy
  - Command: `mypy --strict src/asap/transport/validators.py`

- [ ] 3.2.6 Commit
  - Command: `git commit -m "feat(transport): add timestamp validation for replay prevention"`

**Acceptance**: Validation function works, rejects old/future envelopes

---

## Task 3.3: Implement Nonce Support

- [ ] 3.3.1 Document nonce in envelope.py
  - Update extensions field docstring
  - Explain nonce usage (no code changes)

- [ ] 3.3.2 Add NonceStore Protocol to validators.py
  - Protocol: `is_used(nonce) -> bool`
  - Protocol: `mark_used(nonce, ttl_seconds) -> None`
  - Add @runtime_checkable decorator

- [ ] 3.3.3 Implement InMemoryNonceStore
  - Class with dict storage and RLock
  - TTL-based expiration
  - Lazy cleanup on access

- [ ] 3.3.4 Implement validate_envelope_nonce
  - Function: Skip if no nonce in extensions
  - Check: is_used(), raise if duplicate
  - Mark: mark_used() with 10min TTL

- [ ] 3.3.5 Test in REPL
  - Test no nonce: passes
  - Test first nonce: passes and marked
  - Test duplicate nonce: raises

- [ ] 3.3.6 Export classes in __all__

- [ ] 3.3.7 Commit
  - Command: `git commit -m "feat(transport): add optional nonce validation"`

**Acceptance**: Nonce validation optional, detects duplicates

---

## Task 3.4: Integrate Validation in Server

- [ ] 3.4.1 Import validators in server.py
  - Import: validate_envelope_timestamp, validate_envelope_nonce
  - Import: InMemoryNonceStore, InvalidTimestampError

- [ ] 3.4.2 Add require_nonce to create_app
  - Parameter: `require_nonce: bool = False`
  - Create nonce_store if enabled
  - Store in app.state

- [ ] 3.4.3 Add validation in handle_asap_message
  - After envelope parse, before dispatch
  - Call: validate_envelope_timestamp(envelope)
  - Call: validate_envelope_nonce() if nonce_store exists
  - Catch InvalidTimestampError, return JSON-RPC error

- [ ] 3.4.4 Test locally
  - Test recent envelope: works
  - Test old envelope: HTTP 400
  - Test future envelope: HTTP 400

- [ ] 3.4.5 Commit
  - Command: `git commit -m "feat(transport): integrate timestamp validation in handler"`

**Acceptance**: Validation integrated, old/future envelopes rejected

---

## Task 3.5: Add HTTPS Enforcement to Client

- [ ] 3.5.1 Add _is_localhost helper to client.py
  - Function: Detect localhost/127.0.0.1/::1
  - Use urlparse for hostname extraction

- [ ] 3.5.2 Add require_https parameter to ASAPClient
  - Parameter: `require_https: bool = True`
  - Store in self.require_https

- [ ] 3.5.3 Add HTTPS validation in __init__
  - If require_https and not HTTPS:
    - If localhost: log warning, allow
    - If non-localhost: raise ValueError
  - Clear error message with override instruction

- [ ] 3.5.4 Test in REPL
  - HTTPS URL: works
  - HTTP localhost: works with warning
  - HTTP production: raises ValueError
  - HTTP with override: works

- [ ] 3.5.5 Commit
  - Command: `git commit -m "feat(transport): enforce HTTPS for production connections"`

**Acceptance**: HTTPS enforced, localhost exception, clear errors

---

## Task 3.6: Add Validation Tests

- [ ] 3.6.1 Create test_validators.py
  - File: `tests/transport/test_validators.py`
  - Class: TestTimestampValidation

- [ ] 3.6.2 Add timestamp tests
  - Test: Recent timestamp accepted
  - Test: Old timestamp (>5min) rejected
  - Test: Future timestamp (>30s) rejected
  - Test: Timestamps within tolerance accepted

- [ ] 3.6.3 Add nonce tests
  - Class: TestNonceValidation
  - Test: No nonce passes
  - Test: First nonce use passes
  - Test: Duplicate nonce rejected
  - Test: Expired nonce allowed again

- [ ] 3.6.4 Run tests
  - Command: `uv run pytest tests/transport/test_validators.py -v`
  - Expected: 8+ tests pass

- [ ] 3.6.5 Add HTTPS tests to test_client.py
  - Test: HTTPS URLs accepted
  - Test: HTTP localhost accepted
  - Test: HTTP production rejected
  - Test: require_https=False override

- [ ] 3.6.6 Run client tests
  - Command: `uv run pytest tests/transport/test_client.py -v`

- [ ] 3.6.7 Commit
  - Command: `git commit -m "test(transport): add timestamp and HTTPS validation tests"`

**Acceptance**: 12+ new tests, all pass, coverage >95%

---

## Task 3.7: Update Documentation

- [ ] 3.7.1 Add Timestamp Validation section to docs/security.md
  - Section: "## Replay Attack Prevention"
  - Content: Timestamp window, nonce usage
  - Include: Configuration examples

- [ ] 3.7.2 Add HTTPS Enforcement section
  - Section: "## HTTPS Enforcement"
  - Content: Production vs development
  - Include: require_https parameter docs

- [ ] 3.7.3 Update examples in README
  - Change HTTP URLs to HTTPS where appropriate
  - Add note about localhost development

- [ ] 3.7.4 Commit
  - Command: `git commit -m "docs(security): add replay prevention and HTTPS docs"`

**Acceptance**: Documentation complete, examples updated

---

## Task 3.8: PRD Review Checkpoint

- [ ] 3.8.1 Review PRD Open Questions
  - Open: `.cursor/dev-planning/prd/prd-v1-roadmap.md`
  - Section 11, Question 3: HMAC signing decision
  - Assess complexity based on S1-S3 experience
  - Decide: Include in v1.0.0 or defer to v1.1.0?

- [ ] 3.8.2 Document decision in PRD
  - If decided: Add DD-008 to Section 10
  - If deferred: Update Q3 status, note reasons

- [ ] 3.8.3 Document S1-S3 learnings
  - What went well?
  - Challenges encountered?
  - Adjustments needed for S4-S5?

- [ ] 3.8.4 Update PRD changelog
  - Add entry for S3 review completion

**Acceptance**: PRD reviewed, Q3 answered or deferred, learnings documented

---

**Sprint S3 Definition of Done**:
- [ ] Old/future envelopes rejected
- [ ] HTTPS enforced in production
- [ ] 12+ new tests pass
- [ ] Coverage >95%
- [ ] Examples use HTTPS
- [ ] PRD reviewed

**Total Sub-tasks**: ~35
