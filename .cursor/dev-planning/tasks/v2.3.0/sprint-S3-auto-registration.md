# Sprint S3: Auto-Registration

**PRD**: [v2.3 §4.3](../../../product-specs/prd/prd-v2.3-scale.md) — AUTO-001..007 (P0)
**Branch**: `feat/auto-registration`
**PR Scope**: Self-service registration endpoint backed by the existing Lite Registry (`registry.json`) via a bot-authored PR flow. Compliance-harness gating + rate limiting + anti-spam. **No PostgreSQL backend.**
**Depends on**: v2.2 (Compliance Harness v2, Capability model, OAuth2 token validation)

## Relevant Files

### New Files
- `src/asap/registry/auto_registration.py` — Endpoint handler `POST /registry/agents`
- `src/asap/registry/bot_pr.py` — Bot-driven PR opener (uses GitHub API)
- `src/asap/registry/anti_spam.py` — Trust-level gating (`self-signed` default; `verified` requires manual review)
- `tests/registry/test_auto_registration.py` — Endpoint tests
- `tests/registry/test_bot_pr.py` — Bot PR flow tests with mocked GitHub
- `tests/registry/integration/test_e2e_registration.py` — End-to-end registration → harness → PR → merge → mirror published
- `.github/workflows/auto-merge-registry.yml` — Auto-merge bot PR if all checks green AND trust_level == self-signed
- `apps/registry-bot/` — Lightweight service running the registration endpoint (deployable separately)

### Modified Files
- `src/asap/transport/server.py` — Register `/registry/agents` route group (or wire from `apps/registry-bot`)
- `src/asap/transport/rate_limit.py` — Add `RegistrationRateLimit` (5 attempts per token per hour)
- `docs/registry/auto-registration.md` — Usage guide
- `registry.json` — Bot-edited (existing file)

## Tasks

### 1.0 Endpoint & Compliance Gating (TDD-first)

- [ ] 1.1 Write failing E2E test (TDD)
  - **File**: `tests/registry/integration/test_e2e_registration.py`
  - **What**: Submit a manifest URL via `POST /registry/agents` with a valid OAuth2 token. Mock Compliance Harness v2 → score 1.0. Assert: bot PR opened against `registry.json`, auto-merged, mirror published, registration receipt returned with `agent_id` + `urn` + harness score.
  - **Verify**: Red

- [ ] 1.2 Endpoint scaffolding (AUTO-001)
  - **File**: `src/asap/registry/auto_registration.py`
  - **What**: `POST /registry/agents` accepts `{manifest_url}`. Validate OAuth2 token. Fetch manifest. Run Compliance Harness v2 against the manifest's discovery URL.
  - **Verify**: Unit tests for token validation, manifest fetch, harness invocation

- [ ] 1.3 Compliance gating (AUTO-002)
  - **What**: Reject with 422 if Compliance Harness v2 score < 1.0. Include score and failed checks in error response.
  - **Verify**: Test with non-compliant fixture agent

### 2.0 Rate Limiting & Anti-Spam (AUTO-003, AUTO-005)

- [ ] 2.1 Per-token rate limit (AUTO-003)
  - **File**: `src/asap/transport/rate_limit.py`
  - **What**: `RegistrationRateLimit(max_attempts=5, window=timedelta(hours=1))`. Apply via decorator on the endpoint.
  - **Verify**: 6th attempt within an hour returns 429

- [ ] 2.2 Trust-level anti-spam (AUTO-005)
  - **File**: `src/asap/registry/anti_spam.py`
  - **What**: Newly registered agents start at `trust_level: "self-signed"`. Promotion to `verified` requires a manual review PR (existing IssueOps remains for that path — AUTO-004).
  - **Verify**: Auto-registered fixture lands as `self-signed` in the bot PR

### 3.0 Bot-driven PR Flow (AUTO-006)

- [ ] 3.1 Bot PR opener
  - **File**: `src/asap/registry/bot_pr.py`
  - **What**: Use a `GitHub App` (`asap-bot`) installation token to: clone, branch (`auto-reg/<urn>`), append entry to `registry.json` (sorted, deduped), commit with conventional message `feat(registry): auto-register <name> (<urn>)`, push, open PR with autocomplete details.
  - **Verify**: Test with mocked Octokit; PR title/body matches template

- [ ] 3.2 Auto-merge workflow
  - **File**: `.github/workflows/auto-merge-registry.yml`
  - **What**: Triggered on PRs labeled `auto-registration`. Verify: trust_level == self-signed, registry.json schema validation passes, no other files touched. If all green: enable auto-merge (squash). If trust_level == verified or extra files touched: leave for human review.
  - **Verify**: Dry-run on test PR

- [ ] 3.3 Mirror publication
  - **What**: Existing GitHub Pages workflow already publishes `registry.json` mirror. Verify it picks up the auto-merged change within 5 min.
  - **Verify**: E2E test waits for mirror update via polling

### 4.0 Receipt & Idempotency (AUTO-007)

- [ ] 4.1 Registration receipt
  - **What**: Response `{agent_id, urn, harness_score, pr_url, status: "queued"|"merged"|"verified-pending"}`. `agent_id` deterministic for idempotency (re-submitting same manifest URL returns same `agent_id`).
  - **Verify**: Idempotency test: same manifest twice → same response

### 5.0 Documentation

- [ ] 5.1 Auto-registration guide
  - **File**: `docs/registry/auto-registration.md`
  - **What**: Flow diagram, OAuth2 token acquisition, payload format, response schema, common rejections (harness failures, rate limit, manifest unreachable), upgrading to `verified`
  - **Verify**: Cross-link from main registry docs

- [ ] 5.2 Registry-bot deployment guide
  - **File**: `apps/registry-bot/README.md`
  - **What**: How to deploy the bot service (Vercel Function or Railway), required env vars (`GITHUB_APP_ID`, `GITHUB_APP_PRIVATE_KEY`, `ASAP_OAUTH_PUBLIC_KEY`)
  - **Verify**: Deployable to Vercel preview successfully

## Acceptance Criteria

- [ ] All tests pass (TDD red → green)
- [ ] Coverage ≥90% on new modules
- [ ] `uv run mypy` and `ruff check` clean
- [ ] E2E test: spec → registered → mirror published in <5 min
- [ ] Idempotency verified
- [ ] Auto-merge workflow tested with two fixture PRs (auto-merge eligible + manual review required)
- [ ] Rate limit tested (6th attempt → 429)

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Spam: attacker generates many fake agents | Rate limit + trust_level + Compliance Harness v2 + manifest URL must serve valid manifest |
| Bot PR conflicts when many agents register concurrently | Serialize bot PRs via single-flight queue; rebase on conflict |
| GitHub App token rotation | Document key-rotation runbook; CI alerts when approaching expiration |
| Auto-merge accidentally merges malicious entry | Workflow checks: only `registry.json` touched, schema valid, no insertion of `verified` trust level, no override of existing entries |
| Manifest URL fetch SSRF | Reuse v2.1.1 SSRF protection (DNS rebinding, blocklist private/loopback) |
