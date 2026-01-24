# Tasks: ASAP v1.0.0 Security (P1-P2) - Detailed

> **Sprints**: P1-P2 - Complete remaining security hardening
> **Duration**: Flexible (8-11 days)
> **Goal**: Resolve all MED+LOW security issues
> **Prerequisite**: v0.5.0 released

---

## Relevant Files

### Sprint P1: Sensitive Data Protection
- `src/asap/observability/logging.py` - Log sanitization
- `src/asap/transport/server.py` - Debug mode
- `src/asap/transport/client.py` - Sanitize logged data
- `src/asap/models/parts.py` - FilePart URI validation
- `src/asap/transport/handlers.py` - Handler security helpers
- `tests/observability/test_logging.py` - Sanitization tests (extend)
- `docs/security.md` - Handler security docs (extend)

### Sprint P2: Code Quality
- `src/asap/transport/handlers.py` - Thread safety
- `src/asap/models/entities.py` - Enhanced URN validation
- `tests/models/test_entities.py` - URN tests (extend)

---

## Sprint P1: Sensitive Data Protection

### Task 1.1: Implement Log Sanitization

**Issue**: [#12](https://github.com/adriannoes/asap-protocol/issues/12)

- [ ] 1.1.1 Add sanitize_for_logging function to logging.py
  - Function: Takes dict, returns sanitized dict
  - Pattern detection: password, token, secret, key, authorization
  - Replace values with: "***REDACTED***"
  - Recursive: Handle nested dicts

- [ ] 1.1.2 Apply to envelope logging
  - File: server.py and client.py
  - Before logging envelope: sanitize payload
  - Keep correlation_id visible for debugging

- [ ] 1.1.3 Add ASAP_DEBUG environment variable
  - If True: Log full errors and data
  - If False (production): Sanitize sensitive fields

- [ ] 1.1.4 Update error responses
  - Production: Generic errors only
  - Debug: Include stack traces
  - Always log full errors server-side

- [ ] 1.1.5 Add sanitization tests
  - Test: Tokens redacted
  - Test: Nested objects sanitized
  - Test: Non-sensitive preserved
  - Test: Debug mode shows all

- [ ] 1.1.6 Commit
  - Command: `git commit -m "feat(observability): add log sanitization for sensitive data"`
  - Close issue #12

**Acceptance**: Tokens/secrets redacted, debug mode works

---

### Task 1.2: Handler Security Documentation

- [ ] 1.2.1 Add "Handler Security" section to docs/security.md
  - Content: Input validation requirements
  - Checklist: Handler security review
  - Examples: Secure vs insecure handlers

- [ ] 1.2.2 Add FilePart URI validation
  - File: `src/asap/models/parts.py`
  - Validator: Detect path traversal (../)
  - Validator: Reject suspicious file:// URIs
  - Use: Pydantic @field_validator

- [ ] 1.2.3 Add handler validation helpers
  - File: `src/asap/transport/handlers.py`
  - Function: validate_handler(handler) checks signature
  - Optional: Handler sandboxing docs

- [ ] 1.2.4 Add validation tests
  - Test: Path traversal detected
  - Test: Malicious URIs rejected
  - Test: Valid URIs accepted

- [ ] 1.2.5 Update examples
  - Create: `src/asap/examples/secure_handler.py`
  - Show: Proper input validation

- [ ] 1.2.6 Commit
  - Command: `git commit -m "feat(security): add handler input validation"`

**Acceptance**: Handler security documented, FilePart validated

---

### Task 1.3: PRD Review Checkpoint

- [ ] 1.3.1 Review Q3 (HMAC signing)
  - If deferred from v0.5.0: Reassess complexity
  - Decide: Include in v1.0.0 or defer to v1.1.0
  - Document as DD-008 or note deferral

- [ ] 1.3.2 Update PRD
  - File: `prd-v1-roadmap.md`
  - Update Section 10 with decision
  - Update Section 11 to mark Q3 resolved

**Acceptance**: Q3 answered, PRD updated

---

## Sprint P2: Code Quality & LOW Security

### Task 2.1: Thread Safety Improvements

- [ ] 2.1.1 Review HandlerRegistry concurrency
  - File: `src/asap/transport/handlers.py`
  - Add thread-safe handler storage if needed
  - Copy handler reference before execution

- [ ] 2.1.2 Add concurrent registration test
  - Test: Multiple threads registering handlers
  - Test: Concurrent handler dispatch

- [ ] 2.1.3 Commit
  - Command: `git commit -m "refactor(transport): improve HandlerRegistry thread safety"`

**Acceptance**: Thread-safe handler registration

---

### Task 2.2: Enhanced URN Validation

- [ ] 2.2.1 Add max length validation to entities.py
  - Validator: Max 256 characters for URN
  - Validator: Stricter character restrictions
  - Use: Pydantic @field_validator on Agent.id

- [ ] 2.2.2 Add task depth validation
  - Field: Add depth tracking to Task model
  - Validator: Check depth ≤ MAX_TASK_DEPTH
  - Prevent: Infinite recursion in subtasks

- [ ] 2.2.3 Add validation tests
  - Test: URN length limits
  - Test: Invalid URN characters
  - Test: Task depth limits

- [ ] 2.2.4 Commit
  - Command: `git commit -m "feat(models): add enhanced URN and depth validation"`

**Acceptance**: URN max 256 chars, depth validated

---

### Task 2.3: Final Code Quality Audit

- [ ] 2.3.1 Run ruff with preview rules
  - Command: `uv run ruff check --preview src/ tests/`
  - Fix any new warnings

- [ ] 2.3.2 Run mypy strict on all files
  - Command: `uv run mypy --strict src/`
  - Expected: Zero errors

- [ ] 2.3.3 Check test coverage
  - Command: `uv run pytest --cov=src --cov-report=term-missing`
  - Expected: ≥95%
  - Identify: Any uncovered lines

**Acceptance**: Zero linter errors, ≥95% coverage

---

**P1-P2 Definition of Done**:
- [ ] All security issues resolved (CRIT+HIGH+MED+LOW)
- [ ] Sensitive data sanitized from logs
- [ ] Handler security documented
- [ ] Thread safety improved
- [ ] URN validation enhanced
- [ ] Test coverage >95%
- [ ] Issue #12 closed

**Total Sub-tasks**: ~50
