# Release checklist: v2.3.0

**PRD**: [v2.3 Adoption Multiplier](../../../product/prd/prd-v2.3-scale.md)  
**Pattern**: Follows [v2.2.0 sprint-S6-release](../v2.2.0/sprint-S6-release.md) (pre-flight, tag, verify).  
**Note**: This file tracks **maintainer** steps after code/docs land on `main` (or `release/2.3.0`). Do **not** reuse a failed tag name — see rollback note in S6.

---

## 1.0 Pre-merge verification (local / CI)

Run from repository root (`/Users/adrianno/GitHub/asap-protocol` or CI clone):

| Step | Command | Notes |
|------|---------|--------|
| Sync (match security job) | `uv sync --frozen --all-extras --dev --no-extra crewai --no-extra llamaindex` | Per [SECURITY.md](../../../SECURITY.md) |
| Lint | `uv run ruff check .` | |
| Format | `uv run ruff format --check .` | |
| Types | `uv run mypy src/ scripts/ tests/` | |
| Python tests | `PYTHONPATH=src uv run pytest --cov=src --cov-report=xml` | **2026-05-04**: 3213 passed, 11 skipped (requires extras incl. `webauthn` for full collection) |
| pip-audit | `uv run pip-audit --ignore-vuln CVE-2026-4539 --ignore-vuln CVE-2026-3219` | Same ignores as CI |
| TS client | `pnpm install && pnpm test && pnpm typecheck && pnpm lint` | Root `package.json` delegates to `@asap-protocol/client` + `example-nextjs` lint |
| Web app (if touched) | `cd apps/web && pnpm test` | Vitest; Playwright E2E optional for release gate |

**Known gaps (document, do not hide):**

- **OpenAPI adapter coverage** ~87% on `src/asap/adapters/openapi/` (target ≥90% per sprint S1 — follow-up PR acceptable).
- **`apps/web` npm audit**: `postcss` moderate via `next@16.2.4` (GHSA-qx2v-qp2m-jg93); no non-breaking fix at audit time — track Next.js upgrade.

---

## 2.0 Compliance Harness v2 (example apps)

Example agents should score **1.0** before declaring release readiness.

### `apps/example-agent` (Python)

From repo root (editable `asap-protocol` via `[tool.uv.sources]`):

```bash
cd apps/example-agent
uv sync
PYTHONPATH=../../src uv run pytest tests/test_compliance.py -v
```

Against a **running** agent HTTP(S) base (adjust URL):

```bash
# From an environment where `asap` CLI is on PATH (e.g. root: uv run asap …)
uv run asap compliance-check --url http://127.0.0.1:8000 --exit-on-fail --asap-version 2.2
```

### `examples/openapi_petstore` (OpenAPI adapter demo)

```bash
uv sync --extra openapi
uv run --extra openapi python examples/openapi_petstore/main.py
# In another terminal, after server is listening:
uv run asap compliance-check --url http://127.0.0.1:<port> --exit-on-fail
```

### `apps/example-nextjs`

Reference Next.js consumer of `@asap-protocol/client` (workspace). Build:

```bash
pnpm --filter example-nextjs run build
```

Compliance is enforced on the **Python agent** side in CI; Next.js app follows SDK contract tests. Optionally run `asap compliance-check` against any deployed ASAP URL used in demos.

---

## 3.0 Version & changelog gates

- [ ] `pyproject.toml` → `version = "2.3.0"`
- [ ] `src/asap/__init__.py` → `__version__ = "2.3.0"`
- [ ] `packages/typescript/client/package.json` → `"version": "2.3.0"`
- [ ] `CHANGELOG.md` contains `## [2.3.0] - 2026-05-04` (release workflow may grep this — confirm against `.github/workflows/` validate job)
- [ ] `docs/migration.md` — section **v2.2.x → v2.3.0**
- [ ] `README.md`, `docs/index.md`, `AGENTS.md`, `product/README.md`, PRDs updated to shipped / current

---

## 4.0 Tag, publish, verify (manual / automated)

> Workflows: see `.github/workflows/` for `publish-python`, `publish-typescript`, `release`, and Docker to GHCR. Exact names may differ from v2.2.0 — **read the workflow files** before tagging.

### 4.1 Git tag

- [x] On correct branch (`main` or approved `release/2.3.0`), clean working tree ✅ (2026-05-06, `main`)
- [x] `git tag -a v2.3.0 -m "Release v2.3.0 — Adoption Multiplier"` ✅
- [x] `git push origin v2.3.0` ✅

### 4.2 PyPI

- [ ] Workflow publishes `asap-protocol==2.3.0` (and `asap-compliance` if its version bumped)
- [ ] Verify: `pip install asap-protocol==2.3.0` in a **clean** venv → `import asap; asap.__version__ == "2.3.0"`
- [ ] Confirm `[openapi]` extra installable: `pip install 'asap-protocol[openapi]==2.3.0'`

### 4.3 npm

- [ ] `@asap-protocol/client@2.3.0` published with provenance (per workflow)
- [ ] Verify: `npm install @asap-protocol/client@2.3.0` in empty project

### 4.4 Docker (GHCR)

- [ ] `docker pull ghcr.io/adriannoes/asap-protocol:v2.3.0` (digest recorded)
- [ ] `:latest` points to expected digest post-promotion

### 4.5 GitHub Release

- [ ] Draft/publish release for `v2.3.0` with: PRD link, sprint summary, install snippets (Python + npm), migration link, full CHANGELOG link

---

## 5.0 Post-release follow-ups (explicitly out of band)

Track outside this checklist or as GitHub issues (label `deferred` where applicable):

| Item | Owner | Notes |
|------|--------|--------|
| **Adoption metrics dashboard** (OpenAPI-derived agents, npm weekly downloads, auto-reg %, registry count) | Maintainer | PRD goal; Grafana/GitHub Pages — not automated in-repo |
| **Deferred Registry API Backend** | Product | Gated (500+ agents or IssueOps bottleneck) |
| **Follow-up GitHub issues** | Maintainer | [deferred-backlog.md](./deferred-backlog.md) — issues **#139–#142** (label `deferred`); broader themes (intent search, orchestration, DeepEval) as needed |
| **Vercel preview** for `apps/example-nextjs` | Maintainer | S2 sprint optional item |
| **OpenAPI module coverage ≥90%** | Engineering | Close S1 acceptance debt |
| **npm audit clean on `apps/web`** | Engineering | Likely requires Next.js minor/major bump |

---

## Rollback

If publish fails **after** the tag is pushed: do **not** re-upload the same version to PyPI. Delete remote tag only if no successful publish occurred; if artifacts leaked, ship **v2.3.1** with a fix. See v2.2.0 S6 rollback note.
