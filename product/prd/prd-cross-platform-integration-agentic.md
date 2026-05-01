# PRD: Cross-Platform Integration — Agent Builder (agentic-orchestration)

> **Product Requirements Document**
>
> **Version**: 1.0
> **Created**: 2026-03-05
> **Last Updated**: 2026-03-05
> **Target Repo**: `agentic-orchestration`
> **Companion PRD**: `prd-cross-platform-integration-asap.md` (for `asap-protocol`)

---

## 1. Executive Summary

### 1.1 Purpose

This PRD defines the changes required in the **Agent Builder** (agentic-orchestration) to integrate with the **ASAP Protocol** ecosystem. The integration replaces the existing placeholder Marketplace with the real ASAP Registry, establishes bidirectional navigation, and ensures authentication continuity between both applications.

### 1.2 Strategic Context

The Agent Builder is a visual drag-and-drop platform for creating, configuring, and running AI agents. The ASAP Protocol provides the registry, discovery, and communication standard for those agents. By integrating them:

- **Agent Builder** becomes the "build" layer of the ASAP ecosystem.
- **ASAP Registry** becomes the "discover" layer accessible from within the Builder.
- Users experience a unified product despite separate deployments.

| Application | Vercel Project | Production URL | Auth Stack |
|-------------|---------------|----------------|------------|
| ASAP Protocol | `asap-protocol` | `asap-protocol.vercel.app` | NextAuth v5 + GitHub OAuth |
| Agent Builder | `v0-agent-kit` | `open-agentic-flow.vercel.app` | NextAuth v5 + GitHub OAuth + Supabase (optional) |

### 1.3 Current State (What Exists Today)

**Marketplace** (`/marketplace`):
- Hardcoded integrations in-memory store (`marketplace-store.ts`): Salesforce, HubSpot, Zendesk, Airtable, Twilio, Shopify, Calendly, SendGrid.
- Install/uninstall actions (in-memory, not persisted).
- Category filtering, search, detail dialog.
- **This will be entirely replaced.**

**Sidebar Footer**:
- Static text: "Powered by ASAP protocol." (not clickable).

**Auth**:
- NextAuth v5 with GitHub OAuth.
- Supabase optional (for data persistence).
- No active middleware for route protection.

---

## 2. Goals

| Goal | Metric | Priority |
|------|--------|----------|
| Replace Marketplace with ASAP Registry | `/marketplace` shows real ASAP agents from `registry.json` | P0 |
| Bidirectional navigation | "Back to ASAP Protocol" link always visible in sidebar | P0 |
| Auth continuity (SSO) | Users from ASAP are logged in with ≤ 1 click | P0 |
| Design consistency | Visual style matches ASAP Protocol aesthetic | P1 |
| Mobile experience | Back-navigation and registry accessible on mobile | P1 |
| Registry data freshness | Agent list updated within 60 seconds of registry changes | P2 |

---

## 3. User Stories

### US-1: User Browses ASAP Agents Inside Agent Builder
> As a **user of Agent Builder**, I want to **browse the ASAP Agent Registry from within the Builder** so that **I can discover agents to integrate into my workflows without leaving the app**.

**Acceptance Criteria:**
- The "Marketplace" sidebar item is replaced with "Registry" (or "ASAP Registry").
- The `/marketplace` route renders the ASAP Agent Registry (real agents from `registry.json`).
- Agents display: name, description, version, category, tags, capabilities, auth requirements.
- Search and filtering work (by name, category, tags, skills).
- Clicking an agent shows its detail (similar to ASAP Protocol's `/agents/[id]` page).

### US-2: User Navigates Back to ASAP Protocol
> As a **user who came from ASAP Protocol**, I want to **easily navigate back** so that **I can manage my registered agents or browse the full registry**.

**Acceptance Criteria:**
- Sidebar shows a persistent "ASAP Protocol" link (not conditional on `?from=asap`).
- The "Powered by ASAP protocol." footer text becomes a clickable link to the ASAP Protocol URL.
- On mobile, the back-navigation is accessible.

### US-3: SSO from ASAP Protocol
> As a **user logged in on ASAP Protocol**, I want to **arrive at Agent Builder already authenticated (or with minimal friction)** so that **I don't have to log in again**.

**Acceptance Criteria:**
- Both apps use the same GitHub OAuth App (same `AUTH_GITHUB_ID`).
- When a user navigates from ASAP to Agent Builder, GitHub auto-approves the sign-in (no consent screen for returning users).
- The login page shows a clear "Sign in with GitHub" button for users who arrive without a session.

### US-4: Design Consistency
> As a **user of both platforms**, I want to **feel like I'm using the same product** so that **the experience is cohesive and professional**.

**Acceptance Criteria:**
- Color scheme, typography, and component styling are consistent with ASAP Protocol.
- The `/builder` page is NOT modified (it has been optimized for visual interactions).
- Common pages (Registry, Settings, etc.) follow ASAP's dark zinc/indigo palette.

---

## 4. Functional Requirements

### FR-1: Replace Marketplace with ASAP Registry

#### FR-1.1: Sidebar Update

**Location**: `src/components/sidebar.tsx`

Replace the Marketplace nav item:

```
Before: { href: "/marketplace", label: "Marketplace", icon: Store }
After:  { href: "/marketplace", label: "Registry", icon: Globe }
```

- Keep the `/marketplace` route path (avoids breaking bookmarks/links).
- Change icon from `Store` to `Globe` (or `Search`, matching ASAP's registry aesthetic).
- Add a new item above the footer for ASAP Protocol navigation (see FR-2).

#### FR-1.2: Registry Page

**Location**: `src/app/marketplace/page.tsx` (rewrite)

Replace the entire marketplace page with an ASAP Registry browser:

**Data Source**: Fetch `registry.json` directly from GitHub:
```
https://raw.githubusercontent.com/adriannoes/asap-protocol/main/registry.json
```

Also fetch revoked agents:
```
https://raw.githubusercontent.com/adriannoes/asap-protocol/main/revoked_agents.json
```

**Implementation approach**:
- Server Component that fetches and filters data (same pattern as ASAP's `apps/web/src/app/browse/page.tsx`).
- Client Component for search/filter UI.
- Use ISR with `revalidate = 60` (same as ASAP Protocol).
- Filter out revoked agents.

**Features to implement**:
- Search by name, description, ID (case-insensitive).
- Filter by category.
- Filter by tags.
- Agent cards showing: name, description, version, category, tags, endpoint URL, auth requirements.
- Click on agent → detail view (dialog or dedicated page).

**Features NOT to implement** (keep for future):
- Install/uninstall (the old marketplace concept).
- Ratings/reviews.
- Pricing badges.

#### FR-1.3: Registry Data Types

Create a shared type definition based on the ASAP Protocol's `RegistryAgent` and `Manifest` types:

```typescript
interface RegistryAgent {
  id: string;              // URN (e.g., "urn:asap:agent:user:agent-name")
  name: string;
  version: string;
  description: string;
  capabilities?: {
    skills?: Array<{ id: string; description: string }>;
  };
  endpoints?: {
    asap?: string;
    ws?: string;
  };
  auth?: {
    schemes?: string[];
    oauth2?: { authorization_url?: string; token_url?: string; scopes?: string[] };
  };
  sla?: { max_response_time_seconds?: number };
  repository_url?: string | null;
  documentation_url?: string | null;
  built_with?: string | null;
  category?: string | null;
  tags?: string[];
}
```

#### FR-1.4: Remove Old Marketplace Code

Delete or archive:
- `src/components/integration-marketplace.tsx`
- `src/components/marketplace-card.tsx`
- `src/components/integration-detail-dialog.tsx`
- `src/app/api/marketplace/` (all API routes)
- `src/lib/marketplace-store.ts` (if exists)

### FR-2: Bidirectional Navigation

#### FR-2.1: ASAP Protocol Link in Sidebar

Add a persistent link in the sidebar, positioned **after the last nav item** (Settings) and **before the footer**:

- **Label**: "ASAP Protocol"
- **Icon**: `ExternalLink` from lucide-react (or `Terminal` to match ASAP's logo)
- **URL**: `${NEXT_PUBLIC_ASAP_PROTOCOL_URL}`
- **Styling**: Slightly different from regular nav items — e.g., muted color with external link indicator.
- **Behavior**: Opens in same tab (standard navigation between sister apps).

#### FR-2.2: Footer Link

**Location**: `src/components/sidebar.tsx` (footer section)

Transform "Powered by ASAP protocol." into a clickable link:

```
Before: <p>Powered by ASAP protocol.</p>
After:  <a href={ASAP_PROTOCOL_URL}>Powered by ASAP protocol.</a>
```

- Style: `text-muted-foreground hover:text-foreground transition-colors`
- Opens in same tab.

#### FR-2.3: Mobile Navigation

Ensure the ASAP Protocol link and Registry are accessible on mobile:
- The sidebar collapses on mobile — verify the collapsed state shows the icon.
- If the app uses a mobile sheet/drawer pattern, include the ASAP Protocol link there.

### FR-3: SSO Configuration

#### FR-3.1: Shared GitHub OAuth App

**Prerequisite**: The ASAP Protocol must use the same GitHub OAuth App.

Configuration required:
1. In `src/auth.ts`, ensure the GitHub provider uses the same `AUTH_GITHUB_ID` and `AUTH_GITHUB_SECRET` as ASAP Protocol.
2. In the GitHub OAuth App settings (github.com/settings/developers), add the Agent Builder's callback URL: `https://open-agentic-flow.vercel.app/api/auth/callback/github`.
3. In Vercel project settings for `v0-agent-kit`, set the same OAuth credentials.

#### FR-3.2: Login Page Enhancement

**Location**: `src/app/login/page.tsx` and `src/components/auth/login-form.tsx`

When `?from=asap` query parameter is present:
- Show a contextual message: "Continue with GitHub to access Agent Builder from ASAP Protocol."
- Auto-focus or highlight the "Sign in with GitHub" button.
- After successful login, redirect to `/` (home/agents dashboard).

#### FR-3.3: Redirect Callback

In `src/auth.ts`, add a `redirect` callback to allow the ASAP Protocol URL as a valid redirect target:

```typescript
callbacks: {
  redirect({ url, baseUrl }) {
    const asapUrl = process.env.NEXT_PUBLIC_ASAP_PROTOCOL_URL;
    if (asapUrl && url.startsWith(asapUrl)) {
      return url;
    }
    if (url.startsWith(baseUrl)) return url;
    return baseUrl;
  },
}
```

### FR-4: Environment Variables

| Variable | Default Value | Purpose |
|----------|--------------|---------|
| `NEXT_PUBLIC_ASAP_PROTOCOL_URL` | `https://asap-protocol.vercel.app` | Back-navigation links |
| `NEXT_PUBLIC_REGISTRY_URL` | `https://raw.githubusercontent.com/adriannoes/asap-protocol/main/registry.json` | Registry data source |
| `NEXT_PUBLIC_REVOKED_URL` | `https://raw.githubusercontent.com/adriannoes/asap-protocol/main/revoked_agents.json` | Revoked agents list |
| `AUTH_GITHUB_ID` | (shared with ASAP Protocol) | SSO |
| `AUTH_GITHUB_SECRET` | (shared with ASAP Protocol) | SSO |

Update `.env.example` with these variables and clear documentation.

### FR-5: Design Unification

#### FR-5.1: Color Palette Alignment

ASAP Protocol uses:
- Background: `zinc-950` (pure dark)
- Borders: `zinc-800`
- Text: `white` / `zinc-400` / `zinc-500`
- Accent: `indigo-400` / `indigo-500`
- Cards: `bg-zinc-950/80` with `backdrop-blur`

Agent Builder currently uses Shadcn's default dark theme via CSS variables. To align:
- Verify CSS variables in `globals.css` map to ASAP's palette.
- Ensure cards, borders, and accents use zinc/indigo tones.
- **DO NOT modify the `/builder` page** — it has optimized interactions and custom styling that must be preserved.

#### FR-5.2: Protected Pages

The following pages should receive design alignment:
- `/marketplace` (new Registry page) — highest priority
- `/` (Agents Dashboard)
- `/settings`
- `/login` and `/signup`

The following pages should **NOT** be modified:
- `/builder` — complex canvas with drag-and-drop, custom nodes, edges, and panels. Changing styles here risks breaking optimized interactions.
- Any component under `src/components/builder/` — these are tightly coupled to the builder's UX.

#### FR-5.3: Font Consistency

Both apps already use Geist Sans / Geist Mono. No changes needed.

---

## 5. Non-Goals (Out of Scope)

| Non-Goal | Rationale |
|----------|-----------|
| Modifying the Builder page (`/builder`) | Complex canvas UX already optimized; risk of regression |
| Agent install/uninstall from Registry | The old marketplace concept; not applicable to ASAP Registry |
| Shared database between apps | Different data domains; registry is read from GitHub |
| Token relay between apps | Security risk; SSO via shared OAuth App is safer |
| Custom domain setup | Deferred — see ADR-26 |
| Real-time registry updates (WebSocket) | ISR with 60s revalidation is sufficient |

---

## 6. Technical Considerations

### 6.1 Registry Data Fetching

The ASAP Registry is a static JSON file hosted on GitHub. Fetching approach:

```
GitHub Raw (registry.json)
    │
    ▼
Server Component (ISR, revalidate: 60)
    │
    ▼
Filter revoked agents
    │
    ▼
Pass to Client Component (search/filter in memory)
```

**Schema validation**: Use Zod to validate the registry response (same schema as ASAP Protocol). Reference: `apps/web/src/lib/registry-schema.ts` in asap-protocol.

**Error handling**: If fetch fails, show a friendly error with retry button. Don't crash the page.

### 6.2 Agent Card Component

Create a new `RegistryAgentCard` component that displays:
- Agent name and version badge
- Description (2-line clamp)
- Category badge
- Tags (horizontal scroll)
- Endpoint URL (truncated)
- Auth requirement indicator (lock icon if auth required)
- "View Details" button

Reference the ASAP Protocol's browse-content card layout for consistency.

### 6.3 Agent Detail View

When clicking an agent card, show a dialog (or navigate to a detail page) with:
- Full description
- All capabilities/skills
- Endpoint URLs (HTTP, WebSocket)
- Auth configuration
- SLA details (if available)
- Links to repository and documentation
- "Open in ASAP Registry" link → `${ASAP_PROTOCOL_URL}/agents/${agent.id}`

### 6.4 Files to Create/Modify

| Action | File | Description |
|--------|------|-------------|
| **Modify** | `src/components/sidebar.tsx` | Replace Marketplace → Registry; add ASAP Protocol link; make footer clickable |
| **Rewrite** | `src/app/marketplace/page.tsx` | New Registry page (server component) |
| **Create** | `src/components/registry/registry-content.tsx` | Client component with search/filter UI |
| **Create** | `src/components/registry/registry-agent-card.tsx` | Agent card component |
| **Create** | `src/components/registry/registry-agent-detail.tsx` | Agent detail dialog |
| **Create** | `src/lib/registry.ts` | Fetch functions for registry.json and revoked_agents.json |
| **Create** | `src/lib/registry-schema.ts` | Zod schema for registry validation |
| **Create** | `src/types/registry.d.ts` | TypeScript types for RegistryAgent |
| **Modify** | `src/auth.ts` | Add redirect callback for ASAP Protocol URL |
| **Modify** | `src/app/login/page.tsx` | Handle `?from=asap` context |
| **Modify** | `src/components/auth/login-form.tsx` | Show contextual message for ASAP users |
| **Modify** | `.env.example` | Add new environment variables |
| **Delete** | `src/components/integration-marketplace.tsx` | Old marketplace component |
| **Delete** | `src/components/marketplace-card.tsx` | Old marketplace card |
| **Delete** | `src/components/integration-detail-dialog.tsx` | Old detail dialog |
| **Delete** | `src/app/api/marketplace/**` | Old marketplace API routes |

### 6.5 Middleware Recommendation

Currently, the agentic-orchestration has no active middleware. It is **strongly recommended** to create `middleware.ts` at the project root to:
1. Protect routes that require authentication (e.g., `/builder`, `/runs`, `/settings`).
2. Redirect unauthenticated users to `/login`.
3. Allow public access to `/login`, `/signup`, `/auth/*`, and optionally `/marketplace` (registry browsing).

This is not strictly part of the integration but is a prerequisite for a secure user experience.

---

## 7. Success Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| Registry page load time | < 2s (p95) | Vercel Speed Insights |
| Agent cards rendered | All active (non-revoked) agents from registry | Automated test |
| Search responsiveness | < 100ms for filter operations | Client-side performance |
| Back-navigation usage | > 20% of users who came from ASAP click "ASAP Protocol" link | Vercel Analytics |
| SSO success rate | > 95% of returning GitHub users auto-approved | Manual QA |

---

## 8. Testing Plan

### 8.1 Unit Tests

- `registry.ts`: Test fetch functions with mocked responses (valid, empty, error, malformed).
- `registry-schema.ts`: Test Zod validation with valid and invalid agent data.
- `registry-content.tsx`: Test search and filter logic.
- `registry-agent-card.tsx`: Test rendering with various agent configurations.
- `sidebar.tsx`: Test "Registry" label, ASAP Protocol link, clickable footer.

### 8.2 Integration Tests

- Registry page: Fetch real `registry.json` from GitHub (or fixture), render agent list, apply filters.
- Verify revoked agents are excluded.

### 8.3 E2E Tests

- Navigate to `/marketplace` → verify agent cards from registry.
- Search for an agent by name → verify filtered results.
- Click agent card → verify detail dialog/page.
- Click "ASAP Protocol" in sidebar → verify navigation.
- Login with `?from=asap` → verify contextual message.

---

## 9. Migration Plan

### Phase 1: Foundation (This PRD)
1. SSO setup (shared OAuth App credentials).
2. Replace Marketplace with Registry.
3. Add bidirectional navigation.
4. Design alignment (non-builder pages).

### Phase 2: Deep Integration (Future)
1. "Use in Builder" button on agent detail → auto-add agent node to Builder canvas.
2. Agent health monitoring from within Builder.
3. Publish agent to ASAP Registry directly from Builder.

### Phase 3: Unified Platform (Future — requires custom domain)
1. Custom domain with shared subdomain (e.g., `asap.io` + `builder.asap.io`).
2. Shared cookies for true zero-click SSO.
3. Unified user profile across both apps.

---

## 10. Open Questions

| # | Question | Status |
|---|----------|--------|
| 1 | Should the Registry page also show a "Use in Builder" quick action? | Deferred to Phase 2 |
| 2 | Should we keep the `/marketplace` URL path or rename to `/registry`? | Recommended: keep `/marketplace` for now (avoids breaking links) |
| 3 | Should unauthenticated users be able to browse the Registry? | Recommended: yes (registry data is public) |
| 4 | How should we handle registry.json schema changes between ASAP Protocol versions? | Add version tolerance in Zod schema |

---

## 11. Implementation Order (Cross-Repo Coordination)

> **This section is shared between both PRDs.** It defines the global execution order across the two repositories to avoid broken links, dead-end navigation, or incomplete SSO.

### Global Execution Sequence

```
┌─────────────────────────────────────────────────────────────────────┐
│  STEP 0 — GitHub OAuth App Configuration (PREREQUISITE)            │
│  Repo: Neither (github.com/settings/developers + Vercel dashboard) │
│  Effort: ~15 min                                                   │
│  ⬇                                                                 │
│  STEP 1 — Agent Builder (agentic-orchestration) ← DO THIS FIRST   │
│  Repo: agentic-orchestration                                       │
│  Effort: ~2-3 days                                                 │
│  ⬇                                                                 │
│  STEP 2 — ASAP Protocol (asap-protocol) ← DO THIS SECOND          │
│  Repo: asap-protocol                                               │
│  Effort: ~1 day                                                    │
│  ⬇                                                                 │
│  STEP 3 — Validation & Deploy (both repos)                         │
│  Effort: ~0.5 day                                                  │
└─────────────────────────────────────────────────────────────────────┘
```

### Why This Order?

This repo (agentic-orchestration) MUST be implemented and deployed **before** asap-protocol because:

1. **Dead link prevention**: If ASAP ships the "Agent Builder" link first, users click it and land on the old hardcoded Marketplace (Salesforce, HubSpot, etc.) — a confusing experience.
2. **SSO readiness**: This app must handle `?from=asap` and have the shared OAuth App configured before ASAP starts sending users here.
3. **Registry must exist**: The ASAP Registry page must be live on this app before ASAP promotes it.

### Step-by-Step Breakdown

#### Step 0: GitHub OAuth App (both repos — config only)
1. Go to `github.com/settings/developers` → select (or create) the OAuth App.
2. Add **both** callback URLs:
   - `https://asap-protocol.vercel.app/api/auth/callback/github`
   - `https://open-agentic-flow.vercel.app/api/auth/callback/github`
3. Copy the Client ID and Client Secret.
4. In Vercel dashboard, set `AUTH_GITHUB_ID` and `AUTH_GITHUB_SECRET` on **both** projects with the same values.
5. **Verify**: Deploy both apps → test login on each → confirm both work with the shared OAuth App.

#### Step 1: Agent Builder (agentic-orchestration) — ~2-3 days ← YOU ARE HERE
Execute in this order within the repo:

| # | Task | FR | Blocking? |
|---|------|----|-----------|
| 1.1 | Add env vars (`NEXT_PUBLIC_ASAP_PROTOCOL_URL`, `NEXT_PUBLIC_REGISTRY_URL`, etc.) to `.env.example` and Vercel | FR-4 | Yes |
| 1.2 | Create `src/lib/registry.ts` + `registry-schema.ts` + `src/types/registry.d.ts` (data layer) | FR-1.3 | Yes |
| 1.3 | Create Registry UI components (`registry-content.tsx`, `registry-agent-card.tsx`, `registry-agent-detail.tsx`) | FR-1.2 | Yes |
| 1.4 | Rewrite `src/app/marketplace/page.tsx` to use Registry components | FR-1.2 | Yes |
| 1.5 | Update Sidebar: "Marketplace" → "Registry", add "ASAP Protocol" link, make footer clickable | FR-1.1, FR-2 | No |
| 1.6 | Delete old marketplace code (components, API routes, store) | FR-1.4 | No |
| 1.7 | Update `src/auth.ts` with redirect callback + handle `?from=asap` on login page | FR-3 | No |
| 1.8 | Design alignment on non-builder pages (if needed) | FR-5 | No |
| 1.9 | Write tests (unit + E2E) | — | No |
| 1.10 | **Deploy to Vercel** | — | **Yes (blocks Step 2)** |

#### Step 2: ASAP Protocol (asap-protocol) — ~1 day
Execute in this order within the other repo:

| # | Task | FR | Blocking? |
|---|------|----|-----------|
| 2.1 | Add `NEXT_PUBLIC_AGENT_BUILDER_URL` env var to `.env.example` and Vercel | FR-5 (ASAP PRD) | Yes |
| 2.2 | Update `Header.tsx`: add "Agent Builder" link (post-login) + "Build Agents" CTA (pre-login) | FR-1, FR-2 (ASAP PRD) | Yes |
| 2.3 | Update `mobile-nav.tsx`: add "Agent Builder" / "Build Agents" | FR-3 (ASAP PRD) | No |
| 2.4 | Update `dashboard-client.tsx`: add Agent Builder card | FR-4 (ASAP PRD) | No |
| 2.5 | Update `auth.ts`: add redirect callback for Agent Builder URL | FR-6 (ASAP PRD) | No |
| 2.6 | Write tests (unit + E2E) | — | No |
| 2.7 | **Deploy to Vercel** | — | — |

#### Step 3: Validation (both repos) — ~0.5 day
1. **SSO flow**: Login on ASAP → click "Agent Builder" → verify auto-approve on GitHub → verify session on Agent Builder.
2. **Pre-login CTA**: Click "Build Agents" on ASAP → verify GitHub sign-in → verify redirect to Agent Builder.
3. **Registry**: Verify agents on Agent Builder `/marketplace` match ASAP `/browse`.
4. **Back-navigation**: On Agent Builder, click "ASAP Protocol" in sidebar → verify navigation.
5. **Mobile**: Repeat all flows on mobile viewport.

### Can You Merge in Parallel?

**No.** The correct merge order is:

1. **Merge + deploy agentic-orchestration first** (Steps 0 + 1)
2. **Then merge + deploy asap-protocol** (Step 2)
3. **Validate both together** (Step 3)

If asap-protocol is merged first, the "Agent Builder" link will point to an app that still shows the old hardcoded Marketplace, and `?from=asap` won't be handled.

---

## 12. Dependencies

| Dependency | Type | Notes |
|------------|------|-------|
| Companion PRD (asap-protocol) | External | ASAP Protocol must be deployed AFTER this PRD is deployed (Step 2 follows Step 1) |
| `registry.json` on GitHub | Data | Public JSON file; no API key needed |
| Shared GitHub OAuth App | Configuration | Same credentials on both Vercel projects (Step 0) |
| ADR-26 (Domain Decision) | Documentation | Future domain strategy affects SSO approach |
