# Release checklist: v2.5.3 Adapter Lab II

**Roadmap:** [tasks-v2.5.3-roadmap.md](./tasks-v2.5.3-roadmap.md)  
**PRD:** [prd-v2.5.3-adapter-lab-ii.md](../../../product/prd/prd-v2.5.3-adapter-lab-ii.md)  
**Pattern:** [v2.5.0 release checklist](../v2.5.0/release-checklist.md)

---

## 1.0 Pre-tag verification

| Step | Command | Status |
|------|---------|--------|
| Lint | `uv run ruff check .` | ☐ (Phase 5) |
| Format | `uv run ruff format --check .` | ☐ (Phase 5) |
| Types | `uv run mypy src/ scripts/ tests/` | ☐ (Phase 5) |
| Python tests | `uv run pytest --tb=short --cov=asap --cov-report=xml --cov-fail-under=85` | ☐ (Phase 5) |
| pip-audit | per `SECURITY.md` | ☐ (Phase 5) |
| Web (if touched) | `npm run lint` / `npx tsc --noEmit` / `npx vitest run` / `npm run build` in `apps/web/` | ☐ (Phase 5) |

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

## 4.0 Tag, publish, verify

- [ ] Merge `release/2.5.3` → `main`
- [ ] `git tag -a v2.5.3` + push
- [ ] GitHub Release notes (Adapter Lab II)
- [ ] PyPI / Docker workflow green (if Python version bumped)
- [ ] Spot-check example README command locally

---

## 5.0 Train handoff

| Next | Status |
|------|--------|
| **v2.5.4** Distribution Loop | Create `engineering/tasks/v2.5.4/` when kicked off |
| npm `@asap-protocol/mcp-auth` | Still backlog — [../v2.5.0/backlog-mcp-auth-typescript.md](../v2.5.0/backlog-mcp-auth-typescript.md) |

**v2.5.3 train:** ☑ OPEN (merge-ready) / ☐ CLOSED (after tag)
