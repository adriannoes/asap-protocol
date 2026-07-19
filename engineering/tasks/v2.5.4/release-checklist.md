# Release checklist: v2.5.4 Distribution Loop

**Roadmap:** [tasks-v2.5.4-roadmap.md](./tasks-v2.5.4-roadmap.md)  
**PRD:** [prd-v2.5.4-distribution-loop.md](../../../product/prd/prd-v2.5.4-distribution-loop.md)  
**Pattern:** [v2.5.3 release checklist](../v2.5.3/release-checklist.md)

---

## 1.0 Pre-tag verification

| Step | Command | Status |
|------|---------|--------|
| Lint | `uv run ruff check .` | ☑ PASS (2026-07-18 S5 prep) |
| Format | `uv run ruff format --check .` | ☑ PASS |
| Types | `uv run mypy src/ scripts/ tests/` | ☑ PASS |
| Python tests | `uv run pytest --tb=short --cov=asap --cov-report=xml --cov-fail-under=85` | ☑ PASS (94.46%) |
| pip-audit | per `SECURITY.md` | ☑ PASS (`mcp>=1.28.1`) |
| npm audit (web) | `cd apps/web && npm audit --omit=dev --audit-level=moderate` and `npm audit --audit-level=high` (blocking in CI `quality-web`; see `SECURITY.md`) | ☑ PASS (0 vulns) |
| Web (if touched) | `npm run lint` / format check / `npx tsc --noEmit` / `npx vitest run` / `npm run build` in `apps/web/` | ☑ PASS |
| MkDocs (if docs/nav touched) | `uv run mkdocs build` | ☑ PASS (pre-existing warnings) |
| Starter smokes (DIST-003) | See §1.1 | ☐ (optional maintainer follow-up; not blocking S5 prep) |

### 1.1 Starter smoke commands (DIST-003)

Run from the repository root (each ≤60s headless):

```bash
# OpenAPI provider
uv sync --extra openapi
uv run python examples/starters/openapi-provider/run.py

# MCP Auth Bridge
uv sync
uv run python examples/starters/mcp-auth-bridge/run.py

# TypeScript consumer (fresh clone needs workspace install first)
pnpm install
pnpm --filter @asap-protocol/client run build
pnpm --filter @asap-protocol/starter-typescript-consumer run smoke
```

Optional CI: `.github/workflows/starters-smoke.yml` (path-filtered on `examples/starters/**`).

---

## 2.0 Product DoD

> **S5 owns this section.** Fill when MUST surface is merge-ready.

- [x] DIST-001 — homepage agent-first (D1)
- [x] DIST-002 — CTAs → docs/starters/examples
- [x] DIST-003 — three thin starters at locked paths
- [x] DIST-004 — telemetry ops green **or** deferred on roadmap (satisfied; secrets gap documented)
- [x] DIST-005 — `docs/guides/build-for-agents.md` shipped
- [x] DIST-006 — public copy gate passed
- [x] [docs-review-checklist.md](./docs-review-checklist.md) §§1–8 complete for shipped scope (post-publish swap 2026-07-18)

---

## 3.0 Version & changelog gates

- [x] `pyproject.toml` → `version = "2.5.4"`
- [x] `src/asap/__init__.py` → `__version__ = "2.5.4"`
- [x] `CHANGELOG.md` → `## [2.5.4]`
- [x] `docs/migration.md` → v2.5.3 → v2.5.4
- [x] `README.md`, `docs/index.md`, `AGENTS.md`, `product/README.md`, `product/checkpoints.md`
- [x] npm `@asap-protocol/*` unchanged unless a package was intentionally bumped (**left at 2.4.1**)

---

## 4.0 Merge → tag → publish

**Order:** merge PR → tag `v2.5.4` → confirm publish workflows → then §6 handoff copy.

- [x] **Merge** `release/2.5.4` → `main` — PR [#294](https://github.com/asap-protocol/asap-protocol/pull/294)
- [x] **Tag** `git tag -a v2.5.4` + push — triggers `.github/workflows/release.yml` ([run](https://github.com/asap-protocol/asap-protocol/actions/runs/29650003126))
- [x] **Publish** — [GitHub Release `v2.5.4`](https://github.com/asap-protocol/asap-protocol/releases/tag/v2.5.4); PyPI `asap-protocol==2.5.4`; GHCR `ghcr.io/asap-protocol/asap-protocol:v2.5.4`
- [x] Spot-check starter README smoke locally (optional maintainer follow-up) — CI starters-smoke green on merge
- [x] **Public GitHub links** — Dist Loop CTAs use `blob/main` / `tree/main` (no remaining `release/2.5.4` deep links)

---

## 5.0 Train handoff

| Next | Status |
|------|--------|
| **v2.5.5** Formal Spec / Interop | [PRD](../../../product/prd/prd-v2.5.5-formal-spec-interop.md) — create `engineering/tasks/v2.5.5/` when kicked off |
| npm `@asap-protocol/mcp-auth` | Still backlog — [../v2.5.0/backlog-mcp-auth-typescript.md](../v2.5.0/backlog-mcp-auth-typescript.md) |
| **v3.0** Economy | Vision only — [prd-v3.0-economy.md](../../../product/prd/prd-v3.0-economy.md); trigger-gated |

### 5.1 Handoff inputs for v2.5.5 (confirm at S5)

Mirror of [PRD §11](../../../product/prd/prd-v2.5.4-distribution-loop.md#11-handoff-inputs-for-v255-formal-spec). Soft inputs only.

- [x] Narrative D1 + `docs/guides/build-for-agents.md` linked from Spec kickoff notes
- [x] Three starter paths documented:
  - [x] `examples/starters/openapi-provider/`
  - [x] `examples/starters/typescript-consumer/`
  - [x] `examples/starters/mcp-auth-bridge/`
- [x] DIST-004 status: green **or** deferred (note on roadmap) — satisfied; secrets gap documented
- [x] OOS reminder: no CLI scaffold, no public metrics UI, no pricing/GTM in Spec kickoff copy
- [x] Orphans unchanged: `mcp-auth` npm backlog; TSOA defer-unless-demand; fourth workflow starter not canonical
- [x] Point [prd-v2.5.5-formal-spec-interop.md](../../../product/prd/prd-v2.5.5-formal-spec-interop.md) / train index at shipped Dist artifacts
- [x] Optional: one-line Dist metrics → v3.0 trigger proxies (if S4 ran) — S4 collectors/runbook ready; cron gated on secrets

**v2.5.4 train:** ☐ OPEN / ☑ CLOSED (after §6)

---

## 6.0 Post-publish: swap pending → shipped

> Complete only after PyPI shows `asap-protocol==2.5.4` and the GitHub Release for `v2.5.4` is published.

- [x] `CHANGELOG.md` `[2.5.4]`: remove “pending tag/publish” status callout if used
- [x] `README.md`, `docs/index.md`, `docs/migration.md`: recommend `asap-protocol==2.5.4`
- [x] `AGENTS.md`, `product/checkpoints.md`, `product/README.md`: **shipped** + tag/release links
- [x] Hero / WhatsNew: drop “pending publish” wording if any — hero badge `v2.5.4 — Distribution Loop` → release
- [x] This checklist §§4–5 and [sprint-S5-release.md](./sprint-S5-release.md): check complete
- [x] [tasks-v2.5.4-roadmap.md](./tasks-v2.5.4-roadmap.md): Status **SHIPPED**; S5 Done; train CLOSED
- [x] Link GitHub Release + PyPI (+ GHCR) in the S5 sprint notes
