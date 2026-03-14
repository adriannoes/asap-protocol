# Sprint M3: Data Tables & Bento Cards

## Overview
**Goal:** Upgrade data presentation across the app. Build a reusable `<DataTable>` component (TanStack Table recipe) for listings, and create the interactive Bento Grid component for high-value dashboard/feature areas. This sprint bridges the "functional" (tables) and "premium" (Bento) design patterns.

**Source of Truth:** `design-system.md` §7.2 (Data Presentation), §8.2 (Bento Cards), `analysis-bento-grid.md`.

## Relevant Files
- `apps/web/src/components/ui/table.tsx` — Shadcn `table` primitive (installed in M1).
- `apps/web/src/components/agents/data-table.tsx` — **Modified** Added aria-sort + data-sort-direction for E2E.
- `apps/web/src/components/agents/columns.tsx` — **Created** TanStack column definitions (Name, Status, Version, Skills).
- `apps/web/src/components/ui/bento-grid.tsx` — **Created** BentoGrid + BentoCard with hover lift, radial reveal, gleam overlay.
- `apps/web/src/app/browse/page.tsx` — Browse page, uses `BrowseContent` client component.
- `apps/web/src/app/browse/browse-content.tsx` — **Modified** Replaced card grid with DataTable; kept sidebar filters.
- `apps/web/src/app/dashboard/page.tsx` — Dashboard page, uses `DashboardClient`.
- `apps/web/src/app/dashboard/dashboard-client.tsx` — **Modified** Added BentoGrid metrics cards (Total Agents, Active Tasks, Verified).
- `apps/web/src/app/features/[slug]/page.tsx` — **Modified** Added BentoGrid with capability BentoCards per feature.
- `apps/web/package.json` — **Modified** Added `@tanstack/react-table`.
- `apps/web/tests/browse.spec.ts` — **Modified** DataTable assertions, sort test, pagination test; .first() for strict mode.
- `apps/web/tests/dashboard.spec.ts` — **Modified** Bento cards test (loadtest user + fixture registry); .first() for strict mode.
- `apps/web/playwright.config.ts` — **Modified** REGISTRY_URL for E2E fixture.
- `apps/web/src/proxy.ts` — **Modified** Exclude /api/fixtures from CORS Origin check for server-side fetch.
- `apps/web/src/proxy.test.ts` — **Modified** Added test for /api/fixtures pass-through.

## Tasks

- [x] 1.0 Scaffold DataTable Infrastructure
  - **Trigger / entry point:** User visits `/browse`.
  - **Enables:** Sortable, paginated agent listings replacing `.map()` lists.
  - **Depends on:** Sprint M1 (`table` primitive + `@tanstack/react-table` installed), Sprint M2 (Sidebar layout intact).

  - [x] 1.1 Create Column Definitions.
    - **File**: `apps/web/src/components/agents/columns.tsx` (**create new**)
    - **Directive**: `"use client"` — TanStack column definitions use JSX render functions.
    - **What to build**:
      1. Import `ColumnDef` from `@tanstack/react-table`.
      2. **DRY**: Import the Agent type from existing types in `@/lib/registry` (or wherever the registry types live) rather than redefining. If no shared type exists, create one in `@/types/agent.ts` and import it in both `columns.tsx` and `browse-content.tsx`.
         ```ts
         // Prefer: import { Agent } from "@/types/agent";
         // Fallback: define locally only if no shared type is possible.
         type AgentRow = {
           id: string;
           name: string;
           status: 'active' | 'pending' | 'revoked';
           version: string;
           skills: string[];
         }
         ```
      3. Define columns array with at least these columns:
         - **Name** column: sortable, bold text.
         - **Status** column: sortable, render as `<Badge>` with variant based on status.
         - **Version** column: render with `font-mono` (Geist Mono).
         - **Skills** column: render as comma-separated list or `<Badge>` chips.
      4. Use Shadcn `<Badge>` for status. Ensure badge colors follow monochromatic discipline (§8.3): `bg-black/5 dark:bg-white/10 backdrop-blur-sm`.
    - **File length estimate**: ~50–70 lines.

  - [x] 1.2 Create DataTable Wrapper Component.
    - **File**: `apps/web/src/components/agents/data-table.tsx` (**create new**)
    - **Directive**: `"use client"` — uses `useReactTable` hook and local state.
    - **What to build** (following the [Shadcn DataTable recipe](https://ui.shadcn.com/docs/components/data-table)):
      1. Import `useReactTable`, `getCoreRowModel`, `getPaginationRowModel`, `getSortedRowModel`, `getFilteredRowModel` from `@tanstack/react-table`.
      2. Import `Table`, `TableBody`, `TableCell`, `TableHead`, `TableHeader`, `TableRow` from `@/components/ui/table`.
      3. Accept generic props:
         ```tsx
         interface DataTableProps<TData, TValue> {
           columns: ColumnDef<TData, TValue>[];
           data: TData[];
           searchKey?: string; // column key for global filter
         }
         ```
      4. Implement:
         - **Global search filter**: `<Input>` at the top filtering by `searchKey`.
           - **URL State** (§7 State Management): Sync the search value with `?search=` query param using `useSearchParams()` for shareable/bookmarkable filtered views. Example:
             ```tsx
             const searchParams = useSearchParams();
             const [search, setSearch] = useState(searchParams.get('search') ?? '');
             ```
         - **Sorting**: Click column headers to sort (render arrow indicators via `ArrowUpDown` from `lucide-react`).
         - **Pagination**: Shadcn `<Button>` (outline variant) for "Previous" / "Next" at the bottom with row count.
      5. **Row hover style** (from `design-system.md` §7.2): `hover:bg-muted/50` — NOT the heavy Bento lifts.
      6. **Mobile responsiveness** (from `mobile-strategy.md` §2):
         - Wrap the `<Table>` in a `<div className="overflow-x-auto">` for horizontal scroll on small screens.
         - Optionally hide non-essential columns on mobile: `<TableCell className="hidden sm:table-cell">` for Version and Skills.
         - Search input and Pagination buttons at `w-full` on mobile.
      7. **Data-testid requirements**:
         - Table root: `data-testid="data-table"`
         - Search input: `data-testid="data-table-search"` with `placeholder="Search agents..."`
         - Pagination: `data-testid="data-table-pagination"`
    - **File length estimate**: ~80–120 lines.

  - [x] 1.3 Integrate DataTable into Browse Page.
    - **File**: `apps/web/src/app/browse/browse-content.tsx` (**modify**)
    - **What to change**:
      1. Replace the current `.map()` agent list rendering with:
         ```tsx
         import { DataTable } from "@/components/agents/data-table";
         import { columns } from "@/components/agents/columns";
         // ...
         <DataTable columns={columns} data={agents} searchKey="name" />
         ```
      2. Keep the existing category/filter sidebar if it exists — the DataTable replaces only the list area.
      3. Ensure the search input in the DataTable serves the same role as the current `Search agents...` placeholder.
    - **E2E impact**: The existing `browse.spec.ts` checks for `getByPlaceholder('Search agents...')`. Ensure the DataTable search input uses the same placeholder text OR update the test.

- [x] 2.0 Implement Bento Grid Component
  - **Depends on:** Sprint M1 (tokens ready).
  - **Reference**: `analysis-bento-grid.md` and `design-system.md` §8.2.

  - [x] 2.1 Create Bento Grid Root Component.
    - **File**: `apps/web/src/components/ui/bento-grid.tsx` (**create new**)
    - **Directive**: `"use client"` — uses `group-hover` interactions which require client-side CSS, but no hooks needed. Can omit `"use client"` if only using Tailwind classes (Tailwind hover works server-side). Add `"use client"` only if Framer Motion hover animations are added later.
    - **What to build**: Two sub-components (composition pattern per §5):

      **BentoGrid** (container):
      ```tsx
      interface BentoGridProps {
        children: React.ReactNode;
        className?: string;
      }
      // Layout: grid grid-cols-1 md:grid-cols-3 gap-3
      // Use cn() for className merging (§4)
      ```

      **BentoCard** (items):
      ```tsx
      interface BentoCardProps {
        title: string;
        description: string;
        icon: LucideIcon;
        value?: string | number;  // Metrics display
        className?: string;       // For spanning: "md:col-span-2"
      }
      ```
      **Visual rules for BentoCard** (from `analysis-bento-grid.md`):
      1. **Base state**: `border border-border bg-card rounded-xl p-6 relative overflow-hidden group transition-all duration-300`.
      2. **The Lift** (§8.2): `hover:-translate-y-0.5 will-change-transform` for 60fps hover smoothness.
         - **Touch device scoping** (from `mobile-strategy.md` §4): Wrap hover effects in `@media (hover: hover)` so they only activate on pointer devices. On touch, use `active:scale-[0.98]` as a press feedback alternative.
         ```css
         @media (hover: hover) {
           .group:hover { transform: translateY(-0.125rem); }
         }
         ```
      3. **Ambient shadow**: `hover:shadow-sm` (use Tailwind token instead of arbitrary shadow value — §4 no arbitrary values).
      4. **Radial grid reveal**: Add an absolute `div` child with:
         ```
         absolute inset-0 opacity-0 group-hover:opacity-100 transition-opacity duration-500
         ```
         > **⚠️ Arbitrary value exception**: The radial gradient (`bg-[radial-gradient(...)]`) and its sizing (`bg-[length:4px_4px]`) require arbitrary values because Tailwind has no built-in radial-gradient utilities. This is an accepted design system exception documented in `analysis-bento-grid.md`. Use inline style as an alternative if the team prefers:
         > ```tsx
         > style={{ backgroundImage: 'radial-gradient(circle, rgba(0,0,0,0.02) 1px, transparent 1px)', backgroundSize: '4px 4px' }}
         > ```
      5. **Gleam border overlay**: Secondary absolute `div`:
         ```
         absolute inset-0 opacity-0 group-hover:opacity-100 transition-opacity duration-500
         bg-gradient-to-br from-transparent via-muted to-transparent
         ```
         (Use `via-muted` Tailwind token instead of `via-gray-100/50` — §4 use theme tokens.)
      6. Icon wrapper: `bg-muted rounded-lg p-2 mb-3 w-fit`.
      7. Value display: `text-3xl font-bold font-mono tracking-tight`.
    - **Data-testid**: Each card: `data-testid="bento-card-{title-slug}"`.
    - **File length estimate**: ~80–100 lines.

  - [x] 2.2 Apply Bento to Dashboard.
    - **File**: `apps/web/src/app/dashboard/dashboard-client.tsx` (**modify**)
    - **What to change**: Replace the current metrics display with:
      ```tsx
      <BentoGrid>
        <BentoCard
          icon={Bot}
          title="Total Agents"
          value={agents.length}
          description="Registered agents in your account"
          className="md:col-span-2"
        />
        <BentoCard
          icon={Activity}
          title="Active Tasks"
          value={0}
          description="Currently running task sessions"
        />
        <BentoCard
          icon={Shield}
          title="Verified"
          value={agents.filter(a => a.verified).length}
          description="Agents with verified trust badges"
        />
      </BentoGrid>
      ```
    - **Aesthetic check**: Ensure gradients use **only** Zinc/Indigo tokens — no colored radials.

  - [x] 2.3 Apply Bento to Features Page.
    - **File**: `apps/web/src/app/features/[slug]/page.tsx` (**modify**)
    - **What to change**: Apply the BentoCard pattern to feature detail cards. Each feature's capabilities should render as BentoCard items within a BentoGrid.
    - **Why**: PRD §4.3 explicitly targets this route for Bento refactoring.

- [x] 3.0 E2E Test Updates & New Tests
  - **Depends on:** 1.0 and 2.0.

  - [x] 3.1 Update Browse Page E2E Test.
    - **File**: `apps/web/tests/browse.spec.ts` (**modified**)
    - **Current test** (25 lines): Checks page title, heading "Agent Registry", search placeholder, filter headings (Skills, Trust Levels), SLA checkbox.
    - **What to change/add**:
      1. **Keep** existing title and heading assertions (they should still pass).
      2. **Update search selector** if the DataTable changed the placeholder text.
      3. **Add** DataTable-specific assertions:
         ```ts
         // Verify DataTable renders
         await expect(page.getByTestId('data-table')).toBeVisible();
         
         // Verify table has header row with expected columns
         await expect(page.getByRole('columnheader', { name: /Name/i })).toBeVisible();
         await expect(page.getByRole('columnheader', { name: /Status/i })).toBeVisible();
         ```
      4. **Add** sorting test:
         ```ts
         test('can sort agents by name', async ({ page }) => {
           await page.goto('/browse');
           const nameHeader = page.getByRole('columnheader', { name: /Name/i });
           await nameHeader.click();
           // Verify sort indicator appears (aria-sort attribute or visual indicator)
           await expect(nameHeader).toHaveAttribute('aria-sort', /(ascending|descending)/);
         });
         ```
      5. **Add** pagination test (if enough data):
         ```ts
         test('shows pagination controls', async ({ page }) => {
           await page.goto('/browse');
           await expect(page.getByTestId('data-table-pagination')).toBeVisible();
         });
         ```

  - [x] 3.2 Add Dashboard Bento Visual Test.
    - **File**: `apps/web/tests/dashboard.spec.ts` (**modified**)
    - **What to add**:
      ```ts
      test('dashboard shows Bento metric cards', async ({ page }) => {
        await expect(page.getByTestId('bento-card-total-agents')).toBeVisible();
        await expect(page.getByTestId('bento-card-active-tasks')).toBeVisible();
      });
      ```
    - **Why**: Ensures Bento cards render correctly after the dashboard restructure.

## Acceptance Criteria
- `/browse` displays a sortable, paginated DataTable instead of a basic flex list.
- DataTable supports searching by agent name.
- Column headers are clickable for sort toggling.
- Dashboard cards use the BentoCard component with hover lift effect (`-translate-y-0.5`) and radial gradient reveal.
- Hover transitions are 60fps smooth (`will-change-transform`).
- `features/[slug]` pages use Bento cards for capability display.
- All updated E2E tests pass (browse sorting, pagination, dashboard Bento cards).
- No regression in auth-journey, register, or verify E2E tests.
