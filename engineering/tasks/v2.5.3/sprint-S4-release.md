# Sprint S4: Release v2.5.3

**PRD**: Success metrics / DoD  
**Branch**: work on **`release/2.5.3`** → PR to **`main`**  
**Depends on**: S1–S3 acceptance criteria green

**Trigger:** Lab II MUST items complete on the release branch.  
**Enables:** v2.5.4 Distribution Loop.  
**Depends on:** [release-checklist.md](./release-checklist.md).

---

## Tasks

- [ ] **5.1 Version bumps**
  - [ ] `pyproject.toml` / `src/asap/__init__.py` → **2.5.3** (if Python artifacts changed; if docs-only release, still bump for train consistency unless maintainer chooses docs-only tag policy — default **bump**)
  - [ ] npm packages: leave at current line unless a TS package changed (unlikely)

- [ ] **5.2 Changelog & migration**
  - [ ] `CHANGELOG.md` → `## [2.5.3]`
  - [ ] `docs/migration.md` → upgrading from v2.5.2 (finalize S3 stub)
  - [ ] Update `AGENTS.md`, `product/README.md`, `docs/index.md` version blurb, checkpoints
  - [ ] Confirm [docs-review-checklist.md](./docs-review-checklist.md) §8 version-string sign-off

- [ ] **5.3 Pre-push CI**
  - [ ] `uv run ruff check .`
  - [ ] `uv run ruff format --check .`
  - [ ] `uv run mypy src/ scripts/ tests/`
  - [ ] `uv run pytest --tb=short --cov=asap --cov-report=xml --cov-fail-under=85`
  - [ ] pip-audit per `SECURITY.md` / `git-commits.mdc`
  - [ ] If `apps/web/` changed: lint, `tsc`, vitest, build
  - [ ] MkDocs build if docs/nav changed (`mkdocs build` / project-documented command)

- [ ] **5.4 Tag & publish**
  - [ ] PR `release/2.5.3` → `main`
  - [ ] Tag `v2.5.3` + GitHub Release
  - [ ] Confirm PyPI/Docker workflows as applicable

- [ ] **5.5 Handoff**
  - [ ] Mark this roadmap SHIPPED
  - [ ] Point next work at [prd-v2.5.4-distribution-loop.md](../../../product/prd/prd-v2.5.4-distribution-loop.md)
  - [ ] Remind: `@asap-protocol/mcp-auth` still on [v2.5.0 backlog](../v2.5.0/backlog-mcp-auth-typescript.md)

---

## Acceptance criteria

- [ ] [release-checklist.md](./release-checklist.md) fully checked
- [ ] All LAB2-001..006 DoD items closed or N/A
- [ ] Train handoff to v2.5.4 documented
