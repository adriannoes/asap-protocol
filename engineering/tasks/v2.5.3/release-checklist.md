# Release checklist: v2.5.3 Adapter Lab II

**Roadmap:** [tasks-v2.5.3-roadmap.md](./tasks-v2.5.3-roadmap.md)  
**PRD:** [prd-v2.5.3-adapter-lab-ii.md](../../../product/prd/prd-v2.5.3-adapter-lab-ii.md)  
**Pattern:** [v2.5.0 release checklist](../v2.5.0/release-checklist.md)

---

## 1.0 Pre-tag verification

| Step | Command | Status |
|------|---------|--------|
| Lint | `uv run ruff check .` | ☑ |
| Format | `uv run ruff format --check .` | ☑ |
| Types | `uv run mypy src/ scripts/ tests/` | ☑ |
| Python tests | `uv run pytest --tb=short --cov=asap --cov-report=xml --cov-fail-under=85` | ☑ (94.46%) |
| pip-audit | per `SECURITY.md` | ☑ |
| npm audit (web) | `cd apps/web && npm audit --omit=dev --audit-level=moderate` and `npm audit --audit-level=high` (blocking in CI `quality-web`; see `SECURITY.md`) | ☑ |
| Web (if touched) | `npm run lint` / `npm run format:check -- <PR TS/TSX>` / `npx tsc --noEmit` / `npx vitest run` / `npm run build` in `apps/web/` | ☑ |

---

## 2.0 Product DoD

> **S4 owns this section.** Verified for merge-ready surface 2026-07-14.

- [x] LAB2-001 — no protocol fork
- [x] LAB2-002 — ≥1 workflow/enterprise example
- [x] LAB2-003 — security guide published
- [x] LAB2-004 — homepage/docs routing (`mkdocs.yml` + `docs/index.md` + web)
- [x] [docs-review-checklist.md](./docs-review-checklist.md) §§1–8 complete for shipped scope
- [x] LAB2-005 — [learnings-open-vs-hosted.md](./learnings-open-vs-hosted.md) written
- [x] LAB2-006 — Auth Bridge used or N/A documented
- [x] S1b status: shipped research / maintained / **skipped** → research + MAF guide shipped
- [x] S1c status: guide + demo / guide only / **skipped** → guide + Path A demo
- [x] [research-nemo-agent-toolkit.md](./research-nemo-agent-toolkit.md) pin current if S1c ran

---

## 3.0 Version & changelog gates

- [x] `pyproject.toml` → `version = "2.5.3"` (default)
- [x] `src/asap/__init__.py` → `__version__ = "2.5.3"`
- [x] `CHANGELOG.md` → `## [2.5.3]`
- [x] `docs/migration.md` → v2.5.2 → v2.5.3
- [x] `README.md`, `docs/index.md`, `AGENTS.md`, `product/README.md`, `product/checkpoints.md`
- [x] npm `@asap-protocol/*` unchanged unless a package was intentionally bumped

---

## 4.0 Merge → tag → publish

**Order:** merge PR → tag `v2.5.3` → confirm publish workflows → then §6 handoff copy.

- [x] **Merge** `release/2.5.3` → `main` — PR [#291](https://github.com/adriannoes/asap-protocol/pull/291) **MERGED** 2026-07-15 (`57d73cae`)
- [x] **Tag** `git tag -a v2.5.3` + push (2026-07-16) — triggers `.github/workflows/release.yml` ([run](https://github.com/adriannoes/asap-protocol/actions/runs/29494582885))
- [x] **Publish** — [GitHub Release `v2.5.3`](https://github.com/adriannoes/asap-protocol/releases/tag/v2.5.3) (compare `v2.5.2...v2.5.3`); PyPI `asap-protocol==2.5.3`; Docker/GHCR green
- [x] Spot-check example README command locally (optional maintainer follow-up)

---

## 5.0 Train handoff

| Next | Status |
|------|--------|
| **v2.5.4** Distribution Loop | Create `engineering/tasks/v2.5.4/` when kicked off — [PRD](../../../product/prd/prd-v2.5.4-distribution-loop.md) |
| npm `@asap-protocol/mcp-auth` | Still backlog — [../v2.5.0/backlog-mcp-auth-typescript.md](../v2.5.0/backlog-mcp-auth-typescript.md) |

**v2.5.3 train:** ☐ OPEN / ☑ CLOSED (after §6)

---

## 6.0 Post-publish: swap pending → shipped

> Completed 2026-07-16 after PyPI showed `asap-protocol==2.5.3`, GHCR tags existed, and the GitHub Release for `v2.5.3` was published.

- [x] `CHANGELOG.md` `[2.5.3]`: remove “pending tag/publish” status callout
- [x] `README.md`, `docs/index.md`, `docs/migration.md`: recommend `pip install asap-protocol==2.5.3` / `uv add`; drop “stay on 2.5.2”
- [x] `AGENTS.md`, `product/checkpoints.md`, `product/README.md`: **shipped** + tag/release links
- [x] Hero / WhatsNewRibbon: drop “pending publish” wording
- [x] This checklist §§4–5 and [sprint-S4-release.md](./sprint-S4-release.md) 5.4–5.5: check complete
- [x] [tasks-v2.5.3-roadmap.md](./tasks-v2.5.3-roadmap.md): Status **SHIPPED**; S4 Done; train CLOSED
- [x] Link GitHub Release + PyPI + GHCR in the S4 sprint notes
