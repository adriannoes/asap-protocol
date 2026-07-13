# Sprint S3: Docs review, site routing & learnings (v2.5.3)

**PRD**: LAB2-004, LAB2-005 (+ docs completeness for LAB2-002/003/006)  
**Branch**: `feat/v2.5.3-s3-docs-review` → **`release/2.5.3`**  
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

- [ ] **4.0 Inventory**
  - [ ] Open [docs-review-checklist.md](./docs-review-checklist.md) and mark which new pages actually shipped (S1/S1b/S1c/S2)
  - [ ] Note any path renames (e.g. `n8n.md` vs `workflow-connectors.md`) before editing nav

- [ ] **4.1 MkDocs nav (`mkdocs.yml`)**
  - [ ] Add **Adapters** entries: OpenAPI, MCP Auth Bridge (fix pre-Lab-II gap)
  - [ ] Add Lab II **Integrations** + **Guides** entries for pages that exist
  - [ ] Run MkDocs build (strict if available); fix broken nav targets

- [ ] **4.2 Docs home & cross-links**
  - [ ] Update `docs/index.md` Documentation / Features lists for new pages
  - [ ] Cross-link pass per checklist §4 (`mcp-integration.md`, `adapters/*`, sibling integrations, `security.md` as needed)
  - [ ] Stub or draft `docs/migration.md` “Upgrading from v2.5.2” (S4 finalizes version date)

- [ ] **4.3 Taxonomy check**
  - [ ] Confirm adapters vs integrations vs guides split (checklist §5)
  - [ ] Experimental banners on NAT / SK research pages

- [ ] **4.4 Homepage / web (LAB2-004)**
  - [ ] Cards or links in `apps/web/` for shipped Lab II guides
  - [ ] CTA / telemetry ids if new doc links are added
  - [ ] No hero / GTM rewrite (v2.5.4)

- [ ] **4.5 Learnings note (LAB2-005)**
  - [ ] Write `engineering/tasks/v2.5.3/learnings-open-vs-hosted.md`
  - [ ] Include NAT lesson if S1c ran: open guide vs hosted control-plane vs third-party `nemo-agent-toolkit-*` plugin later
  - [ ] Optional one-line pointer from local `product/strategy/roadmap.md`

- [ ] **4.6 Demand signal snapshot**
  - [ ] Update demand sheet with post-S1 asks (does not block ship)

- [ ] **4.7 Checklist sign-off**
  - [ ] Complete [docs-review-checklist.md](./docs-review-checklist.md) §§1–7 for shipped scope
  - [ ] Leave §8 S4 version-string sign-off for release sprint

---

## Acceptance criteria

- [ ] LAB2-004: site + docs route to new guides
- [ ] LAB2-005: learnings file exists and is referenced from the roadmap DoD
- [ ] `mkdocs.yml` lists Adapters (OpenAPI, MCP Auth Bridge) and all shipped Lab II pages
- [ ] Docs checklist completed for shipped pages (no broken nav)
- [ ] No Distribution Loop scope creep

## Relevant files

### Modify

- `mkdocs.yml`
- `docs/index.md`
- `docs/mcp-integration.md`, `docs/adapters/openapi.md`, `docs/adapters/mcp-auth-bridge.md` (cross-links)
- `docs/migration.md` (stub/section)
- `docs/security.md` / `docs/troubleshooting.md` (as needed)
- `apps/web/` (CTAs / cards)
- [docs-review-checklist.md](./docs-review-checklist.md)

### New

- `engineering/tasks/v2.5.3/learnings-open-vs-hosted.md`

### Reference (produced earlier)

- `docs/integrations/workflow-connectors.md`
- `docs/guides/automation-connector-security.md`
- `docs/integrations/nemo-agent-toolkit.md` (if S1c)
- `docs/integrations/semantic-kernel.md` (if S1b)
