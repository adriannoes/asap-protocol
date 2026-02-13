# Tasks: Security Review Hardening

> Task list generated from [security-review-report.md](../code-review/security-review-report.md)
>
> **Context**: Pre-PyPI release security review identified 14 vulnerabilities that need to be addressed to ensure production-ready security posture.
>
> **Approach**: Prioritized by severity (Critical → High → Medium → Low). Critical issues must be resolved before PyPI release.

---

## Relevant Files

### Authentication & Authorization
- `src/asap/models/entities.py` - `AuthScheme` model (lines 121-145) - Already exists
- `src/asap/transport/server.py` - ✅ `create_app()` with auth middleware integration
- `src/asap/transport/server.py` - ✅ `handle_asap_message()` with auth verification and sender validation
- `src/asap/transport/middleware.py` - ✅ Authentication middleware with Bearer token support
- `tests/transport/test_middleware.py` - ✅ Comprehensive tests (17 tests, all passing)
- `docs/security.md` - ✅ Updated with complete auth implementation examples and best practices

### Rate Limiting & DoS Protection
- `src/asap/transport/server.py` - `create_app()` - Needs rate limiting middleware
- `src/asap/transport/middleware.py` - Rate limiting implementation
- `pyproject.toml` - Add `slowapi` dependency for rate limiting
- `tests/transport/test_middleware.py` - Rate limiting tests

### Request Validation & Size Limits
- `src/asap/transport/server.py` - `parse_json_body()` (lines 156-173) - Needs size validation
- `src/asap/models/constants.py` - Add `MAX_REQUEST_SIZE` constant
- `tests/transport/test_server.py` - Add payload size tests

### Timestamp & Replay Attack Prevention
- `src/asap/models/envelope.py` - `timestamp` validation (lines 79-85) - Needs age validation
- `src/asap/models/constants.py` - Add timestamp window constants
- `src/asap/transport/server.py` - Add timestamp validation before processing
- `tests/models/test_envelope.py` - Add timestamp validation tests

### HTTPS Enforcement
- `src/asap/transport/client.py` - `__init__()` (lines 135-164) - Needs HTTPS validation
- `tests/transport/test_client.py` - Add HTTPS enforcement tests

### Retry Logic & Backoff
- `src/asap/transport/client.py` - `send()` method (lines 198-392) - Needs exponential backoff
- `tests/transport/test_client.py` - Add backoff tests

### Logging & Error Handling
- `src/asap/observability/logging.py` - Needs sensitive data sanitization
- `src/asap/transport/server.py` - Error handling (lines 387-426) - Needs debug mode
- `tests/observability/test_logging.py` - Add sanitization tests

### Input Validation
- `src/asap/transport/handlers.py` - Handler registry security documentation
- `src/asap/models/parts.py` - `FilePart` URI validation (lines 65-127)
- `tests/models/test_parts.py` - Add path traversal tests

### Configuration & CI/CD
- `.github/dependabot.yml` - New file for dependency monitoring (post-v0.1.0)
- `.github/workflows/ci.yml` - Already has pip-audit ✅
- `CONTRIBUTING.md` - Needs dependency update process documentation
- `SECURITY.md` - Needs security update policy documentation
- `docs/security.md` - Update with production configuration guidance

### Notes

- **Test runner**: Use `uv run pytest tests/transport/` for transport tests
- **Security audit**: Use `uv run pip-audit` to check dependencies
- **Coverage**: Maintain >95% coverage after security improvements
- **Documentation**: All security features must be documented in `docs/security.md`

---

## Tasks

- [x] 1.0 Critical Security - Authentication Implementation (CRIT-01)
  - [x] 1.1 Create authentication middleware module
    - Create `src/asap/transport/middleware.py` with `AuthenticationMiddleware` class
    - Support Bearer token authentication based on `AuthScheme` in manifest
    - Extract and validate `Authorization` header from requests
  - [x] 1.2 Implement token validation interface
    - Define `TokenValidator` protocol in `middleware.py`
    - Implement `BearerTokenValidator` with customizable validation logic
    - Support dependency injection for custom validators
  - [x] 1.3 Add sender verification
    - Verify that `envelope.sender` matches authenticated agent ID
    - Reject requests where sender doesn't match token identity
    - Return HTTP 403 with proper JSON-RPC error
  - [x] 1.4 Integrate auth middleware in server
    - Update `create_app()` in `server.py` to add auth middleware
    - Make authentication optional based on `manifest.auth` configuration
    - Add `token_validator` parameter to server factory
  - [x] 1.5 Add comprehensive tests
    - Test successful authentication with valid Bearer token
    - Test rejection of requests without authentication when required
    - Test rejection of mismatched sender/token
    - Test that authentication is skipped when not configured
  - [x] 1.6 Update documentation
    - Add authentication implementation examples to `docs/security.md`
    - Document how to implement custom `TokenValidator`
    - Add example of OAuth2 integration pattern

- [x] 2.0 Critical Security - Dependency Monitoring Setup (CRIT-02)
  - [x] 2.1 Create Dependabot configuration (Post-Release v0.1.0)
    - Create `.github/dependabot.yml` with pip ecosystem config
    - Configure daily security checks for Python dependencies
    - Set `open-pull-requests-limit: 5` to avoid PR spam
    - **Initially**: Security updates ONLY (no version updates)
    - Add labels: "dependencies" and "security"
  - [x] 2.2 Document dependency update process
    - Add dependency update process to `CONTRIBUTING.md`
    - Document how to review and merge Dependabot PRs
    - Add security update policy to `SECURITY.md`
    - Document that version updates will be enabled later (monthly schedule)
  - [x] 2.3 Verify CI integration
    - Ensure `pip-audit` continues running in CI (already configured)
    - Verify Dependabot PRs trigger full CI suite automatically
    - Test that security updates are properly flagged
    - Confirm no additional CI costs for public repo
  - [x] 2.4 Enable version updates (Post-Release v0.1.1+)
    - Add monthly version update schedule to dependabot.yml
    - Configure grouping for minor/patch updates
    - Set up auto-merge for passing tests (optional)
    - Monitor PR volume and adjust schedule if needed

- [x] 3.0 High Priority - DoS Prevention (HIGH-01, HIGH-02)
  - [x] 3.1 Add rate limiting dependency
    - Add `slowapi>=0.1.9` to `pyproject.toml` dependencies
    - Update `uv.lock` with new dependency
  - [x] 3.2 Implement rate limiting middleware
    - Create `RateLimiter` in `middleware.py` using slowapi
    - Configure rate limit based on `envelope.sender` header
    - Set default limit to 100 requests/minute per sender
    - Return HTTP 429 with `Retry-After` header when limit exceeded
  - [x] 3.3 Add request size validation
    - Define `MAX_REQUEST_SIZE = 10 * 1024 * 1024` (10MB) in `constants.py`
    - Update `parse_json_body()` to check `Content-Length` header
    - Validate actual body size after reading
    - Return JSON-RPC parse error for oversized requests
  - [x] 3.4 Make limits configurable
    - Add `max_request_size: int` parameter to `create_app()`
    - Add `rate_limit: str` parameter (e.g., "100/minute")
    - Support environment variable overrides
  - [x] 3.5 Add rate limiting tests
    - Test requests within limit succeed
    - Test requests exceeding limit return HTTP 429
    - Test rate limit reset after time window
    - Test different senders have independent limits
  - [x] 3.6 Add payload size tests
    - Test requests under 10MB are accepted
    - Test requests over 10MB are rejected
    - Test Content-Length header validation
    - Test actual body size validation
  - [x] 3.7 Update documentation
    - Document rate limiting configuration in `docs/security.md`
    - Add production recommendations for rate limits
    - Document request size limits and rationale

- [x] 4.0 High Priority - Replay Attack Prevention (HIGH-03)
  - [x] 4.1 Add timestamp validation constants
    - Add `MAX_ENVELOPE_AGE_SECONDS = 300` (5 minutes) to `constants.py`
    - Add `MAX_FUTURE_TOLERANCE_SECONDS = 30` (30 seconds) to `constants.py`
    - Document rationale for chosen time windows
  - [x] 4.2 Implement timestamp validation function
    - Create `validate_envelope_timestamp()` in new `src/asap/transport/validators.py`
    - Reject envelopes older than `MAX_ENVELOPE_AGE_SECONDS`
    - Reject envelopes with timestamp in future beyond tolerance
    - Return detailed error message with timestamp details
  - [x] 4.3 Integrate validation in server
    - Call `validate_envelope_timestamp()` before handler dispatch
    - Return JSON-RPC error for invalid timestamps
    - Include timestamp window info in error response
  - [x] 4.4 Add optional nonce support
    - Add `nonce: str | None` field to `Envelope` extensions
    - Create `NonceStore` protocol for tracking used nonces
    - Implement `InMemoryNonceStore` with expiration
    - Make nonce validation optional based on configuration
  - [x] 4.5 Add comprehensive tests
    - Test recent timestamps are accepted
    - Test old timestamps are rejected (>5 minutes)
    - Test future timestamps are rejected (>30 seconds)
    - Test timestamps within tolerance are accepted
    - Test nonce validation prevents replay within window
  - [x] 4.6 Update documentation
    - Document timestamp validation in `docs/security.md`
    - Explain replay attack prevention mechanism
    - Document nonce usage for critical operations

- [x] 5.0 High Priority - HTTPS Enforcement (HIGH-04)
  - [x] 5.1 Add HTTPS validation to client
    - Add `require_https: bool = True` parameter to `ASAPClient.__init__()`
    - Validate URL scheme is HTTPS when `require_https=True`
    - Allow HTTP only for localhost/127.0.0.1 in development
    - Raise `ValueError` with clear message for HTTP in production
  - [x] 5.2 Add environment-aware defaults
    - Detect development environment (localhost, 127.0.0.1, ::1)
    - Auto-disable HTTPS requirement for local development
    - Add warning log when using HTTP in development
  - [x] 5.3 Add tests for HTTPS enforcement
    - Test HTTPS URLs are always accepted
    - Test HTTP URLs are rejected in production mode
    - Test HTTP localhost URLs are accepted
    - Test `require_https=False` allows any URL
  - [x] 5.4 Update documentation and examples
    - Update client examples in README to use HTTPS
    - Document `require_https` parameter in API docs
    - Add security warning about disabling HTTPS
    - Update `docs/security.md` with HTTPS best practices

- [x] 6.0 High Priority - Retry Logic Improvements (HIGH-05)
  - [x] 6.1 Implement exponential backoff
    - Add `_calculate_backoff()` method to `ASAPClient`
    - Implement exponential backoff: base_delay = 2^attempt seconds
    - Add jitter: random.uniform(0, 0.5) to prevent thundering herd
    - Cap maximum delay at 60 seconds
  - [x] 6.2 Add backoff configuration
    - Add `base_delay: float = 1.0` parameter to `ASAPClient`
    - Add `max_delay: float = 60.0` parameter
    - Add `jitter: bool = True` parameter
  - [x] 6.3 Update retry loop
    - Replace immediate retry with `await asyncio.sleep(delay)`
    - Apply backoff only for retriable errors (5xx, connection errors)
    - Don't apply backoff for client errors (4xx)
    - Log retry attempts with delay information
  - [x] 6.4 Add circuit breaker pattern (optional)
    - Track consecutive failures per base_url
    - Open circuit after N consecutive failures
    - Add exponential backoff for circuit reset
    - Log circuit state changes
  - [x] 6.5 Add retry tests
    - Test backoff delays increase exponentially
    - Test jitter is applied correctly
    - Test maximum delay is respected
    - Test immediate retry for non-retriable errors
  - [x] 6.6 Update documentation
    - Document retry configuration in client API docs
    - Explain backoff strategy in `docs/transport.md`
    - Add best practices for retry configuration

- [x] 7.0 Medium Priority - Sensitive Data Protection (MED-01, MED-02)
  - **Related Issue**: [#12](https://github.com/adriannoes/asap-protocol/issues/12) - Security hardening - token logging
  - [x] 7.1 Implement log sanitization
    - Create `sanitize_for_logging()` function in `logging.py`
    - Define sensitive key patterns (password, token, secret, key, authorization)
    - Recursively sanitize nested dictionaries
    - Replace sensitive values with "***REDACTED***"
    - **Note**: This addresses token prefix logging issue identified in PR #8
  - [x] 7.2 Update logging calls
    - Apply sanitization to envelope payloads before logging
    - Sanitize request/response data in transport layer
    - Sanitize error details in exception handlers
  - [x] 7.3 Add debug mode for development
    - Add `ASAP_DEBUG` environment variable
    - Show full error details only when debug=True
    - Return generic errors in production mode
    - Log full stack traces server-side always
  - [x] 7.4 Update error responses
    - Modify exception handler in `server.py`
    - Return sanitized error details by default
    - Include full details only in debug mode
    - Always log full errors server-side
  - [x] 7.5 Add sanitization tests
    - Test sensitive keys are redacted from logs
    - Test nested objects are sanitized
    - Test non-sensitive data is preserved
    - Test debug mode exposes full errors
    - Test production mode hides details
  - [x] 7.6 Update documentation
    - Document sensitive data handling in `docs/security.md`
    - Document debug mode usage in `docs/observability.md`
    - Add production logging best practices

- [x] 8.0 Medium Priority - Input Validation Hardening (MED-03, MED-04)
  - [x] 8.1 Document handler security requirements
    - Add "Handler Security" section to `docs/security.md`
    - Document input validation requirements for handlers
    - Provide examples of secure handler implementation
    - Add checklist for handler security review
  - [x] 8.2 Add FilePart URI validation
    - Add `validate_uri()` field validator to `FilePart`
    - Detect path traversal attempts (../ patterns)
    - Reject file:// URIs with suspicious paths
    - Validate URI format with urlparse
  - [x] 8.3 Add handler validation helpers
    - Create `validate_handler()` utility function
    - Check handler signature matches expected interface
    - Validate handler doesn't access dangerous modules
    - Add opt-in handler sandboxing documentation
  - [x] 8.4 Add validation tests
    - Test path traversal detection in FilePart
    - Test malicious file:// URIs are rejected
    - Test valid URIs are accepted
    - Test handler validation utility
  - [x] 8.5 Update handler examples
    - Add security-focused handler example
    - Show proper input validation patterns
    - Demonstrate error handling best practices
    - Add example of rate-limited handler

- [x] 9.0 Low Priority - Code Improvements (LOW-01, LOW-02, LOW-03)
  - [x] 9.1 Improve HandlerRegistry thread safety
    - Copy handler reference before execution
    - Document thread-safe usage patterns
    - Add test for concurrent handler registration
  - [x] 9.2 Enhance URN validation
    - Add max length validation (suggested: 256 chars)
    - Restrict special characters more strictly
    - Add validation tests for edge cases
  - [x] 9.3 Add task depth validation
    - Implement depth validation in `Task` model
    - Check depth when creating subtasks
    - Raise error if depth exceeds `MAX_TASK_DEPTH`
    - Add validation tests

---

## Definition of Done

### Critical Tasks (1.0, 2.0)
- [x] Task 1.0: Authentication implementation completed ✅
- [x] Task 2.0: To be completed AFTER v0.1.0 release
  - Dependabot is free and takes 5 minutes to configure
  - Will be done post-release to avoid delaying launch
  - Security monitoring already covered by pip-audit in CI
- [x] CI passes with >95% coverage maintained
- [x] Documentation updated in `docs/security.md`
- [x] Breaking changes (if any) documented in CHANGELOG.md
- [x] Ready for PyPI v0.1.0 release

### High Priority Tasks (3.0-6.0)
- [x] All sub-tasks completed and tested
- [x] Backward compatible (no breaking changes)
- [x] Performance benchmarks show no regression
- [x] Ready for v0.1.1 release

### Medium Priority Tasks (7.0-8.0)
- [x] All sub-tasks completed and tested
- [x] Production deployment guide updated
- [x] Security best practices documented
- [x] Ready for v0.1.2 release

### Low Priority Tasks (9.0)
- [x] Code quality improvements verified
- [x] No performance impact
- [x] Future release (v0.2.0+)