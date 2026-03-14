# Code Review: Sprint M5 (Hero Animations)

## 1. Executive Summary
| Category | Status | Summary |
| :--- | :--- | :--- |
| **Tech Stack** | ✅ | Next.js 15, Framer Motion, and Tailwind v4 are used correctly and consistently. |
| **Architecture** | ⚠️ | High-impact UI components are properly implemented, but RSC boundary could be optimized in the Landing Page Hero. |
| **Security** | ✅ | No security regressions. Client and server separation logic is sound, and all routes properly leverage existing auth middleware. |
| **Tests** | ✅ | Perfect alignment with E2E specifications; animated elements are gracefully accommodated in `auth-journey.spec.ts`. |

> **General Feedback:** The code quality is excellent and visually aligns perfectly with the "Clean Architect" standard. The animations are tastefully executed with the correct spring physics and delays. However, there are a few minor architectural and accessibility optimizations to address before merging to maintain our strict front-end excellence.

## 2. Required Fixes (Must Address Before Merge)
*These issues block the PR from being "Production Ready".*

### Screen-Reader Accessibility for Animated Typography
*   **Location:** `apps/web/src/components/ui/animated-text.tsx:28`
*   **Problem:** By mapping `.split(" ")` into individual `<span>` tags, screen readers may read the heading disjointedly ("The [pause] Marketplace [pause] for..."). 
*   **Rationale (Expert View):** Semantic HTML implies not just tags, but natural text reading paths. Maintaining an A11y-compliant protocol portal is crucial.
*   **Fix Suggestion:** Hide the split words from screen readers and render a visually hidden span containing the full text.
    ```tsx
    <Tag className={cn(className)}>
      <span className="sr-only">{text}</span>
      <span aria-hidden="true">
        {words.map((word, i) => (
          <motion.span
             // ... existing props
          >
            {word}
          </motion.span>
        ))}
      </span>
    </Tag>
    ```

## 3. Tech-Specific Bug Hunt (Deep Dive)

*   [x] **Client Component Abuse**: Found in `apps/web/src/components/landing/HeroSection.tsx`. The entire HeroSection is marked `"use client"` just to accommodate the `[tick]` and `visibleLines` `useEffect` array for the Terminal animation. **Strongly recommend** extracting the `Terminal` interactive code into its own `<HeroTerminal />` Client Component so the outer Hero (with the static text and links) remains a React Server Component (RSC) for better initial load performance and SEO caching.
*   [ ] **Mutable Default Argument**: None found. Proper destructuring and default parameters are used.
*   [ ] **Garbage Collected Task**: N/A for frontend. 
*   [ ] **Hydration Mismatch Risk**: Handled safely. Although `useIsMobile()` conditionally limits `<BackgroundPaths>` SVG generation, it initializes to `undefined/false` during SSR and re-renders on the client via `useEffect`, successfully avoiding React hydration errors.

## 4. Improvements & Refactoring (Highly Recommended)
*Code is correct, but can be cleaner/faster/safer.*

*   [x] **Optimization (RSC Isolation)**: As noted above, shift `"use client"` strictly down to `<HeroTerminal />` and `<BackgroundPaths />` (which is already done), keeping `HeroSection.tsx` server-side rendered.
*   [x] **Design System Check (Blur/Glow)**: In `HeroSection.tsx:49`, there is a `<div className="... rounded-full bg-indigo-500/10 blur-[120px]" />`. While this functions as a soft ambient glow, it slightly brushes against the "No heavy neon glows" rule in `.cursor/design/design-system.md`. Given its low 10% opacity it's acceptable, but verify it doesn't disrupt the pure "Glassmorphism" effect.
*   [x] **Code Splitting**: The SVG path generation in `background-paths.tsx` is neat and mathematically elegant, but ensures framer-motion is properly code-split on routes that don't need it.

## 5. Verification Steps
*How should the developer verify the fixes?*
> Run: `npx playwright test --ui` to visually confirm that the `auth-journey.spec.ts` continues to pass without errors.
> Use `VoiceOver` (Mac) or `NVDA` (Windows) to verify the `<AnimatedText />` announces the header as a single cohesive sentence.
> Run `pnpm build` to verify the refactoring of `HeroSection.tsx` correctly shifts it to static generation.
