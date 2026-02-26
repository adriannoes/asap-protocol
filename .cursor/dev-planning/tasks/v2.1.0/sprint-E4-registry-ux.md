# Sprint E4: Registry UX (Category/Tags)

> **Goal**: Category/tags in RegistryEntry, Issue template, process_registration, Browse filters, Revoked badge
> **Prerequisite**: Sprint E1 (for revoked_agents.json in Task 4.6)
> **Parent Roadmap**: [tasks-v2.1.0-roadmap.md](./tasks-v2.1.0-roadmap.md)
> **Estimated Duration**: 4–5 days

---

## Relevant Files

- `src/asap/discovery/registry.py` — RegistryEntry (category, tags)
- `scripts/process_registration.py` — Parse category/tags
- `scripts/validate_registry.py` — Schema validation
- `.github/ISSUE_TEMPLATE/register_agent.yml` — Category dropdown, tags input
- `apps/web/src/app/browse/browse-content.tsx` — Filters
- `apps/web/src/lib/registry-schema.ts` — Zod schema
- `apps/web/src/types/registry.d.ts` — TypeScript types
- `apps/web/src/lib/registry.ts` — Fetch revoked_agents.json

---

## Trigger / Enables / Depends on

**Trigger:** User registers agent (IssueOps) or browses Web App.

**Enables:** Better discovery; filtered Browse experience.

**Depends on:** Sprint E1 (for Task 4.6 — revoked_agents.json); existing `RegistryEntry`, `process_registration.py`, Browse page.

---

## Acceptance Criteria

- [ ] `RegistryEntry` has optional `category: str | None` and `tags: list[str]`
- [ ] GitHub register template has category dropdown and tags input
- [ ] `process_registration.py` parses and writes category/tags to registry.json
- [ ] Web App Browse has filter controls for category and tags
- [ ] `validate_registry.py` accepts category/tags in schema
- [ ] Web App: revoked agents show "Revoked" badge and are excluded from Browse (REV-004)

---

## Task 4.1: Extend RegistryEntry with category and tags

- [ ] **4.1.1** Add category and tags fields to RegistryEntry
  - **File**: `src/asap/discovery/registry.py` (modify)
  - **What**: Add `category: str | None = None` and `tags: list[str] = Field(default_factory=list)` to `RegistryEntry`. Add Field descriptions.
  - **Why**: CAT-001 — schema support for categorization.
  - **Verify**: `RegistryEntry.model_validate({"id": "urn:asap:agent:test", "name": "x", "description": "x", "endpoints": {}, "asap_version": "2.0", "category": "Coding", "tags": ["ai"]})` succeeds.

- [ ] **4.1.2** Update generate_registry_entry for category/tags
  - **File**: `src/asap/discovery/registry.py`
  - **What**: Add `category: str | None = None`, `tags: list[str] | None = None` kwargs to `generate_registry_entry()`. Pass to `RegistryEntry()`.
  - **Why**: Scripts and callers can set category/tags.
  - **Verify**: `pytest tests/discovery/test_registry.py` — generate_registry_entry with category/tags produces valid entry.

---

## Task 4.2: Add category and tags to GitHub Issue template

- [ ] **4.2.1** Add category dropdown to register_agent.yml
  - **File**: `.github/ISSUE_TEMPLATE/register_agent.yml` (modify)
  - **What**: Add dropdown `category` with options: Research, Coding, Productivity, Data, Security, Infrastructure, Creative, Finance, Other. Optional. Place after `built_with` or before `repository_url`.
  - **Why**: CAT-002 — registration captures metadata.
  - **Pattern**: Follow existing `built_with` dropdown structure.
  - **Verify**: Manual: create issue from template; category dropdown appears.

- [ ] **4.2.2** Add tags input to register_agent.yml
  - **File**: `.github/ISSUE_TEMPLATE/register_agent.yml`
  - **What**: Add input `tags` (comma-separated). Optional. Description: "Comma-separated tags for discovery (e.g. web_research, summarization)".
  - **Verify**: Manual: tags input appears.

---

## Task 4.3: Parse and write category/tags in process_registration

- [ ] **4.3.1** Add _HEADER_TO_FIELD mapping for Category and Tags
  - **File**: `scripts/process_registration.py` (modify)
  - **What**: In `parse_issue_body` / `_HEADER_TO_FIELD`, add "Category" → "category", "Tags" → "tags". Parse values; tags: split by comma, strip, filter empty.
  - **Why**: CAT-003 — parse from issue body.
  - **Pattern**: Follow existing `### Manifest URL` etc. in `process_registration.py`.
  - **Verify**: Unit test: parse body with ### Category and ### Tags; assert fields extracted.

- [ ] **4.3.2** Pass category/tags to generate_registry_entry and save
  - **File**: `scripts/process_registration.py`
  - **What**: When building RegistryEntry, pass `category` and `tags` from parsed fields. Ensure `save_registry` / `lib/registry_io` writes them to JSON.
  - **Why**: CAT-003 — registry.json populated.
  - **Verify**: `pytest tests/scripts/test_process_registration.py` — body with category/tags produces registry entry with them.

---

## Task 4.4: Add category and tags filters to Web App Browse

- [ ] **4.4.1** Update Zod schema and TypeScript types
  - **File**: `apps/web/src/lib/registry-schema.ts` (modify), `apps/web/src/types/registry.d.ts` (modify)
  - **What**: Add `category?: string` and `tags?: string[]` to registry agent schema. Update RegistryAgent / Manifest types.
  - **Why**: Type-safe category/tags in UI.
  - **Verify**: `npm run build` in apps/web; no type errors.

- [ ] **4.4.2** Add category dropdown filter to Browse sidebar
  - **File**: `apps/web/src/app/browse/browse-content.tsx` (modify)
  - **What**: Extract unique categories from `initialAgents`. Add dropdown (or select) for category. State: `selectedCategory`. Filter `filteredAgents` by `agent.category === selectedCategory` when set.
  - **Why**: CAT-004 — filter by category.
  - **Pattern**: Follow Skills filter; add new section "Category".
  - **Verify**: Manual: select category; agents filter.

- [ ] **4.4.3** Add tags multi-select filter to Browse sidebar
  - **File**: `apps/web/src/app/browse/browse-content.tsx`
  - **What**: Extract unique tags from `initialAgents`. Add badge toggle or multi-select for tags. State: `selectedTags`. Filter by agents whose `tags` includes any selected tag (or all).
  - **Why**: CAT-004 — filter by tags.
  - **Verify**: Manual: select tag; agents filter.

---

## Task 4.5: Update validate_registry for category/tags

- [ ] **4.5.1** Ensure validate_registry accepts category/tags
  - **File**: `scripts/validate_registry.py` (modify if needed)
  - **What**: `RegistryEntry` Pydantic model already has category/tags (Task 4.1). If validate_registry uses raw JSON validation, ensure it accepts these fields. No change needed if it uses `RegistryEntry.model_validate`.
  - **Verify**: `uv run python scripts/validate_registry.py registry.json` passes with category/tags in entries.

---

## Task 4.6: Web App — Revoked badge and exclude from search (REV-004)

- [ ] **4.6.1** Fetch revoked_agents.json in registry layer
  - **File**: `apps/web/src/lib/registry.ts` (modify)
  - **What**: Add `fetchRevokedUrns()` or merge revoked fetch into `fetchRegistry()`. Fetch from `REVOKED_URL` or GitHub raw `revoked_agents.json`. Return set of revoked URNs. Cache with same revalidate as registry (or shorter).
  - **Why**: REV-004 — need revoked list for filtering.
  - **Integration**: Consumes `revoked_agents.json` from Sprint E1.
  - **Verify**: Unit test or manual: fetch returns revoked URNs.

- [ ] **4.6.2** Filter revoked agents from Browse results
  - **File**: `apps/web/src/app/browse/page.tsx` (modify), `apps/web/src/app/browse/browse-content.tsx` (modify)
  - **What**: Pass `revokedUrns` to BrowseContent (or fetch in page, pass as prop). In `filteredAgents`, exclude agents whose `id` is in `revokedUrns`.
  - **Why**: REV-004 — revoked excluded from search.
  - **Verify**: Manual: add URN to revoked_agents.json; Browse excludes that agent.

- [ ] **4.6.3** Show Revoked badge on agent detail page
  - **File**: `apps/web/src/app/agents/[id]/` (modify — page.tsx and/or agent-detail-client.tsx)
  - **What**: Fetch revoked list (or pass from page). If agent URN in revoked list, show "Revoked" badge (red/warning style) next to agent name.
  - **Why**: REV-004 — users see revocation status.
  - **Verify**: Manual: agent in revoked list shows Revoked badge on detail page.

---

## Definition of Done

- [ ] Browse filterable by category and tags
- [ ] Revoked agents excluded from Browse; Revoked badge on detail page
- [ ] `validate_registry.py` passes with category/tags
- [ ] `npm run build` in apps/web succeeds
