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

- [ ] 4.1.7 Commit Browser
  - **Command**: `git commit -m "feat(web): implement registry browser and filters"`

---

## Task 2.2: Agent Detail Page

### Sub-tasks

- [ ] 4.2.1 /agents/[id] route

- [ ] 4.2.2 Manifest display

- [ ] 4.2.3 SLA section

- [ ] 4.2.4 Reputation and reviews

- [ ] 4.2.5 "Connect" CTA

- [ ] 4.2.6 Commit Agent Detail
  - **Command**: `git commit -m "feat(web): implement agent detail page"`

---

## Task 2.3: Developer Dashboard

### Sub-tasks

- [ ] 4.3.1 /dashboard layout

- [ ] 4.3.2 My agents list

- [ ] 4.3.3 Agent status (online/offline)
  - **Note**: Client-side fetch. Agents *must* support CORS or will show as unreachable.

- [ ] 4.3.4 Usage metrics

- [ ] 4.3.5 API keys management

- [ ] 4.3.6 Commit Dashboard
  - **Command**: `git commit -m "feat(web): implement developer dashboard structure"`

---

## Task 2.4: Register Agent Flow (ADR-18)

### Sub-tasks

- [ ] 2.4.1 /dashboard/register page
  - **Form**: Name, Description, HTTP/WS endpoints, Manifest URL, Skills (tags)
  - **Auth**: Require GitHub Login (from Task 1.3)

- [ ] 2.4.2 Validation Logic
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

- [ ] 2.4.3 GitHub Automation (ADR-18)
  - **Library**: `octokit` (SDK)
  - **Token**: Use `getToken()` in Server Action; pass `accessToken` to Octokit
  - **Flow** (validated in pre-M2; see `validate-github-pr-flow.mjs`):
    1. **Fork**: `createFork({ owner, repo })` — use `GITHUB_REGISTRY_OWNER/REPO` env (default: `adriannoes/asap-protocol`)
    2. **Branch**: `createRef(...)` -> `refs/heads/register/<agent>`
    3. **File**: `createOrUpdateFileContents(...)` -> `registry.json` — **must pass `sha`** when updating existing file
    4. **PR**: `pulls.create(...)` — Title: "Register Agent: <name>", Body: "Automated registration via Marketplace."

- [ ] 2.4.4 Dashboard Status Updates
  - **Poll**: `SWR` or `React Query` to poll `/api/github/pr-status`
  - **Display**: Badge (Yellow: Pending, Red: Changes Requested, Green: Merged)
  - **Admin Context**: Link to PR for user to see comments.

- [ ] 2.4.5 Commit Registration
  - **Command**: `git commit -m "feat(web): implement agent registration flow"`

**Acceptance Criteria**:
- [ ] Developer can register agent via form
- [ ] Automated PR created on GitHub
- [ ] Dashboard reflects PR status

---

## Sprint M2 Definition of Done

- [ ] Browse and search functional
- [ ] Agent detail page working
- [ ] Dashboard operational
- [ ] Agent registration flow complete

**Total Sub-tasks**: ~20

## Documentation Updates
- [ ] **Update Roadmap**: Mark completed items in [v2.0.0 Roadmap](./tasks-v2.0.0-roadmap.md)
