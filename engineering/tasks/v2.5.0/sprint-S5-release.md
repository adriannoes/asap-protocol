# Sprint S5: Release 2.5.0 (v2.5.0)

**PRD**: [prd-v2.5-roadmap.md](../../../product/prd/prd-v2.5-roadmap.md) — release train
**Branch**: `feat/v2.5.0-s5-release` → merge into **`release/2.5.0`**, then **`release/2.5.0` → `main`**
**Depends on**: S0–S4 complete on `release/2.5.0`

**Trigger:** All sprint acceptance criteria met on integration branch.
**Enables:** v2.5.1 Adapter Lab II.
**Depends on:** Full CI green on `release/2.5.0`.

---

## Relevant Files

### Version & changelog
- `pyproject.toml` — version `2.5.0`
- `CHANGELOG.md` — v2.5.0 section
- `product/checkpoints.md` — post-release checkpoint
- `AGENTS.md` — knowledge map and version context

### Optional (SHOULD defer)
- `packages/typescript/` — `@asap-protocol/mcp-auth` npm package (v2.5.0.1 if not ready)
- `engineering/tasks/v2.5.0/typescript-mcp-auth-spike.md` — S4 ship/defer decision

### CI / publish
- `.github/workflows/release.yml` (tag-driven PyPI + Docker release)
- `SECURITY.md` — run pip-audit before tag

---

## Tasks

### 1.0 Pre-release verification

- [ ] 1.1 Full local CI per `AGENTS.md` / `.cursor/rules/git-commits.mdc`
  - **Commands**:
    - `uv run ruff check .`
    - `uv run ruff format --check .`
    - `uv run mypy src/ scripts/ tests/`
    - `uv run pytest --tb=short --cov=asap --cov-report=xml --cov-fail-under=85`
    - pip-audit per SECURITY.md
  - **Verify**: All pass on `release/2.5.0`

- [ ] 1.2 Coverage gate on `asap.adapters.mcp`
  - **Verify**: ≥90% per PRD non-functional reqs

### 2.0 Version bump & changelog

- [ ] 2.1 Bump to 2.5.0
  - **File**: `pyproject.toml`
  - **What**: `[project].version = "2.5.0"`
  - **Verify**: `uv run python -c "import asap; print(asap.__version__)"` if exposed

- [ ] 2.2 CHANGELOG entry
  - **File**: `CHANGELOG.md`
  - **What**: MCP Auth Bridge features, migration note (opt-in `protect_server`), breaking: none, and TypeScript middleware status (shipped or deferred to v2.5.0.1 with rationale)
  - **Verify**: Links to `docs/adapters/mcp-auth-bridge.md`

### 3.0 Merge to main & tag

- [ ] 3.1 Open PR `release/2.5.0` → `main`
  - **What**: Squash or merge commit per repo convention; include all sprint summaries in PR body
  - **Verify**: CI green on PR

- [ ] 3.2 Tag `v2.5.0`
  - **Command**: `git tag -a v2.5.0 -m "v2.5.0: MCP Auth Bridge"`
  - **Verify**: Publish workflow triggers (maintainer)

- [ ] 3.3 Update checkpoints
  - **File**: `product/checkpoints.md`
  - **What**: Mark v2.5.0 shipped; link PRD and release notes

### 4.0 Post-release (optional)

- [ ] 4.1 TypeScript `@asap-protocol/mcp-auth` follow-up issue
  - **What**: Track v2.5.0.1 if npm package is deferred after the S4 spike. Link the spike note and record MCP-TS-001..003 as deferred, not dropped.
  - **Verify**: Issue or task file in `engineering/tasks/v2.5.0/` backlog; CHANGELOG mentions the defer.

---

## Acceptance Criteria (S5)

- [ ] `release/2.5.0` merged to `main`
- [ ] Tag `v2.5.0` created
- [ ] CHANGELOG and checkpoints updated
- [ ] TypeScript middleware is shipped or explicitly deferred with linked backlog
- [ ] PyPI `asap-protocol` 2.5.0 published (maintainer workflow)
