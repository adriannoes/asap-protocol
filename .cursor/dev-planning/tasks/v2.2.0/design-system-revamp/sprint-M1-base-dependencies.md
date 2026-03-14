# Sprint M1: Foundation & Dependencies

## Overview
**Goal:** Establish the technical foundation for the Design System Revamp. No major UI rewrites yet — only installing dependencies, verifying design tokens, and ensuring the environment is ready for Sprints M2–M5. This PR should be purely additive or configuration-based.

**Source of Truth:** `.cursor/design/design-system.md` §2 (Technology Stack), §3 (Typography), §4 (Color Palette).

## Relevant Files
- `apps/web/package.json` — For new dependencies.
- `apps/web/src/app/globals.css` — For the finalized OKLCH palette and font imports (126 lines, already has tokens).
- `apps/web/src/app/layout.tsx` — Root layout, imports `Geist` and `Geist_Mono`, wraps with `TooltipProvider`.
- `apps/web/src/components/ui/*` — Shadcn components (sidebar, table, dialog, tooltip, etc.).
- `apps/web/.npmrc` — Project-level pnpm store-dir for consistent installs.

## Tasks

- [x] 1.0 Dependency Installation
  - **Trigger / entry point:** Start of Sprint M1.
  - **Enables:** Sprints M2-M5 (Animations, 3D, Structural components).
  - **Depends on:** Current `main` branch state.

  - [x] 1.1 Install Animation & 3D libraries.
    - **Command:** Run in `apps/web/`:
      ```bash
      pnpm install framer-motion three @react-three/fiber @types/three
      ```
    - **Why**: `framer-motion` is required for M2 (GlassContainer transitions), M3 (Bento hover physics), M4 (AnimatePresence auth), M5 (staggered typography). `three` + `@react-three/fiber` are required for M4 (WebGL Canvas shader backgrounds).
    - **Verification**: After install, confirm in `apps/web/package.json` that all 4 packages appear under `dependencies` or `devDependencies` without version conflicts. Run `pnpm ls framer-motion three @react-three/fiber` to verify.

  - [x] 1.2 Install required Shadcn components.
    - **Command:** Run in `apps/web/`:
      ```bash
      npx shadcn@latest add sidebar table dialog
      ```
    - **Why**: `sidebar` → M2 (Global Shell). `table` → M3 (DataTable recipe base). `dialog` → M3 (creation flows). `skeleton` already exists in `components/ui/skeleton.tsx`.
    - **Note**: Shadcn `data-table` is NOT a CLI component — it's a recipe built on TanStack Table. The `table` primitive is installed here; the full DataTable scaffolding (columns + wrapper) will be created in Sprint M3.
    - **Verification**: Confirm these new files exist:
      - `apps/web/src/components/ui/sidebar.tsx`
      - `apps/web/src/components/ui/table.tsx`
      - `apps/web/src/components/ui/dialog.tsx` (already exists — may get updated)
    - **Important**: If Shadcn prompts to overwrite existing `dialog.tsx`, choose **yes** to get the latest version.

  - [x] 1.3 Install TanStack Table dependency.
    - **Command:** Run in `apps/web/`:
      ```bash
      pnpm install @tanstack/react-table
      ```
    - **Why**: Required by the DataTable recipe in Sprint M3. The Shadcn `table` component is only the visual primitive; TanStack Table provides the sorting, pagination, and filtering logic.
    - **Verification**: `pnpm ls @tanstack/react-table` shows the installed version.

- [x] 2.0 Theme & Typography Verification
  - **Depends on:** 1.0 (Dependency Installation).
  - **Context**: The current `globals.css` (126 lines) and `layout.tsx` (47 lines) **already have** most tokens correctly configured. This task is about **auditing and verifying** — not rewriting from scratch.

  - [x] 2.1 Audit Global CSS Tokens.
    - **File**: `apps/web/src/app/globals.css` (modify if needed)
    - **What to verify**:
      1. `--radius: 0.625rem` exists at line 51 → ✅ already correct.
      2. Light mode variables (`:root` block, lines 50–83) match `design-system.md` §4 Light Mode exactly:
         - `--background: oklch(1 0 0)` ✅
         - `--foreground: oklch(0.145 0 0)` ✅
         - `--primary: oklch(0.205 0 0)` ✅
         - `--destructive: oklch(0.577 0.245 27.325)` ✅
         - `--ring: oklch(0.708 0 0)` ✅
      3. Dark mode variables (`.dark` block, lines 85–117) match `design-system.md` §4 Dark Mode:
         - `--background: oklch(0.145 0 0)` ✅
         - `--border: oklch(1 0 0 / 10%)` ✅
         - `--input: oklch(1 0 0 / 15%)` ✅
      4. Sidebar tokens exist → ✅ already present (lines 12–19, 75–82, 109–116).
    - **Action**: If all values match, no changes needed. If any lingering unused variables exist (e.g., old non-OKLCH values), remove them. Document what was removed in the PR description.
    - **Anti-pattern check**: Search `globals.css` for any `#hex` or `rgb()` color values — these MUST be replaced with OKLCH equivalents per the design system.

  - [x] 2.2 Verify Geist Fonts.
    - **File**: `apps/web/src/app/layout.tsx` (verify, modify only if needed)
    - **What to verify**:
      1. Line 2: `import { Geist, Geist_Mono } from 'next/font/google';` ✅ already correct.
      2. Lines 10-18: Both fonts instantiated with correct `variable` names:
         - `Geist({ variable: '--font-geist-sans', subsets: ['latin'] })` ✅
         - `Geist_Mono({ variable: '--font-geist-mono', subsets: ['latin'] })` ✅
      3. Line 33: `<body>` tag applies both variables: `${geistSans.variable} ${geistMono.variable}` ✅
      4. `globals.css` lines 10-11 map these to Tailwind: `--font-sans: var(--font-geist-sans)` and `--font-mono: var(--font-geist-mono)` ✅
    - **Action**: If all correct, no changes needed. Just confirm in the PR description.

- [x] 3.0 Build Verification
  - **Depends on:** 1.0 and 2.0.
  - [x] 3.1 Run the full build.
    - **Command:** From project root:
      ```bash
      pnpm build
      ```
    - **What to check**: Build completes without errors. Pay special attention to:
      - No TypeScript errors from `@types/three`.
      - No CSS compilation errors from any new token.
      - No dependency resolution conflicts.
  - [x] 3.2 Run existing E2E tests.
    - **Command:** From `apps/web/`:
      ```bash
      npx playwright test
      ```
    - **What to check**: All 5 existing test files pass (auth-journey: 4 tests, browse: 1 test, dashboard: 1 test, register: 1 test, verify: 2 tests = **9 total tests × 3 browsers = 27 test runs**). No visual regressions since we haven't changed any layouts, only added dependencies and verified tokens.
    - **If any test fails**: The failure is unrelated to M1 changes (since M1 is purely additive). Investigate the root cause and document it, but do not block the PR.

## Acceptance Criteria
- `apps/web/package.json` contains `framer-motion`, `three`, `@react-three/fiber`, `@types/three`, and `@tanstack/react-table` without version conflicts.
- Shadcn `sidebar`, `skeleton`, `table`, and `dialog` exist in `components/ui/`.
- App builds successfully (`pnpm build`) with zero errors.
- All 9 existing E2E tests pass across 3 browsers.
- No visual regressions on any existing page — this sprint is purely foundational infrastructure.
