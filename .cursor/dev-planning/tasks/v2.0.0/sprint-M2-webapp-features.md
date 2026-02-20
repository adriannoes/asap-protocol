# Sprint M2: Web App Features

> **Goal**: Registry browser and developer dashboard
> **Prerequisites**: Sprint M1 completed (Web App Foundation)
> **Parent Roadmap**: [tasks-v2.0.0-roadmap.md](./tasks-v2.0.0-roadmap.md)

---

## Pre-M2 Validation (Recommended)

Before starting Sprint M2, run the validation scripts to ensure registry fetch and GitHub PR flow work:

- **Guide**: [pre-M2-validation-guide.md](./pre-M2-validation-guide.md)
- **Scripts**: `apps/web/scripts/validate-registry-fetch.mjs`, `validate-github-pr-flow.mjs`

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

- [ ] 4.1.1 /browse page layout
  - **Strategy**: Incremental Static Regeneration (ISR) with `revalidate: 60`
  - **Data Source**: Fetch `https://raw.githubusercontent.com/.../registry.json`

- [ ] 4.1.2 Search input
  - Client-side filtering of the JSON list (registry is small < 1MB)
  - Debounced search (300ms)

- [ ] 4.1.3 Skill filters
  - Extract unique skills from `registry.json`
  - Multi-select checkbox/badges

- [ ] 4.1.4 Trust level filters

- [ ] 4.1.5 Agent cards grid

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
  - **Flow**:
    1. **Fork**: `octokit.rest.repos.createFork({ owner: "asap-protocol", repo: "registry" })`
    2. **Branch**: `octokit.rest.git.createRef(...)` -> `refs/heads/register/<agent>`
    3. **File**: `octokit.rest.repos.createOrUpdateFileContents(...)` -> `registry.json`
    4. **PR**: `octokit.rest.pulls.create(...)`
      - **Title**: "Register Agent: <name>"
      - **Body**: "Automated registration via Marketplace."

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
