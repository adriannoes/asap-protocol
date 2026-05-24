# Release checklist: v2.4.0

**Roadmap:** [tasks-v2.4.0-roadmap.md](./tasks-v2.4.0-roadmap.md)  
**Merged PR:** [#178](https://github.com/adriannoes/asap-protocol/pull/178)  
**Pattern:** [v2.3.0 release checklist](../v2.3.0/release-checklist.md)

---

## 1.0 Pre-tag verification

| Step | Command | Status |
|------|---------|--------|
| Lint | `uv run ruff check .` | |
| Format | `uv run ruff format --check .` | |
| Types | `uv run mypy src/ scripts/ tests/` | |
| Python tests | `PYTHONPATH=src uv run pytest` | PR #178: 3439 passed |
| Web | `cd apps/web && pnpm lint && pnpm exec tsc --noEmit && pnpm test` | |
| TS client | `pnpm --filter @asap-protocol/client test` | |

---

## 2.0 Version & changelog gates

- [x] `pyproject.toml` → `version = "2.4.0"`
- [x] `src/asap/__init__.py` → `__version__ = "2.4.0"`
- [x] `packages/typescript/client/package.json` → `"version": "2.4.0"`
- [x] `CHANGELOG.md` → `## [2.4.0] - 2026-05-24`
- [x] `docs/migration.md` → [v2.3.x → v2.4.0](../../../docs/migration.md#upgrading-from-v23x-to-v240)
- [x] `README.md`, `docs/index.md`, `AGENTS.md`, `product/README.md`, landing (Hero, WhatsNewRibbon, metadata)
- [x] `.github/workflows/publish-typescript.yml` → tags `v2.4.*`

---

## 3.0 Tag, publish, verify

### 3.1 Git tag

```bash
git tag -a v2.4.0 -m "Release v2.4.0 — Edge-AI discovery and ShellClaw onboarding"
git push origin main
git push origin v2.4.0
```

Workflows: `release.yml` (PyPI + GitHub Release + Docker GHCR), `publish-typescript.yml` (npm).

### 3.2 PyPI

- [ ] `pip index versions asap-protocol` → includes **2.4.0**
- [ ] Clean venv: `pip install asap-protocol==2.4.0` → `import asap; asap.__version__ == "2.4.0"`

### 3.3 npm

Maintainer runbook: [docs/maintainers/npm-publishing.md](../../../docs/maintainers/npm-publishing.md).

- [ ] `npm view @asap-protocol/client version` → **2.4.0**
- [ ] `npm view @asap-protocol/mastra version` → **2.4.0**
- [ ] `npm view @asap-protocol/openai-agents version` → **2.4.0**

### 3.4 Docker (GHCR)

- [ ] `docker pull ghcr.io/adriannoes/asap-protocol:v2.4.0`

### 3.5 GitHub Release

- [ ] [v2.4.0](https://github.com/adriannoes/asap-protocol/releases/tag/v2.4.0) published with CHANGELOG body

### 3.6 Vercel production

- [ ] https://asap-protocol.com/ — Hero badge **v2.4.0**, WhatsNew ribbon updated
- [ ] https://asap-protocol.com/browse — hardware class / inference / I/O filters visible

---

## 4.0 ShellClaw coordination (maintainer, out of band)

- [ ] Paste handoff into `adriannoes/shellclaw` from [shellclaw-s1-structured-fields-handoff.md](./shellclaw-s1-structured-fields-handoff.md)
- [ ] Open IssueOps PR to add ShellClaw entry to `registry.json` when Wave 6.2 is ready
- [ ] Community feedback: [#176](https://github.com/adriannoes/asap-protocol/issues/176)

---

## Rollback

If publish fails after the tag is pushed: do **not** re-upload the same version to PyPI/npm. Ship **v2.4.1** with a fix or delete the remote tag only if no artifacts were published.
