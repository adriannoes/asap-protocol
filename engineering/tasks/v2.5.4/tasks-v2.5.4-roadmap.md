# Tasks: v2.5.4 Distribution Loop — Sprint Index

**Status: ACTIVE** — PRD decisions locked 2026-07-18; S0 scope lock done; **`release/2.5.4` exists on origin** (all sprint branches merge into it). **Predecessor:** [v2.5.3](../v2.5.3/tasks-v2.5.3-roadmap.md) SHIPPED. **Next after ship:** [prd-v2.5.5-formal-spec-interop.md](../../../product/prd/prd-v2.5.5-formal-spec-interop.md).

Based on [PRD v2.5.4 Distribution Loop](../../../product/prd/prd-v2.5.4-distribution-loop.md). **Every** sprint PR merges into **`release/2.5.4`** (see [BRANCHING.md](./BRANCHING.md)); only S5 opens one PR to `main`.

## Prerequisites

- [x] v2.5.3 Adapter Lab II shipped (2026-07-16)
- [x] PRD D1–D5 locked (2026-07-18)
- [x] Baseline inventory documented in PRD §4 (homepage, CTAs, examples, telemetry)
- [x] `release/2.5.4` on origin (2026-07-18)
- [x] Maintainer marks this folder **ACTIVE** (S0 scope lock done 2026-07-18)

## Sprint plan

| Sprint | Focus | PRD | Priority | Status |
|--------|-------|-----|----------|--------|
| **S0** | [Scope lock](./sprint-S0-scope-lock.md) | D1–D5, §4 baseline | P0 | Done |
| **S1** | [Thin starter pack](./sprint-S1-starter-pack.md) | DIST-003 | P0 | Done |
| **S2** | [Build for agents guide](./sprint-S2-build-for-agents-guide.md) | DIST-005 | P0 | Done |
| **S3** | [Homepage narrative & CTA routing](./sprint-S3-homepage-routing.md) | DIST-001, DIST-002, DIST-005 (homepage link), DIST-006 | P0 | Planned |
| **S4** | [Telemetry operations](./sprint-S4-telemetry-operations.md) | DIST-004 | P1 (SHOULD) | Planned |
| **S5** | [Release v2.5.4](./sprint-S5-release.md) | DoD, D5 | P0 | Planned |

## Dependency graph

```
S0 (scope lock)
 │
 ├──► S1 (starters) ──► S2 (guide) ──┐
 │         │                         ├──► S3 (homepage + CTAs)
 │         └─────────────────────────┘
 │
 └──► S4 (telemetry ops, parallel; SHOULD)
                                        │
                                        ▼
                                      S5 (release)
```

S1 and S4 may run in parallel after S0. S2 needs starter paths from S1. S3 needs guide (S2) and starter URLs (S1). S5 requires all MUST items (S1–S3); S4 MAY defer with explicit roadmap note.

## Parent tasks (high-level)

- [x] **1.0 Scope lock (S0)**
  - **Trigger:** Maintainer kickoff after PRD harden.
  - **Enables:** S1 starters; S4 telemetry; branch train.
  - **Depends on:** PRD D1–D5; v2.5.3 shipped.
  - **Acceptance criteria:**
    - [x] `release/2.5.4` exists on origin (sprint PRs merge into it)
    - [x] D1–D5 reconfirmed in sprint notes (no silent swaps)
    - [x] Baseline gaps listed for S1–S4
    - [x] Roadmap status → ACTIVE

- [x] **2.0 Thin starter pack (S1)**
  - **Trigger:** S0 complete.
  - **Enables:** S2 guide links; S3 primary CTAs.
  - **Depends on:** Task 1.0; parent examples in tree.
  - **Acceptance criteria:**
    - [x] `examples/starters/openapi-provider/`
    - [x] `examples/starters/typescript-consumer/`
    - [x] `examples/starters/mcp-auth-bridge/`
    - [x] Index README + headless smoke per starter
    - [x] DIST-003 satisfied

- [x] **3.0 Build for agents guide (S2)**
  - **Trigger:** S1 starter paths known (may draft in parallel once paths locked in S0/S1).
  - **Enables:** S3 hero CTA target; docs surface.
  - **Depends on:** Task 2.0 (for live starter links).
  - **Acceptance criteria:**
    - [x] `docs/guides/build-for-agents.md` published
    - [x] `mkdocs.yml` nav entry
    - [x] Links to all three starters + key adapters
    - [x] DIST-005 producer slice satisfied (guide + nav + starters index + docs/index); homepage link deferred to S3
    - [x] DIST-006 copy clean

- [ ] **4.0 Homepage narrative & CTA routing (S3)**
  - **Trigger:** Guide + starters available for primary CTAs.
  - **Enables:** S5 public web surface.
  - **Depends on:** Tasks 2.0–3.0; [docs-review-checklist.md](./docs-review-checklist.md).
  - **Acceptance criteria:**
    - [ ] Hero / metadata follow D1 agent-first narrative
    - [ ] Primary CTAs → guide and/or `examples/starters/`
    - [ ] Homepage primary CTA → `docs/guides/build-for-agents.md` (DIST-005 homepage half)
    - [ ] Marketplace browse/register remain secondary
    - [ ] `data-cta` IDs coherent; live link audit
    - [ ] DIST-001, DIST-002, DIST-005 (homepage link), DIST-006 satisfied

- [ ] **5.0 Telemetry operations (S4)**
  - **Trigger:** S0 complete (parallel with S1).
  - **Enables:** DIST-004 DoD; does not block S5 if deferred.
  - **Depends on:** Task 1.0; existing `scripts/telemetry/`.
  - **Acceptance criteria:**
    - [ ] npm collectors cover ≥3 scoped packages
    - [ ] PyPI aggregate covers `asap-protocol` + `asap-compliance`
    - [ ] Guide-view proxy documented (GitHub + site CTR)
    - [ ] Runbook updated; `workflow_dispatch` green once (or secrets gap documented)
    - [ ] **No** new public metrics UI
    - [ ] DIST-004 satisfied **or** explicit defer on roadmap

- [ ] **6.0 Release (S5)**
  - **Trigger:** MUST sprints green on `release/2.5.4`.
  - **Enables:** v2.5.5 Formal Spec kickoff.
  - **Depends on:** Tasks 2.0–4.0; Task 5.0 or documented deferral; [release-checklist.md](./release-checklist.md).
  - **Sequence:** **merge → tag → publish → handoff** (do not mark SHIPPED before publish).
  - **Acceptance criteria:**
    - [ ] Version **2.5.4**, CHANGELOG, migration note
    - [ ] Pre-push CI green (ruff, mypy, pytest ≥85%, pip-audit; web gates if touched)
    - [ ] Merge `release/2.5.4` → `main`
    - [ ] Tag `v2.5.4` + PyPI / GitHub Release green
    - [ ] Post-publish swap pending → shipped
    - [ ] Handoff to v2.5.5

## Definition of Done — v2.5.4

- [ ] DIST-001 — homepage agent-first (D1)
- [ ] DIST-002 — CTAs → docs/starters/examples
- [ ] DIST-003 — three thin starters at locked paths
- [ ] DIST-004 — telemetry ops documented/runnable **or** deferred
- [ ] DIST-005 — `docs/guides/build-for-agents.md` shipped
- [ ] DIST-006 — no private GTM/pricing/fundraising in public copy
- [ ] [docs-review-checklist.md](./docs-review-checklist.md) signed
- [ ] [release-checklist.md](./release-checklist.md) §§1–6 complete

## Out of scope (defer)

| Item | Where |
|------|--------|
| Full Design System Revamp | Separate design track |
| `create-asap` / scaffold CLI | Post–v2.5.4 |
| Public live metrics dashboard | PRD D4 |
| MkDocs analytics plugin | PRD §3.2 proxies only |
| `@asap-protocol/mcp-auth` | [../v2.5.0/backlog-mcp-auth-typescript.md](../v2.5.0/backlog-mcp-auth-typescript.md) |
| Formal Spec / A2A | [prd-v2.5.5-formal-spec-interop.md](../../../product/prd/prd-v2.5.5-formal-spec-interop.md) (soft successor; see Dist PRD §11) |
| Economy / pricing | [prd-v3.0-economy.md](../../../product/prd/prd-v3.0-economy.md) (trigger-gated) |
| Workflow as 4th starter | Optional; `examples/workflow_asap_connector/` already public |
| Orphan owners (mcp-auth, TSOA, …) | [prd-v2.5-roadmap.md](../../../product/prd/prd-v2.5-roadmap.md) parked table |

## Relevant files (planned)

### Likely new

- `examples/starters/README.md`
- `examples/starters/openapi-provider/`
- `examples/starters/typescript-consumer/`
- `examples/starters/mcp-auth-bridge/`
- `docs/guides/build-for-agents.md`

### Likely modify

- `apps/web/src/components/landing/*` — hero, terminal, how-it-works, what's new, features
- `apps/web/src/lib/telemetry/homepage-cta-ids.ts`
- `apps/web/src/app/page.tsx` — metadata
- `mkdocs.yml`, `docs/index.md`
- `scripts/telemetry/collect_npm.py`, `aggregate.py`, related tests
- `docs/maintainers/telemetry.md`
- `.github/workflows/telemetry-weekly.yml` — dispatch/schedule policy only when secrets ready
- `pyproject.toml`, `src/asap/__init__.py`, `CHANGELOG.md`, `docs/migration.md`
- `AGENTS.md`, `product/checkpoints.md`, `product/README.md`

### Reference

- `examples/openapi_petstore/`, `examples/mcp_auth_bridge/`
- `apps/example-nextjs/`, `packages/typescript/client`
- `docs/adapters/openapi.md`, `docs/adapters/mcp-auth-bridge.md`, `docs/sdks/typescript.md`
- `engineering/tasks/v2.5.3/` — prior train pattern

## Change log

| Date | Change |
|------|--------|
| 2026-07-18 | Train handoff §11 / release-checklist §5.1; orphan owners; Spec/Economy cross-links before kickoff |
| 2026-07-18 | `release/2.5.4` on origin; [BRANCHING.md](./BRANCHING.md) locks all sprint PRs → integration branch |
| 2026-07-18 | Initial sprint index from hardened PRD (D1–D5, DIST-001..006); S0–S5 |
| 2026-07-18 | S0 complete: D1–D5 reconfirmed; gaps listed; status → ACTIVE; working branch `feat/v2.5.4-s0-s2-starters-guide` |
| 2026-07-18 | S2 complete: `docs/guides/build-for-agents.md` + MkDocs nav + index/starters cross-links (DIST-005 producer slice; homepage link → S3) |
| 2026-07-18 | C.7 review feedback: DIST-005 ownership clarified; TypeScript smoke package-boundary + HTTPS enforce |
