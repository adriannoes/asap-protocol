# Sprint S5: Release 2.5.0 (v2.5.0)

**PRD**: [prd-v2.5-roadmap.md](../../../product/prd/prd-v2.5-roadmap.md) — release train
**Branch**: `feat/v2.5.0-s5-release` → merge into **`release/2.5.0`**, then **`release/2.5.0` → `main`**
**Depends on**: S0–S4 complete on `release/2.5.0`

> **Status:** **SHIPPED** — `main` @ tag [`v2.5.0`](https://github.com/adriannoes/asap-protocol/releases/tag/v2.5.0) (2026-06-24). Merge [#236](https://github.com/adriannoes/asap-protocol/pull/236); prep [#235](https://github.com/adriannoes/asap-protocol/pull/235).

**Trigger:** All sprint acceptance criteria met on integration branch.
**Enables:** v2.5.1 Adapter Lab II.
**Depends on:** Full CI green on `release/2.5.0`.

---

## Relevant Files

### Sprint tracking (docs sync — pre-S5)
- `engineering/tasks/v2.5.0/tasks-v2.5.0-roadmap.md` — sprint index; S5 active
- `engineering/tasks/v2.5.0/sprint-S5-release.md` — this file
- `product/prd/prd-v2.5.0-mcp-auth-bridge.md` — DoD + deliverable status
- `product/prd/prd-v2.5-roadmap.md` — train schedule status

### Version & changelog
- `pyproject.toml` — version `2.5.0` ✅
- `src/asap/__init__.py` — `__version__` (must match metadata)
- `uv.lock` — local package version pin
- `CHANGELOG.md` — v2.5.0 section ✅
- `product/checkpoints.md` — post-release checkpoint
- `AGENTS.md` — knowledge map and version context ✅

### Optional (SHOULD defer)
- `packages/typescript/` — `@asap-protocol/mcp-auth` npm package (v2.5.0.1 if not ready)
- `engineering/tasks/v2.5.0/typescript-mcp-auth-spike.md` — S4 ship/defer decision

### CI / publish
- `.github/workflows/release.yml` (tag-driven PyPI + Docker release)
- `SECURITY.md` — run pip-audit before tag

---

## Tasks

### 1.0 Pre-release verification ✅

- [x] 1.1 Full local CI per `AGENTS.md` / `.cursor/rules/git-commits.mdc`
  - **Commands**:
    - `uv run ruff check .`
    - `uv run ruff format --check .`
    - `uv run mypy src/ scripts/ tests/`
    - `uv run pytest --tb=short --cov=asap --cov-report=xml --cov-fail-under=85`
    - pip-audit per SECURITY.md
  - **Verify**: All pass on `release/2.5.0`
  - **Result (2026-06-24, `feat/v2.5.0-s5-release`)**: ruff ✅ · format ✅ · mypy (437 files) ✅ · pytest **3614 passed**, coverage **93.08%** ✅ · pip-audit ✅

- [x] 1.2 Coverage gate on `asap.adapters.mcp`
  - **Verify**: ≥90% per PRD non-functional reqs
  - **Result (2026-06-24)**: `uv run pytest tests/adapters/mcp/ --cov=asap.adapters.mcp --cov-fail-under=90` → **96.17%** (163 stmts; lowest file `jwt_extractor.py` 90.91%)

### 2.0 Version bump & changelog ✅

- [x] 2.1 Bump to 2.5.0
  - **File**: `pyproject.toml`
  - **What**: `[project].version = "2.5.0"`
  - **Verify**: `uv run python -c "import asap; print(asap.__version__)"` if exposed
  - **Result (2026-06-24)**: `pyproject.toml` + `src/asap/__init__.py` → `2.5.0`; `uv.lock` refreshed; `asap.__version__` prints `2.5.0`; `tests/test_version.py` ✅

- [x] 2.2 CHANGELOG entry
  - **File**: `CHANGELOG.md`
  - **What**: MCP Auth Bridge features, migration note (opt-in `protect_server`), breaking: none, and TypeScript middleware status (shipped or deferred to v2.5.0.1 with rationale)
  - **Verify**: Links to `docs/adapters/mcp-auth-bridge.md`
  - **Result (2026-06-24)**: `## [2.5.0] - 2026-06-24` — Added (bridge, compliance, tests), Deferred (MAP-004, initialize), TypeScript defer v2.5.0.1, Migration (no breaking); links to adapter guide + spike

### 3.0 Merge to main & tag ✅

- [x] 3.1 Open PR `release/2.5.0` → `main`
  - **What**: Squash or merge commit per repo convention; include all sprint summaries in PR body
  - **Verify**: CI green on PR
  - **Status**: Merged [PR #236](https://github.com/adriannoes/asap-protocol/pull/236) (2026-06-24)

- [x] 3.2 Tag `v2.5.0`
  - **Command**: `git tag -a v2.5.0 -m "v2.5.0: MCP Auth Bridge"`
  - **Verify**: Publish workflow triggers (maintainer)
  - **Result**: Tag pushed 2026-06-24; `release.yml` run [28122899827](https://github.com/adriannoes/asap-protocol/actions/runs/28122899827)

- [x] 3.3 Update checkpoints
  - **File**: `product/checkpoints.md`
  - **What**: Mark v2.5.0 shipped; link PRD and release notes

### 4.0 Post-release (optional)

- [x] 4.1 TypeScript `@asap-protocol/mcp-auth` follow-up issue
  - **What**: Track v2.5.0.1 if npm package is deferred after the S4 spike. Link the spike note and record MCP-TS-001..003 as deferred, not dropped.
  - **Verify**: Issue or task file in `engineering/tasks/v2.5.0/` backlog; CHANGELOG mentions the defer.
  - **Result**: [backlog-mcp-auth-typescript.md](./backlog-mcp-auth-typescript.md)

---

## Acceptance Criteria (S5)

- [x] `release/2.5.0` merged to `main`
- [x] Tag `v2.5.0` created
- [x] CHANGELOG and checkpoints updated
- [x] TypeScript middleware is shipped or explicitly deferred with linked backlog
- [ ] PyPI `asap-protocol` 2.5.0 published (maintainer workflow — verify after `release.yml` green)
