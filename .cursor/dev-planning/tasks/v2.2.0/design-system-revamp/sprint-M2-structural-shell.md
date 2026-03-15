# Sprint M2: Structural Shell & Feedback

## Overview
**Goal:** Replace the current application navigation with the modern Shadcn `<Sidebar>`, creating a cohesive "Clean Architect" shell. Standardize loading states, empty states, and create a reusable Glassmorphism container. This is the biggest structural change and **will break existing E2E selectors** — so E2E updates are mandatory.

**Mobile Reference:** All responsive layout decisions MUST follow `.cursor/design/mobile-strategy.md` — especially the Sidebar → hamburger/Sheet behavior on mobile breakpoints.

**Source of Truth:** `design-system.md` §7.1 (Sidebar), §7.4 (Empty States & Loading), §8.1 (Glassmorphism).

## Relevant Files
- `apps/web/src/components/ui/empty-state.tsx` — **New** EmptyState component (icon, title, description, optional action); h2 for E2E heading.
- `apps/web/src/app/dashboard/loading.tsx` — **New** Skeleton grid (6 cards) with data-testid="dashboard-skeletons".
- `apps/web/src/components/layout/app-sidebar.tsx` — **New** AppSidebar with NAV_ITEMS, usePathname active state, data-testid for E2E.
- `apps/web/src/app/dashboard/layout.tsx` — **New** Dashboard layout with SidebarProvider, AppSidebar, SidebarTrigger (lg:hidden), semantic main.
- `apps/web/src/components/layout/Header.tsx` — Server Component wrapper; fetches session, delegates to HeaderContent.
- `apps/web/src/components/layout/header-content.tsx` — **New** Client Header with usePathname(); hides center nav + MobileNav on /dashboard/*.
- `apps/web/src/actions/auth.ts` — **New** Server actions for signIn/signOut (used by HeaderContent).
- `apps/web/src/components/layout/mobile-nav.tsx` — Current mobile navigation (4292 bytes, will be replaced by Sidebar's built-in Sheet drawer).
- `apps/web/src/app/dashboard/page.tsx` — Dashboard page with `DashboardClient` component.
- `apps/web/src/app/dashboard/dashboard-client.tsx` — Uses EmptyState for "No agents found"; Skeleton import available.
- `apps/web/src/components/ui/glass-container.tsx` — **New** GlassContainer (design-system §8.1); frosted glass, gradient border, dark mode.
- `apps/web/tests/dashboard.spec.ts` — Updated: sidebar assertions, navigate via sidebar, mobile hamburger test.
- `apps/web/tests/auth-journey.spec.ts` — Unchanged; Register Agent / Explore Agents from HeroSection (/) still work.
- `apps/web/playwright.config.ts` — Mobile Chrome project enabled.

## Tasks

- [x] 1.0 Implement Global Sidebar
  - **Trigger / entry point:** User navigates to any `apps/web/src/app/dashboard/*` route.
  - **Enables:** Consistent, accessible navigation for all dashboard routes.
  - **Depends on:** Sprint M1 (Shadcn `sidebar` installed).

  - [x] 1.1 Create AppSidebar component.
    - **File**: `apps/web/src/components/layout/app-sidebar.tsx` (**create new**)
    - **Directive**: `"use client"` — uses `usePathname()` hook (§2 RSC-first: only add `"use client"` when hooks are needed).
    - **What to build**:
      1. Import `Sidebar`, `SidebarContent`, `SidebarGroup`, `SidebarGroupLabel`, `SidebarGroupContent`, `SidebarMenu`, `SidebarMenuItem`, `SidebarMenuButton` from `@/components/ui/sidebar`.
      2. Define navigation items as a **typed constant** array (§ Clean Code: semantic naming):
         ```ts
         const NAV_ITEMS = [
           { label: 'Dashboard', icon: LayoutDashboard, href: '/dashboard', testId: 'sidebar-link-dashboard' },
           { label: 'Browse Agents', icon: Search, href: '/browse', testId: 'sidebar-link-browse' },
           { label: 'Register Agent', icon: Plus, href: '/dashboard/register', testId: 'sidebar-link-register' },
           { label: 'Verify Agent', icon: ShieldCheck, href: '/dashboard/verify', testId: 'sidebar-link-verify' },
         ] as const;
         ```
      3. Use `usePathname()` from `next/navigation` to highlight active menu item.
      4. Map `NAV_ITEMS` to render — do NOT repeat JSX per item (§ DRY principle).
      5. **Aesthetic rules** (from `design-system.md` §7.1):
         - Background: `bg-background` or `bg-sidebar` (NOT a dark contrasting sidebar).
         - No heavy visual separation — rely on subtle `border-sidebar-border` only.
         - Font: `font-sans` (Geist Sans, inherited from body).
    - **Data-testid requirements** (for E2E):
      - Root sidebar: `data-testid="app-sidebar"`
      - Each menu item: `data-testid="sidebar-link-{name}"` (e.g., `sidebar-link-dashboard`)
    - **File length estimate**: ~60–80 lines.

  - [x] 1.2 Create Dashboard Layout with SidebarProvider.
    - **File**: `apps/web/src/app/dashboard/layout.tsx` (**create new** — currently doesn't exist as a dedicated file)
    - **Directive**: This can be a **Server Component** (no `"use client"` needed). `SidebarProvider` is a client component internally, but can be server-rendered as a child import. If React Context errors arise, add `"use client"` as a last resort.
    - **What to build**:
      1. Import `SidebarProvider`, `SidebarTrigger` from `@/components/ui/sidebar`.
      2. Import `AppSidebar` from `@/components/layout/app-sidebar`.
      3. Use semantic `<main>` tag for content area (§5 Accessibility).
      4. Wrap `children` in:
         ```tsx
         <SidebarProvider>
           <AppSidebar />
           <main className="flex-1" data-testid="dashboard-main">
             <SidebarTrigger className="lg:hidden" data-testid="sidebar-mobile-trigger" />
             {children}
           </main>
         </SidebarProvider>
         ```
      5. **Mobile behavior** (from `mobile-strategy.md` §4):
         - Below `lg` breakpoint: Sidebar auto-hides, trigger button visible.
         - Shadcn Sidebar handles this natively via its built-in Sheet drawer.
    - **Important**: The existing `dashboard/page.tsx` must still work inside this new layout. The `<div className="container mx-auto...">` wrapper in `page.tsx` stays; the layout wraps it.
    - **File length estimate**: ~30–40 lines.

  - [x] 1.3 Update existing Header for public/dashboard route distinction.
    - **File**: `apps/web/src/components/layout/Header.tsx` (**modify**)
    - **What to change**: The global `<Header>` currently handles all navigation. After the Sidebar is added:
      - **Public routes** (`/`, `/browse`, `/features/*`): Keep the Header as-is.
      - **Dashboard routes** (`/dashboard/*`): The Header should remain but simplify — the main navigational links are now in the Sidebar. The Header on dashboard routes should only show the logo, theme toggle, and user avatar/session info.
    - **How**: Use `usePathname()` to conditionally render navigation items. If path starts with `/dashboard`, hide the main nav links.
    - **Do NOT delete `Header.tsx`** — it's still used on public routes.

- [x] 2.0 Standardize Feedback States
  - **Depends on:** Sprint M1 (`skeleton` already installed at `components/ui/skeleton.tsx`).

  - [x] 2.1 Create Premium Empty State Component.
    - **File**: `apps/web/src/components/ui/empty-state.tsx` (**create new**)
    - **What to build**: A reusable component with this API:
      ```tsx
      interface EmptyStateProps {
        icon: LucideIcon;       // e.g., PackageSearch
        title: string;          // e.g., "No agents found"
        description: string;    // e.g., "You haven't registered any agents yet."
        actionLabel?: string;   // e.g., "Register your first agent"
        actionHref?: string;    // e.g., "/dashboard/register"
      }
      ```
    - **Visual rules** (from `design-system.md` §7.4):
      - Icon: Centered, `text-muted-foreground opacity-50`, size `h-12 w-12`.
      - Title: `text-lg font-semibold text-foreground`.
      - Description: `text-sm text-muted-foreground max-w-sm text-center`.
      - Action button: Use Shadcn `<Button>` (default variant).
      - Strict monochromatic discipline (§8.3) — NO colored icons or buttons beyond the standard primary.
    - **Data-testid**: `data-testid="empty-state"`, `data-testid="empty-state-action"`.
    - **File length estimate**: ~40–50 lines.

  - [x] 2.2 Apply Empty State to Dashboard.
    - **File**: `apps/web/src/app/dashboard/dashboard-client.tsx` (**modify** — this is the client component imported by `dashboard/page.tsx`)
    - **What to change**: Find the current "No agents found" text rendering and replace it with:
      ```tsx
      <EmptyState
        icon={PackageSearch}
        title="No agents found"
        description="You haven't registered any agents yet."
        actionLabel="Register your first agent"
        actionHref="/dashboard/register"
      />
      ```
    - **E2E impact**: The existing `dashboard.spec.ts` test uses `getByRole('heading', { name: 'No agents found' })`. The `EmptyState` component MUST render the title as an `<h2>` or `<h3>` heading to keep this selector working.

  - [x] 2.3 Apply Skeletons to Dashboard.
    - **File**: `apps/web/src/app/dashboard/dashboard-client.tsx` (**modify**)
    - **What to change**: If a loading state exists (or add one via Suspense), replace any spinner/loading text with:
      ```tsx
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {Array.from({ length: 6 }).map((_, i) => (
          <Skeleton key={i} className="h-[200px] w-full rounded-xl" />
        ))}
      </div>
      ```
    - **Import**: `import { Skeleton } from "@/components/ui/skeleton"` (already exists).
    - **Data-testid**: Skeleton container: `data-testid="dashboard-skeletons"`.

- [x] 3.0 Reusable Glassmorphism Component
  - **Depends on:** Sprint M1 (Tokens ready).

  - [x] 3.1 Create GlassContainer Component.
    - **File**: `apps/web/src/components/ui/glass-container.tsx` (**create new**)
    - **What to build**: A wrapper component implementing `design-system.md` §8.1:
      ```tsx
      import { cn } from "@/lib/utils"; // §4: ALWAYS use cn() for conditional classes

      interface GlassContainerProps {
        children: React.ReactNode;
        className?: string;
      }

      export function GlassContainer({ children, className }: GlassContainerProps) {
        return (
          <div className={cn(
            // Outer wrapper: 1px gradient pseudo-border
            "bg-gradient-to-b from-black/10 to-white/10 p-px rounded-2xl backdrop-blur-lg",
            // Dark mode equivalent
            "dark:from-white/10 dark:to-white/5"
          )}>
            <div className={cn(
              // Inner element: frosted glass
              // Use rounded-2xl (Tailwind token) instead of arbitrary rounded-[calc(...)]
              // The 1px difference from p-px is visually negligible
              "bg-white/95 backdrop-blur-md rounded-2xl",
              // Dark mode
              "dark:bg-black/80",
              className
            )}>
              {children}
            </div>
          </div>
        );
      }
      ```
    - **Rule compliance**:
      - Uses `cn()` helper for class merging (§4).
      - Uses `rounded-2xl` Tailwind token instead of arbitrary `rounded-[calc(1rem-1px)]` (§4: no arbitrary values).
      - Accepts `className` for Open/Closed extensibility (SOLID).
      - Single responsibility: only handles the glass visual wrapper.
    - **Why**: PRD §2 lists Glassmorphism as a top-level goal. Reusable wrapper consumed by M4 (auth forms) and M5 (hero CTAs).
    - **Do NOT use it on dashboard cards** — cards use the Bento pattern (M3) instead.
    - **File length estimate**: ~25–30 lines.

- [x] 4.0 E2E Test Updates (Navigation)
  - **Depends on:** 1.0 (Sidebar restructure complete), 2.0 (Empty state updated).
  - **Context**: Current tests use selectors that will break:
    - `dashboard.spec.ts`: Uses `getByRole('heading', { name: 'Developer Dashboard' })` and tab selectors.
    - `auth-journey.spec.ts`: Uses `getByRole('link', { name: 'Register Agent' })` and `getByRole('button', { name: /Connect \/ Login/i })` — these come from the Header.

  - [x] 4.1 Update Dashboard E2E Test.
    - **File**: `apps/web/tests/dashboard.spec.ts` (**modify**)
    - **What to change**:
      1. **Add Sidebar visibility assertion** after login:
         ```ts
         await expect(page.getByTestId('app-sidebar')).toBeVisible();
         ```
      2. **Verify Sidebar navigation links** exist:
         ```ts
         await expect(page.getByTestId('sidebar-link-dashboard')).toBeVisible();
         await expect(page.getByTestId('sidebar-link-browse')).toBeVisible();
         await expect(page.getByTestId('sidebar-link-register')).toBeVisible();
         ```
      3. **Add Sidebar navigation test** — click Browse link from Sidebar and verify route:
         ```ts
         test('can navigate via sidebar', async ({ page }) => {
           await page.getByTestId('sidebar-link-browse').click();
           await expect(page).toHaveURL(/\/browse/);
         });
         ```
      4. **Keep existing empty state assertions** — they should still pass if `EmptyState` renders the heading correctly.

  - [x] 4.2 Update Auth Journey E2E Test.
    - **File**: `apps/web/tests/auth-journey.spec.ts` (**modify**)
    - **What to check**: The "Register Agent" link and "Connect / Login" button are in the `Header.tsx`, which is NOT being replaced on public routes. These selectors should still work. BUT verify after changes:
      1. Run the test and confirm the 4 existing assertions pass.
      2. If Header conditionally hides nav items on dashboard routes, the "Explore Agents" test (which runs from `/`) should still work since `/` is a public route.

  - [x] 4.3 Add Mobile Sidebar E2E Test.
    - **File**: `apps/web/tests/dashboard.spec.ts` (**modify**, add new test)
    - **What to add**:
      ```ts
      test('mobile: sidebar triggers via hamburger menu', async ({ page }) => {
        // Set mobile viewport
        await page.setViewportSize({ width: 375, height: 812 });
        await page.goto('/api/auth/test-login?username=e2e-tester-no-agents');
        
        // Sidebar should be hidden on mobile
        await expect(page.getByTestId('app-sidebar')).toBeHidden();
        
        // Click the trigger button
        await page.getByTestId('sidebar-mobile-trigger').click();
        
        // Sidebar should now be visible (via Sheet drawer)
        await expect(page.getByTestId('app-sidebar')).toBeVisible();
      });
      ```
    - **Why**: `mobile-strategy.md` mandates hamburger → Sheet behavior. This test validates it.

  - [x] 4.4 Enable Mobile Chrome in Playwright Config (Optional but Recommended).
    - **File**: `apps/web/playwright.config.ts` (**modify**)
    - **What to change**: Uncomment the `Mobile Chrome` project (currently commented out at lines 54–57):
      ```ts
      {
        name: 'Mobile Chrome',
        use: { ...devices['Pixel 5'] },
      },
      ```
    - **Why**: We're adding mobile-specific behavior. Running tests on a mobile viewport ensures we don't break responsive behavior across sprints.
    - **Risk**: Adds ~9 extra test runs per E2E suite execution. If CI time is a concern, keep commented and only enable locally.

## Acceptance Criteria
- Navigating to `/dashboard` renders the new collapsible Shadcn Sidebar with at least 4 navigation items.
- Mobile view (`< 1024px`) correctly hides the Sidebar and provides a trigger button (per `mobile-strategy.md`).
- Dashboard empty state uses the new `EmptyState` component with proper heading semantics.
- Simulating a slow network shows Skeleton grids instead of spinners.
- `GlassContainer` component exists, renders in both Light/Dark modes, and is not yet used in production pages (only available for M4/M5).
- All 9+ existing E2E tests pass across 3 browsers with updated selectors.
- New mobile sidebar E2E test passes.
