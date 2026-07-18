# Sprint S5: Release v2.5.4

**PRD**: Definition of Done / D5  
**Branch**: work on **`release/2.5.4`** → PR to **`main`**  
**Depends on**: S1–S3 MUST green; S4 green **or** deferred on roadmap  
**Status**: Planned

**Trigger:** Distribution Loop MUST items complete on the release branch.  
**Enables:** v2.5.5 Formal Spec kickoff.  
**Depends on:** [release-checklist.md](./release-checklist.md).

**Release sequence:** **merge → tag → publish → handoff** — do not mark SHIPPED before publish.

---

## Tasks

- [ ] **6.1 Version bumps**
  - [ ] `pyproject.toml` / `src/asap/__init__.py` → **2.5.4**
  - [ ] npm `@asap-protocol/*`: leave at current line unless a TS package intentionally changed

- [ ] **6.2 Changelog & migration**
  - [ ] `CHANGELOG.md` → `## [2.5.4]`
  - [ ] `docs/migration.md` → upgrading from v2.5.3 → v2.5.4 (`#upgrading-from-v253-to-v254`)
  - [ ] Update `AGENTS.md`, `product/README.md`, `docs/index.md`, `product/checkpoints.md`
  - [ ] Confirm [docs-review-checklist.md](./docs-review-checklist.md) version-string sign-off

- [ ] **6.3 Pre-push CI**
  - [ ] `uv run ruff check .`
  - [ ] `uv run ruff format --check .`
  - [ ] `uv run mypy src/ scripts/ tests/`
  - [ ] `uv run pytest --tb=short --cov=asap --cov-report=xml --cov-fail-under=85`
  - [ ] pip-audit per `SECURITY.md` / `git-commits.mdc`
  - [ ] If `apps/web/` changed: lint, `tsc`, vitest, build
  - [ ] MkDocs build if docs/nav changed

- [ ] **6.4 Merge → tag → publish**
  - [ ] **Merge** PR `release/2.5.4` → `main`
  - [ ] **Tag** `v2.5.4` + push (triggers release workflow)
  - [ ] **Publish** — GitHub Release + PyPI `asap-protocol==2.5.4` (+ Docker/GHCR if applicable)
  - [ ] Post-publish checklist ([release-checklist §6](./release-checklist.md#60-post-publish-swap-pending--shipped))

- [ ] **6.5 Handoff**
  - [ ] Mark this roadmap SHIPPED
  - [ ] Complete [release-checklist §5.1](./release-checklist.md#51-handoff-inputs-for-v255-confirm-at-s5) (starter paths, guide, OOS, orphans)
  - [ ] Point next work at [prd-v2.5.5-formal-spec-interop.md](../../../product/prd/prd-v2.5.5-formal-spec-interop.md)
  - [ ] Remind: `@asap-protocol/mcp-auth` still on [v2.5.0 backlog](../v2.5.0/backlog-mcp-auth-typescript.md); Economy remains trigger-gated ([prd-v3.0-economy.md](../../../product/prd/prd-v3.0-economy.md))

---

## Acceptance criteria

- [ ] [release-checklist.md](./release-checklist.md) §§1–6 complete
- [ ] All DIST MUST items closed; DIST-004 closed or deferred
- [ ] Train handoff to v2.5.5 documented
