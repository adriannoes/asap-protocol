# Release checklist: v2.5.0 MCP Auth Bridge

**Roadmap:** [tasks-v2.5.0-roadmap.md](./tasks-v2.5.0-roadmap.md)  
**Merged PR:** [#236](https://github.com/adriannoes/asap-protocol/pull/236) (`release/2.5.0` → `main`)  
**Release commit:** `1c5027c` · **Tag:** [`v2.5.0`](https://github.com/adriannoes/asap-protocol/releases/tag/v2.5.0) (2026-06-24)  
**Compliance patch:** [`v2.5.0.1`](https://github.com/adriannoes/asap-protocol/releases/tag/v2.5.0.1) → PyPI `asap-compliance` **1.3.0** (2026-06-24)  
**Pattern:** [v2.4.0 release checklist](../v2.4.0/release-checklist.md)

---

## 1.0 Pre-tag verification

| Step | Command | Status |
|------|---------|--------|
| Lint | `uv run ruff check .` | ✅ S5 — [sprint-S5-release.md](./sprint-S5-release.md) §1.1 |
| Format | `uv run ruff format --check .` | ✅ S5 |
| Types | `uv run mypy src/ scripts/ tests/` | ✅ S5 |
| Python tests | `uv run pytest --cov=asap --cov-fail-under=85` | ✅ 3614 passed, 93.08% cov |
| MCP adapter cov | `uv run pytest tests/adapters/mcp/ --cov=asap.adapters.mcp --cov-fail-under=90` | ✅ 96.17% |
| pip-audit | per `SECURITY.md` | ✅ S5 |

---

## 2.0 Version & changelog gates

- [x] `pyproject.toml` → `version = "2.5.0"`
- [x] `src/asap/__init__.py` → `__version__ = "2.5.0"`
- [x] `CHANGELOG.md` → `## [2.5.0] - 2026-06-24` + `## [2.5.0.1]` (compliance)
- [x] `docs/migration.md` → [v2.4.1 → v2.5.0](../../../docs/migration.md#upgrading-from-v241-to-v250)
- [x] `README.md`, `docs/index.md`, `AGENTS.md`, `product/README.md`, homepage (`0bb406f`)
- [x] `asap-compliance` → **1.3.0** (`mcp-auth-bridge` profile; requires `asap-protocol>=2.5.0`)
- [x] npm `@asap-protocol/*` remain **2.4.1** (`@asap-protocol/mcp-auth` deferred — [backlog](./backlog-mcp-auth-typescript.md))

---

## 3.0 Tag, publish, verify

### 3.1 Git tags

- [x] Merge `release/2.5.0` → `main` — [PR #236](https://github.com/adriannoes/asap-protocol/pull/236) (2026-06-24)
- [x] `git tag -a v2.5.0` + `git push origin v2.5.0`
- [x] `git tag -a v2.5.0.1` + `git push origin v2.5.0.1` (compliance republish only)

| Workflow | Tag | Run | Result |
|----------|-----|-----|--------|
| Release (PyPI + Docker) | `v2.5.0` | [28122899827](https://github.com/adriannoes/asap-protocol/actions/runs/28122899827) | ✅ success |
| Release (PyPI + Docker) | `v2.5.0.1` | [28123172771](https://github.com/adriannoes/asap-protocol/actions/runs/28123172771) | ✅ success |

### 3.2 PyPI

- [x] `asap-protocol` **2.5.0** (verified 2026-06-24)
- [x] `asap-compliance` **1.3.0** (verified 2026-06-24)
- [x] `from asap.adapters.mcp import protect_server` — import OK on installed wheel

### 3.3 npm

- [x] `@asap-protocol/client` **2.4.1** (unchanged; expected)
- [ ] `@asap-protocol/mcp-auth` — deferred (npm patch TBD)

### 3.4 GitHub Releases

- [x] [v2.5.0](https://github.com/adriannoes/asap-protocol/releases/tag/v2.5.0) — MCP Auth Bridge
- [x] [v2.5.0.1](https://github.com/adriannoes/asap-protocol/releases/tag/v2.5.0.1) — compliance publish

### 3.5 Post-ship docs

- [x] `product/checkpoints.md` — v2.5.0 shipped roll-up
- [x] [sprint-S5-release.md](./sprint-S5-release.md) — acceptance criteria complete
- [x] [backlog-mcp-auth-typescript.md](./backlog-mcp-auth-typescript.md) — MCP-TS follow-up

---

## 4.0 Train handoff

| Next | Status |
|------|--------|
| **v2.5.1** Adapter Lab II | Planned — [prd-v2.5.1-adapter-lab-ii.md](../../../product/prd/prd-v2.5.1-adapter-lab-ii.md) |
| npm `@asap-protocol/mcp-auth` | Backlog — future patch tag TBD (not `v2.5.0.1`) |

**v2.5.0 train: CLOSED** (2026-06-24).
