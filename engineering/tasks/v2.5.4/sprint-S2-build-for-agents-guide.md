# Sprint S2: Build for agents guide (v2.5.4)

**PRD**: DIST-005 (D1 narrative)  
**Branch**: `feat/v2.5.4-s0-s2-starters-guide` (combined S0–S2) → **`release/2.5.4`**  
**Depends on**: [S1](./sprint-S1-starter-pack.md) (starter URLs)  
**Status**: Done

**Trigger:** Starter pack paths exist so the guide can link executable entry points.  
**Enables:** S3 primary homepage CTA; docs-review surface.  
**Depends on:** Task 2.0; PRD §6 canonical narrative.

---

## Goal

Publish a public guide that states the agent-first story and routes readers into the three starters and key existing adapters/SDKs.

---

## Tasks

- [x] **3.1 Draft guide**
  - [x] Create `docs/guides/build-for-agents.md`
  - [x] Lead with PRD §6 narrative (D1)
  - [x] Audience: API providers and agent/app builders
  - [x] Explicit status: **maintained**
  - [x] Link: three starters, OpenAPI adapter, MCP Auth Bridge, TypeScript SDK, first-agent tutorial as needed
  - [x] HTTPS/TLS / least-privilege notes where network or credentials appear
  - [x] DIST-006: no pricing, fundraising, or private GTM

- [x] **3.2 MkDocs wiring**
  - [x] Add nav entry under Guides in `mkdocs.yml`
  - [x] Smoke: `uv run mkdocs build` (document `--strict` caveats if pre-existing)
    - `uv sync --extra docs && uv run mkdocs build` → **exit 0** (2026-07-18)
    - `uv run mkdocs build --strict` still fails on **pre-existing** warnings (missing `api/*` + `contributing.md` nav stubs; out-of-docs link warnings) — same caveat as Lab II docs-review; **not** introduced by this guide

- [x] **3.3 Cross-links (minimal)**
  - [x] Starters index → guide
  - [x] Optional “See also” on `docs/index.md` (full index polish may wait for docs checklist / S3)

---

## Acceptance criteria

- [x] Guide file exists and is English, professional, public-safe
- [x] Nav includes the guide
- [x] Links to all three `examples/starters/*` resolve
- [x] DIST-005 producer slice satisfied (guide + nav + starters index + docs/index); homepage link deferred to S3
- [x] DIST-006 clean

## Reviews

| Date | Tier | Verdict | Report |
|------|------|---------|--------|
| 2026-07-18 | T2 | Approved with caveats (r2) | [review-v2.5.4-S0-S2-starters-guide-20260718-r2.md](../../../code-review/private/review-v2.5.4-S0-S2-starters-guide-20260718-r2.md) |
| 2026-07-18 | C.7 | Rejected (r1) — fixes applied pending r2 | [review-v2.5.4-S0-S2-starters-guide-20260718.md](../../../code-review/private/review-v2.5.4-S0-S2-starters-guide-20260718.md) |

## Relevant files

- `docs/guides/build-for-agents.md`
- `mkdocs.yml`
- `docs/index.md`
- `examples/starters/README.md`
- [docs-review-checklist.md](./docs-review-checklist.md)
