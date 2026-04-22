# Sprint S5: Release v2.3.0

**PRD**: [v2.3 Adoption Multiplier](../../../product-specs/prd/prd-v2.3-scale.md) — Release coordination
**Branch**: `release/2.3.0`
**PR Scope**: Version bumps, CHANGELOG, migration guide, multi-package publish (PyPI + npm), Docker build, GitHub Release.
**Depends on**: Sprints S1, S2, S3, S4 all merged on `main`

## Relevant Files

### Modified Files
- `pyproject.toml` — Bump version to `2.3.0`
- `src/asap/__init__.py` — `__version__ = "2.3.0"`
- `packages/typescript/client/package.json` — `"version": "2.3.0"`
- `apps/example-nextjs/package.json` — Bump dep to `^2.3.0`
- `apps/example-agent/pyproject.toml` — Bump dep to `^2.3.0`
- `CHANGELOG.md` — `[Unreleased]` → `[2.3.0]` with grouped Added/Changed/Security
- `docs/migration.md` — Section "v2.2.x → v2.3.0"
- `docs/index.md` — Update headline + feature highlights
- `README.md` — Bump version badge, mention OpenAPI Adapter + TS SDK
- `apps/web` — Update copy on landing page (hero + feature cards)

### New Files
- `.cursor/dev-planning/code-review/v2.3.0/` — Code review notes per PR
- `.cursor/dev-planning/tasks/v2.3.0/release-checklist.md` — Manual checklist (exists pattern from v2.2.0)

## Tasks

### 1.0 Pre-release Audit

- [ ] 1.1 Verify all sprint DoD checked
  - **What**: Re-read `tasks-v2.3.0-adoption-multiplier.md` and confirm S1–S4 DoD all `[x]`
  - **Verify**: Manual review

- [ ] 1.2 Run full test matrix
  - **What**: `uv run pytest` (Python), `pnpm -r test` (TypeScript). Both green with ≥90% coverage.
  - **Verify**: CI green on `main` HEAD

- [ ] 1.3 Run Compliance Harness v2 against example agents
  - **What**: `apps/example-agent` and `apps/example-nextjs` (via `apps/example-openapi-petstore`) both score 1.0
  - **Verify**: Output of `asap compliance-check --url ...` (from v2.2.1)

- [ ] 1.4 Security audit
  - **What**: `pip-audit`, `npm audit`, manual review of new modules for SSRF/XSS/injection
  - **Verify**: All clean or documented overrides

### 2.0 Version Bump & CHANGELOG

- [ ] 2.1 Bump versions
  - **Files**: `pyproject.toml`, `src/asap/__init__.py`, `packages/typescript/client/package.json`, app `package.json`/`pyproject.toml`
  - **Verify**: `git diff` shows all coordinated bumps

- [ ] 2.2 CHANGELOG entry
  - **File**: `CHANGELOG.md`
  - **What**: Move `[Unreleased]` content to `## [2.3.0] - <date>`. Group:
    - **Added**: OpenAPI Adapter (Python), TypeScript Client SDK, Auto-Registration, Capability Escalation, WWW-Authenticate ASAP Challenge
    - **Changed**: Wire protocol unchanged; new optional packages
    - **Deprecated**: None
    - **Security**: Per dependency sweep
  - **Verify**: Markdown lint + cross-links to PRs

- [ ] 2.3 Migration guide
  - **File**: `docs/migration.md`
  - **What**: Section "v2.2.x → v2.3.0": new optional adapters, TS SDK installation, Auto-Registration deployment, escalation behavior changes, ASAP challenge opt-in
  - **Verify**: Reviewed against PRD for completeness

### 3.0 Publish

- [ ] 3.1 Tag and push
  - **What**: `git tag v2.3.0 && git push origin v2.3.0`
  - **Verify**: Tag visible on GitHub

- [ ] 3.2 PyPI publish
  - **What**: Triggered by tag via `.github/workflows/publish-python.yml`. Publishes `asap-protocol==2.3.0` and `asap-compliance` if version changed.
  - **Verify**: `pip install asap-protocol==2.3.0` works in clean venv

- [ ] 3.3 npm publish
  - **What**: Triggered by tag via `.github/workflows/publish-typescript.yml`. Publishes `@asap-protocol/client@2.3.0` with provenance.
  - **Verify**: `npm install @asap-protocol/client@2.3.0` works in clean directory

- [ ] 3.4 Docker build
  - **What**: GitHub Actions builds and pushes `ghcr.io/adriannoes/asap-protocol:v2.3.0` and `:latest`
  - **Verify**: `docker pull ghcr.io/adriannoes/asap-protocol:v2.3.0`

- [ ] 3.5 GitHub Release
  - **What**: Draft GitHub Release for tag `v2.3.0` with: PRD reference, sprint summary, install commands (Python + TS), migration link, full CHANGELOG link
  - **Verify**: Release published

### 4.0 Post-release

- [ ] 4.1 Update product-specs README + roadmap
  - **Files**: `.cursor/product-specs/README.md`, `.cursor/product-specs/strategy/roadmap-to-marketplace.md`
  - **What**: Status `🚧 DRAFT` → `✅ Released (<date>)` for v2.3
  - **Verify**: Diff committed

- [ ] 4.2 Update PRD status
  - **File**: `.cursor/product-specs/prd/prd-v2.3-scale.md`
  - **What**: `Status: DRAFT` → `Status: ✅ SHIPPED (<date>, tag v2.3.0)` + delivery summary + change log entry
  - **Verify**: Reviewed against PRs merged

- [ ] 4.3 Refresh apps/web with v2.3 highlights
  - **Files**: hero, feature cards, "what's new" ribbon
  - **Verify**: Vercel preview review

- [ ] 4.4 Open follow-up tracking issues
  - **What**: Create issues for: (a) deferred Registry API Backend (gated by 500-agent trigger), (b) Intent-Based Search, (c) Orchestration Primitives, (d) DeepEval. Label `deferred` and link to deferred-backlog.md.
  - **Verify**: Issues created and visible on project board

- [ ] 4.5 Adoption metrics dashboard
  - **What**: Dashboard tracking: agents onboarded via OpenAPI adapter, weekly npm downloads, Auto-Reg adoption %, total agents in registry. Use Grafana (existing v1.0 P12) or simple GitHub Pages chart.
  - **Verify**: Dashboard live and linked from README

## Acceptance Criteria (DoD)

- [ ] All sprint DoD verified
- [ ] CI green on `main`
- [ ] Tag `v2.3.0` pushed
- [ ] `asap-protocol==2.3.0` on PyPI
- [ ] `@asap-protocol/client@2.3.0` on npm
- [ ] Docker `:v2.3.0` and `:latest` on GHCR
- [ ] GitHub Release published
- [ ] PRD + roadmap + README updated to "shipped"
- [ ] Adoption metrics dashboard live
- [ ] No P0/P1 regressions reported in 7 days post-release

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Publish race between PyPI and npm | Release workflow serializes: PyPI first, then npm |
| Breaking change accidentally introduced | Wire protocol unchanged; capability/identity APIs additive only; contract tests guard backward compat |
| Adoption metrics not actionable in week 1 | Set 90-day window for trigger evaluation; weekly review |
| Deferred items lost in backlog | All deferred items have explicit return-trigger documented in `deferred-backlog.md` |
