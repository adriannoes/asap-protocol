# Sprint S0: Scope lock (v2.5.4)

**PRD**: [prd-v2.5.4-distribution-loop.md](../../../product/prd/prd-v2.5.4-distribution-loop.md) §3 D1–D5, §4  
**Branch**: `feat/v2.5.4-s0-s2-starters-guide` (combined S0+S1+S2) → **`release/2.5.4`**  
**Depends on**: v2.5.3 shipped; PRD decisions locked  
**Status**: Done (2026-07-18)

**Trigger:** Maintainer kickoff of Distribution Loop.  
**Enables:** S1 starters; S4 telemetry; S2/S3 after starter/guide paths exist.  
**Depends on:** PRD D1–D5; baseline inventory in PRD §4.

---

## Goal

Confirm locked decisions, confirm the integration branch, and list concrete gaps so S1–S4 do not reinvent Lab II work.

---

## Tasks

- [x] **1.1 Integration branch**
  - [x] `release/2.5.4` already on origin (2026-07-18) — do **not** recreate
  - [x] Working branch: `feat/v2.5.4-s0-s2-starters-guide` (combined S0+S1+S2) → **`release/2.5.4`** (see [BRANCHING.md](./BRANCHING.md)); original slug `feat/v2.5.4-s0-scope-lock` unused
  - [x] Set [tasks-v2.5.4-roadmap.md](./tasks-v2.5.4-roadmap.md) status to **ACTIVE**

- [x] **1.2 Reconfirm locked decisions** (2026-07-18 — no maintainer overrides; no silent swaps)
  - [x] **D1** — Build for agents primary; marketplace secondary — confirmed (PRD §3)
  - [x] **D2** — Starters: OpenAPI · TypeScript consumer · MCP Auth Bridge — confirmed (PRD §3)
  - [x] **D3** — Thin wrappers under `examples/starters/` — confirmed (PRD §3)
  - [x] **D4** — Operationalize telemetry; no public live dashboard — confirmed (PRD §3)
  - [x] **D5** — Versioned release `v2.5.4` (Python bump + CHANGELOG + migration) — confirmed (PRD §3)
  - [x] No maintainer override recorded (defaults stand)

- [x] **1.3 Baseline gap list** (verified 2026-07-18)
  - [x] **Homepage marketplace-primary → S3** — hero / primary CTAs still marketplace-first; agent-first narrative + CTA routing deferred to S3
  - [x] **No `examples/starters/` → S1** — directory absent; thin wrappers not yet created (do not invent Lab II parents)
  - [x] **No `docs/guides/build-for-agents.md` → S2** — guide file absent; S2 owns publish + mkdocs nav
  - [x] **Telemetry package coverage / schedule secrets → S4** — `scripts/telemetry/` exists; npm coverage and weekly-schedule secrets still S4 ops work; no public live dashboard (D4)
  - [x] **Parent sources confirmed present** (ls 2026-07-18):
    - `examples/openapi_petstore/` — present (README, main.py, openapi-fragment.json)
    - `examples/mcp_auth_bridge/` — present (README, client.py, server.py)
    - `apps/example-nextjs/` — present (Next.js consumer app)
    - `scripts/telemetry/` — present (aggregate, collect_npm/pypi/github/registry)

- [x] **1.4 DIST-006 gate setup**
  - [x] Public-copy grep terms for release / docs review: `pricing`, `fundraising`, paid timing (e.g. “pay”, “paid”, “pricing tier”), private GTM phrases (campaign codenames, internal funnel jargon). Run before S5 publish and when touching homepage/guide copy (see [docs-review-checklist.md](./docs-review-checklist.md))
  - [x] `product/strategy/` remains gitignored — confirmed: `git check-ignore -v product/strategy/` → `.gitignore:187:product/strategy/`

---

## Acceptance criteria

- [x] `release/2.5.4` exists on origin (all sprint PRs merge **into** it)
- [x] D1–D5 confirmed (or override documented)
- [x] Gap list written in this file or linked note
- [x] Roadmap sprint table: S0 → Done; train ACTIVE

## Reviews

| Date | Tier | Verdict | Report |
|------|------|---------|--------|
| 2026-07-18 | T2 | Approved with caveats (r2) | [review-v2.5.4-S0-S2-starters-guide-20260718-r2.md](../../../code-review/private/review-v2.5.4-S0-S2-starters-guide-20260718-r2.md) |
| 2026-07-18 | C.7 | Rejected (r1) — fixes applied pending r2 | [review-v2.5.4-S0-S2-starters-guide-20260718.md](../../../code-review/private/review-v2.5.4-S0-S2-starters-guide-20260718.md) |

## Relevant files

- `product/prd/prd-v2.5.4-distribution-loop.md`
- `engineering/tasks/v2.5.4/tasks-v2.5.4-roadmap.md`
- `engineering/tasks/v2.5.4/BRANCHING.md`
