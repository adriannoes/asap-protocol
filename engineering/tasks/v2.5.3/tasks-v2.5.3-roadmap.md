# Tasks: v2.5.3 Adapter Lab II — Sprint Index

**Status: MERGE-READY (pending tag/publish)** — `release/2.5.3` on origin; S0–S3 Done; S4 content/CI green. Public install remains **`asap-protocol==2.5.2`** on PyPI until sequence **merge → tag → publish → handoff** completes. Demand sheet: [demand-sheet.md](./demand-sheet.md).

Based on [PRD v2.5.3 Adapter Lab II](../../../product/prd/prd-v2.5.3-adapter-lab-ii.md). Each sprint merges into **`release/2.5.3`** (see [BRANCHING.md](./BRANCHING.md)); merge to `main` only after S4 content gates, then tag/publish.

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
| **S1b** | [Conditional SK / .NET spike](./sprint-S1b-semantic-kernel.md) | D2 | P0 if gate | Done (guide-only; 2b.3 skipped) |
| **S1c** | [NeMo Agent Toolkit spike](./sprint-S1c-nemo-agent-toolkit.md) | D7 | P0 planned | Done |
| **S2** | [Security guide & MCP patterns](./sprint-S2-security-docs.md) | LAB2-003, LAB2-006 | P0 | Done |
| **S3** | [Docs review, site routing & learnings](./sprint-S3-docs-review.md) | LAB2-004, LAB2-005 + docs surface | P0 | Done |
| **S4** | [Release v2.5.3](./sprint-S4-release.md) | DoD, metrics | P0 | Merge-ready · pending tag/publish |

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

S1b / S1c never block S1/S2/S3/S4. S0 D2 was **no-go** on demand; **maintainer override (2026-07-13)** reopened S1b (guide-only). S1c defaults to **go** (D7); skip only with explicit maintainer no-go in the demand sheet. Combined spike branch: `feat/v2.5.3-s1b-s1c-spikes`.

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

- [x] **2b.0 Conditional Semantic Kernel spike (S1b)**
  - **Trigger:** S0 D2 was no-go on demand; **maintainer override (2026-07-13)** reopened S1b for a research/experimental guide.
  - **Enables:** Optional second public guide; does not block release if incomplete.
  - **Depends on:** Task 1.0; [demand-sheet.md](./demand-sheet.md) override; [research-semantic-kernel.md](./research-semantic-kernel.md).
  - **Acceptance criteria:**
    - [x] Interop note + .NET/guide path documented (`docs/integrations/microsoft-agent-framework.md`)
    - [x] Explicit “maintained vs research” status in the guide
  - **Note:** 2b.3 C# sample **skipped / N/A** (guide-only per 2b.1). MkDocs nav/index deferred to S3.

- [x] **2c.0 NeMo Agent Toolkit spike (S1c)**
  - **Trigger:** S0 D7 default go (or explicit no-go skip).
  - **Enables:** NVIDIA-stack guide + optional MCP bridge demo; feeds v2.5.5 Agent Card mapping.
  - **Depends on:** Task 1.0; [research-nemo-agent-toolkit.md](./research-nemo-agent-toolkit.md).
  - **Acceptance criteria:**
    - [x] Research pin refreshed; auth/transport gap tables written
    - [x] `docs/integrations/nemo-agent-toolkit.md` published (honest limits)
    - [x] Path A demo **or** documented blocker + follow-up (no fake native claim)
    - [x] Third-party NAT plugin deferred (Path C)

- [x] **3.0 Security & MCP docs (S2)**
  - **Trigger:** S1 example shape known.
  - **Enables:** Safe public adoption; S4 DoD for LAB2-003/006.
  - **Depends on:** Task 2.0.
  - **Acceptance criteria:**
    - [x] Security guide published (secrets, least privilege, HTTPS/TLS)
    - [x] If example exposes MCP: Auth Bridge pattern referenced (LAB2-006) — workflow OpenAPI-only N/A; NeMo Path A Mode A documented

- [x] **4.0 Docs review, site & learnings (S3)**
  - **Trigger:** Guides from S1/S2/(S1b)/(S1c) merged to release branch.
  - **Enables:** S4 public surface; discoverable MkDocs + homepage.
  - **Depends on:** Tasks 2.0–3.0; [docs-review-checklist.md](./docs-review-checklist.md).
  - **Acceptance criteria:**
    - [x] Homepage/docs CTAs route to new guides (LAB2-004)
    - [x] `mkdocs.yml` includes Adapters + shipped Lab II pages; build/nav clean
    - [x] Cross-links + taxonomy check done per checklist
    - [x] LAB2-005 note written (open vs hosted vs enterprise)

- [x] **5.0 Release (S4)**
  - **Trigger:** S1–S3 DoD green on `release/2.5.3`.
  - **Enables:** v2.5.4 Distribution Loop kickoff.
  - **Depends on:** Tasks 2.0–4.0; [release-checklist.md](./release-checklist.md).
  - **Sequence:** **merge → tag → publish → handoff** (do not mark SHIPPED before publish).
  - **Acceptance criteria:**
    - [x] Version **2.5.3**, CHANGELOG, migration note
    - [x] Pre-push CI green (ruff, mypy, pytest ≥85%, pip-audit)
    - [x] Public copy: PyPI **2.5.2** available; **2.5.3** pending tag/publish
    - [ ] Merge `release/2.5.3` → `main`
    - [ ] Tag `v2.5.3` + PyPI / Docker / GitHub Release green
    - [ ] Post-publish swap pending → shipped ([release-checklist §6](./release-checklist.md#60-post-publish-swap-pending--shipped))
    - [ ] Handoff to v2.5.4

## Definition of Done — v2.5.3

- [x] LAB2-001 — no protocol fork; reuse existing adapter interfaces
- [x] LAB2-002 — ≥1 workflow/enterprise example shipped
- [x] LAB2-003 — security guide published
- [x] LAB2-004 — site/docs routing updated (`mkdocs.yml` + `docs/index.md` + web CTAs)
- [x] Docs review checklist signed for shipped pages — [docs-review-checklist.md](./docs-review-checklist.md) (§§1–8)
- [x] LAB2-005 — open vs hosted learnings captured
- [x] LAB2-006 — Auth Bridge referenced if MCP exposed (or N/A documented)
- [x] Transport growth lint clean across v2.5.3 PRs
- [x] [release-checklist.md](./release-checklist.md) §§1–3 signed (S4 content + CI); §§4–6 merge/tag/publish/handoff pending

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
- Optional: `docs/integrations/microsoft-agent-framework.md` — S1b (guide-only; see research note)
- Optional: `docs/integrations/nemo-agent-toolkit.md` + `examples/nemo_agent_toolkit_asap/` — S1c
- [research-nemo-agent-toolkit.md](./research-nemo-agent-toolkit.md) — upstream map for S1c
- [research-semantic-kernel.md](./research-semantic-kernel.md) — S1b naming + guide-only lock

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
| 2026-07-13 | **S1b Done**: MAF guide-only ([microsoft-agent-framework.md](../../../docs/integrations/microsoft-agent-framework.md)); 2b.3 C# sample skipped/N/A |
| 2026-07-13 | **S1c Done**: Path A example + [nemo-agent-toolkit.md](../../../docs/integrations/nemo-agent-toolkit.md); Path C out of ship; NAT optional in CI |
| 2026-07-14 | **S2+S3 Done**: security guide + MCP N/A/Path A docs; MkDocs/nav/web CTAs; learnings note; docs checklist §§1–7 signed (T2 review blockers pending re-review) |
| 2026-07-14 | **S4 merge-ready**: public copy pending tag/publish; sequence merge → tag → publish → handoff; do not mark SHIPPED until PyPI/Docker/Release green |
