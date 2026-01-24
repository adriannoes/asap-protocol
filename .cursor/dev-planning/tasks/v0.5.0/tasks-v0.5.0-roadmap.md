# Tasks: ASAP Protocol v0.5.0 Roadmap

> Task list for v0.5.0 milestone (Security-Hardened Release)
>
> **Parent PRD**: [prd-v1-roadmap.md](../prd/prd-v1-roadmap.md)
> **Current Version**: v0.1.0
> **Target Version**: v0.5.0
> **Focus**: CRITICAL + HIGH priority security issues

---

## Sprint S1: Quick Wins & Dependency Setup

**Duration**: Flexible (estimated 3-5 days)
**Goal**: Resolve low-hanging fruit and establish dependency monitoring

### 1.1 Code Quality Improvements

- [x] 1.1.1 ~~Authentication implementation~~ ✅
  - **Status**: Already completed in [PR #8](https://github.com/adriannoes/asap-protocol/pull/8)
  - Includes: Bearer token auth, middleware, sender verification, tests
  - Coverage: 17 tests, all passing

- [ ] 1.1.2 Remove `type: ignore` in handlers.py
  - **Issue**: [#10](https://github.com/adriannoes/asap-protocol/issues/10)
  - **File**: `src/asap/transport/handlers.py`
  - **Action**: Refactor type annotations to eliminate need for suppression
  - **Test**: Verify `mypy --strict` passes without ignores

- [ ] 1.1.3 Refactor `handle_message` into smaller helpers
  - **Issue**: [#9](https://github.com/adriannoes/asap-protocol/issues/9)
  - **File**: `src/asap/transport/server.py`
  - **Action**: Extract smaller, testable functions (e.g., `_validate_envelope`, `_dispatch_to_handler`, `_create_error_response`)
  - **Test**: Maintain test coverage, add unit tests for extracted functions

### 1.2 Dependency Updates

- [ ] 1.2.1 Upgrade FastAPI to 0.128.0+
  - **Issue**: [#7](https://github.com/adriannoes/asap-protocol/issues/7)
  - **Current**: FastAPI 0.124
  - **Target**: FastAPI ≥0.128.0
  - **Action**: Update `pyproject.toml`, run full test suite
  - **Test**: Verify backward compatibility, check for breaking changes

- [ ] 1.2.2 Test compatibility with updated FastAPI
  - Run all 543 existing tests
  - Check deprecation warnings
  - Verify examples still work
  - Update docs if API changes

### 1.3 Dependency Monitoring Setup

- [ ] 1.3.1 Create Dependabot configuration
  - **Task Reference**: [Task 2.0](./tasks-security-review-report.md#20-critical-security---dependency-monitoring-setup-crit-02)
  - **File**: `.github/dependabot.yml`
  - **Config**:
    ```yaml
    version: 2
    updates:
      - package-ecosystem: "pip"
        directory: "/"
        schedule:
          interval: "daily"
        open-pull-requests-limit: 5
        labels:
          - "dependencies"
          - "security"
        # Initially: security updates only
        # Version updates will be enabled post-v0.5.0
    ```

- [ ] 1.3.2 Update CONTRIBUTING.md with dependency process
  - Add section: "Reviewing Dependabot PRs"
  - Document security update workflow
  - Explain when to approve/reject updates

- [ ] 1.3.3 Update SECURITY.md with update policy
  - Document security update SLA (e.g., critical: 24h, high: 7 days)
  - Explain how vulnerabilities are tracked
  - Link to GitHub Security Advisories

- [ ] 1.3.4 Verify CI integration
  - Ensure pip-audit runs on Dependabot PRs
  - Verify full CI suite runs automatically
  - Test that security updates are flagged correctly

**Definition of Done**:
- [ ] All GitHub issues #7, #9, #10 closed
- [ ] Dependabot configured and first PR merged
- [ ] CI passes with updated FastAPI version
- [ ] No breaking changes introduced
- [ ] Documentation updated

---

## Sprint S2: DoS Prevention & Rate Limiting

**Duration**: Flexible (estimated 5-7 days)
**Goal**: Implement rate limiting and request size validation

### 2.1 Rate Limiting Implementation

- [ ] 2.1.1 Add slowapi dependency
  - **Task Reference**: [Task 3.1](./tasks-security-review-report.md#30-high-priority---dos-prevention-high-01-high-02)
  - **File**: `pyproject.toml`
  - **Action**: Add `slowapi>=0.1.9` to dependencies
  - **Command**: `uv add slowapi>=0.1.9`

- [ ] 2.1.2 Implement rate limiting middleware
  - **Task Reference**: [Task 3.2](./tasks-security-review-report.md#30-high-priority---dos-prevention-high-01-high-02)
  - **File**: `src/asap/transport/middleware.py`
  - **Implementation**:
    ```python
    from slowapi import Limiter
    from slowapi.util import get_remote_address

    limiter = Limiter(key_func=lambda: envelope.sender)
    # Default: 100 requests/minute per sender
    ```
  - **Response**: HTTP 429 with `Retry-After` header

- [ ] 2.1.3 Integrate rate limiter in server
  - **File**: `src/asap/transport/server.py`
  - **Action**: Add rate limiter to `/asap` endpoint
  - **Config**: Make limit configurable via `create_app(rate_limit="100/minute")`

### 2.2 Request Size Validation

- [ ] 2.2.1 Add size validation constants
  - **Task Reference**: [Task 3.3](./tasks-security-review-report.md#30-high-priority---dos-prevention-high-01-high-02)
  - **File**: `src/asap/models/constants.py`
  - **Constant**: `MAX_REQUEST_SIZE = 10 * 1024 * 1024  # 10MB`

- [ ] 2.2.2 Implement size validation in parse_json_body
  - **File**: `src/asap/transport/server.py`
  - **Action**: Check `Content-Length` header before reading body
  - **Error**: Return JSON-RPC parse error (-32700) for oversized requests

- [ ] 2.2.3 Add actual body size validation
  - **Action**: Validate size after reading to detect mismatched headers
  - **Security**: Prevent memory exhaustion from large payloads

### 2.3 Configuration

- [ ] 2.3.1 Make limits configurable
  - **Task Reference**: [Task 3.4](./tasks-security-review-report.md#30-high-priority---dos-prevention-high-01-high-02)
  - **Parameters**:
    - `create_app(max_request_size: int = 10_485_760)`  # 10MB
    - `create_app(rate_limit: str = "100/minute")`
  - **Environment Variables**:
    - `ASAP_MAX_REQUEST_SIZE`
    - `ASAP_RATE_LIMIT`

### 2.4 Testing

- [ ] 2.4.1 Add rate limiting tests
  - **Task Reference**: [Task 3.5](./tasks-security-review-report.md#30-high-priority---dos-prevention-high-01-high-02)
  - **File**: `tests/transport/test_middleware.py`
  - **Tests**:
    - Requests within limit succeed
    - Requests exceeding limit return HTTP 429
    - Rate limit resets after time window
    - Different senders have independent limits

- [ ] 2.4.2 Add payload size tests
  - **Task Reference**: [Task 3.6](./tasks-security-review-report.md#30-high-priority---dos-prevention-high-01-high-02)
  - **File**: `tests/transport/test_server.py`
  - **Tests**:
    - Requests under 10MB are accepted
    - Requests over 10MB are rejected
    - Content-Length header validation works
    - Actual body size validation works

### 2.5 Documentation

- [ ] 2.5.1 Update security documentation
  - **Task Reference**: [Task 3.7](./tasks-security-review-report.md#30-high-priority---dos-prevention-high-01-high-02)
  - **File**: `docs/security.md`
  - **Content**:
    - Rate limiting configuration examples
    - Production recommendations (e.g., 1000/minute for high-traffic)
    - Request size limits and rationale
    - Monitoring rate limit hits

**Definition of Done**:
- [ ] Rate limiting working: HTTP 429 after limit exceeded
- [ ] Request size validation: 10MB default limit enforced
- [ ] Test coverage >95% maintained
- [ ] Documentation updated with configuration examples

---

## Sprint S3: Replay Attack Prevention & HTTPS

**Duration**: Flexible (estimated 4-6 days)
**Goal**: Implement timestamp validation and HTTPS enforcement

### 3.1 Timestamp Validation

- [ ] 3.1.1 Add timestamp constants
  - **Task Reference**: [Task 4.1](./tasks-security-review-report.md#40-high-priority---replay-attack-prevention-high-03)
  - **File**: `src/asap/models/constants.py`
  - **Constants**:
    ```python
    MAX_ENVELOPE_AGE_SECONDS = 300  # 5 minutes
    MAX_FUTURE_TOLERANCE_SECONDS = 30  # 30 seconds
    ```
  - **Rationale**: Balance security (short window) vs clock skew tolerance

- [ ] 3.1.2 Create validators module
  - **Task Reference**: [Task 4.2](./tasks-security-review-report.md#40-high-priority---replay-attack-prevention-high-03)
  - **File**: `src/asap/transport/validators.py`
  - **Function**: `validate_envelope_timestamp(envelope: Envelope) -> None`
  - **Logic**:
    - Reject if `timestamp < now - MAX_ENVELOPE_AGE_SECONDS`
    - Reject if `timestamp > now + MAX_FUTURE_TOLERANCE_SECONDS`
    - Raise `InvalidTimestampError` with details

- [ ] 3.1.3 Integrate validation in server
  - **Task Reference**: [Task 4.3](./tasks-security-review-report.md#40-high-priority---replay-attack-prevention-high-03)
  - **File**: `src/asap/transport/server.py`
  - **Action**: Call `validate_envelope_timestamp()` before handler dispatch
  - **Error**: Return JSON-RPC error with timestamp window info

### 3.2 Optional Nonce Support

- [ ] 3.2.1 Add nonce field to Envelope extensions
  - **Task Reference**: [Task 4.4](./tasks-security-review-report.md#40-high-priority---replay-attack-prevention-high-03)
  - **File**: `src/asap/models/envelope.py`
  - **Field**: `extensions.nonce: str | None` (optional)

- [ ] 3.2.2 Create NonceStore protocol
  - **File**: `src/asap/transport/validators.py`
  - **Protocol**:
    ```python
    @runtime_checkable
    class NonceStore(Protocol):
        def is_used(self, nonce: str) -> bool: ...
        def mark_used(self, nonce: str, ttl_seconds: int) -> None: ...
    ```

- [ ] 3.2.3 Implement InMemoryNonceStore
  - **File**: `src/asap/transport/validators.py`
  - **Implementation**: In-memory store with expiration (TTL)
  - **TTL**: `MAX_ENVELOPE_AGE_SECONDS * 2` (10 minutes)

- [ ] 3.2.4 Add optional nonce validation
  - **Config**: `create_app(require_nonce: bool = False)`
  - **Logic**: If enabled, validate nonce uniqueness
  - **Error**: Return JSON-RPC error for duplicate nonce

### 3.3 HTTPS Enforcement

- [ ] 3.3.1 Add HTTPS validation to client
  - **Task Reference**: [Task 5.1](./tasks-security-review-report.md#50-high-priority---https-enforcement-high-04)
  - **File**: `src/asap/transport/client.py`
  - **Parameter**: `require_https: bool = True` in `ASAPClient.__init__()`
  - **Validation**:
    ```python
    if require_https and not url.startswith("https://"):
        if not _is_localhost(url):
            raise ValueError("HTTPS required for non-localhost URLs")
    ```

- [ ] 3.3.2 Add environment-aware defaults
  - **Task Reference**: [Task 5.2](./tasks-security-review-report.md#50-high-priority---https-enforcement-high-04)
  - **Function**: `_is_localhost(url: str) -> bool`
  - **Logic**: Detect localhost, 127.0.0.1, ::1
  - **Behavior**: Allow HTTP for localhost in development

- [ ] 3.3.3 Add warning for HTTP in development
  - **Action**: Log warning when using HTTP with localhost
  - **Message**: "Using HTTP for development. HTTPS required in production."

### 3.4 Testing

- [ ] 3.4.1 Add timestamp validation tests
  - **Task Reference**: [Task 4.5](./tasks-security-review-report.md#40-high-priority---replay-attack-prevention-high-03)
  - **File**: `tests/transport/test_validators.py`
  - **Tests**:
    - Recent timestamps accepted
    - Old timestamps rejected (>5 minutes)
    - Future timestamps rejected (>30 seconds)
    - Timestamps within tolerance accepted

- [ ] 3.4.2 Add nonce validation tests
  - **Tests**:
    - Nonce validation prevents replay within window
    - Expired nonces are not checked
    - Different nonces accepted
    - Duplicate nonces rejected

- [ ] 3.4.3 Add HTTPS enforcement tests
  - **Task Reference**: [Task 5.3](./tasks-security-review-report.md#50-high-priority---https-enforcement-high-04)
  - **File**: `tests/transport/test_client.py`
  - **Tests**:
    - HTTPS URLs always accepted
    - HTTP URLs rejected in production mode
    - HTTP localhost URLs accepted
    - `require_https=False` allows any URL

### 3.5 Documentation

- [ ] 3.5.1 Document timestamp validation
  - **Task Reference**: [Task 4.6](./tasks-security-review-report.md#40-high-priority---replay-attack-prevention-high-03)
  - **File**: `docs/security.md`
  - **Content**:
    - Replay attack prevention mechanism
    - Timestamp window configuration
    - Clock synchronization requirements (NTP)
    - Nonce usage for critical operations

- [ ] 3.5.2 Update client documentation
  - **Task Reference**: [Task 5.4](./tasks-security-review-report.md#50-high-priority---https-enforcement-high-04)
  - **Files**: `docs/security.md`, README examples
  - **Content**:
    - HTTPS best practices
    - Development vs production configuration
    - Security warning about disabling HTTPS

### 3.6 PRD Review Checkpoint

- [ ] 3.6.1 Review PRD Open Questions
  - **PRD Reference**: [Section 11](../prd/prd-v1-roadmap.md#11-open-questions)
  - **Action**: Review security-related open questions (Q3, Q4)
  - **Questions to Answer**:
    - Q3: HMAC request signing - include in v1.0.0 or defer?
    - Assess complexity based on Sprint P1-P2 experience
  - **Deliverable**: Update PRD with decision (DD-008 if decided)

- [ ] 3.6.2 Document learnings from security implementation
  - **File**: `prd-v1-roadmap.md` Section 10
  - **Content**:
    - Any design decisions made during S1-S3
    - Lessons learned about rate limiting, HTTPS, timestamps
    - Recommendations for future improvements

**Definition of Done**:
- [ ] Envelopes older than 5 minutes rejected
- [ ] Future timestamps beyond 30s rejected
- [ ] HTTPS enforced in production mode
- [ ] Test coverage >95% maintained
- [ ] Examples updated to use HTTPS
- [ ] PRD reviewed and updated with learnings

---

## Sprint S4: Retry Logic & Authorization

**Duration**: Flexible (estimated 3-5 days)
**Goal**: Implement exponential backoff and authorization validation

### 4.1 Exponential Backoff

- [ ] 4.1.1 Implement backoff calculation
  - **Task Reference**: [Task 6.1](./tasks-security-review-report.md#60-high-priority---retry-logic-improvements-high-05)
  - **File**: `src/asap/transport/client.py`
  - **Method**: `_calculate_backoff(attempt: int) -> float`
  - **Algorithm**:
    ```python
    base_delay = 2 ** attempt  # Exponential: 1s, 2s, 4s, 8s, ...
    jitter = random.uniform(0, 0.5)  # Prevent thundering herd
    delay = min(base_delay + jitter, max_delay)  # Cap at max_delay
    ```

- [ ] 4.1.2 Add backoff configuration
  - **Task Reference**: [Task 6.2](./tasks-security-review-report.md#60-high-priority---retry-logic-improvements-high-05)
  - **Parameters**:
    - `base_delay: float = 1.0`
    - `max_delay: float = 60.0`
    - `jitter: bool = True`

- [ ] 4.1.3 Update retry loop with backoff
  - **Task Reference**: [Task 6.3](./tasks-security-review-report.md#60-high-priority---retry-logic-improvements-high-05)
  - **File**: `src/asap/transport/client.py` (send method)
  - **Logic**:
    - Apply backoff for retriable errors (5xx, connection errors)
    - No backoff for client errors (4xx)
    - Log retry attempts with delay
    - `await asyncio.sleep(delay)`

### 4.2 Circuit Breaker (Optional)

- [ ] 4.2.1 Implement circuit breaker pattern
  - **Task Reference**: [Task 6.4](./tasks-security-review-report.md#60-high-priority---retry-logic-improvements-high-05)
  - **File**: `src/asap/transport/client.py`
  - **States**: Closed → Open → Half-Open
  - **Logic**:
    - Track consecutive failures per base_url
    - Open circuit after N failures (default: 5)
    - Half-open after timeout (exponential backoff)
    - Close on success in half-open state

- [ ] 4.2.2 Add circuit breaker configuration
  - **Parameters**:
    - `circuit_breaker_enabled: bool = False`
    - `circuit_breaker_threshold: int = 5`
    - `circuit_breaker_timeout: float = 60.0`

- [ ] 4.2.3 Log circuit state changes
  - **Action**: Log when circuit opens, half-opens, closes
  - **Level**: WARNING for open, INFO for close

### 4.3 Authorization Scheme Validation

- [ ] 4.3.1 Add scheme validation to Manifest
  - **Issue**: [#13](https://github.com/adriannoes/asap-protocol/issues/13)
  - **File**: `src/asap/models/entities.py`
  - **Validation**: Ensure `auth.schemes` are supported
  - **Supported**: `bearer`, `basic`, `oauth2` (future), `hmac` (future)

- [ ] 4.3.2 Add validation function
  - **Function**: `validate_auth_scheme(scheme: AuthScheme) -> None`
  - **Logic**: Check scheme against supported list
  - **Error**: Raise `UnsupportedAuthSchemeError` if invalid

- [ ] 4.3.3 Integrate in create_app
  - **File**: `src/asap/transport/server.py`
  - **Action**: Validate manifest.auth schemes at startup
  - **Error**: Fail fast with clear error message

### 4.4 Testing

- [ ] 4.4.1 Add backoff tests
  - **Task Reference**: [Task 6.5](./tasks-security-review-report.md#60-high-priority---retry-logic-improvements-high-05)
  - **File**: `tests/transport/test_client.py`
  - **Tests**:
    - Backoff delays increase exponentially
    - Jitter is applied correctly
    - Maximum delay is respected
    - Immediate retry for non-retriable errors

- [ ] 4.4.2 Add circuit breaker tests
  - **Tests**:
    - Circuit opens after threshold failures
    - Circuit half-opens after timeout
    - Circuit closes on success
    - Open circuit rejects requests immediately

- [ ] 4.4.3 Add authorization validation tests
  - **File**: `tests/models/test_entities.py`
  - **Tests**:
    - Valid schemes accepted
    - Invalid schemes rejected
    - Missing auth config works (no auth)
    - create_app fails with unsupported scheme

### 4.5 Documentation

- [ ] 4.5.1 Document retry configuration
  - **Task Reference**: [Task 6.6](./tasks-security-review-report.md#60-high-priority---retry-logic-improvements-high-05)
  - **File**: `docs/transport.md`
  - **Content**:
    - Backoff strategy explanation
    - Configuration examples
    - When to use circuit breaker

- [ ] 4.5.2 Document authorization schemes
  - **File**: `docs/security.md`
  - **Content**:
    - Supported auth schemes
    - How to configure each scheme
    - Validation behavior
    - Future schemes (OAuth2, HMAC)

**Definition of Done**:
- [ ] Exponential backoff with jitter working
- [ ] Max delay capped at 60 seconds
- [ ] Authorization schemes validated at manifest load
- [ ] Test coverage >95% maintained
- [ ] Documentation covers retry configuration

---

## Sprint S5: v0.5.0 Release Preparation

**Duration**: Flexible (estimated 2-3 days)
**Goal**: Final testing, documentation, and release

### 5.1 Security Audit

- [ ] 5.1.1 Run pip-audit
  - **Command**: `uv run pip-audit`
  - **Action**: Verify no known vulnerabilities
  - **Resolution**: Update or document false positives

- [ ] 5.1.2 Run bandit security linter
  - **Command**: `uv run bandit -r src/`
  - **Action**: Check for security issues in code
  - **Resolution**: Fix high/medium severity findings

- [ ] 5.1.3 Manual security review
  - Review all CRIT+HIGH tasks completed
  - Verify secure defaults (HTTPS, auth, rate limiting)
  - Check error messages don't leak sensitive info

### 5.2 Testing & Quality

- [ ] 5.2.1 Run full test suite
  - **Command**: `uv run pytest`
  - **Target**: All tests passing
  - **Coverage**: ≥95%

- [ ] 5.2.2 Run benchmark suite
  - **Command**: `uv run pytest benchmarks/`
  - **Action**: Verify no performance regressions
  - **Threshold**: <5% slowdown vs v0.1.0

- [ ] 5.2.3 Run linters
  - **Commands**:
    - `uv run ruff check src/ tests/`
    - `uv run ruff format src/ tests/`
    - `uv run mypy --strict src/`
  - **Target**: Zero errors

### 5.3 Compatibility Testing

- [ ] 5.3.1 Test upgrade path from v0.1.0
  - Install v0.1.0, create agent
  - Upgrade to v0.5.0
  - Verify agent still works without changes
  - Test new security features are opt-in

- [ ] 5.3.2 Test examples
  - Run all examples in `src/asap/examples/`
  - Verify they work with v0.5.0
  - Update examples if needed

### 5.4 Documentation Review

- [ ] 5.4.1 Review all documentation
  - README.md - update version, features
  - docs/ - verify accuracy
  - CHANGELOG.md - complete v0.5.0 entry
  - API docs - check for broken links

- [ ] 5.4.2 Update migration guide
  - Document v0.1.0 → v0.5.0 upgrade
  - List new configuration options
  - Highlight backward compatibility

### 5.5 Release Preparation

- [ ] 5.5.1 Update CHANGELOG.md
  - **Section**: `## [0.5.0] - YYYY-MM-DD`
  - **Content**:
    - All security improvements (CRIT+HIGH)
    - Code quality fixes (issues #7, #9, #10)
    - Dependency updates
    - Breaking changes (if any)
  - **Format**: Follow [Keep a Changelog](https://keepachangelog.com/)

- [ ] 5.5.2 Create release notes
  - **File**: `.github/release-notes-v0.5.0.md`
  - **Sections**:
    - Security hardening highlights
    - Upgrade instructions
    - Breaking changes
    - Thank contributors

- [ ] 5.5.3 Review open PRs
  - Merge ready PRs
  - Defer non-critical PRs to v0.6.0 or v1.0.0
  - Close stale PRs

- [ ] 5.5.4 Tag and publish
  - **Tag**: `git tag v0.5.0 && git push origin v0.5.0`
  - **Publish**: `uv build && uv publish`
  - **Verify**: Check PyPI package page

- [ ] 5.5.5 Create GitHub release
  - Use release notes from 5.5.2
  - Attach wheel and sdist
  - Mark as "Pre-release" (still alpha)

### 5.6 Communication

- [ ] 5.6.1 Announce release
  - Update README badges
  - Post to GitHub Discussions
  - Share on social media (if applicable)

- [ ] 5.6.2 Notify users
  - Comment on resolved issues
  - Thank contributors

**Definition of Done**:
- [ ] All CRIT+HIGH security tasks completed
- [ ] Zero breaking changes vs v0.1.0 (or documented)
- [ ] CI passes on all platforms
- [ ] v0.5.0 published to PyPI
- [ ] GitHub release created with notes
- [ ] Test coverage ≥95%
- [ ] Performance regression <5%

---

## Summary

| Sprint | Tasks | Focus | Estimated Days |
|--------|-------|-------|----------------|
| S1 | 9 | Quick wins + Dependabot | 3-5 |
| S2 | 12 | DoS prevention | 5-7 |
| S3 | 16 | Replay attack + HTTPS + **PRD Review** | 4-6 |
| S4 | 13 | Retry + Authorization | 3-5 |
| S5 | 16 | Release prep | 2-3 |

**Total**: 66 tasks across 5 sprints

**PRD Review Checkpoints**: 1 (Sprint S3)

---

## Progress Tracking

**Overall Progress**: 1/66 tasks completed (1.52%)

**Sprint Status**:
- ✅ S1: 1/9 tasks (11.11%) - Authentication completed in PR #8
- ⏳ S2: 0/12 tasks (0%)
- ⏳ S3: 0/16 tasks (0%) - **Includes PRD review checkpoint**
- ⏳ S4: 0/13 tasks (0%)
- ⏳ S5: 0/16 tasks (0%)

**PRD Maintenance**:
- Next review: End of Sprint S3
- Questions to address: Q3 (HMAC signing decision)

**Last Updated**: 2026-01-24
