# Code Review: PR #75 — feat(E4): Registry UX

> **Branch:** `feat/sprint-e4-registry-ux` → `main`
> **Sprint:** [sprint-E4-registry-ux.md](file:///Users/adrianno/GitHub/asap-protocol/.cursor/dev-planning/tasks/v2.1.0/sprint-E4-registry-ux.md)
> **Reviewed:** 2026-02-28

---

## ✅ Feedback Addressed (2026-02-28)

All required fixes (§2) and recommended items (§3–§4) have been addressed:

- **§2.1** — Agent detail: null guard first; `Promise.all` for `fetchAgentById` + `fetchRevokedUrns`.
- **§2.2** — Python tests for `category`/`tags` in `test_registry.py` and `test_process_registration.py` (incl. `test_valid_issue_with_category_tags_writes_registry_entry`).
- **§2.3** — CSP: `unsafe-eval` only in dev (conditional in `next.config.ts`).
- **§3** — Browse uses Shadcn `<Select>`; LlamaIndex and SmolAgents tabs in `usage-snippets.tsx`; `fetchRevokedUrns` with Zod (`RevokedResponseSchema`); `RegistryEntry` with `normalize_category`.
- **§4** — Parallel fetch in Browse page (`Promise.all`); parallel fetch in Agent Detail page; `UsageSnippets` extracted to `usage-snippets.tsx`; `fetchRevokedUrns` uses Zod-parsed type (`RevokedResponseSchema`), no cast.

Verification: `pytest` (39 passed) and `npm run build` completed successfully.

---

## 1. Executive Summary

| Category | Status | Summary |
| :--- | :--- | :--- |
| **Tech Stack** | ⚠️ | CSP header includes `unsafe-eval`; raw `<select>` used instead of Shadcn Select |
| **Architecture** | ✅ | Clean separation — RSC fetches data, client component handles filters |
| **Security** | ⚠️ | `unsafe-eval` in CSP weakens XSS mitigation; `fetchRevokedUrns` trusts JSON shape |
| **Tests** | ⚠️ | Zero test coverage for new `category`/`tags` fields in both Python and frontend |

> **General Feedback:** Solid PR overall — the Browse filters, revoked badge, and usage snippets all align well with Sprint E4 tasks. The main blockers are a logic bug in agent detail (revoked check before null guard), missing test coverage for the new schema fields, and a CSP that permits `unsafe-eval`. These should be addressed before merge.

---

## 2. Required Fixes (Must Address Before Merge)

### 2.1 Race Condition: Revoked Check Before Null Guard

*   **Location:** `apps/web/src/app/agents/[id]/page.tsx:42-44`
*   **Problem:** `fetchRevokedUrns()` is called and `isRevoked` is computed using `agent?.id` **before** the `if (!agent)` guard. If agent is `null`, `revokedUrns.has('')` is evaluated (always `false`), which is wasteful. More critically, if `fetchRevokedUrns()` throws, the page will error out instead of showing the 404.
*   **Rationale:** The null guard should be the first thing checked. `fetchRevokedUrns()` is a network call — performing it for a non-existent agent wastes resources and introduces a failure point before the graceful 404.
*   **Fix Suggestion:**
    ```typescript
    export default async function AgentDetailPage({ params }: Props) {
        const p = await params;
        const decodedId = decodeURIComponent(p.id);
        const agent = await fetchAgentById(decodedId);

        if (!agent) {
            return notFound();
        }

        const revokedUrns = await fetchRevokedUrns();
        const isRevoked = revokedUrns.has(agent.id || '');

        return (
            <div className="container mx-auto py-10 px-4 max-w-5xl">
                <AgentDetailClient agent={agent} isRevoked={isRevoked} />
            </div>
        );
    }
    ```

---

### 2.2 Zero Test Coverage for `category` / `tags`

*   **Location:** `tests/discovery/test_registry.py`, `tests/scripts/test_process_registration.py`
*   **Problem:** Neither test file contains any assertions for the new `category` or `tags` fields. The sprint acceptance criteria explicitly states: _"Unit test: parse body with ### Category and ### Tags; assert fields extracted."_ and _"`generate_registry_entry` with category/tags produces valid entry"_.
*   **Rationale:** These are schema-level additions that affect the registry format consumed by every downstream component (Web App, SDK, validate_registry). Untested schema fields are a regression waiting to happen.
*   **Fix Suggestion:** Add tests for:
    ```python
    # tests/discovery/test_registry.py
    def test_registry_entry_with_category_tags():
        entry = RegistryEntry.model_validate({
            "id": "urn:asap:agent:test:bot",
            "name": "Test",
            "description": "x",
            "endpoints": {"http": "https://example.com"},
            "asap_version": "2.0",
            "category": "Coding",
            "tags": ["ai", "code_review"],
        })
        assert entry.category == "Coding"
        assert entry.tags == ["ai", "code_review"]

    def test_registry_entry_defaults_without_category_tags():
        entry = RegistryEntry.model_validate({
            "id": "urn:asap:agent:test:bot",
            "name": "Test",
            "description": "x",
            "endpoints": {"http": "https://example.com"},
            "asap_version": "2.0",
        })
        assert entry.category is None
        assert entry.tags == []

    # tests/scripts/test_process_registration.py
    def test_parse_body_with_category_and_tags():
        body = "### Category\n\nCoding\n\n### Tags\n\nai, code_review, testing"
        parsed = parse_issue_body(body)
        assert parsed["category"] == "Coding"
        assert parsed["tags"] == "ai, code_review, testing"
    ```

---

### 2.3 CSP: `unsafe-eval` Should Be Removed

*   **Location:** `apps/web/next.config.ts` — CSP header
*   **Problem:** The `script-src` directive includes `'unsafe-eval'`, which significantly weakens XSS protection. This likely was added to avoid Next.js dev tooling errors, but it **must not** ship to production.
*   **Rationale:** `unsafe-eval` allows `eval()` and `Function()` calls, which is the primary vector for reflected XSS attacks. The ASAP Protocol marketplace handles agent URNs in URLs and query parameters — this is a real attack surface.
*   **Fix Suggestion:**
    ```typescript
    // next.config.ts — Remove 'unsafe-eval' from script-src
    {
        key: "Content-Security-Policy",
        value: "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' blob: data: https:; font-src 'self' data:; connect-src 'self' https://raw.githubusercontent.com;",
    }
    ```
    If Next.js requires `unsafe-eval` in dev mode only, conditionally apply it:
    ```typescript
    const isDev = process.env.NODE_ENV === 'development';
    const scriptSrc = isDev
        ? "'self' 'unsafe-eval' 'unsafe-inline'"
        : "'self' 'unsafe-inline'";
    ```

---

## 3. Tech-Specific Bug Hunt (Deep Dive)

### Next.js 15 / React 19

- [ ] **Raw `<select>` instead of Shadcn Select:** `browse-content.tsx` uses a native `<select>` for Category filter. Per tech-stack-decisions §4.3, the UI must use Shadcn/UI components. Replace with `<Select>` from `@/components/ui/select`.

- [ ] **Missing `SmolAgents` and `LlamaIndex` tabs:** The sprint task (4.7.1) specifies 6 framework snippets: SDK, LangChain, LlamaIndex, CrewAI, SmolAgents, MCP. The PR only includes 5 tabs (Node.js, LangChain, CrewAI, PydanticAI, MCP). `LlamaIndex` and `SmolAgents` are missing; `PydanticAI` was added instead. Either update the task or add the missing tabs.

- [ ] **`fetchRevokedUrns` trusts JSON shape without validation:** In `registry.ts`, `data.revoked` is accessed directly and `.map((entry: { urn: string }) => entry.urn)` is applied without any Zod validation. If the JSON shape changes or is malformed, this silently produces `undefined` entries in the Set.
    ```typescript
    // Suggested: Add a minimal Zod schema
    const RevokedSchema = z.object({
        revoked: z.array(z.object({ urn: z.string() })).default([]),
    });
    const parsed = RevokedSchema.safeParse(data);
    const urns = parsed.success ? parsed.data.revoked.map(e => e.urn) : [];
    ```

### FastAPI & Pydantic v2

- [ ] **No `category` validation constraints:** `RegistryEntry.category` is `str | None` with no `Literal` type or enum constraint. The GitHub issue template has a fixed list (Research, Coding, Productivity, etc.), but the Pydantic model accepts any string. This could lead to data inconsistency (e.g., "coding" vs "Coding" vs "CODING"). Consider adding a `field_validator` to normalize or a `Literal` type.

---

## 4. Improvements & Refactoring (Highly Recommended)

- [x] **Optimization — Parallel fetch in Browse page:** In `browse/page.tsx`, `fetchRegistry()` and `fetchRevokedUrns()` are called sequentially. They are independent — use `Promise.all` for a ~50% latency reduction:
    ```typescript
    const [allAgents, revokedUrns] = await Promise.all([
        fetchRegistry(),
        fetchRevokedUrns(),
    ]);
    ```

- [x] **Optimization — Parallel fetch in Agent Detail page:** Same pattern applies in `agents/[id]/page.tsx` — after fixing issue 2.1, the `fetchAgentById` and `fetchRevokedUrns` could be parallelized:
    ```typescript
    const [agent, revokedUrns] = await Promise.all([
        fetchAgentById(decodedId),
        fetchRevokedUrns(),
    ]);
    if (!agent) return notFound();
    const isRevoked = revokedUrns.has(agent.id || '');
    ```

- [x] **Readability — Extract Usage Snippets to separate component:** `agent-detail-client.tsx` grew by 108 lines (mostly JSX for usage snippets). Extract into a dedicated `<UsageSnippets agentId={agent.id} skills={...} />` component for better maintainability. This also aligns with the sprint task (4.7.1: _"or new component `usage-snippets.tsx`"_).

- [x] **Typing — `fetchRevokedUrns` return type annotation:** The function returns `Promise<Set<string>>` which is good, but the internal cast `(entry: { urn: string })` should be a proper Zod-parsed type (see §3 above).

---

## 5. Verification Steps

After addressing the fixes above, verify with:

```bash
# Python tests (new category/tags coverage)
uv run pytest tests/discovery/test_registry.py tests/scripts/test_process_registration.py -v

# Full Python suite
uv run pytest --tb=short

# Type checking
uv run mypy src/ scripts/ tests/

# Frontend build (catches TypeScript errors)
cd apps/web && npm run build

# Frontend lint
cd apps/web && npm run lint

# Manual: Browse page → Category filter renders Shadcn Select
# Manual: Agent detail → All 6 framework tabs present
# Manual: Agent in revoked_agents.json → shows red "Revoked" badge
# Manual: Revoked agent excluded from Browse results
```
