# Sprint S5: Release v2.5.4

**PRD**: Definition of Done / D5  
**Branch**: work on **`release/2.5.4`** → PR to **`main`**  
**Depends on**: S1–S3 MUST green; S4 green **or** deferred on roadmap  
**Status**: **Done (shipped)** — tag [`v2.5.4`](https://github.com/asap-protocol/asap-protocol/releases/tag/v2.5.4); PyPI `asap-protocol==2.5.4`; workflow [29650003126](https://github.com/asap-protocol/asap-protocol/actions/runs/29650003126)

**Trigger:** Distribution Loop MUST items complete on the release branch.  
**Enables:** v2.5.5 Formal Spec kickoff.  
**Depends on:** [release-checklist.md](./release-checklist.md).

**Release sequence:** **merge → tag → publish → handoff** — do not mark SHIPPED before publish.

---

## Tasks

- [x] **6.1 Version bumps**
  - [x] `pyproject.toml` / `src/asap/__init__.py` → **2.5.4**
  - [x] npm `@asap-protocol/*`: leave at current line unless a TS package intentionally changed (**unchanged at 2.4.1**)

- [x] **6.2 Changelog & migration**
  - [x] `CHANGELOG.md` → `## [2.5.4]`
  - [x] `docs/migration.md` → upgrading from v2.5.3 → v2.5.4 (`#upgrading-from-v253-to-v254`)
  - [x] Update `AGENTS.md`, `product/README.md`, `docs/index.md`, `product/checkpoints.md`
  - [x] Confirm [docs-review-checklist.md](./docs-review-checklist.md) version-string sign-off (prep; post-publish swap remains)

- [x] **6.3 Pre-push CI**
  - [x] `uv run ruff check .` — **PASS**
  - [x] `uv run ruff format --check .` — **PASS** (539 files)
  - [x] `uv run mypy src/ scripts/ tests/` — **PASS** (496 source files)
  - [x] `uv run pytest --tb=short --cov=asap --cov-report=xml --cov-fail-under=85` — **PASS** (3841 passed, 13 skipped; coverage **94.46%**)
  - [x] pip-audit per `SECURITY.md` / `git-commits.mdc` — **PASS** after bumping optional `[mcp]` to `>=1.28.1` (CVE-2026-52869 / 52870 / 59950)
  - [x] `apps/web/`: lint, `tsc`, vitest, build — **PASS**; `npm audit` moderate/high — **0 vulns**
  - [x] `uv run mkdocs build` — **PASS** (pre-existing link warnings only; no new failures)

  **CI results (2026-07-18, S5 prep):** all gates above green. Note: full pytest run after `uv sync --frozen --all-extras --dev --no-extra crewai --no-extra llamaindex`; mcp smoke re-verified post-bump (120 passed).

- [x] **6.4 Merge → tag → publish**
  - [x] **Merge** PR `release/2.5.4` → `main` — [#294](https://github.com/asap-protocol/asap-protocol/pull/294)
  - [x] **Tag** `v2.5.4` + push — [Release workflow](https://github.com/asap-protocol/asap-protocol/actions/runs/29650003126)
  - [x] **Publish** — [GitHub Release `v2.5.4`](https://github.com/asap-protocol/asap-protocol/releases/tag/v2.5.4); PyPI `asap-protocol==2.5.4`; GHCR `ghcr.io/asap-protocol/asap-protocol:v2.5.4`
  - [x] Post-publish checklist ([release-checklist §6](./release-checklist.md#60-post-publish-swap-pending--shipped))

- [x] **6.5 Handoff**
  - [x] Mark this roadmap SHIPPED
  - [x] Complete [release-checklist §5.1](./release-checklist.md#51-handoff-inputs-for-v255-confirm-at-s5) (starter paths, guide, OOS, orphans)
  - [x] Point next work at [prd-v2.5.5-formal-spec-interop.md](../../../product/prd/prd-v2.5.5-formal-spec-interop.md)
  - [x] Remind: `@asap-protocol/mcp-auth` still on [v2.5.0 backlog](../v2.5.0/backlog-mcp-auth-typescript.md); Economy remains trigger-gated ([prd-v3.0-economy.md](../../../product/prd/prd-v3.0-economy.md))

---

## Reviews

| Date | Tier | Verdict | Report |
|------|------|---------|--------|
| 2026-07-18 | T2 | Approved with caveats | [review-v2.5.4-S3-S5-homepage-telemetry-release-20260718.md](../../code-review/private/review-v2.5.4-S3-S5-homepage-telemetry-release-20260718.md) |

## Acceptance criteria

- [x] [release-checklist.md](./release-checklist.md) §§1–6 complete
- [x] All DIST MUST items closed; DIST-004 closed or deferred
- [x] Train handoff to v2.5.5 documented
