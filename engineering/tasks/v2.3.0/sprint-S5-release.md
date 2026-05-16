# Sprint S5: Release v2.3.0

**PRD**: [v2.3 Adoption Multiplier](../../../product/prd/prd-v2.3-scale.md) — Release coordination  
**Branch**: `release/2.3.0` (optional) / merge to `main`  
**PR Scope**: Version bumps, CHANGELOG, migration guide, multi-package publish (PyPI + npm), Docker build, GitHub Release.  
**Depends on**: Sprints S1–S4 merged (code in `main`)

## Relevant Files

### Modified / verified in-repo

- `pyproject.toml` — Version **2.3.0**
- `src/asap/__init__.py` — `__version__ = "2.3.0"`
- `packages/typescript/client/package.json` — `"version": "2.3.0"`
- `apps/example-nextjs/package.json` — Uses `workspace:*` for `@asap-protocol/client` (monorepo); published consumers pin `^2.3.0`
- `apps/example-agent/pyproject.toml` — `asap-protocol>=2.3.0,<3` + editable path
- `CHANGELOG.md` — `## [2.3.0] - 2026-05-04`
- `docs/migration.md` — Section **v2.2.x → v2.3.0**
- `docs/index.md` — v2.3.0 headline + TypeScript SDK doc link
- `README.md` — v2.3.0 version history + adoption features
- `AGENTS.md` — Status line for v2.3.0 / publish note
- `apps/web/src/app/page.tsx` — Metadata for v2.3.0 highlights
- `apps/web/src/components/landing/*` — Hero, ribbon, feature cards
- `product/README.md` — Roadmap table row v2.3.0 shipped
- `product/prd/prd-v2.0-roadmap.md` — Changelog row for v2.3.0 successor note
- `product/prd/prd-v2.3-scale.md` — Status SHIPPED (with publish caveat)
- `engineering/tasks/v2.3.0/tasks-v2.3.0-adoption-multiplier.md` — Sprint index + DoD refresh
- **`engineering/tasks/v2.3.0/release-checklist.md`** — Maintainer pre-flight + manual steps
- **`engineering/tasks/v2.3.0/deferred-backlog.md`** — Post-release GitHub issue index (`deferred` label)

### New / optional

- `engineering/code-review/v2.3.0/` — Code review notes per PR (when used)

---

## Progress (2026-05-04)

| Gate | Result |
|------|--------|
| `uv sync --frozen --all-extras --dev --no-extra crewai --no-extra llamaindex` | OK |
| `PYTHONPATH=src uv run pytest` | **3213 passed**, 11 skipped (~2m18s) |
| `pnpm` (root) | `pnpm test` in `packages/typescript/client` — **Vitest green**, statements ~87.7% / lines ~90.9% coverage |
| `uv run pip-audit --ignore-vuln CVE-2026-4539 --ignore-vuln CVE-2026-4963 --ignore-vuln CVE-2026-2654` | **0 vulns** (3 CVEs ignored per SECURITY.md) |
| `uv run mypy src/ scripts/ tests/` | **Success** (396 files) |
| `cd apps/web && npm audit` | **2 moderate** (`postcss` via `next`) — documented in CHANGELOG + release-checklist |
| S1–S4 DoD (adoption index) | **Repo scope done**; S1 acceptance still notes **OpenAPI coverage below 90%**; S4 narrow-cov caveat documented |
| GitHub Actions **CI** (`ci.yml`) on `main` | **success** (2026-05-04) — [run 25347366275](https://github.com/adriannoes/asap-protocol/actions/runs/25347366275); **re-check** after the next push to `main` |
| Post-release follow-ups | Issues [#139](https://github.com/adriannoes/asap-protocol/issues/139)–[#142](https://github.com/adriannoes/asap-protocol/issues/142) (label `deferred`); index [deferred-backlog.md](./deferred-backlog.md) |
| Git tag **`v2.3.0`** | **Pushed** (2026-05-06) — triggers [Release (PyPI + Docker)](https://github.com/adriannoes/asap-protocol/actions/workflows/release.yml) + [Publish TypeScript SDK](https://github.com/adriannoes/asap-protocol/actions/workflows/publish-typescript.yml); **maintainer**: confirm green + artifacts (PyPI, npm, GHCR, GitHub Release) |

---

## Tasks

### 1.0 Pre-release Audit

- [x] 1.1 Verify sprint DoD (S1–S4 + adoption index)
  - **What**: [tasks-v2.3.0-adoption-multiplier.md](./tasks-v2.3.0-adoption-multiplier.md) updated; individual sprint files: S2–S3 acceptance complete; S1 has optional coverage debt; S4 has documented `--cov` caveat.
  - **Verify**: Manual review ✅

- [x] 1.2 Run full test matrix
  - **What**: `uv run pytest` (with extras for WebAuthn tests); `pnpm test` / `pnpm typecheck` / `pnpm lint` from root for TS workspace.
  - **Verify**: See Progress table ✅

- [x] 1.3 Compliance Harness v2 commands documented
  - **What**: Example-agent pytest + `asap compliance-check` + OpenAPI PetStore flow documented in [release-checklist.md](./release-checklist.md) §2.0.
  - **Verify**: Maintainers run against their deployed URLs before tag.

- [x] 1.4 Security audit
  - **What**: `pip-audit` (CI flags); `npm audit` in `apps/web`; SSRF/XSS/injection spot-check delegated to ongoing review.
  - **Verify**: pip-audit clean with documented ignores; npm moderate issues **documented** (not silently ignored).

### 2.0 Version Bump & CHANGELOG

- [x] 2.1 Bump versions
  - **Files**: Coordinated **2.3.0** in Python + TS client; example-agent constraint; `apps/web` private package version unchanged (not protocol version).
  - **Verify**: `grep` / `git diff` ✅

- [x] 2.2 CHANGELOG entry
  - **File**: `CHANGELOG.md` — `## [2.3.0] - 2026-05-04` with Added / Changed / Security.
  - **Verify**: Present ✅

- [x] 2.3 Migration guide
  - **File**: `docs/migration.md` — **v2.2.x → v2.3.0**
  - **Verify**: Linked from `docs/index.md` ✅

### 3.0 Publish (manual — do not execute unless explicitly requested)

- [x] 3.1 Tag and push — `git tag -a v2.3.0 -m "…" && git push origin v2.3.0` ✅ (2026-05-06)
- [x] 3.2 PyPI publish — **OK** — `asap-protocol==2.3.0` em [PyPI](https://pypi.org/project/asap-protocol/) (workflow [25432265870](https://github.com/adriannoes/asap-protocol/actions/runs/25432265870))
- [x] 3.3 npm publish — **OK** — [@asap-protocol/client@2.3.0](https://www.npmjs.com/package/@asap-protocol/client) no registry (bootstrap via maintainer após falha do workflow [25432265924](https://github.com/adriannoes/asap-protocol/actions/runs/25432265924)); OIDC/provenance de rotina: [S0 unblock npm](../private/v2.3.1/sprint-S0-unblock-npm.md)
- [x] 3.4 Docker build / GHCR — imagem publicada no job **Build and push Docker image** do mesmo workflow; verificar: `docker pull ghcr.io/adriannoes/asap-protocol:v2.3.0`
- [x] 3.5 GitHub Release — [v2.3.0](https://github.com/adriannoes/asap-protocol/releases/tag/v2.3.0) (artefatos `.whl` / `.tar.gz` anexados)

### 4.0 Post-release (product + web)

- [x] 4.1 Update product README + roadmap
  - **Files**: `product/README.md`, `product/prd/prd-v2.0-roadmap.md`
  - **Verify**: v2.3.0 row + changelog entry ✅

- [x] 4.2 Update PRD status
  - **File**: `product/prd/prd-v2.3-scale.md` — SHIPPED with maintainer publish caveat ✅

- [x] 4.3 Refresh `apps/web` with v2.3 highlights
  - **Files**: Hero, ribbon, feature cards, metadata ✅

- [x] 4.4 Open follow-up tracking issues — GitHub **#139–#142** + [deferred-backlog.md](./deferred-backlog.md); label **`deferred`** created on repo
- [ ] 4.5 Adoption metrics dashboard — **manual** (PRD metric; not in-repo); tracked by [#141](https://github.com/adriannoes/asap-protocol/issues/141)

---

## Acceptance Criteria (DoD)

- [x] Sprint DoD verified for **in-repo** scope (see adoption multiplier file)
- [ ] CI green on `main` HEAD at merge time — **maintainer**: confirm GitHub Actions (push só de docs pode não acionar `ci.yml` por *path filter*; após tag, workflow **Release** ficou verde)
- [x] Tag `v2.3.0` pushed ✅ (2026-05-06)
- [x] `asap-protocol==2.3.0` on PyPI ✅
- [x] `@asap-protocol/client@2.3.0` on npm — [package](https://www.npmjs.com/package/@asap-protocol/client) (ver 3.3)
- [x] Docker `:v2.3.0` and `:latest` on GHCR — **build/push OK** no workflow Release; confirmar digest localmente com `docker pull`
- [x] GitHub Release published — [releases/tag/v2.3.0](https://github.com/adriannoes/asap-protocol/releases/tag/v2.3.0)
- [x] PRD + roadmap + README + docs + web copy updated for **shipped** narrative (publish caveat where artifacts not yet live)
- [ ] Adoption metrics dashboard live — see [#141](https://github.com/adriannoes/asap-protocol/issues/141)
- [ ] No P0/P1 regressions in 7 days — **post-release observation**

---

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Publish race between PyPI and npm | Release workflow serializes: PyPI first, then npm |
| Breaking change accidentally introduced | Wire protocol unchanged; new routes opt-in; contract tests |
| Adoption metrics not actionable in week 1 | 90-day evaluation window per PRD |
| Deferred items lost | `deferred-backlog.md` + GitHub issues (`deferred` label) |
