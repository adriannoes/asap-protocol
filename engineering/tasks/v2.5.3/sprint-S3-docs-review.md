# Sprint S3: Docs review, site routing & learnings (v2.5.3)

**PRD**: LAB2-004, LAB2-005 (+ docs completeness for LAB2-002/003/006)  
**Branch**: `feat/v2.5.3-s2-s3-docs-review` → **`release/2.5.3`**  
**Depends on**: S1 + S2 guides merged (or co-landing); S1b/S1c pages if those sprints shipped  
**Checklist**: [docs-review-checklist.md](./docs-review-checklist.md)

**Trigger:** Lab II content pages exist (workflow + security at minimum).  
**Enables:** Discoverable public docs; S4 release surface.  
**Depends on:** Stable paths from S1/S2/(S1b)/(S1c).

---

## Goal

Run a **full docs surface review** for Adapter Lab II: wire new pages into MkDocs + `docs/index.md`, fix stale nav (Adapters missing today), cross-link MCP/OpenAPI/integrations, update web CTAs (LAB2-004), and capture open-vs-hosted learnings (LAB2-005).

This sprint is **documentation & discoverability**, not new product features. Distribution Loop hero rewrite stays in v2.5.4.

---

## Tasks

- [x] **4.0 Inventory**
  - [x] Open [docs-review-checklist.md](./docs-review-checklist.md) and mark which new pages actually shipped (S1/S1b/S1c/S2)
  - [x] Note any path renames (e.g. `n8n.md` vs `workflow-connectors.md`; S1b is `microsoft-agent-framework.md` not `semantic-kernel.md`) before editing nav

- [x] **4.1 MkDocs nav (`mkdocs.yml`)**
  - [x] Add **Adapters** entries: OpenAPI, MCP Auth Bridge (fix pre-Lab-II gap)
  - [x] Add Lab II **Integrations** + **Guides** entries for pages that exist
  - [x] Run MkDocs build (strict if available); fix broken nav targets
    - Lab II + Adapters nav OK; `mkdocs build` succeeds; `--strict` fails on **pre-existing** missing `api/*` / `contributing.md` nav entries + out-of-tree link warnings

- [x] **4.2 Docs home & cross-links**
  - [x] Update `docs/index.md` Documentation / Features lists for new pages
  - [x] Cross-link pass per checklist §4 (`mcp-integration.md`, `adapters/*`, sibling integrations, `security.md` as needed)
  - [x] Stub or draft `docs/migration.md` “Upgrading from v2.5.2” (S4 finalizes version date)

- [x] **4.3 Taxonomy check**
  - [x] Confirm adapters vs integrations vs guides split (checklist §5)
  - [x] Experimental banners on NAT / MAF research pages (kept; files not moved)

- [x] **4.4 Homepage / web (LAB2-004)**
  - [x] Cards or links in `apps/web/` for shipped Lab II guides
  - [x] CTA / telemetry ids if new doc links are added
  - [x] No hero / GTM rewrite (v2.5.4)

- [x] **4.5 Learnings note (LAB2-005)**
  - [x] Write `engineering/tasks/v2.5.3/learnings-open-vs-hosted.md`
  - [x] Include NAT lesson if S1c ran: open guide vs hosted control-plane vs third-party `nemo-agent-toolkit-*` plugin later
  - [x] Optional one-line pointer from local `product/strategy/roadmap.md`

- [x] **4.6 Demand signal snapshot**
  - [x] Update demand sheet with post-S1 asks (does not block ship)

- [x] **4.7 Checklist sign-off**
  - [x] Complete [docs-review-checklist.md](./docs-review-checklist.md) §§1–7 for shipped docs scope
  - [x] Leave §8 S4 version-string sign-off for release sprint

---

## Acceptance criteria

- [x] LAB2-004: site + docs route to new guides
- [x] LAB2-005: learnings file exists and is referenced from the roadmap DoD *(file exists; strategy roadmap pointer added locally)*
- [x] `mkdocs.yml` lists Adapters (OpenAPI, MCP Auth Bridge) and all shipped Lab II pages
- [x] Docs checklist completed for shipped pages (no broken nav) — §§1–7; §8 left for S4
- [x] No Distribution Loop scope creep

## Reviews

| Date | Tier | Verdict | Report |
|------|------|---------|--------|
| 2026-07-14 | T2 | Approved (attempt 2) | [review-v2.5.3-S2-S3-docs-review-20260714-r2.md](../../code-review/private/review-v2.5.3-S2-S3-docs-review-20260714-r2.md) |
| 2026-07-14 | T2 | Rejected (attempt 1) | [review-v2.5.3-S2-S3-docs-review-20260714.md](../../code-review/private/review-v2.5.3-S2-S3-docs-review-20260714.md) |

## Relevant files

### Modify

- `mkdocs.yml`
- `docs/index.md`
- `docs/mcp-integration.md`, `docs/adapters/openapi.md`, `docs/adapters/mcp-auth-bridge.md` (cross-links)
- `docs/migration.md` (stub/section)
- `docs/security.md` / `docs/troubleshooting.md`
- `docs/integrations/mastra.md`, `docs/integrations/openai-agents.md` (sibling Lab II footers)
- `README.md` (Framework Ecosystem pointers)
- [docs-review-checklist.md](./docs-review-checklist.md)
- [demand-sheet.md](./demand-sheet.md)
- `apps/web/` (CTAs / cards) — **task 4.4 only**

### New

- `engineering/tasks/v2.5.3/learnings-open-vs-hosted.md`

### Reference (produced earlier)

- `docs/integrations/workflow-connectors.md`
- `docs/guides/automation-connector-security.md`
- `docs/integrations/nemo-agent-toolkit.md` (S1c)
- `docs/integrations/microsoft-agent-framework.md` (S1b; not `semantic-kernel.md`)
- `examples/workflow_asap_connector/`, `examples/nemo_agent_toolkit_asap/`
