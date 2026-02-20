# Sprint M2: Web App Features

> **Goal**: Registry browser and developer dashboard
> **Prerequisites**: Sprint M1 completed (Web App Foundation)
> **Parent Roadmap**: [tasks-v2.0.0-roadmap.md](./tasks-v2.0.0-roadmap.md)

---

## Pre-M2 Validation ✅ Complete (2026-02-19)

All validation steps passed. Ready to start Sprint M2.

| Check | Status |
|-------|--------|
| Registry fetch | ✅ `registry.json` at repo root, fetchable |
| GitHub PR flow | ✅ Fork → Branch → File → PR (sha fix in script) |
| OAuth token in JWT | ✅ `auth.ts` stores `access_token`; `/api/debug/token` verified |

**Guide**: [pre-M2-validation-guide.md](./pre-M2-validation-guide.md)

---

## Relevant Files

- `apps/web/app/browse/page.tsx` - Browse page
- `apps/web/app/agents/[id]/page.tsx` - Agent detail page
- `apps/web/app/dashboard/page.tsx` - Developer dashboard
- `apps/web/app/dashboard/register/page.tsx` - Register agent flow

---

## Context

This sprint adds the core features: browsing agents, viewing agent details, and the developer dashboard.

---

## Task 2.1: Registry Browser

### Sub-tasks

- [x] 4.1.1 /browse page layout
  - **Strategy**: Incremental Static Regeneration (ISR) with `revalidate: 60`
  - **Data Source**: `lib/registry.ts` fetches `registry.json` from `NEXT_PUBLIC_REGISTRY_URL` (default: `adriannoes/asap-protocol/main`)

- [x] 4.1.2 Search input
  - Client-side filtering of the JSON list (registry is small < 1MB)
  - Debounced search (300ms)

- [x] 4.1.3 Skill filters
  - Extract unique skills from `registry.json`
  - Multi-select checkbox/badges

- [x] 4.1.4 Trust level filters

- [x] 4.1.5 Agent cards grid

- [x] 4.1.7 Commit Browser
  - **Command**: `git commit -m "feat(web): implement registry browser and filters"`

---

## Task 2.2: Agent Detail Page

### Sub-tasks

- [x] 4.2.1 `/agents/[id]` route
  - Create dynamic route using App Router (`app/agents/[id]/page.tsx`)
  - Server-side data fetching (`fetchAgentById`)
  - Use ISR (`revalidate: 60`)
  - Back to browse navigation link

- [x] 4.2.2 Manifest display
  - Parse and display the agent's `manifest.json` data visually.
  - Show name, version, ID, description.
  - Explicitly list supported schemas, protocol compatibility (`capabilities.asap_version`), skills.
  - Streaming and state persistence badges.

- [x] 4.2.3 SLA section
  - Dedicated section demonstrating the agent's `SLADefinition`.
  - Include availability, latency (P95), and error rate promises.

- [x] 4.2.4 Reputation and reviews
  - *Note: Leave placeholder for future implementation as detailed in the PRD.*
  - Just UI elements indicating future "Trust Score."

- [x] 4.2.5 "Connect" CTA
  - Button to connect to the agent
  - Display the `asap` protocol endpoint clearly for developer reference (`endpoints.asap`)
  - **Note**: Client-side fetch. Agents *must* support CORS or will show as unreachable.

- [x] 4.2.6 Commit Agent Detail
  - **Command**: `git commit -m "feat(web): implement agent detail page"`

---

## Task 2.3: Developer Dashboard

### Sub-tasks

- [x] 4.3.1 /dashboard layout

- [x] 4.3.2 My agents list

- [x] 4.3.3 Agent status (online/offline)
  - **Note**: Client-side fetch. Agents *must* support CORS or will show as unreachable.

- [x] 4.3.4 Usage metrics

- [x] 4.3.5 API keys management

- [x] 4.3.6 Commit Dashboard
  - **Command**: `git commit -m "feat(web): implement developer dashboard structure"`

---

## Task 2.4: Register Agent Flow (ADR-18)

### Sub-tasks

- [x] 2.4.1 /dashboard/register page
  - **Form**: Name, Description, HTTP/WS endpoints, Manifest URL, Skills (tags)
  - **Auth**: Require GitHub Login (from Task 1.3)

- [x] 2.4.2 Validation Logic
  - **Library**: `zod` + `react-hook-form`
  - **Schema**:
    ```typescript
    z.object({
      name: z.string().min(3).max(50).regex(/^[a-z0-9-]+$/), // Slug friendly
      description: z.string().min(10).max(200),
      manifest_url: z.string().url(),
      endpoints: z.object({ http: z.string().url(), ws: z.string().url().optional() }),
      skills: z.array(z.string()).min(1)
    })
    ```
  - **Reachability**: SSR/Server Action to fetch manifest URL and validate headers/CORS
  - **Security**: Verify Manifest Ed25519 Signature (prevent impersonation)
  - **Security**: Check `ttl_seconds` is valid

- [x] 2.4.3 GitHub Automation (ADR-18)
  - **Library**: `octokit` (SDK)
  - **Token**: Use `getToken()` in Server Action; pass `accessToken` to Octokit
  - **Flow** (validated in pre-M2; see `validate-github-pr-flow.mjs`):
    1. **Fork**: `createFork({ owner, repo })` — use `GITHUB_REGISTRY_OWNER/REPO` env (default: `adriannoes/asap-protocol`)
    2. **Branch**: `createRef(...)` -> `refs/heads/register/<agent>`
    3. **File**: `createOrUpdateFileContents(...)` -> `registry.json` — **must pass `sha`** when updating existing file
    4. **PR**: `pulls.create(...)` — Title: "Register Agent: <name>", Body: "Automated registration via Marketplace."

- [x] 2.4.4 Dashboard Status Updates
  - **Poll**: `SWR` or `React Query` to poll `/api/github/pr-status`
  - **Display**: Badge (Yellow: Pending, Red: Changes Requested, Green: Merged)
  - **Admin Context**: Link to PR for user to see comments.

- [x] 2.4.5 Commit Registration
  - **Command**: `git commit -m "feat(web): implement agent registration flow"`

**Acceptance Criteria**:
- [x] Developer can register agent via form
- [x] Automated PR created on GitHub
- [x] Dashboard reflects PR status

---

## Sprint M2 Definition of Done

- [x] Web app builds (`npm run build`) without Next.js errors.
- [x] User can browse the registry with filters working (client-side).
- [x] User can view detailed Agent Information (Server-Rendered).
- [x] User can log in via GitHub (OAuth).
- [x] User can see a dashboard with their agents (filtered by username for MVP).
- [x] User can submit a new Agent via a form -> creates a GitHub PR.in [v2.0.0 Roadmap](./tasks-v2.0.0-roadmap.md)

**Total Sub-tasks**: ~20

## Documentation Updates
- [ ] **Update Roadmap**: Mark completed items in [v2.0.0 Roadmap](./tasks-v2.0.0-roadmap.md)
