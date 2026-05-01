# PRD: Cross-Platform Integration — ASAP Protocol Web App

> **Product Requirements Document**
>
> **Version**: 1.0
> **Created**: 2026-03-05
> **Last Updated**: 2026-03-05
> **Target Repo**: `asap-protocol` (`apps/web/`)
> **Companion PRD**: `prd-cross-platform-integration-agentic.md` (for `agentic-orchestration`)

---

## 1. Executive Summary

### 1.1 Purpose

This PRD defines the changes required in the **ASAP Protocol web app** to enable a seamless cross-platform experience with the **Agent Builder** (agentic-orchestration). The goal is to treat both applications as a unified product suite where users can:

1. Discover and browse agents on the ASAP Protocol Registry.
2. Navigate to the Agent Builder to create, configure, and run agents.
3. Maintain authentication continuity across both apps.

### 1.2 Strategic Context

The ASAP Protocol and Agent Builder are deployed as separate Next.js applications on Vercel:

| Application | Vercel Project | Production URL | Auth Stack |
|-------------|---------------|----------------|------------|
| ASAP Protocol | `asap-protocol` | `asap-protocol.vercel.app` | NextAuth v5 + GitHub OAuth |
| Agent Builder | `v0-agent-kit` | `open-agentic-flow.vercel.app` | NextAuth v5 + GitHub OAuth + Supabase (optional) |

Both apps share the **same auth provider** (GitHub OAuth via NextAuth v5), which is the foundation for the SSO strategy.

> **Domain Decision**: Current URLs are Vercel subdomains (not definitive). A custom domain will be acquired in the future. See ADR-26 in `decision-records/05-product-strategy.md` for rationale and migration plan.

---

## 2. Goals

| Goal | Metric | Priority |
|------|--------|----------|
| Cross-navigation | Users can reach Agent Builder from ASAP in ≤ 1 click | P0 |
| Auth continuity | Users arriving at Agent Builder from ASAP are logged in with ≤ 1 extra click (GitHub auto-approve) | P0 |
| Pre-login awareness | Non-authenticated users see a CTA for Agent Builder with conversion intent | P1 |
| Mobile parity | Agent Builder link accessible on mobile nav (Sheet) | P1 |
| URL configurability | All cross-app URLs use environment variables (no hardcoded domains) | P1 |

---

## 3. User Stories

### US-1: Authenticated User Navigates to Agent Builder
> As a **logged-in user on ASAP Protocol**, I want to **click "Agent Builder" in the navigation** so that **I'm taken to the Agent Builder app and remain authenticated**.

**Acceptance Criteria:**
- "Agent Builder" link visible in Header nav and Mobile nav (only when logged in).
- Link opens Agent Builder in the same tab (not `target="_blank"`).
- URL includes `?from=asap` query parameter for analytics and back-navigation.
- If the user is using the same GitHub OAuth App, GitHub auto-approves the sign-in on Agent Builder (no re-consent prompt).

### US-2: Non-Authenticated User Sees Agent Builder CTA
> As a **visitor (not logged in) on ASAP Protocol**, I want to **see what Agent Builder offers** so that **I'm motivated to sign up and build agents**.

**Acceptance Criteria:**
- In place of the "Agent Builder" nav link, show a styled CTA element (e.g., badge, button, or nav item with distinct styling).
- Clicking the CTA redirects to sign-in (GitHub OAuth) with `callbackUrl` pointing to the Agent Builder URL (so after login, the user lands directly on Agent Builder).
- Copy example: "Build Agents →" with a subtle badge like "New" or a sparkle icon.

### US-3: Dashboard Quick Access
> As a **logged-in user on the Dashboard**, I want to **quickly access the Agent Builder** so that **I can start building agents without navigating back to the header**.

**Acceptance Criteria:**
- A prominent card or banner on the Dashboard "My Agents" tab linking to Agent Builder.
- Card includes brief description: "Design, connect, and run AI agents visually."
- Uses the same URL pattern (`AGENT_BUILDER_URL + ?from=asap`).

---

## 4. Functional Requirements

### FR-1: Header Navigation — Agent Builder Link (Post-Login)

**Location**: `apps/web/src/components/layout/Header.tsx`

When `session?.user` exists, add a nav link **after "Docs"** in the center nav:

```
Registry | Demos | Developers | Docs | Agent Builder (new)
```

- **Label**: "Agent Builder"
- **Icon**: Optional — `Workflow` from lucide-react (matches agentic-orchestration's Builder icon)
- **URL**: `${NEXT_PUBLIC_AGENT_BUILDER_URL}?from=asap`
- **Behavior**: Standard `<a>` tag (external navigation, same tab), NOT `<Link>` (since it's a different app).
- **Styling**: Match existing nav link style (`text-sm font-medium text-zinc-400 transition-colors hover:text-white`).

### FR-2: Header Navigation — Agent Builder CTA (Pre-Login)

When `session?.user` is falsy, show a CTA in the center nav:

- **Label**: "Build Agents" (shorter, action-oriented)
- **Position**: After "Docs" in the nav, replacing where "Agent Builder" would be.
- **Styling**: Differentiated from regular nav links — e.g., `text-indigo-400 hover:text-indigo-300` with a sparkle/star icon or a "New" badge.
- **onClick**: Trigger GitHub sign-in with `callbackUrl` set to `${NEXT_PUBLIC_AGENT_BUILDER_URL}?from=asap`.
- **Implementation**: Server Action form (same pattern as "Connect / Login" button) with `signIn("github", { redirectTo: AGENT_BUILDER_URL + "?from=asap" })`.

### FR-3: Mobile Navigation

**Location**: `apps/web/src/components/layout/mobile-nav.tsx`

- Add "Agent Builder" / "Build Agents" to the mobile Sheet nav, following the same post-login / pre-login logic as FR-1 and FR-2.
- Position: After "Developer Experience" (last item before close).

### FR-4: Dashboard Card

**Location**: `apps/web/src/app/dashboard/dashboard-client.tsx`

- Add a card/banner at the top of the "agents" tab content (before "Registered Agents" heading).
- **Design**: Full-width card with gradient border (indigo), icon (Workflow), title "Agent Builder", description "Design, connect, and run AI agents visually with our drag-and-drop builder.", and a CTA button "Open Agent Builder →".
- **Link**: `${NEXT_PUBLIC_AGENT_BUILDER_URL}?from=asap`

### FR-5: Environment Variable

Add `NEXT_PUBLIC_AGENT_BUILDER_URL` to the app configuration:

- **Default value**: `https://open-agentic-flow.vercel.app`
- **Usage**: All cross-app links use this variable.
- **Documentation**: Add to `.env.example` (create if not exists) and document in README.

### FR-6: Shared GitHub OAuth App (SSO Foundation)

Both applications MUST use the **same GitHub OAuth App** credentials:

- Same `AUTH_GITHUB_ID` (Client ID)
- Same `AUTH_GITHUB_SECRET` (Client Secret)
- The GitHub OAuth App must have **both** callback URLs registered:
  - `https://asap-protocol.vercel.app/api/auth/callback/github`
  - `https://open-agentic-flow.vercel.app/api/auth/callback/github`

**Vercel Configuration**:
- In the ASAP Protocol Vercel project settings, ensure `AUTH_GITHUB_ID` and `AUTH_GITHUB_SECRET` match the Agent Builder project.
- In the Agent Builder Vercel project settings, set the same values.

**GitHub OAuth App Settings** (at `github.com/settings/developers`):
- Add both callback URLs.
- This ensures that once a user authorizes the app on ASAP, GitHub automatically approves on Agent Builder (no re-consent).

> **Security Note**: This is the standard OAuth 2.0 pattern. No tokens are passed between apps. Each app creates its own independent NextAuth session. The only shared element is the GitHub OAuth App ID, which GitHub uses to skip the authorization prompt for already-authorized users.

---

## 5. Non-Goals (Out of Scope)

| Non-Goal | Rationale |
|----------|-----------|
| Embedding Agent Builder in an iframe | Poor UX, CSP issues, breaks auth |
| Shared session/cookie between apps | Requires same domain (deferred to custom domain phase) |
| Token relay via URL params | Security risk (tokens in URL history/logs) |
| Custom domain setup | Deferred — see ADR-26 |
| Changes to the Agent Builder codebase | Covered in companion PRD |
| Registry API for external consumption | Covered in `prd-v2.2-scale.md` (Registry API Backend) |

---

## 6. Design Considerations

### 6.1 Header Layout

The header currently has 4 nav items (Registry, Demos, Developers, Docs). Adding "Agent Builder" makes 5. Verify that 5 items fit comfortably at `md:flex` breakpoint (768px). If tight, consider:
- Shorter labels (e.g., "Builder" instead of "Agent Builder")
- Grouping under a dropdown

### 6.2 CTA Styling (Pre-Login)

The pre-login CTA should stand out from regular nav links without being intrusive:
- Use `text-indigo-400` (brand color) instead of `text-zinc-400`
- Add a subtle icon (e.g., `Sparkles` from lucide-react)
- Optional: animated border or pulse effect

### 6.3 Dashboard Card

Follow the existing card pattern in Dashboard. Reference the pending registration cards for layout consistency. Use `bg-gradient-to-r from-indigo-500/10 to-purple-500/10` for the gradient background.

---

## 7. Technical Considerations

### 7.1 Auth Flow (SSO via Shared OAuth App)

```
User on ASAP Protocol (logged in via GitHub)
  │
  ├─ Clicks "Agent Builder" → navigates to Agent Builder URL
  │
  └─ Agent Builder (NextAuth) detects no session
       │
       ├─ User clicks "Sign in with GitHub"
       │
       └─ GitHub recognizes already-authorized OAuth App
            │
            └─ Auto-approves → redirects back → session created
                 (No consent screen, feels seamless)
```

**Important**: This flow requires 1 extra click ("Sign in with GitHub") on the Agent Builder side. For truly zero-click SSO, a custom domain with shared cookies would be needed (future phase).

### 7.2 `redirectTo` Behavior

NextAuth's `signIn()` accepts a `redirectTo` parameter. When the pre-login CTA triggers sign-in:
1. User clicks "Build Agents" on ASAP
2. NextAuth redirects to GitHub for auth
3. GitHub redirects back to ASAP's callback
4. NextAuth processes the callback and redirects to `redirectTo` (the Agent Builder URL)

**Caveat**: `redirectTo` in NextAuth v5 only allows URLs that are in the `AUTH_TRUST_HOST` or same origin by default. For cross-origin redirects, the `redirect` callback in `auth.ts` must be configured to allow the Agent Builder domain:

```typescript
callbacks: {
  redirect({ url, baseUrl }) {
    const agentBuilderUrl = process.env.NEXT_PUBLIC_AGENT_BUILDER_URL;
    if (agentBuilderUrl && url.startsWith(agentBuilderUrl)) {
      return url;
    }
    if (url.startsWith(baseUrl)) return url;
    return baseUrl;
  },
}
```

### 7.3 Environment Variables

| Variable | Value (Production) | Used In |
|----------|-------------------|---------|
| `NEXT_PUBLIC_AGENT_BUILDER_URL` | `https://open-agentic-flow.vercel.app` | Header, MobileNav, Dashboard |
| `AUTH_GITHUB_ID` | (shared with Agent Builder) | NextAuth config |
| `AUTH_GITHUB_SECRET` | (shared with Agent Builder) | NextAuth config |

### 7.4 Files to Modify

| File | Change |
|------|--------|
| `apps/web/src/components/layout/Header.tsx` | Add Agent Builder link (FR-1, FR-2) |
| `apps/web/src/components/layout/mobile-nav.tsx` | Add Agent Builder to mobile Sheet (FR-3) |
| `apps/web/src/app/dashboard/dashboard-client.tsx` | Add Agent Builder card (FR-4) |
| `apps/web/src/auth.ts` | Add `redirect` callback for cross-origin (FR-6) |
| `.env.example` (create) | Document `NEXT_PUBLIC_AGENT_BUILDER_URL` (FR-5) |

---

## 8. Success Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| Click-through rate on "Agent Builder" | > 10% of logged-in users | Vercel Analytics event |
| CTA conversion (pre-login → login → Agent Builder) | > 5% of CTA clicks | Vercel Analytics funnel |
| Auth continuity (no re-consent on GitHub) | 100% for returning users | Manual QA |
| Mobile usability | Agent Builder accessible via mobile nav | E2E test |

---

## 9. Testing Plan

### 9.1 Unit Tests

- `Header.tsx`: Verify "Agent Builder" link rendered when session exists; verify "Build Agents" CTA rendered when no session.
- `mobile-nav.tsx`: Same session-based rendering tests.
- `auth.ts`: Verify `redirect` callback allows Agent Builder URL and blocks unknown URLs.

### 9.2 E2E Tests

- **Auth journey**: Login → verify "Agent Builder" link visible → click → verify redirect includes `?from=asap`.
- **Pre-login CTA**: Click "Build Agents" → verify redirect to GitHub sign-in → verify `callbackUrl` includes Agent Builder URL.
- **Mobile**: Open mobile nav → verify "Agent Builder" / "Build Agents" present.

---

## 10. Open Questions

| # | Question | Status |
|---|----------|--------|
| 1 | Should the Dashboard card include usage stats from Agent Builder (e.g., "3 agents built")? | Deferred to future integration |
| 2 | Should we add Vercel Analytics custom events for cross-app navigation tracking? | Recommended but not blocking |
| 3 | Will the `redirectTo` cross-origin work with NextAuth v5 beta.30's security defaults? | Needs verification in dev |

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

The agentic-orchestration MUST be implemented and deployed **before** asap-protocol because:

1. **Dead link prevention**: If ASAP ships the "Agent Builder" link first, users click it and land on the old hardcoded Marketplace (Salesforce, HubSpot, etc.) — a confusing experience.
2. **SSO readiness**: The Agent Builder must handle `?from=asap` and have the shared OAuth App configured before ASAP starts sending users there.
3. **Registry must exist**: The ASAP Registry page on Agent Builder must be live before ASAP promotes it.

### Step-by-Step Breakdown

#### Step 0: GitHub OAuth App (both repos — config only)
1. Go to `github.com/settings/developers` → select (or create) the OAuth App.
2. Add **both** callback URLs:
   - `https://asap-protocol.vercel.app/api/auth/callback/github`
   - `https://open-agentic-flow.vercel.app/api/auth/callback/github`
3. Copy the Client ID and Client Secret.
4. In Vercel dashboard, set `AUTH_GITHUB_ID` and `AUTH_GITHUB_SECRET` on **both** projects with the same values.
5. **Verify**: Deploy both apps → test login on each → confirm both work with the shared OAuth App.

#### Step 1: Agent Builder (agentic-orchestration) — ~2-3 days
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
Execute in this order within the repo (THIS is where you are now):

| # | Task | FR | Blocking? |
|---|------|----|-----------|
| 2.1 | Add `NEXT_PUBLIC_AGENT_BUILDER_URL` env var to `.env.example` and Vercel | FR-5 | Yes |
| 2.2 | Update `Header.tsx`: add "Agent Builder" link (post-login) + "Build Agents" CTA (pre-login) | FR-1, FR-2 | Yes |
| 2.3 | Update `mobile-nav.tsx`: add "Agent Builder" / "Build Agents" | FR-3 | No |
| 2.4 | Update `dashboard-client.tsx`: add Agent Builder card | FR-4 | No |
| 2.5 | Update `auth.ts`: add redirect callback for Agent Builder URL | FR-6 | No |
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

If you merge asap-protocol first, the "Agent Builder" link will point to an app that still shows the old hardcoded Marketplace, and `?from=asap` won't be handled.

---

## 12. Dependencies

| Dependency | Type | Notes |
|------------|------|-------|
| Companion PRD (agentic-orchestration) | External | Agent Builder must be deployed FIRST (Steps 0 + 1) before this PRD is deployed |
| Shared GitHub OAuth App | Configuration | Must configure same OAuth App credentials on both Vercel projects (Step 0) |
| ADR-26 (Domain Decision) | Documentation | Documents deferred custom domain decision |
