# Release checklist: v2.4.0

**Roadmap:** [tasks-v2.4.0-roadmap.md](./tasks-v2.4.0-roadmap.md)  
**Merged PR:** [#178](https://github.com/adriannoes/asap-protocol/pull/178)  
**Release commit:** `d7958d8` (docs/landing/workflow) · **Tag:** `v2.4.0` (2026-05-24)  
**Pattern:** [v2.3.0 release checklist](../v2.3.0/release-checklist.md)

---

## 1.0 Pre-tag verification

| Step | Command | Status |
|------|---------|--------|
| Lint | `uv run ruff check .` | ✅ PR #178 / pre-tag |
| Format | `uv run ruff format --check .` | ✅ PR #178 / pre-tag |
| Types | `uv run mypy src/ scripts/ tests/` | ✅ PR #178 / pre-tag |
| Python tests | `uv run pytest` | ✅ 3439 passed (PR #178) |
| Web | `cd apps/web && pnpm lint && pnpm exec tsc --noEmit && pnpm test` | ✅ PR #178 / pre-tag |
| TS client | `pnpm --filter @asap-protocol/client test` | ✅ 105 tests (PR #178) |

---

## 2.0 Version & changelog gates

- [x] `pyproject.toml` → `version = "2.4.0"`
- [x] `src/asap/__init__.py` → `__version__ = "2.4.0"`
- [x] `packages/typescript/client/package.json` → `"version": "2.4.0"`
- [x] `packages/typescript/mastra/package.json` → `"version": "2.4.0"` (published with tag)
- [x] `packages/typescript/openai-agents/package.json` → `"version": "2.4.0"` (published with tag)
- [x] `CHANGELOG.md` → `## [2.4.0] - 2026-05-24`; `[Unreleased]` deduped
- [x] `docs/migration.md` → [v2.3.x → v2.4.0](../../../docs/migration.md#upgrading-from-v23x-to-v240)
- [x] `README.md`, `docs/index.md`, `AGENTS.md`, `product/README.md`, landing (Hero, WhatsNewRibbon, metadata)
- [x] `.github/workflows/publish-typescript.yml` → tags `v2.4.*`

---

## 3.0 Tag, publish, verify

### 3.1 Git tag

- [x] `git push origin main` (`d7958d8`, 2026-05-24)
- [x] `git tag -a v2.4.0` + `git push origin v2.4.0` (2026-05-24)

Workflows: `release.yml` (PyPI + GitHub Release + Docker GHCR), `publish-typescript.yml` (npm).

| Workflow | Run | Result |
|----------|-----|--------|
| Release (PyPI + Docker) | [26373376184](https://github.com/adriannoes/asap-protocol/actions/runs/26373376184) | ✅ success |
| Publish TypeScript SDK | [26373376159](https://github.com/adriannoes/asap-protocol/actions/runs/26373376159) | ✅ success |

### 3.2 PyPI

- [x] `pip index versions asap-protocol` / PyPI API → includes **2.4.0** (verified 2026-05-24)
- [x] `pip install asap-protocol==2.4.0` → `asap.__version__ == "2.4.0"` (PyPI publish confirmed via API + release workflow)

### 3.3 npm

Maintainer runbook: [docs/maintainers/npm-publishing.md](../../../docs/maintainers/npm-publishing.md).

- [x] `npm view @asap-protocol/client version` → **2.4.0** (2026-05-24)
- [x] `npm view @asap-protocol/mastra version` → **2.4.0** (2026-05-24)
- [x] `npm view @asap-protocol/openai-agents version` → **2.4.0** (2026-05-24)

### 3.4 Docker (GHCR)

- [x] Image built and pushed by release workflow ([26373376184](https://github.com/adriannoes/asap-protocol/actions/runs/26373376184) docker job)
- [ ] Optional local: `docker pull ghcr.io/adriannoes/asap-protocol:v2.4.0` (digest recorded)

### 3.5 GitHub Release

- [x] [v2.4.0](https://github.com/adriannoes/asap-protocol/releases/tag/v2.4.0) published with CHANGELOG body (2026-05-24)

### 3.6 Vercel production

- [x] https://asap-protocol.com/ — Hero badge **v2.4.0**, WhatsNew ribbon updated (verified 2026-05-24)
- [x] https://asap-protocol.com/browse — **Edge & Hardware** filter UI deployed (conditional: section renders when registry entries include `hardware_class` / `inference_modes` / `hardware_io`)
- [ ] Browse filters **visible in prod** today — **blocked** until ShellClaw (or another agent) is listed with structured fields (0/120 agents in live `registry.json` have hardware metadata; see §4.0)

---

## 4.0 ShellClaw coordination (maintainer, out of band)

Upstream **v2.4.0** shipped — handoff doc ready; ShellClaw repo / IssueOps are separate tracks.

- [ ] Paste handoff into `adriannoes/shellclaw` from [shellclaw-s1-structured-fields-handoff.md](./shellclaw-s1-structured-fields-handoff.md) (maintainer)
- [ ] Open IssueOps PR to add ShellClaw entry to `registry.json` when Wave 6.2 is ready (maintainer / ShellClaw)
- [ ] Community feedback: [#176](https://github.com/adriannoes/asap-protocol/issues/176) (ongoing — enum / field extensions)

---

## Rollback

If publish fails after the tag is pushed: do **not** re-upload the same version to PyPI/npm. Ship **v2.4.1** with a fix or delete the remote tag only if no artifacts were published.
