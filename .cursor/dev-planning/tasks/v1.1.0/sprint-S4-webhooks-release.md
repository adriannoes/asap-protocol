# Sprint S4: Webhooks & Release

> **Goal**: Webhook delivery, release preparation, and v1.1.0 publication
> **Prerequisites**: Sprints S1, S2, S2.5, S3 completed
> **Parent Roadmap**: [tasks-v1.1.0-roadmap.md](./tasks-v1.1.0-roadmap.md)

---

## Relevant Files

- `src/asap/transport/webhook.py` - Webhook delivery
- `src/asap/transport/rate_limit.py` - Custom rate limiter
- `tests/transport/test_webhook.py` - Webhook tests
- `tests/transport/test_rate_limiting.py` - Rate limiting tests
- `pyproject.toml` - Version bump and dependencies
- `CHANGELOG.md` - Release notes
- `README.md` - Quick start updates
- `AGENTS.md` - AI agent instructions

---

## Context

Sprint S4 wraps up v1.1.0 with webhook support for event-driven callbacks, addresses tech debt (slowapi migration), and prepares the release.

---

## Task 4.1: Webhook Delivery

**Goal**: POST callbacks to registered URLs

**Context**: Webhooks enable asynchronous notifications when events occur.

**Prerequisites**: Sprint S3 completed

### Sub-tasks

- [ ] 4.1.1 Create webhook module
  - **File**: `src/asap/transport/webhook.py`
  - **Class**: `WebhookDelivery`
  - **Verify**: Module imports correctly

- [ ] 4.1.2 Implement URL validation (SSRF prevention)
  - **File**: `src/asap/transport/webhook.py`
  - **What**:
    - Block: Private IPs (10.x, 192.168.x, 127.x)
    - Block: localhost, link-local
    - Allow: Only HTTPS in production
  - **Reference**: Security best practices
  - **Verify**: Private IPs blocked

- [ ] 4.1.3 Implement delivery
  - **File**: `src/asap/transport/webhook.py`
  - **What**:
    - POST payload as JSON
    - Include: HMAC signature header
    - Timeout: Configurable (default 10s)
  - **Verify**: Webhooks delivered to valid URLs

- [ ] 4.1.4 Add signature verification
  - **File**: `src/asap/transport/webhook.py`
  - **What**:
    - Header: `X-ASAP-Signature`
    - Algorithm: HMAC-SHA256
    - Payload: Request body
  - **Verify**: Signatures validate correctly

- [ ] 4.1.5 Write security tests
  - **File**: `tests/transport/test_webhook.py`
  - **What**: Test:
    - SSRF blocked
    - Signature verified
    - HTTPS enforced in production
  - **Verify**: `pytest tests/transport/test_webhook.py -v` passes

- [ ] 4.1.6 Commit
  - **Command**: `git commit -m "feat(transport): add webhook delivery with SSRF protection"`

**Acceptance Criteria**:
- [ ] Webhooks deliver securely
- [ ] SSRF attacks blocked
- [ ] Signatures work

---

## Task 4.2: Callback Retry Logic

**Goal**: Reliable webhook delivery

**Context**: Transient failures should not lose webhook deliveries.

**Prerequisites**: Task 4.1 completed

### Sub-tasks

- [ ] 4.2.1 Implement retry queue
  - **File**: `src/asap/transport/webhook.py`
  - **What**:
    - In-memory queue (v1.1)
    - Future: Persistent queue option
  - **Verify**: Failed webhooks queued for retry

- [ ] 4.2.2 Add exponential backoff
  - **File**: `src/asap/transport/webhook.py`
  - **What**:
    - Delays: 1s, 2s, 4s, 8s, 16s
    - Max retries: 5
  - **Verify**: Retries follow backoff pattern

- [ ] 4.2.3 Add dead letter handling
  - **File**: `src/asap/transport/webhook.py`
  - **What**:
    - After max retries: Log and emit event
    - Optional: callback for DLQ handling
  - **Verify**: Failed deliveries go to DLQ

- [ ] 4.2.4 Add rate limiting for callbacks
  - **File**: `src/asap/transport/webhook.py`
  - **What**:
    - Per-URL rate limit
    - Default: 10/second per URL
  - **Verify**: Rate limits enforced

- [ ] 4.2.5 Write tests
  - **File**: `tests/transport/test_webhook.py`
  - **What**: Test:
    - Retry on 5xx
    - Don't retry on 4xx
    - DLQ after max retries
  - **Verify**: All tests pass

- [ ] 4.2.6 Commit
  - **Command**: `git commit -m "feat(transport): add webhook retry with exponential backoff"`

**Acceptance Criteria**:
- [ ] Failed webhooks retry reliably
- [ ] Exponential backoff works
- [ ] DLQ handles persistent failures

---

## Task 4.3: Migrate from slowapi (Tech Debt)

**Goal**: Replace slowapi with custom rate limiter to fix deprecation warnings

**Context**: slowapi uses `asyncio.iscoroutinefunction` which is deprecated in Python 3.12+ and will be removed in 3.16.

### Sub-tasks

- [ ] 4.3.1 Evaluate alternatives
  - **Options**:
    - A: Use `limits` package directly (slowapi's backend)
    - B: Custom middleware using `limits` + in-memory storage
  - **Decision**: Choose based on simplicity and testability

- [ ] 4.3.2 Implement custom rate limiter
  - **File**: `src/asap/transport/rate_limit.py` (new)
  - **What**:
    - Use `limits` package directly
    - Maintain current API: `create_limiter()`, `rate_limit_handler()`
    - Keep `memory://` storage, document Redis option
  - **Verify**: Rate limiting still works

- [ ] 4.3.3 Update middleware.py
  - **File**: `src/asap/transport/middleware.py`
  - **What**:
    - Remove slowapi imports
    - Use new `rate_limit.py` module
    - Keep backward compatibility

- [ ] 4.3.4 Update pyproject.toml
  - **What**:
    - Remove: `slowapi>=0.1.9`
    - Add: `limits>=3.0` (if not already transitive dep)

- [ ] 4.3.5 Verify deprecation warnings gone
  - **Command**: `uv run pytest --tb=short 2>&1 | grep -i deprecat`
  - **Target**: No asyncio deprecation warnings

- [ ] 4.3.6 Run rate limiting tests
  - **Command**: `uv run pytest tests/transport/test_rate_limiting.py -v`
  - **Verify**: All tests pass

- [ ] 4.3.7 Commit
  - **Command**: `git commit -m "refactor(transport): migrate from slowapi to custom rate limiter"`

**Acceptance Criteria**:
- [ ] No deprecation warnings
- [ ] Rate limiting works identically

---

## Task 4.4: Comprehensive Testing

**Goal**: Validate v1.1.0 features

**Context**: Ensure all new features work correctly before release.

### Sub-tasks

- [ ] 4.4.1 Run all unit tests
  - **Command**: `uv run pytest tests/ -v`
  - **Target**: 100% pass, >95% coverage

- [ ] 4.4.2 Run integration tests
  - **What**:
    - WebSocket + OAuth2 flow
    - Discovery + Task execution
    - State Storage: SQLite persistence across restarts
    - Health endpoint + discovery flow

- [ ] 4.4.3 Run property tests
  - **What**: Add properties for new models

- [ ] 4.4.4 Update documentation
  - **What**:
    - API reference for new features
    - Examples for OAuth2, WebSocket, Webhooks, State Storage, Health

**Acceptance Criteria**:
- [ ] All tests pass
- [ ] Coverage >95%

---

## Task 4.5: Security Model Documentation (ADR-17)

**Goal**: Create comprehensive security model documentation for v1.1.

**Context**: v1.1 provides authentication (OAuth2) and authorization (scopes), but NOT identity verification (that comes in v1.2 with Ed25519 signed manifests). This must be documented explicitly to prevent false security expectations. Developers need clear guidance on Custom Claims configuration for identity binding. See [ADR-17](../../../product-specs/ADR.md#question-17-trust-model-and-identity-binding-in-v11).

**Prerequisites**: All feature sprints (S1-S3) completed

### Sub-tasks

- [ ] 4.5.1 Create Security Model document
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

- [ ] 4.5.2 Add Custom Claims examples
  - **File**: `docs/security/v1.1-security-model.md` (modify)
  - **What**: Provider-specific guides:
    - **Auth0**: Rules → Add `https://asap.ai/agent_id` to `idToken`/`accessToken`
    - **Keycloak**: Client Scopes → Add custom claim mapper
    - **Azure AD**: App Roles or optional claims
  - **Why**: Developers need concrete steps, not abstract instructions
  - **Verify**: Examples work with each provider

- [ ] 4.5.3 Commit milestone
  - **Command**: `git commit -m "docs(security): add v1.1 Security Model and Custom Claims guide (ADR-17)"`
  - **Scope**: security model doc
  - **Verify**: `git log -1` shows correct message

**Acceptance Criteria**:
- [ ] Security Model document clearly explains v1.1 trust limitations
- [ ] Custom Claims guide covers Auth0, Keycloak, and Azure AD
- [ ] Migration path to v1.2 is documented
- [ ] Document is discoverable (linked from README, AGENTS.md, and PRD)

---

## Task 4.6: Release Preparation

**Goal**: Prepare v1.1.0 release materials

### Sub-tasks

- [ ] 4.6.1 Update CHANGELOG.md
  - **Section**: [1.1.0] - YYYY-MM-DD
  - **List**: All new features (including Lite Registry, MessageAck, Custom Claims, Best Practices)

- [ ] 4.6.2 Bump version
  - **File**: `pyproject.toml`
  - **Value**: `1.1.0`

- [ ] 4.6.3 Update README
  - **Add**: OAuth2 quick start (with Custom Claims guide)
  - **Add**: WebSocket example (with MessageAck behavior)
  - **Add**: Lite Registry — how to discover and register agents
  - **Add**: State Storage configuration (ASAP_STORAGE_BACKEND env var)
  - **Add**: Health/liveness endpoint usage
  - **Add**: Link to Security Model document

- [ ] 4.6.4 Update AGENTS.md
  - **Add**: OAuth2 setup commands and environment variables
  - **Add**: Custom Claims identity binding (ADR-17)
  - **Add**: WebSocket patterns, MessageAck, and AckAwareClient (ADR-16)
  - **Add**: Lite Registry discovery (SD-11, ADR-15)
  - **Add**: State Storage Interface and SQLite backend (SD-9)
  - **Add**: Health endpoint for agent liveness (SD-10)
  - **Add**: Best Practices: Agent Failover & Migration
  - **Update**: Security considerations with auth info + trust model limitations
  - **Update**: Project Structure with new modules (state/stores/, discovery/health.py, discovery/registry.py)

- [ ] 4.6.5 Review all docs
  - **Verify**: Examples work
  - **Verify**: Links valid
  - **Verify**: Security Model document accurate

- [ ] 4.6.6 Complete checkpoint CP-1
  - **File**: [checkpoints.md](../../checkpoints.md#cp-1-post-v110-release)
  - **Review**: Learnings and update velocity tracking

- [ ] 4.6.7 Create `examples/secure_agent.py`
  - **File**: `examples/secure_agent.py` (new)
  - **What**: "Copy-paste" ready example showing:
    - `ASAPServer` with `OAuth2Config`
    - `OAuth2Middleware` setup
    - Environment variables: `ASAP_AUTH_CUSTOM_CLAIM`, `ASAP_AUTH_ISSUER`, `ASAP_AUTH_AUDIENCE`
    - Client usage with `OAuth2ClientCredentials`
  - **Why**: Documentation alone is insufficient; users need working code to copy.

**Acceptance Criteria**:
- [ ] Release materials ready
- [ ] Documentation complete (including Security Model, Lite Registry, Best Practices)

---

## Task 4.7: Build and Publish

**Goal**: Publish v1.1.0

### Sub-tasks

- [ ] 4.7.1 Create release branch
  - **Branch**: `release/v1.1.0`

- [ ] 4.7.2 Run CI pipeline
  - **Verify**: All checks pass

- [ ] 4.7.3 Tag release
  - **Command**: `git tag v1.1.0`

- [ ] 4.7.4 Publish to PyPI
  - **Command**: `uv publish`

- [ ] 4.7.5 Create GitHub release
  - **Tag**: v1.1.0
  - **Notes**: From CHANGELOG

- [ ] 4.7.6 Update Docker images
  - **Push**: `ghcr.io/adriannoes/asap-protocol:v1.1.0`

**Acceptance Criteria**:
- [ ] v1.1.0 published to PyPI
- [ ] Docker image available

---

## Task 4.8: Mark Sprint S4 Complete

### Sub-tasks

- [ ] 4.8.1 Update roadmap progress
  - Mark all S4 tasks complete
  - Update progress to 100%

- [ ] 4.8.2 Verify release
  - **Confirm**: PyPI package installable
  - **Confirm**: Docker image runnable

**Acceptance Criteria**:
- [ ] v1.1.0 released
- [ ] Roadmap complete

---

## Sprint S4 Definition of Done

- [ ] Webhooks deliver with SSRF protection
- [ ] Retry logic functional
- [ ] slowapi migration complete (no deprecation warnings)
- [ ] Security Model document published (ADR-17)
- [ ] All tests pass
- [ ] v1.1.0 on PyPI
- [ ] Docker image published

**Total Sub-tasks**: ~38
