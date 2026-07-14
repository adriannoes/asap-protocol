# Sprint S4: Release v2.5.3

**PRD**: Success metrics / DoD  
**Branch**: work on **`release/2.5.3`** → PR to **`main`**  
**Depends on**: S1–S3 acceptance criteria green

**Trigger:** Lab II MUST items complete on the release branch.  
**Enables:** v2.5.4 Distribution Loop.  
**Depends on:** [release-checklist.md](./release-checklist.md).

---

## Tasks

- [x] **5.1 Version bumps**
  - [x] `pyproject.toml` / `src/asap/__init__.py` → **2.5.3** (if Python artifacts changed; if docs-only release, still bump for train consistency unless maintainer chooses docs-only tag policy — default **bump**)
  - [x] npm packages: leave at current line unless a TS package changed (unlikely)

- [x] **5.2 Changelog & migration**
  - [x] `CHANGELOG.md` → `## [2.5.3]`
  - [x] `docs/migration.md` → upgrading from v2.5.2 (finalize S3 stub)
  - [x] Update `AGENTS.md`, `product/README.md`, `docs/index.md` version blurb, checkpoints
  - [x] Confirm [docs-review-checklist.md](./docs-review-checklist.md) §8 version-string sign-off

- [x] **5.3 Pre-push CI** (Phase 5 green 2026-07-14)
  - [x] `uv run ruff check .`
  - [x] `uv run ruff format --check .`
  - [x] `uv run mypy src/ scripts/ tests/`
  - [x] `uv run pytest --tb=short --cov=asap --cov-report=xml --cov-fail-under=85`
  - [x] pip-audit per `SECURITY.md` / `git-commits.mdc`
  - [x] If `apps/web/` changed: lint, `tsc`, vitest, build
  - [x] MkDocs build if docs/nav changed (`mkdocs build` / project-documented command)

- [ ] **5.4 Tag & publish** *(requires explicit user confirmation)*
  - [ ] PR `release/2.5.3` → `main` — [#291](https://github.com/adriannoes/asap-protocol/pull/291) **OPEN** (merge not done)
  - [ ] Tag `v2.5.3` + GitHub Release
  - [ ] Confirm PyPI/Docker workflows as applicable

- [ ] **5.5 Handoff** *(after tag)*
  - [ ] Mark this roadmap SHIPPED
  - [ ] Point next work at [prd-v2.5.4-distribution-loop.md](../../../product/prd/prd-v2.5.4-distribution-loop.md)
  - [ ] Remind: `@asap-protocol/mcp-auth` still on [v2.5.0 backlog](../v2.5.0/backlog-mcp-auth-typescript.md)

---

## Acceptance criteria

- [x] [release-checklist.md](./release-checklist.md) §§1–3 content gates prepared (CI boxes filled after Phase 5)
- [x] All LAB2-001..006 DoD items closed or N/A
- [ ] Train handoff to v2.5.4 documented *(after tag)*
