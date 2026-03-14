# Sprint M5: Hero Animations & Final Polish

## Overview
**Goal:** Apply the final high-end visual touches to entry routes (Landing and Developer Experience) using animated SVG background paths and staggered typography reveals. Then conduct a comprehensive anti-boilerplate QA sweep and icon migration audit to close out the Design System Revamp.

**Source of Truth:** `design-system.md` §8.4 (Typography Motion), §8.1 (Glassmorphism for CTA button), `analysis-background-paths.md`.

## Relevant Files
- `apps/web/src/app/page.tsx` — Landing page root (server component, renders hero, features, CTA sections).
- `apps/web/src/app/developer-experience/page.tsx` — Dev Ex entry point. Modified: added BackgroundPaths (pathCount=4) to hero section.
- `apps/web/src/components/ui/background-paths.tsx` — **Created** SVG path animator with Framer Motion, mobile-responsive pathCount.
- `apps/web/src/components/ui/animated-text.tsx` — **Created** word-by-word staggered text reveal with spring physics.
- `apps/web/src/components/landing/HeroSection.tsx` — Refactored to Server Component. BackgroundPaths + AnimatedText + HeroTerminal composition.
- `apps/web/src/components/landing/HeroTerminal.tsx` — **Created** extracted client component with terminal animation logic (useState/useEffect).
- `apps/web/src/components/landing/FeaturedAgents.tsx` — Modified: hover:shadow-lg removed, replaced with hover:border-indigo-500/30.
- `apps/web/src/app/dashboard/dashboard-client.tsx` — Modified: rounded-full → rounded-[--radius] on icon wrapper.
- `apps/web/src/app/auth/signin/signin-form.tsx` — Modified: custom GitHub SVG replaced with Lucide Github icon.
- `apps/web/tests/auth-journey.spec.ts` — Modified: added 2 E2E tests for Landing Page animations (BackgroundPaths + AnimatedText).
- `apps/web/src/components/ui/glass-container.tsx` — **Exists** from M2 (reuse for CTA button wrapper).
- `apps/web/tests/auth-journey.spec.ts` — Tests that navigate from `/` (Explore Agents, Register Agent).

## Tasks

- [x] 1.0 Hero Background Path Animations
  - **Trigger / entry point:** User visits the Landing Page (`/`).
  - **Depends on:** Sprint M1 (`framer-motion` installed).

  - [x] 1.1 Create FloatingPaths Component.
    - **File**: `apps/web/src/components/ui/background-paths.tsx` (**create new**)
    - **Directive**: `"use client"` — uses Framer Motion hooks and SVG animation (§2 RSC-first).
      1. Mark as `"use client"`.
      2. Import `motion` from `framer-motion`.
      3. Create a component that generates multiple SVG `<path>` elements with organic bezier curves.
      4. Each path should have:
         - Very low opacity stroke: `stroke="currentColor"` with `opacity={0.05 + (i * 0.02)}`.
         - Theme-aware color: The SVG container uses `className="text-foreground"` so paths inherit the right color in light/dark mode.
         - Animated `strokeDashoffset` using Framer Motion:
           ```tsx
           <motion.path
             d={pathData}
             fill="none"
             stroke="currentColor"
             strokeWidth={0.5}
             strokeDasharray="1000"
             initial={{ strokeDashoffset: 1000 }}
             animate={{ strokeDashoffset: 0 }}
             transition={{
               duration: 20 + (i * 5),
               repeat: Infinity,
               repeatType: "loop",
               ease: "linear",
             }}
           />
           ```
      5. Generate 5–8 paths with different curves and timing offsets to create layered depth.
      6. The container should be `absolute inset-0 overflow-hidden -z-10`.
      7. Expose a clean API (use `cn()` for className merging per §4):
         ```tsx
         interface BackgroundPathsProps {
           className?: string;
           pathCount?: number; // default 6 (desktop), 3-4 recommended for mobile
         }
         ```
      8. **Mobile performance** (from `mobile-strategy.md` §1): Reduce `pathCount` on mobile to limit SVG complexity. Either accept a responsive prop or use `useMediaQuery` internally:
         ```tsx
         const isMobile = useMediaQuery('(max-width: 768px)');
         const count = pathCount ?? (isMobile ? 4 : 6);
         ```
    - **Data-testid**: `data-testid="background-paths"`.
    - **File length estimate**: ~60–80 lines.

  - [x] 1.2 Update Landing Page Hero.
    - **File**: `apps/web/src/app/page.tsx` (**modify**)
    - **What to change**:
      1. Identify the hero `<section>` (likely the first section with the main `<h1>` and CTA buttons).
      2. Wrap it in a `relative overflow-hidden` container.
      3. Inject `<BackgroundPaths />` inside:
         ```tsx
         <section className="relative overflow-hidden ...">
           <BackgroundPaths />
           {/* existing hero content */}
         </section>
         ```
      4. Ensure the hero content has `relative z-10` to sit above the paths.
      5. **Optional**: Wrap the primary CTA button in `<GlassContainer>` from M2.
    - **§2 RSC pattern**: `page.tsx` is a Server Component. `<BackgroundPaths>` is `"use client"` — this is valid, Next.js supports client component imports inside server components. Do NOT add `"use client"` to `page.tsx` itself.

  - [x] 1.3 Apply BackgroundPaths to Developer Experience Page.
    - **File**: `apps/web/src/app/developer-experience/page.tsx` (**modify**)
    - **What to change**: Same pattern as 1.2 — add `<BackgroundPaths />` behind the hero section.
    - **Why**: PRD §4.5 explicitly targets this route as a high-impact entry point.
    - **Variation**: Consider using a lower `pathCount` (e.g., 3–4) for a subtler effect compared to the Landing Page.

- [x] 2.0 Staggered Typography
  - **Depends on:** 1.0 (Hero structure in place).

  - [x] 2.1 Create AnimatedText Component.
    - **File**: `apps/web/src/components/ui/animated-text.tsx` (**create new**)
    - **Directive**: `"use client"` — uses Framer Motion `motion` components (§2 RSC-first).
    - **What to build**: A reusable, single-responsibility component (§ SRP) that splits text into words and staggers their reveal:
      ```tsx
      "use client";
      import { motion } from "framer-motion";
      import { cn } from "@/lib/utils"; // §4: ALWAYS use cn()

      interface AnimatedTextProps {
        text: string;
        className?: string;
        as?: "h1" | "h2" | "h3" | "p" | "span"; // Semantic HTML tag (§5)
        delay?: number; // initial delay before animation starts
      }

      export function AnimatedText({ text, className, as: Tag = "h1", delay = 0 }: AnimatedTextProps) {
        const words = text.split(" ");
        
        return (
          <Tag className={className}>
            {words.map((word, i) => (
              <motion.span
                key={i}
                className="inline-block mr-[0.25em]"
                initial={{ y: 20, opacity: 0 }}
                animate={{ y: 0, opacity: 1 }}
                transition={{
                  type: "spring",
                  stiffness: 150,
                  damping: 25,
                  delay: delay + i * 0.05,
                }}
              >
                {word}
              </motion.span>
            ))}
          </Tag>
        );
      }
      ```
    - **Visual rules** (from `design-system.md` §8.4):
      - Spring physics: `stiffness: 150`, `damping: 25`.
      - Word-by-word stagger with 50ms intervals.
      - Optional: Add gradient text effect for the title:
        ```css
        bg-clip-text text-transparent bg-gradient-to-r from-neutral-900 to-neutral-700/80
        dark:from-white dark:to-white/80
        ```
    - **File length estimate**: ~40–50 lines.

  - [x] 2.2 Apply AnimatedText to Landing Page Hero.
    - **File**: `apps/web/src/app/page.tsx` (**modify**)
    - **What to change**: Replace the static `<h1>` in the hero section with:
      ```tsx
      <AnimatedText
        text="The Marketplace for Autonomous Agents"
        className="text-4xl md:text-6xl font-bold tracking-tight bg-clip-text text-transparent bg-gradient-to-r from-neutral-900 to-neutral-700/80 dark:from-white dark:to-white/80"
      />
      ```
    - Also animate the subtitle `<p>`:
      ```tsx
      <AnimatedText
        text="Discover, verify, and integrate autonomous agents..."
        as="p"
        delay={0.3}
        className="text-lg text-muted-foreground max-w-2xl"
      />
      ```
    - **E2E impact**: The existing `auth-journey.spec.ts` navigates from `/` using `getByRole('link', { name: 'Register Agent' })` and `getByRole('link', { name: 'Explore Agents' })`. These selectors target the CTA buttons, NOT the title — so they should be unaffected. BUT: the `AnimatedText` must render the text so that screen readers can still read it (the `<h1>` semantic tag is preserved via the `as` prop).

- [x] 3.0 Final Anti-Boilerplate QA
  - **Depends on:** Sprints M1-M4 completed.

  - [x] 3.1 Global Sweep for Generic Styling.
    - **What**: Search the entire `apps/web/src` codebase for anti-patterns:
      1. **Pill shapes**: Search for `rounded-full`. Replace with `rounded-[--radius]` UNLESS it's on:
         - Avatar images (`<Avatar>` component) — `rounded-full` is correct.
         - Small status dots or indicators — `rounded-full` is acceptable.
         - Badges — check case-by-case.
         ```bash
         grep -rn "rounded-full" apps/web/src/ --include="*.tsx" --include="*.ts"
         ```
      2. **Heavy drop-shadows**: Search for `shadow-lg`, `shadow-xl`, `shadow-2xl`. Replace with micro-borders:
         ```bash
         grep -rn "shadow-lg\|shadow-xl\|shadow-2xl" apps/web/src/ --include="*.tsx"
         ```
         Replace with: `border border-white/10` (dark mode) or `border border-black/5` (light mode), using the `border-border` token where possible.
      3. **Non-OKLCH colors**: Search for `#`, `rgb(`, `hsl(` in stylesheets:
         ```bash
         grep -rn "rgb(\|hsl(\|#[0-9a-fA-F]" apps/web/src/ --include="*.css" --include="*.tsx"
         ```
         Replace any hardcoded colors with design system tokens.
      4. **Generic font families**: Search for `font-sans` or `font-serif` usage that's NOT our Geist font.
      5. **Excessive line-height**: Ensure hero/dashboard text uses `leading-snug` or `leading-tight` per §8.3, not default `leading-normal`.

  - [x] 3.2 Icon Migration Audit.
    - **What**: Scan for custom SVG usage:
      ```bash
      grep -rn "<svg" apps/web/src/ --include="*.tsx" -l
      ```
      For each file found:
      1. Check if the SVG has a `lucide-react` equivalent (browse https://lucide.dev/icons).
      2. If yes → **Replace** with the Lucide import. Example:
         ```tsx
         // Before
         <svg viewBox="0 0 24 24">...</svg>
         // After
         import { Terminal } from "lucide-react";
         <Terminal className="h-6 w-6" />
         ```
      3. If no Lucide equivalent → **Keep** the custom SVG but ensure:
         - It uses `currentColor` for fill/stroke (theme compatibility).
         - It follows the monochromatic Zinc/Indigo discipline (§8.3).
         - It accepts `className` for sizing (`h-*`, `w-*`).
    - **Why**: PRD §9 resolved: Lucide React is the canonical icon library.

- [x] 4.0 Final E2E Regression Suite
  - **Depends on:** All previous tasks in M5.

  - [x] 4.1 Run Full E2E Suite.
    - **Command**: From `apps/web/`:
      ```bash
      npx playwright test
      ```
    - **Expected**: ALL tests pass across 3 browsers (Chromium, Firefox, WebKit):
      - `auth-journey.spec.ts`: 4+ tests (original 4 + Canvas assertion from M4).
      - `browse.spec.ts`: 2+ tests (original 1 + DataTable tests from M3).
      - `dashboard.spec.ts`: 3+ tests (original 1 + Sidebar tests from M2 + Bento tests from M3).
      - `register.spec.ts`: 1+ test (original 1, updated selectors from M4).
      - `verify.spec.ts`: 2 tests (unchanged).
    - **Total**: ~12+ tests × 3 browsers = 36+ test runs.

  - [x] 4.2 Add Landing Page Animation E2E Test.
    - **File**: `apps/web/tests/auth-journey.spec.ts` (**modify**, or create new `landing.spec.ts`)
    - **What to add**:
      ```ts
      test('Landing page renders animated background paths', async ({ page }) => {
        await page.goto('/');
        await expect(page.getByTestId('background-paths')).toBeVisible({ timeout: 5000 });
      });

      test('Landing page hero text animates on load', async ({ page }) => {
        await page.goto('/');
        // After animation completes, the h1 should be visible
        const heading = page.getByRole('heading', { level: 1 });
        await expect(heading).toBeVisible({ timeout: 5000 });
        // Verify text content is rendered
        await expect(heading).toContainText(/Marketplace|Agents/i);
      });
      ```

  - [x] 4.3 Visual Consistency Spot Check.
    - **What**: Manually verify (or add screenshot comparison tests) for these key pages:
      1. `/` — BackgroundPaths visible, H1 animates, CTA buttons work.
      2. `/browse` — DataTable renders with visible columns and pagination.
      3. `/dashboard` — Sidebar visible (desktop), Bento cards hover correctly.
      4. `/auth/signin` — Canvas background renders, ghost inputs are transparent.
      5. `/developer-experience` — BackgroundPaths visible.
    - **Command** (optional Playwright screenshot comparison):
      ```bash
      npx playwright test --update-snapshots
      ```

  - [x] 4.4 Build Verification.
    - **Command**: From project root:
      ```bash
      pnpm build
      ```
    - **What to check**:
      - Zero TypeScript errors.
      - Zero CSS compilation errors.
      - Build output size is reasonable (WebGL/Three.js will increase bundle — verify it's code-split to auth routes only).
      - Run `pnpm build` output and check for any "Large page data" warnings.

  - [x] 4.5 Run Backend Tests (Sanity Check).
    - **Command**: From project root:
      ```bash
      uv run pytest
      ```
    - **What to check**: All Python-side tests pass. This sprint should have zero backend impact, but running ensures nothing was accidentally broken.

## Acceptance Criteria
- The Landing Page displays floating, animated SVG paths behind the hero section.
- Reloading the Landing Page causes the H1 title to animate word-by-word onto the screen using Spring physics.
- Developer Experience page has BackgroundPaths behind its hero.
- Codebase contains zero generic, non-brand CSS shapes from Lovable/v0 defaults:
  - No unauthorized `rounded-full` (only on avatars/dots).
  - No `shadow-lg`/`shadow-xl` on content areas.
  - No hardcoded hex/rgb colors (all OKLCH tokens).
- All custom SVGs either migrated to Lucide or use `currentColor`.
- All E2E tests pass (`npx playwright test`).
- Full production build passes (`pnpm build`).
- Backend tests pass (`uv run pytest`).
