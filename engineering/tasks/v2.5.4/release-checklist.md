# Release checklist: v2.5.4 Distribution Loop

**Roadmap:** [tasks-v2.5.4-roadmap.md](./tasks-v2.5.4-roadmap.md)  
**PRD:** [prd-v2.5.4-distribution-loop.md](../../../product/prd/prd-v2.5.4-distribution-loop.md)  
**Pattern:** [v2.5.3 release checklist](../v2.5.3/release-checklist.md)

---

## 1.0 Pre-tag verification

| Step | Command | Status |
|------|---------|--------|
| Lint | `uv run ruff check .` | ☐ |
| Format | `uv run ruff format --check .` | ☐ |
| Types | `uv run mypy src/ scripts/ tests/` | ☐ |
| Python tests | `uv run pytest --tb=short --cov=asap --cov-report=xml --cov-fail-under=85` | ☐ |
| pip-audit | per `SECURITY.md` | ☐ |
| npm audit (web) | `cd apps/web && npm audit --omit=dev --audit-level=moderate` and `npm audit --audit-level=high` (blocking in CI `quality-web`; see `SECURITY.md`) | ☐ |
| Web (if touched) | `npm run lint` / format check / `npx tsc --noEmit` / `npx vitest run` / `npm run build` in `apps/web/` | ☐ |
| MkDocs (if docs/nav touched) | `uv run mkdocs build` | ☐ |

---

## 2.0 Product DoD

> **S5 owns this section.** Fill when MUST surface is merge-ready.

- [ ] DIST-001 — homepage agent-first (D1)
- [ ] DIST-002 — CTAs → docs/starters/examples
- [ ] DIST-003 — three thin starters at locked paths
- [ ] DIST-004 — telemetry ops green **or** deferred on roadmap
- [ ] DIST-005 — `docs/guides/build-for-agents.md` shipped
- [ ] DIST-006 — public copy gate passed
- [ ] [docs-review-checklist.md](./docs-review-checklist.md) §§1–8 complete for shipped scope

---

## 3.0 Version & changelog gates

- [ ] `pyproject.toml` → `version = "2.5.4"`
- [ ] `src/asap/__init__.py` → `__version__ = "2.5.4"`
- [ ] `CHANGELOG.md` → `## [2.5.4]`
- [ ] `docs/migration.md` → v2.5.3 → v2.5.4
- [ ] `README.md`, `docs/index.md`, `AGENTS.md`, `product/README.md`, `product/checkpoints.md`
- [ ] npm `@asap-protocol/*` unchanged unless a package was intentionally bumped

---

## 4.0 Merge → tag → publish

**Order:** merge PR → tag `v2.5.4` → confirm publish workflows → then §6 handoff copy.

- [ ] **Merge** `release/2.5.4` → `main` — PR #____
- [ ] **Tag** `git tag -a v2.5.4` + push — triggers `.github/workflows/release.yml`
- [ ] **Publish** — GitHub Release `v2.5.4`; PyPI `asap-protocol==2.5.4`; Docker/GHCR if applicable
- [ ] Spot-check starter README smoke locally (optional maintainer follow-up)

---

## 5.0 Train handoff

| Next | Status |
|------|--------|
| **v2.5.5** Formal Spec / Interop | [PRD](../../../product/prd/prd-v2.5.5-formal-spec-interop.md) — create `engineering/tasks/v2.5.5/` when kicked off |
| npm `@asap-protocol/mcp-auth` | Still backlog — [../v2.5.0/backlog-mcp-auth-typescript.md](../v2.5.0/backlog-mcp-auth-typescript.md) |
| **v3.0** Economy | Vision only — [prd-v3.0-economy.md](../../../product/prd/prd-v3.0-economy.md); trigger-gated |

### 5.1 Handoff inputs for v2.5.5 (confirm at S5)

Mirror of [PRD §11](../../../product/prd/prd-v2.5.4-distribution-loop.md#11-handoff-inputs-for-v255-formal-spec). Soft inputs only.

- [ ] Narrative D1 + `docs/guides/build-for-agents.md` linked from Spec kickoff notes
- [ ] Three starter paths documented:
  - [ ] `examples/starters/openapi-provider/`
  - [ ] `examples/starters/typescript-consumer/`
  - [ ] `examples/starters/mcp-auth-bridge/`
- [ ] DIST-004 status: green **or** deferred (note on roadmap)
- [ ] OOS reminder: no CLI scaffold, no public metrics UI, no pricing/GTM in Spec kickoff copy
- [ ] Orphans unchanged: `mcp-auth` npm backlog; TSOA defer-unless-demand; fourth workflow starter not canonical
- [ ] Point [prd-v2.5.5-formal-spec-interop.md](../../../product/prd/prd-v2.5.5-formal-spec-interop.md) / train index at shipped Dist artifacts
- [ ] Optional: one-line Dist metrics → v3.0 trigger proxies (if S4 ran)

**v2.5.4 train:** ☑ OPEN / ☐ CLOSED (after §6)

---

## 6.0 Post-publish: swap pending → shipped

> Complete only after PyPI shows `asap-protocol==2.5.4` and the GitHub Release for `v2.5.4` is published.

- [ ] `CHANGELOG.md` `[2.5.4]`: remove “pending tag/publish” status callout if used
- [ ] `README.md`, `docs/index.md`, `docs/migration.md`: recommend `asap-protocol==2.5.4`
- [ ] `AGENTS.md`, `product/checkpoints.md`, `product/README.md`: **shipped** + tag/release links
- [ ] Hero / WhatsNew: drop “pending publish” wording if any
- [ ] This checklist §§4–5 and [sprint-S5-release.md](./sprint-S5-release.md): check complete
- [ ] [tasks-v2.5.4-roadmap.md](./tasks-v2.5.4-roadmap.md): Status **SHIPPED**; S5 Done; train CLOSED
- [ ] Link GitHub Release + PyPI (+ GHCR) in the S5 sprint notes
