# Tasks: Cross-Platform Integration — ASAP Protocol Web App (v2.2.0)

> **PRD**: `prd-cross-platform-integration-asap.md`
> **Goal**: Enable seamless cross-navigation from ASAP Protocol to Agent Builder with SSO continuity
> **Prerequisite**: Step 0 (GitHub OAuth App config) and Step 1 (agentic-orchestration deployed) must be completed first — see PRD §11
> **Cross-Repo Dependency**: agentic-orchestration must be deployed before merging/deploying this work

## Sprint Split (3 PRs)

| Sprint | File | Scope |
|--------|------|-------|
| **CP1** | [sprint-CP1-foundation.md](./sprint-CP1-foundation.md) | Env + Auth redirect + auth tests (~3 files) |
| **CP2** | [sprint-CP2-navigation.md](./sprint-CP2-navigation.md) | Header + MobileNav + nav tests (~4 files) |
| **CP3** | [sprint-CP3-dashboard-qa.md](./sprint-CP3-dashboard-qa.md) | Dashboard card + card tests + full CI (~2 files) |

**Roadmap**: [tasks-v2.2.0-roadmap.md](./tasks-v2.2.0-roadmap.md)

---

## Relevant Files

### Environment & Configuration
- `apps/web/.env.example` (create new) — Document `NEXT_PUBLIC_AGENT_BUILDER_URL` and other env vars
- `apps/web/.gitignore` (modify existing) — Add `!.env.example` so example file is tracked
- `apps/web/src/auth.ts` (modify existing) — Add `redirect` callback and `pages.signIn` for custom sign-in
- `apps/web/src/auth-redirect.ts` (create new) — Extracted redirect logic for testability

### Auth & Sign-in
- `apps/web/src/app/auth/signin/page.tsx` (create new) — Custom sign-in page with ASAP Protocol identity
- `apps/web/src/app/auth/signin/signin-form.tsx` (create new) — Sign-in form component (GitHub OAuth, links)

### Navigation Components
- `apps/web/src/components/layout/Header.tsx` (modify existing) — Add "Agent Builder" link (post-login) and "Build Agents" CTA (pre-login)
- `apps/web/src/components/layout/mobile-nav.tsx` (modify existing) — Add Agent Builder to mobile Sheet nav

### Dashboard
- `apps/web/src/app/dashboard/dashboard-client.tsx` (modify existing) — Add Agent Builder promotional card
- `apps/web/src/app/dashboard/register/page.tsx` (modify existing) — Redirect to sign-in with callbackUrl when unauthenticated

### Tests
- `apps/web/src/components/layout/__tests__/header.test.tsx` (create new) — Unit tests for Header session-based rendering
- `apps/web/src/components/layout/__tests__/mobile-nav.test.tsx` (create new) — Unit tests for MobileNav Agent Builder link
- `apps/web/src/app/dashboard/__tests__/dashboard-agent-builder-card.test.tsx` (create new) — Unit tests for Agent Builder card
- `apps/web/src/__tests__/auth-redirect.test.ts` (create new) — Unit tests for resolveRedirectUrl

### Notes

- Unit tests should be placed in `__tests__/` folders co-located with the source (existing project pattern — see `apps/web/src/app/dashboard/verify/__tests__/`).
- Use `vitest` to run tests: `npm test` or `npx vitest run` from `apps/web/`.
- The `MobileNav` is a Client Component (`'use client'`), while `Header` is a Server Component (async). Test strategies differ accordingly.
- Test framework: `vitest` + `@testing-library/react`. Imports: `{ describe, it, expect, vi } from 'vitest'` and `{ render, screen } from '@testing-library/react'`.

---

## Tasks

### Task 1.0: Environment Variable & Configuration Setup

**Goal**: Establish the `NEXT_PUBLIC_AGENT_BUILDER_URL` environment variable so all cross-app links are configurable and never hardcoded.

**Context**: The Agent Builder URL will change when custom domains are acquired (see ADR-26). Using an env var ensures migration is a config change, not a code change. This task must be done first because all subsequent tasks depend on this variable.

**Trigger**: Step 0 (GitHub OAuth App) completed; agentic-orchestration deployed to Vercel.
**Enables**: Tasks 2.0–5.0 (all need the env var to build links).
**Depends on**: Nothing within this repo.

#### Sub-tasks

- [x] 1.1 Create `.env.example` with `NEXT_PUBLIC_AGENT_BUILDER_URL`
  - **File**: `apps/web/.env.example` (create new)
  - **What**: Create a `.env.example` file documenting all environment variables. Include `NEXT_PUBLIC_AGENT_BUILDER_URL` with its default value and a comment explaining its purpose. Also list existing vars (`AUTH_SECRET`, `GITHUB_CLIENT_ID`, `GITHUB_CLIENT_SECRET`, `REGISTRY_URL`, `REVOKED_URL`, `REGISTRY_REVALIDATE_SECONDS`, `NEXT_PUBLIC_APP_URL`, `ENABLE_FIXTURE_ROUTES`) with placeholder comments.
  - **Why**: The project currently has no `.env.example`. This is essential for developer onboarding and Vercel configuration documentation.
  - **Pattern**: Follow standard `.env.example` format — comments with `#`, no real values, only placeholders.
  - **Verify**: File exists at `apps/web/.env.example` and contains `NEXT_PUBLIC_AGENT_BUILDER_URL=https://open-agentic-flow.vercel.app`.

- [x] 1.2 Add `.env.example` to `.gitignore` audit
  - **File**: `apps/web/.gitignore` (verify existing)
  - **What**: Ensure `.env` (not `.env.example`) is in `.gitignore`. The `.env.example` MUST NOT be gitignored (it should be committed). Verify that `.env.local` and `.env` are already ignored.
  - **Why**: Prevent accidental commit of real secrets while ensuring the example file is tracked.
  - **Verify**: `grep -q "\.env\.local" apps/web/.gitignore` returns match. `.env.example` is NOT matched by any ignore pattern.

- [x] 1.3 Commit
  - **Command**: `git commit -m "chore(web): add .env.example with NEXT_PUBLIC_AGENT_BUILDER_URL"`
  - **Scope**: `apps/web/.env.example`

**Acceptance Criteria**:
- [x] `apps/web/.env.example` exists and is committed to git.
- [x] `NEXT_PUBLIC_AGENT_BUILDER_URL` is documented with default value `https://open-agentic-flow.vercel.app`.
- [x] All existing env vars are listed as placeholders (no real secrets).

---

### Task 2.0: Auth Configuration — Cross-Origin Redirect Callback

**Goal**: Allow NextAuth's `signIn()` to redirect users to the Agent Builder URL after authentication (cross-origin redirect).

**Context**: By default, NextAuth v5 only allows redirects to the same origin (`baseUrl`). The pre-login CTA "Build Agents" needs to sign the user in on ASAP and then redirect them to the Agent Builder. Without this callback, NextAuth will silently redirect to `/` instead of the Agent Builder URL.

**Trigger**: User clicks "Build Agents" CTA (Task 3.0) which calls `signIn("github", { redirectTo: agentBuilderUrl })`.
**Enables**: Task 3.0 FR-2 (pre-login CTA cross-origin redirect).
**Depends on**: Task 1.0 (`NEXT_PUBLIC_AGENT_BUILDER_URL` env var must exist).

#### Sub-tasks

- [x] 2.1 Add `redirect` callback to NextAuth configuration
  - **File**: `apps/web/src/auth.ts` (modify existing)
  - **What**: Add a `redirect` callback inside the existing `callbacks` object (after the `session` callback, before closing `}`). The callback should:
    1. Check if `url` starts with the Agent Builder URL (`process.env.NEXT_PUBLIC_AGENT_BUILDER_URL`).
    2. If yes, allow the redirect by returning `url`.
    3. If no, fall back to default behavior: allow same-origin (`url.startsWith(baseUrl)`) or return `baseUrl`.
  - **Why**: NextAuth v5 blocks cross-origin redirects by default (security feature). We need an explicit allowlist for the Agent Builder domain.
  - **Pattern**: The existing `callbacks` object at line 59 of `auth.ts` has `jwt` and `session`. Add `redirect` as a third callback:
    ```typescript
    redirect({ url, baseUrl }) {
        const agentBuilderUrl = process.env.NEXT_PUBLIC_AGENT_BUILDER_URL;
        if (agentBuilderUrl && url.startsWith(agentBuilderUrl)) {
            return url;
        }
        if (url.startsWith(baseUrl)) return url;
        return baseUrl;
    },
    ```
  - **Verify**: Write a test (Task 6.0) that calls the redirect callback with Agent Builder URL and confirms it's returned unchanged. Also test that random external URLs are blocked (returns `baseUrl`).
  - **Integration**: This callback is invoked by NextAuth whenever `signIn("github", { redirectTo: ... })` is called. Task 3.0 (Header CTA) relies on this to redirect post-login.

- [x] 2.2 Commit
  - **Command**: `git commit -m "feat(auth): add redirect callback for cross-origin Agent Builder SSO"`
  - **Scope**: `apps/web/src/auth.ts`

**Acceptance Criteria**:
- [x] `auth.ts` has a `redirect` callback in the `callbacks` object.
- [x] Redirect allows URLs starting with `NEXT_PUBLIC_AGENT_BUILDER_URL`.
- [x] Redirect blocks arbitrary external URLs (returns `baseUrl`).
- [x] Existing callbacks (`jwt`, `session`) remain unchanged.

---

### Task 3.0: Header Navigation — Agent Builder Link & CTA

**Goal**: Add "Agent Builder" link for logged-in users and "Build Agents" CTA for visitors in the desktop Header.

**Context**: The Header is a Server Component (async) that reads `session` via `auth()`. It currently has 4 nav items (Registry, Demos, Developers, Docs). We add a 5th item that behaves differently based on auth state. The `Header` component already imports `signIn` from `@/auth` — we'll use that for the CTA form.

**Trigger**: User views any page on the ASAP Protocol web app.
**Enables**: Users can navigate to Agent Builder; pre-login users can sign-in and be redirected.
**Depends on**: Task 1.0 (env var), Task 2.0 (redirect callback for CTA).

#### Sub-tasks

- [x] 3.1 Add `Workflow` and `Sparkles` icon imports
  - **File**: `apps/web/src/components/layout/Header.tsx` (modify existing)
  - **What**: Add `Workflow` and `Sparkles` to the lucide-react import on line 2. Change: `import { Terminal } from "lucide-react"` → `import { Terminal, Workflow, Sparkles } from "lucide-react"`.
  - **Why**: `Workflow` icon matches the Agent Builder's icon in agentic-orchestration sidebar. `Sparkles` is used for the pre-login CTA to visually differentiate it.
  - **Verify**: No TypeScript errors; icons are available for use.

- [x] 3.2 Add Agent Builder link for authenticated users (post-login)
  - **File**: `apps/web/src/components/layout/Header.tsx` (modify existing)
  - **What**: Inside the `{/* Center Nav */}` section (line 38–66), **after** the "Docs" `<Link>` (line 58–65) and **before** the closing `</nav>` (line 66), add a session-conditional block:
    ```tsx
    {session?.user && (
        <a
            href={`${process.env.NEXT_PUBLIC_AGENT_BUILDER_URL ?? 'https://open-agentic-flow.vercel.app'}?from=asap`}
            className="text-sm font-medium text-zinc-400 transition-colors hover:text-white inline-flex items-center gap-1.5"
        >
            <Workflow className="h-3.5 w-3.5" />
            Agent Builder
        </a>
    )}
    ```
  - **Why**: Post-login users get a direct navigation link. Uses `<a>` instead of `<Link>` because it's an external app. The `?from=asap` param enables back-navigation in the Agent Builder.
  - **Pattern**: Same styling as existing nav links (`text-sm font-medium text-zinc-400 transition-colors hover:text-white`). The `session` variable is already available at line 17.
  - **Verify**: When logged in, "Agent Builder" appears after "Docs" in the header nav. When not logged in, it does not appear.
  - **Integration**: The URL includes `?from=asap` which is consumed by agentic-orchestration (companion PRD Task 1.7) to show contextual login UI and back-navigation.

- [x] 3.3 Add "Build Agents" CTA for non-authenticated users (pre-login)
  - **File**: `apps/web/src/components/layout/Header.tsx` (modify existing)
  - **What**: Immediately after the authenticated block from 3.2, add a non-authenticated CTA:
    ```tsx
    {!session?.user && (
        <form
            action={async () => {
                "use server";
                await signIn("github", {
                    redirectTo: `${process.env.NEXT_PUBLIC_AGENT_BUILDER_URL ?? 'https://open-agentic-flow.vercel.app'}?from=asap`,
                });
            }}
        >
            <button
                type="submit"
                className="text-sm font-medium text-indigo-400 transition-colors hover:text-indigo-300 inline-flex items-center gap-1.5"
            >
                <Sparkles className="h-3.5 w-3.5" />
                Build Agents
            </button>
        </form>
    )}
    ```
  - **Why**: Non-authenticated visitors see a CTA that triggers GitHub sign-in. After sign-in, NextAuth redirects to the Agent Builder URL (enabled by Task 2.0's redirect callback). Uses indigo color to differentiate from regular nav links.
  - **Pattern**: Same Server Action pattern as the existing "Connect / Login" button (lines 112–121 of `Header.tsx`). Uses `signIn("github", { redirectTo: ... })`.
  - **Verify**: When not logged in, "Build Agents" appears in indigo color after "Docs". Clicking it triggers GitHub OAuth flow. After login, user is redirected to Agent Builder URL.
  - **Integration**: Depends on Task 2.0 (redirect callback) to allow cross-origin redirect after sign-in.

- [x] 3.4 Verify 5-item header layout at md breakpoint
  - **What**: Manually verify (or via E2E) that 5 nav items (Registry, Demos, Developers, Docs, Agent Builder / Build Agents) fit at the `md:flex` breakpoint (768px). If they overflow, shorten "Agent Builder" to "Builder" or "Developers" to "Devs".
  - **Verify**: At 768px viewport width, all 5 nav items are visible without wrapping.

- [x] 3.5 Commit
  - **Command**: `git commit -m "feat(web): add Agent Builder link and Build Agents CTA to Header"`
  - **Scope**: `apps/web/src/components/layout/Header.tsx`

**Acceptance Criteria**:
- [x] Logged-in users see "Agent Builder" with Workflow icon in Header nav (after Docs).
- [x] Non-logged-in users see "Build Agents" in indigo color with Sparkles icon.
- [x] "Agent Builder" link href includes `?from=asap`.
- [x] "Build Agents" CTA triggers GitHub sign-in with `redirectTo` pointing to Agent Builder URL.
- [x] All 5 nav items fit at md breakpoint without layout issues.

---

### Task 4.0: Mobile Navigation — Agent Builder Link & CTA

**Goal**: Add Agent Builder navigation to the mobile Sheet nav, maintaining feature parity with desktop.

**Context**: `MobileNav` is a Client Component (`'use client'`). It does NOT have access to the server-side `session`. To add session-conditional behavior, we need to either: (a) pass `session` as a prop from the parent `Header` (Server Component), or (b) use `useSession()` from `next-auth/react` (requires `SessionProvider`). The simplest approach is **(a)** since `Header` already calls `auth()`.

**Trigger**: User opens the mobile navigation sheet on any page.
**Enables**: Mobile users can navigate to Agent Builder.
**Depends on**: Task 1.0 (env var), Task 2.0 (redirect callback for CTA), Task 3.0 (establishes the pattern).

#### Sub-tasks

- [x] 4.1 Pass `session` prop from `Header` to `MobileNav`
  - **File**: `apps/web/src/components/layout/Header.tsx` (modify existing)
  - **What**: Change `<MobileNav />` (line 35) to `<MobileNav session={session} />`. The `session` variable already exists at line 17.
  - **Why**: `MobileNav` is a Client Component and can't call `auth()` directly. Passing the session from the Server Component parent is the idiomatic Next.js pattern.
  - **Verify**: No TypeScript errors after updating the prop.

- [x] 4.2 Update `MobileNav` to accept `session` prop and render Agent Builder link
  - **File**: `apps/web/src/components/layout/mobile-nav.tsx` (modify existing)
  - **What**:
    1. Import `Workflow` and `Sparkles` from `lucide-react` (add to existing import on line 5).
    2. Import `Session` type: `import type { Session } from 'next-auth'`.
    3. Update the component signature to accept `session`: `export function MobileNav({ session }: { session: Session | null })`.
    4. After the "Docs" link (line 53–61), add a session-conditional block:
       - If `session?.user`: render a standard `<a>` link to Agent Builder with `?from=asap` (same styling as other mobile nav items, `text-lg font-medium`).
       - If `!session?.user`: render a styled "Build Agents" text with `text-indigo-400` color (note: CTA can't be a Server Action form in a Client Component — use a plain link to the sign-in endpoint: `href="/api/auth/signin?callbackUrl=${encodeURIComponent(agentBuilderUrl)}"` or simply link to the Agent Builder directly, letting it handle login).
  - **Why**: Mobile users must have the same navigation options as desktop.
  - **Pattern**: Follow existing link pattern in `mobile-nav.tsx` (lines 32–61). Each link has `onClick={() => setOpen(false)}` to close the sheet after click.
  - **Verify**: Opening mobile nav on small viewport shows "Agent Builder" (logged in) or "Build Agents" (not logged in) after "Docs".

- [x] 4.3 Commit
  - **Command**: `git commit -m "feat(web): add Agent Builder link to mobile navigation"`
  - **Scope**: `apps/web/src/components/layout/Header.tsx`, `apps/web/src/components/layout/mobile-nav.tsx`

**Acceptance Criteria**:
- [x] `MobileNav` accepts a `session` prop.
- [x] Logged-in mobile users see "Agent Builder" link in the Sheet nav.
- [x] Non-logged-in mobile users see "Build Agents" CTA in indigo.
- [x] Clicking any link closes the Sheet (existing `onClick={() => setOpen(false)}` pattern).
- [x] No TypeScript errors.

---

### Task 5.0: Dashboard — Agent Builder Promotional Card

**Goal**: Add a promotional card at the top of the Dashboard "My Agents" tab to drive users to the Agent Builder.

**Context**: `DashboardClient` is a Client Component. It renders a tabbed interface with "My Agents", "Usage Metrics", and "API Keys" tabs. The card should appear at the very top of the "agents" `TabsContent`, before the "Registered Agents" heading and actions row.

**Trigger**: User navigates to `/dashboard` (authenticated).
**Enables**: Quick access to Agent Builder from the dashboard.
**Depends on**: Task 1.0 (env var for URL).

#### Sub-tasks

- [x] 5.1 Add `Workflow` icon import to `dashboard-client.tsx`
  - **File**: `apps/web/src/app/dashboard/dashboard-client.tsx` (modify existing)
  - **What**: Add `Workflow` to the lucide-react import on line 8: add it after `RefreshCw` in the existing destructured import.
  - **Why**: Used as the icon on the Agent Builder card.
  - **Verify**: No TypeScript error.

- [x] 5.2 Add Agent Builder promotional card to "agents" tab
  - **File**: `apps/web/src/app/dashboard/dashboard-client.tsx` (modify existing)
  - **What**: Inside `<TabsContent value="agents" className="space-y-6">` (line 68), add a new card **as the first child** (before the `<div className="flex justify-between items-center...">` on line 69):
    ```tsx
    <Card className="bg-gradient-to-r from-indigo-500/10 to-purple-500/10 border-indigo-500/20">
        <CardContent className="p-4 flex items-center gap-4">
            <div className="p-3 bg-indigo-500/10 rounded-lg border border-indigo-500/20 shrink-0">
                <Workflow className="w-6 h-6 text-indigo-400" />
            </div>
            <div className="flex-1 min-w-0">
                <h3 className="font-semibold text-sm">Agent Builder</h3>
                <p className="text-xs text-muted-foreground mt-0.5">
                    Design, connect, and run AI agents visually with our drag-and-drop builder.
                </p>
            </div>
            <Button asChild variant="outline" size="sm" className="shrink-0 border-indigo-500/30 text-indigo-400 hover:bg-indigo-500/10">
                <a
                    href={`${process.env.NEXT_PUBLIC_AGENT_BUILDER_URL ?? 'https://open-agentic-flow.vercel.app'}?from=asap`}
                    className="flex items-center gap-1.5"
                >
                    Open Agent Builder
                    <ExternalLink className="w-3 h-3" />
                </a>
            </Button>
        </CardContent>
    </Card>
    ```
  - **Why**: Provides a prominent entry point to the Agent Builder for dashboard users. Gradient background differentiates it from regular agent cards.
  - **Pattern**: Uses the same `Card`/`CardContent`/`Button` components already imported in the file. Gradient pattern follows PRD §6.3. Layout follows the pending registration card pattern (lines 92–114).
  - **Verify**: Visiting `/dashboard` (logged in) shows the Agent Builder card at the top of the "My Agents" tab with gradient background, Workflow icon, description, and "Open Agent Builder" button.
  - **Integration**: The `href` includes `?from=asap` which is consumed by agentic-orchestration for back-navigation.

- [x] 5.3 Commit
  - **Command**: `git commit -m "feat(dashboard): add Agent Builder promotional card"`
  - **Scope**: `apps/web/src/app/dashboard/dashboard-client.tsx`

**Acceptance Criteria**:
- [x] Agent Builder card is the first element inside the "agents" tab.
- [x] Card has gradient background (indigo → purple), Workflow icon, description text, and "Open Agent Builder" button.
- [x] Button links to `NEXT_PUBLIC_AGENT_BUILDER_URL?from=asap`.
- [x] Card layout is responsive (stacks nicely on mobile).
- [x] Existing dashboard functionality (pending registrations, agent cards, tabs) is unaffected.

---

### Task 6.0: Testing & Quality Assurance

**Goal**: Write unit tests covering all new functionality and verify the full CI pipeline passes.

**Context**: The project uses `vitest` + `@testing-library/react`. Tests are co-located in `__tests__/` folders. Existing test patterns: `apps/web/src/app/dashboard/verify/__tests__/verify-form.test.tsx` and `apps/web/src/proxy.test.ts`.

**Trigger**: Tasks 1.0–5.0 completed.
**Enables**: Merge confidence; CI green.
**Depends on**: Tasks 1.0–5.0 (all features implemented).

#### Sub-tasks

- [x] 6.1 Write unit tests for the `redirect` callback in `auth.ts`
  - **File**: `apps/web/src/__tests__/auth-redirect.test.ts` (create new)
  - **What**: Test the redirect callback logic in isolation:
    - Test: returns Agent Builder URL when `url` starts with `NEXT_PUBLIC_AGENT_BUILDER_URL`.
    - Test: returns `baseUrl` when `url` is an arbitrary external URL (e.g., `https://evil.com`).
    - Test: returns `url` when `url` starts with `baseUrl` (same origin).
    - Test: returns `baseUrl` when `NEXT_PUBLIC_AGENT_BUILDER_URL` is undefined (graceful fallback).
  - **Why**: The redirect callback is a security-critical function — an error here could allow open redirect attacks.
  - **Pattern**: Follow `apps/web/src/proxy.test.ts` pattern — import from vitest, use `describe`/`it`/`expect`. Since the callback is embedded in the NextAuth config, extract the redirect logic into a testable function or test by mocking the NextAuth config.
  - **Verify**: `npx vitest run src/__tests__/auth-redirect.test.ts` — all 4 tests pass.

- [x] 6.2 Write unit tests for Header Agent Builder rendering
  - **File**: `apps/web/src/components/layout/__tests__/header.test.tsx` (create new)
  - **What**: Test that the Header renders the correct Agent Builder element based on auth state:
    - Test: when session exists, "Agent Builder" link is rendered with correct `href` (including `?from=asap`).
    - Test: when session is null, "Build Agents" CTA is rendered with indigo styling.
    - Test: "Agent Builder" link is NOT rendered when session is null.
    - Test: "Build Agents" CTA is NOT rendered when session exists.
  - **Why**: Session-conditional rendering is a common source of bugs; both states must be verified.
  - **Pattern**: Since `Header` is a Server Component (async), testing it requires mocking `@/auth`. Mock `auth` to return a session object or `null`. Follow `apps/web/src/app/dashboard/verify/__tests__/verify-form.test.tsx` for vitest + testing-library setup.
  - **Verify**: `npx vitest run src/components/layout/__tests__/header.test.tsx` — all 4 tests pass.

- [x] 6.3 Write unit tests for MobileNav Agent Builder rendering
  - **File**: `apps/web/src/components/layout/__tests__/mobile-nav.test.tsx` (create new)
  - **What**: Test that `MobileNav` renders the correct Agent Builder element based on session prop:
    - Test: when `session.user` exists, "Agent Builder" link is rendered.
    - Test: when `session` is null, "Build Agents" CTA is rendered.
  - **Why**: Mobile parity must be verified.
  - **Pattern**: `MobileNav` is a Client Component — standard `render(<MobileNav session={mockSession} />)` works. Mock next/link and lucide-react icons as needed.
  - **Verify**: `npx vitest run src/components/layout/__tests__/mobile-nav.test.tsx` — all tests pass.

- [x] 6.4 Write unit tests for Dashboard Agent Builder card
  - **File**: `apps/web/src/app/dashboard/__tests__/dashboard-agent-builder-card.test.tsx` (create new)
  - **What**: Test that `DashboardClient` renders the Agent Builder card:
    - Test: card is present with text "Agent Builder" and "Open Agent Builder" button.
    - Test: button href includes `?from=asap`.
  - **Why**: Ensure the card renders correctly and the link is correct.
  - **Pattern**: Follow `apps/web/src/app/dashboard/verify/__tests__/verify-form.test.tsx` pattern. Render `<DashboardClient initialAgents={[]} username="test" />` and assert card content. Mock `next/navigation`, `swr`, and server actions.
  - **Verify**: `npx vitest run src/app/dashboard/__tests__/dashboard-agent-builder-card.test.tsx` — all tests pass.

- [x] 6.5 Run full CI check suite
  - **What**: Run the complete CI checks from `apps/web/`:
    1. `npm run lint` — ESLint passes.
    2. `npx tsc --noEmit` — TypeScript compiles without errors.
    3. `npx vitest run` — All tests pass (new and existing).
    4. `npm run build` — Next.js production build succeeds.
  - **Why**: Ensure no regressions before merge.
  - **Verify**: All 4 commands exit with code 0.

- [x] 6.6 Commit tests
  - **Command**: `git commit -m "test(web): add unit tests for cross-platform integration"`
  - **Scope**: All `__tests__/` files created in 6.1–6.4.

**Acceptance Criteria**:
- [x] All new tests pass (`npx vitest run`).
- [x] ESLint clean (`npm run lint`).
- [x] TypeScript clean (`npx tsc --noEmit`).
- [x] Next.js build succeeds (`npm run build`).
- [x] No existing tests broken.

---

## Definition of Done

- [x] `NEXT_PUBLIC_AGENT_BUILDER_URL` documented in `.env.example` and set on Vercel.
- [x] `auth.ts` has `redirect` callback allowing Agent Builder URL.
- [x] Header shows "Agent Builder" (logged in) or "Build Agents" CTA (not logged in).
- [x] Mobile nav shows the same elements.
- [x] Dashboard has Agent Builder promotional card.
- [x] All tests passing, linting clean, build succeeds.
- [ ] **agentic-orchestration deployed first** (Step 1 in cross-repo sequence).

**Total Sub-tasks**: 17
