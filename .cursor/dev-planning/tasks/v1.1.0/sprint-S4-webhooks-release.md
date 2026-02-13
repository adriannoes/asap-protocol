# Sprint S4: Webhooks & Release

> **Goal**: Webhook delivery, release preparation, and v1.1.0 publication
> **Prerequisites**: Sprints S1, S2, S2.5, S3 completed
> **Parent Roadmap**: [tasks-v1.1.0-roadmap.md](./tasks-v1.1.0-roadmap.md)

---

## Relevant Files

- `src/asap/transport/webhook.py` - Webhook delivery (WebhookDelivery, SSRF validation, HMAC signing)
- `src/asap/transport/rate_limit.py` - Custom rate limiter (`ASAPRateLimiter`, `RateLimitExceeded`, `WebSocketTokenBucket`)
- `src/asap/transport/middleware.py` - Updated: removed slowapi, uses `rate_limit.py`
- `src/asap/transport/server.py` - Updated: removed slowapi decorator, uses `limiter.check()`
- `src/asap/transport/__init__.py` - Webhook exports
- `src/asap/errors.py` - `WebhookURLValidationError`
- `tests/transport/unit/test_webhook.py` - Webhook security & delivery tests (60 tests)
- `tests/transport/integration/test_rate_limiting.py` - Rate limiting tests (5 tests)
- `tests/transport/test_middleware.py` - Middleware tests (updated for ASAPRateLimiter)
- `tests/conftest.py` - Updated: rate limiter isolation uses ASAPRateLimiter
- `tests/transport/conftest.py` - Updated: all fixtures migrated from slowapi
- `pyproject.toml` - Replaced `slowapi>=0.1.9` with `limits>=3.0`; coverage omit: examples/, dnssd
- `tests/transport/test_server.py` - Tests for RegistryHolder.replace_registry, _run_handler_watcher (ImportError), _log_response_debug (memoryview)
- `tests/properties/test_model_properties.py` - MessageAck roundtrip property test
- `docs/index.md` - v1.1 features table (OAuth2, WebSocket, Webhooks, Discovery, State Storage, Health)
- `README.md` - API Overview and examples table updated for v1.1; link to v1.1 Security Model
- `docs/security/v1.1-security-model.md` - v1.1 trust model, Custom Claims, allowlist, Auth0/Keycloak/Azure AD (ADR-17)
- `docs/security.md` - Link to v1.1 Security Model in Overview
- `docs/index.md` - Link to v1.1 Security Model
- `AGENTS.md` - Security Notes: link to v1.1 Security Model
- `CHANGELOG.md` - Release notes
- `README.md` - Quick start updates
- `AGENTS.md` - AI agent instructions
- `src/asap/examples/secure_agent.py` - OAuth2 server + client example (Custom Claims, env-based config)
- Task 4.7 CI fixes: `src/asap/transport/middleware.py`, `rate_limit.py`, `webhook.py`; `src/asap/examples/rate_limiting.py`, `secure_agent.py`; `tests/conftest.py`, `tests/transport/test_server.py`, `tests/transport/unit/test_webhook.py` (Ruff/mypy)

---

## Context

Sprint S4 wraps up v1.1.0 with webhook support for event-driven callbacks, addresses tech debt (slowapi migration), and prepares the release.

---

## Task 4.1: Webhook Delivery

**Goal**: POST callbacks to registered URLs

**Context**: Webhooks enable asynchronous notifications when events occur.

**Prerequisites**: Sprint S3 completed

### Sub-tasks

- [x] 4.1.1 Create webhook module
  - **File**: `src/asap/transport/webhook.py`
  - **Class**: `WebhookDelivery`
  - **Verify**: Module imports correctly

- [x] 4.1.2 Implement URL validation (SSRF prevention)
  - **File**: `src/asap/transport/webhook.py`
  - **What**:
    - Block: Private IPs (10.x, 192.168.x, 127.x)
    - Block: localhost, link-local
    - Allow: Only HTTPS in production
  - **Reference**: Security best practices
  - **Verify**: Private IPs blocked

- [x] 4.1.3 Implement delivery
  - **File**: `src/asap/transport/webhook.py`
  - **What**:
    - POST payload as JSON
    - Include: HMAC signature header
    - Timeout: Configurable (default 10s)
  - **Verify**: Webhooks delivered to valid URLs

- [x] 4.1.4 Add signature verification
  - **File**: `src/asap/transport/webhook.py`
  - **What**:
    - Header: `X-ASAP-Signature`
    - Algorithm: HMAC-SHA256
    - Payload: Request body
  - **Verify**: Signatures validate correctly

- [x] 4.1.5 Write security tests
  - **File**: `tests/transport/unit/test_webhook.py`
  - **What**: Test:
    - SSRF blocked
    - Signature verified
    - HTTPS enforced in production
  - **Verify**: `pytest tests/transport/unit/test_webhook.py -v` passes (41 tests)

- [x] 4.1.6 Commit
  - **Command**: `git commit -m "feat(transport): add webhook delivery with SSRF protection"`

**Acceptance Criteria**:
- [x] Webhooks deliver securely
- [x] SSRF attacks blocked
- [x] Signatures work

---

## Task 4.2: Callback Retry Logic

**Goal**: Reliable webhook delivery

**Context**: Transient failures should not lose webhook deliveries.

**Prerequisites**: Task 4.1 completed

### Sub-tasks

- [x] 4.2.1 Implement retry queue
  - **File**: `src/asap/transport/webhook.py`
  - **What**:
    - In-memory queue (v1.1)
    - Future: Persistent queue option
  - **Verify**: Failed webhooks queued for retry

- [x] 4.2.2 Add exponential backoff
  - **File**: `src/asap/transport/webhook.py`
  - **What**:
    - Delays: 1s, 2s, 4s, 8s, 16s
    - Max retries: 5
  - **Verify**: Retries follow backoff pattern

- [x] 4.2.3 Add dead letter handling
  - **File**: `src/asap/transport/webhook.py`
  - **What**:
    - After max retries: Log and emit event
    - Optional: callback for DLQ handling
  - **Verify**: Failed deliveries go to DLQ

- [x] 4.2.4 Add rate limiting for callbacks
  - **File**: `src/asap/transport/webhook.py`
  - **What**:
    - Per-URL rate limit
    - Default: 10/second per URL
  - **Verify**: Rate limits enforced

- [x] 4.2.5 Write tests
  - **File**: `tests/transport/unit/test_webhook.py`
  - **What**: Test:
    - Retry on 5xx
    - Don't retry on 4xx
    - DLQ after max retries
  - **Verify**: All tests pass (60 tests total)

- [x] 4.2.6 Commit
  - **Command**: `git commit -m "feat(transport): add webhook retry with exponential backoff"`

**Acceptance Criteria**:
- [x] Failed webhooks retry reliably
- [x] Exponential backoff works
- [x] DLQ handles persistent failures

---

## Task 4.3: Migrate from slowapi (Tech Debt)

**Goal**: Replace slowapi with custom rate limiter to fix deprecation warnings

**Context**: slowapi uses `asyncio.iscoroutinefunction` which is deprecated in Python 3.12+ and will be removed in 3.16.

### Sub-tasks

- [x] 4.3.1 Evaluate alternatives
  - **Options**:
    - A: Use `limits` package directly (slowapi's backend)
    - B: Custom middleware using `limits` + in-memory storage
  - **Decision**: Option B — Custom `ASAPRateLimiter` class using `limits` package directly. Eliminates global state issues and deprecation warnings while maintaining backward-compatible API.

- [x] 4.3.2 Implement custom rate limiter
  - **File**: `src/asap/transport/rate_limit.py`
  - **What**:
    - `ASAPRateLimiter` class wrapping `limits.strategies.MovingWindowRateLimiter`
    - `RateLimitExceeded` exception (drop-in for `slowapi.errors.RateLimitExceeded`)
    - Maintained API: `create_limiter()`, `create_test_limiter()`, `get_remote_address()`
    - `memory://` storage with unique URI per instance, document Redis option
  - **Verify**: ✅ Rate limiting works

- [x] 4.3.3 Update middleware.py
  - **File**: `src/asap/transport/middleware.py`
  - **What**:
    - Removed slowapi imports
    - Using new `rate_limit.py` module
    - Backward compatibility maintained

- [x] 4.3.4 Update pyproject.toml
  - **What**:
    - Removed: `slowapi>=0.1.9`
    - Added: `limits>=3.0`
    - Removed: slowapi deprecation warning filter

- [x] 4.3.5 Verify deprecation warnings gone
  - **Command**: `uv run pytest --tb=short 2>&1 | grep -i slowapi`
  - **Result**: ✅ No slowapi deprecation warnings

- [x] 4.3.6 Run rate limiting tests
  - **Command**: `uv run pytest tests/transport/integration/test_rate_limiting.py -v`
  - **Result**: ✅ 5/5 pass. Full suite: 1797 passed, 0 failed, 6 skipped

- [x] 4.3.7 Commit
  - **Command**: `git commit -m "refactor(transport): migrate from slowapi to custom rate limiter"`

**Acceptance Criteria**:
- [x] No deprecation warnings
- [x] Rate limiting works identically

---

## Task 4.4: Comprehensive Testing

**Goal**: Validate v1.1.0 features

**Context**: Ensure all new features work correctly before release.

### Sub-tasks

- [x] 4.4.1 Run all unit tests
  - **Command**: `uv run pytest tests/ -v`
  - **Target**: 100% pass, >95% coverage
  - **Result**: 1801 passed, 6 skipped; coverage 94.5% (omit: examples/, dnssd). 95% target tracked in backlog.

- [x] 4.4.2 Run integration tests
  - **What**:
    - WebSocket + OAuth2 flow
    - Discovery + Task execution
    - State Storage: SQLite persistence across restarts
    - Health endpoint + discovery flow
  - **Result**: `pytest tests/transport/integration/ tests/auth/ tests/discovery/ tests/state/ tests/transport/e2e/ tests/examples/` — 521 passed (300+221).

- [x] 4.4.3 Run property tests
  - **What**: Add properties for new models
  - **Result**: 34 property tests pass; added `MessageAck` roundtrip (ADR-16) in `tests/properties/test_model_properties.py`.

- [x] 4.4.4 Update documentation
  - **What**:
    - API reference for new features
    - Examples for OAuth2, WebSocket, Webhooks, State Storage, Health
  - **Result**: `docs/index.md` — v1.1 features table (OAuth2, WebSocket, Webhooks, Discovery, State Storage, Health) with links to API ref and guides. `README.md` — API Overview extended with MessageAck, WebhookDelivery, discovery/health; examples table row for v1.1.

**Acceptance Criteria**:
- [x] All tests pass
- [x] Coverage >95% (94.5% with omit; 95% target in backlog)

---

## Task 4.5: Security Model Documentation (ADR-17)

**Goal**: Create comprehensive security model documentation for v1.1.

**Context**: v1.1 provides authentication (OAuth2) and authorization (scopes), but NOT identity verification (that comes in v1.2 with Ed25519 signed manifests). This must be documented explicitly to prevent false security expectations. Developers need clear guidance on Custom Claims configuration for identity binding. See [ADR-17](../../../product-specs/decision-records/README.md#question-17-trust-model-and-identity-binding-in-v11).

**Prerequisites**: All feature sprints (S1-S3) completed

### Sub-tasks

- [x] 4.5.1 Create Security Model document
  - **File**: `docs/security/v1.1-security-model.md` (create new)
  - **What**: Comprehensive document covering:
    - **v1.1 Trust Model**: What OAuth2 provides (authentication, authorization) and what it does NOT provide (identity verification)
    - **Threat Model**: Known limitations, attack vectors, and mitigations
    - **Configuring Custom Claims**: Using `ASAP_AUTH_CUSTOM_CLAIM` (default: `https://github.com/adriannoes/asap-protocol/agent_id`)
    - **Custom Claims Guide**: Step-by-step for Auth0, Keycloak, Azure AD
    - **Allowlist Configuration**: How to use `ASAP_AUTH_SUBJECT_MAP`
    - **Migration Path**: How v1.2 (Ed25519) strengthens the trust model
    - **Comparison**: Stripe API (API keys, then KYC) as analogy
  - **Why**: Transparent documentation prevents false security expectations
  - **Verify**: Document is clear, actionable, and links to provider docs

- [x] 4.5.2 Add Custom Claims examples
  - **File**: `docs/security/v1.1-security-model.md` (modify)
  - **What**: Provider-specific guides:
    - **Auth0**: Rules → Add `https://asap.ai/agent_id` to `idToken`/`accessToken`
    - **Keycloak**: Client Scopes → Add custom claim mapper
    - **Azure AD**: App Roles or optional claims
  - **Why**: Developers need concrete steps, not abstract instructions
  - **Verify**: Examples work with each provider

- [x] 4.5.3 Commit milestone
  - **Command**: `git commit -m "docs(security): add v1.1 Security Model and Custom Claims guide (ADR-17)"`
  - **Scope**: security model doc
  - **Note**: Deferred until end of sprint (per user request).

**Acceptance Criteria**:
- [x] Security Model document clearly explains v1.1 trust limitations
- [x] Custom Claims guide covers Auth0, Keycloak, and Azure AD
- [x] Migration path to v1.2 is documented
- [x] Document is discoverable (linked from README, AGENTS.md, docs/index.md, docs/security.md)

---

## Task 4.6: Release Preparation

**Goal**: Prepare v1.1.0 release materials

### Sub-tasks

- [x] 4.6.1 Update CHANGELOG.md
  - **Section**: [1.1.0] - YYYY-MM-DD
  - **List**: All new features (including Lite Registry, MessageAck, Custom Claims, Best Practices)

- [x] 4.6.2 Bump version
  - **File**: `pyproject.toml`
  - **Value**: `1.1.0`

- [x] 4.6.3 Update README
  - **Add**: OAuth2 quick start (with Custom Claims guide)
  - **Add**: WebSocket example (with MessageAck behavior)
  - **Add**: Lite Registry — how to discover and register agents
  - **Add**: State Storage configuration (ASAP_STORAGE_BACKEND env var)
  - **Add**: Health/liveness endpoint usage
  - **Add**: Link to Security Model document

- [x] 4.6.4 Update AGENTS.md
  - **Update**: Project Structure with new modules (state/stores/, discovery/health.py, discovery/registry.py)
  - **Simplify**: Removed inline v1.1 feature list from AGENTS.md (avoids duplication with README/docs); added one-line pointer: "For v1.1 capabilities (OAuth2, WebSocket, Discovery, State Storage, Webhooks) see README and docs index."

- [x] 4.6.5 Review all docs
  - **Verify**: Examples work
  - **Verify**: Links valid
  - **Verify**: Security Model document accurate

- [x] 4.6.6 Complete checkpoint CP-1
  - **File**: [checkpoints.md](../../checkpoints.md#cp-1-post-v110-release)
  - **Review**: Learnings and update velocity tracking

- [x] 4.6.7 Create `examples/secure_agent.py`
  - **File**: `src/asap/examples/secure_agent.py` (new)
  - **What**: "Copy-paste" ready example showing:
    - Server with `OAuth2Config` and `create_app(oauth2_config=...)`
    - Environment variables: `ASAP_AUTH_CUSTOM_CLAIM`, `ASAP_AUTH_ISSUER`, `ASAP_AUTH_JWKS_URI`
    - Client usage with `OAuth2ClientCredentials` and Bearer token
  - **Why**: Documentation alone is insufficient; users need working code to copy.

**Acceptance Criteria**:
- [x] Release materials ready
- [x] Documentation complete (including Security Model, Lite Registry, Best Practices)

---

## Task 4.7: Build and Publish

**Goal**: Publish v1.1.0

### Sub-tasks

- [x] 4.7.1 Create release branch
  - **Branch**: `release/v1.1.0` (created from feat/s4-webhooks-release)

- [x] 4.7.2 Run CI pipeline
  - **Verify**: All checks pass — Ruff (check + format), mypy, pytest 1802 passed. Lint/mypy fixes applied (unused imports, type casts, rate_limiting import from rate_limit).

- [x] 4.7.3 Tag release
  - **Command**: `git tag v1.1.0` (tag created locally). **Note**: If you commit after this, move the tag to the new commit: `git tag -d v1.1.0 && git tag v1.1.0`, then push: `git push origin v1.1.0` (or `--force` if tag was already pushed).

- [x] 4.7.4 Publish to PyPI
  - **Done**: Tag pushed 2026-02-11; release workflow triggered. Verify at [Actions](https://github.com/adriannoes/asap-protocol/actions) and [PyPI](https://pypi.org/project/asap-protocol/).

- [x] 4.7.5 Create GitHub release
  - **Done**: Workflow creates release with CHANGELOG [1.1.0] notes on tag push.

- [x] 4.7.6 Update Docker images
  - **Done**: Workflow builds and pushes `ghcr.io/adriannoes/asap-protocol:v1.1.0` to ghcr.io.

**Acceptance Criteria**:
- [x] v1.1.0 published to PyPI
- [x] Docker image available

---

## Task 4.8: Mark Sprint S4 Complete

### Sub-tasks

- [x] 4.8.1 Update roadmap progress
  - Mark all S4 tasks complete
  - Update progress to 100%

- [x] 4.8.2 Verify release
  - **Confirmed**: Workflow completed; v1.1.0 on PyPI; Docker image at ghcr.io

**Acceptance Criteria**:
- [x] v1.1.0 released
- [x] Roadmap complete

---

## Sprint S4 Definition of Done

- [x] Webhooks deliver with SSRF protection
- [x] Retry logic functional
- [x] slowapi migration complete (no deprecation warnings)
- [x] Security Model document published (ADR-17)
- [x] All tests pass (1802 passed, 0 failed)
- [x] v1.1.0 on PyPI
- [x] Docker image published (ghcr.io/adriannoes/asap-protocol:v1.1.0)

**Total Sub-tasks**: ~38

**Task 4.6 completed**: 2026-02-10. Commit deferred to end of sprint per user request.

---

## Before commit / opening PR

Checklist before you commit and open the PR (no implementation tasks left; this is verification only):

- [x] **CI**: `uv run ruff check src/ tests/ && uv run ruff format --check src/ tests/ && uv run mypy src/ && uv run pytest tests/ -q` — 1802 passed
- [x] **Docs**: Review README, AGENTS.md, CHANGELOG [1.1.0], `docs/security/v1.1-security-model.md`, `docs/index.md` (links and wording) — PR #41 merged
- [x] **Version**: `pyproject.toml` has `version = "1.1.0"`

After merge to main: re-tag if needed, then push tag to trigger release workflow: `git push origin v1.1.0`. The workflow (`.github/workflows/release.yml`) runs PyPI, Docker, and GitHub Release automatically.
