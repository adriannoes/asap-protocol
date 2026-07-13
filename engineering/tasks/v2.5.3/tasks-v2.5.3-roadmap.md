# Tasks: v2.5.3 Adapter Lab II — Sprint Index

**Status: ACTIVE (kickoff started 2026-07-13)** — `release/2.5.3` on origin; working branch `feat/v2.5.3-s0-s1-workflow`. Demand sheet: [demand-sheet.md](./demand-sheet.md).

Based on [PRD v2.5.3 Adapter Lab II](../../../product/prd/prd-v2.5.3-adapter-lab-ii.md). Each sprint merges into **`release/2.5.3`** (see [BRANCHING.md](./BRANCHING.md)); merge to `main` only after S4.

## Prerequisites

- [x] v2.5.2 security follow-up shipped (2026-07-08)
- [x] v2.5.0 MCP Auth Bridge in tree (`asap.adapters.mcp.protect_server`)
- [x] v2.3.0 OpenAPI adapter + v2.3.1 Mastra / OpenAI Agents adapters shipped
- [x] `scripts/lint_no_transport_growth.py` CI-enforced (Lab I D4)
- [x] Maintainer opens kickoff (this folder + `release/2.5.3` branch)

## Sprint plan

| Sprint | Focus | PRD | Priority | Status |
|--------|-------|-----|----------|--------|
| **S0** | [Candidate lock & demand check](./sprint-S0-candidate-lock.md) | D1–D7, §6 gates | P0 | Done |
| **S1** | [Workflow prototype (primary)](./sprint-S1-workflow-prototype.md) | LAB2-001, LAB2-002 | P0 | Done |
| **S1b** | [Conditional SK / .NET spike](./sprint-S1b-semantic-kernel.md) | D2 | P0 if gate | Skipped (D2 no-go) |
| **S1c** | [NeMo Agent Toolkit spike](./sprint-S1c-nemo-agent-toolkit.md) | D7 | P0 planned | Planned (D7 go) |
| **S2** | [Security guide & MCP patterns](./sprint-S2-security-docs.md) | LAB2-003, LAB2-006 | P0 | Planned |
| **S3** | [Docs review, site routing & learnings](./sprint-S3-docs-review.md) | LAB2-004, LAB2-005 + docs surface | P0 | Planned |
| **S4** | [Release v2.5.3](./sprint-S4-release.md) | DoD, metrics | P0 | Planned |

## Dependency graph

```
S0 (candidate lock)
 │
 ├──► S1 (workflow → ASAP prototype) ──► S2 (security + MCP docs)
 │         │                                    │
 │         ├──► S1b (only if D2 gate)           │
 │         └──► S1c (NAT spike, default go)     │
 │                                              ▼
 └────────────────────────────────────────► S3 (docs review + site + LAB2-005)
                                              │
                                              ▼
                                            S4 (release)
```

S1b / S1c never block S1/S2/S3/S4. If D2 fails, skip S1b. S1c defaults to **go** (D7); skip only with explicit maintainer no-go in the demand sheet.

## Parent tasks (high-level)

- [x] **1.0 Candidate lock (S0)**
  - **Trigger:** Maintainer kickoff after v2.5.2.
  - **Enables:** S1 primary path; optional S1b; planned S1c.
  - **Depends on:** PRD D1–D7; GitHub `adapter-request` label / issues.
  - **Acceptance criteria:**
    - [x] Demand sheet filled (SK / Haystack / Letta / n8n / NeMo Agent Toolkit counts)
    - [x] Primary confirmed: workflow connector **or** explicit swap documented
    - [x] S1b go/no-go recorded
    - [x] S1c go/no-go recorded (**default go** per D7)
    - [x] `release/2.5.3` branch exists

- [x] **2.0 Workflow prototype (S1)**
  - **Trigger:** S0 primary = workflow (default).
  - **Enables:** S2 security guide against a real example; S3 site links.
  - **Depends on:** Task 1.0; OpenAPI adapter and/or capability grant APIs in tree.
  - **Acceptance criteria:**
    - [x] Runnable example under `examples/` (or `apps/`) maps workflow/API actions → ASAP capabilities
    - [x] Guide under `docs/integrations/` (or `docs/adapters/`)
    - [x] No protocol fork; transport lint clean
    - [x] LAB2-001 / LAB2-002 satisfied for the primary

- [ ] **2b.0 Conditional Semantic Kernel spike (S1b)**
  - **Trigger:** S0 D2 gate pass.
  - **Enables:** Optional second public guide; does not block release if incomplete.
  - **Depends on:** Task 1.0 go decision.
  - **Acceptance criteria:**
    - [ ] Interop note + .NET/guide path documented
    - [ ] Explicit “maintained vs research” status in the guide

- [ ] **2c.0 NeMo Agent Toolkit spike (S1c)**
  - **Trigger:** S0 D7 default go (or explicit no-go skip).
  - **Enables:** NVIDIA-stack guide + optional MCP bridge demo; feeds v2.5.5 Agent Card mapping.
  - **Depends on:** Task 1.0; [research-nemo-agent-toolkit.md](./research-nemo-agent-toolkit.md).
  - **Acceptance criteria:**
    - [ ] Research pin refreshed; auth/transport gap tables written
    - [ ] `docs/integrations/nemo-agent-toolkit.md` published (honest limits)
    - [ ] Path A demo **or** documented blocker + follow-up (no fake native claim)
    - [ ] Third-party NAT plugin deferred (Path C)

- [ ] **3.0 Security & MCP docs (S2)**
  - **Trigger:** S1 example shape known.
  - **Enables:** Safe public adoption; S4 DoD for LAB2-003/006.
  - **Depends on:** Task 2.0.
  - **Acceptance criteria:**
    - [ ] Security guide published (secrets, least privilege, HTTPS/TLS)
    - [ ] If example exposes MCP: Auth Bridge pattern referenced (LAB2-006)

- [ ] **4.0 Docs review, site & learnings (S3)**
  - **Trigger:** Guides from S1/S2/(S1b)/(S1c) merged to release branch.
  - **Enables:** S4 public surface; discoverable MkDocs + homepage.
  - **Depends on:** Tasks 2.0–3.0; [docs-review-checklist.md](./docs-review-checklist.md).
  - **Acceptance criteria:**
    - [ ] Homepage/docs CTAs route to new guides (LAB2-004)
    - [ ] `mkdocs.yml` includes Adapters + shipped Lab II pages; build/nav clean
    - [ ] Cross-links + taxonomy check done per checklist
    - [ ] LAB2-005 note written (open vs hosted vs enterprise)

- [ ] **5.0 Release (S4)**
  - **Trigger:** S1–S3 DoD green on `release/2.5.3`.
  - **Enables:** v2.5.4 Distribution Loop kickoff.
  - **Depends on:** Tasks 2.0–4.0; [release-checklist.md](./release-checklist.md).
  - **Acceptance criteria:**
    - [ ] Version **2.5.3**, CHANGELOG, migration note
    - [ ] Pre-push CI green (ruff, mypy, pytest ≥85%, pip-audit)
    - [ ] Tag `v2.5.3` + PyPI as applicable
    - [ ] `release/2.5.3` → `main`

## Definition of Done — v2.5.3

- [ ] LAB2-001 — no protocol fork; reuse existing adapter interfaces
- [ ] LAB2-002 — ≥1 workflow/enterprise example shipped
- [ ] LAB2-003 — security guide published
- [ ] LAB2-004 — site/docs routing updated (`mkdocs.yml` + `docs/index.md` + web CTAs)
- [ ] Docs review checklist signed for shipped pages — [docs-review-checklist.md](./docs-review-checklist.md)
- [ ] LAB2-005 — open vs hosted learnings captured
- [ ] LAB2-006 — Auth Bridge referenced if MCP exposed (or N/A documented)
- [ ] Transport growth lint clean across v2.5.3 PRs
- [ ] [release-checklist.md](./release-checklist.md) complete

## Out of scope (defer)

| Item | Where |
|------|--------|
| `@asap-protocol/mcp-auth` | [../v2.5.0/backlog-mcp-auth-typescript.md](../v2.5.0/backlog-mcp-auth-typescript.md) |
| `nemo-agent-toolkit-asap` third-party plugin | Post–v2.5.3 (see research note Path C) |
| Distribution Loop | [prd-v2.5.4-distribution-loop.md](../../../product/prd/prd-v2.5.4-distribution-loop.md) |
| Formal Spec / A2A bridge | [prd-v2.5.5-formal-spec-interop.md](../../../product/prd/prd-v2.5.5-formal-spec-interop.md) |
| G5/G6 governance product | Local `product/strategy/roadmap.md` §4 |

## Relevant files (overview)

### Likely new

- `examples/workflow_asap_connector/` (or `n8n_asap_connector/`) — primary prototype
- `docs/integrations/workflow-connectors.md` (or `n8n.md`) — user guide
- `docs/guides/automation-connector-security.md` — LAB2-003
- `engineering/tasks/v2.5.3/learnings-open-vs-hosted.md` — LAB2-005
- [docs-review-checklist.md](./docs-review-checklist.md) — S3 nav/index/cross-link gate
- Optional: `docs/integrations/semantic-kernel.md` — only if S1b runs
- Optional: `docs/integrations/nemo-agent-toolkit.md` + `examples/nemo_agent_toolkit_asap/` — S1c
- [research-nemo-agent-toolkit.md](./research-nemo-agent-toolkit.md) — upstream map for S1c

### Likely modify

- `mkdocs.yml` — Adapters + Lab II Integrations/Guides (S3; fix pre-existing Adapters gap)
- `apps/web/` — adapter/integration cards or docs links (LAB2-004)
- `docs/index.md`, `README.md`, `CHANGELOG.md`, `docs/migration.md`
- `docs/mcp-integration.md`, `docs/adapters/*` — cross-links (S3)
- `product/checkpoints.md`, `AGENTS.md`, `product/README.md`

### Reference

- `examples/openapi_petstore/` — OpenAPI → capabilities pattern
- `docs/adapters/openapi.md`, `docs/adapters/mcp-auth-bridge.md`
- `docs/integrations/mastra.md`, `docs/integrations/openai-agents.md`
- `engineering/tasks/private/v2.3.1/tasks-v2.3.1-adapter-lab.md` — Lab I sequencing lessons

## Change log

| Date | Change |
|------|--------|
| 2026-07-11 | Initial sprint index from revised PRD (D1–D6); S0–S4 + optional S1b |
| 2026-07-11 | **D7 / S1c**: NeMo Agent Toolkit spike + [research-nemo-agent-toolkit.md](./research-nemo-agent-toolkit.md) |
| 2026-07-12 | **S3 docs review**: [sprint-S3-docs-review.md](./sprint-S3-docs-review.md) + [docs-review-checklist.md](./docs-review-checklist.md); replaces S3 site-learnings-only |
| 2026-07-13 | **S0 Done**: [demand-sheet.md](./demand-sheet.md); D1 workflow primary (no swap); D2 S1b skipped; D7 S1c planned; kickoff ACTIVE |
| 2026-07-13 | **S1 Done**: workflow example + [workflow-connectors.md](../../../docs/integrations/workflow-connectors.md); MkDocs nav deferred to S3 |
