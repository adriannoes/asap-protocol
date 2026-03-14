# Sprint M4: Authentication Flow (WebGL)

## Overview
**Goal:** Replace the standard form-based login/signup with the premium 3D WebGL flow. This is the highest visual-impact sprint. The auth pages (`/auth/signin`, `/dashboard/register`, `/docs/register`) will feature immersive Canvas shader backgrounds, liquid form transitions via `AnimatePresence`, and ghost transparent inputs.

**Source of Truth:** `design-system.md` §8.6 (Auth & Focus Flows), `analysis-sign-in-3d.md`.

## Relevant Files
- `apps/web/src/app/auth/signin/page.tsx` — Current auth page (71 lines): static layout, indigo blur circle bg, `SignInForm` component.
- `apps/web/src/app/auth/signin/signin-form.tsx` — Client-side form component with GitHub OAuth submit.
- `apps/web/src/app/dashboard/register/page.tsx` — Registration page.
- `apps/web/src/app/docs/register/page.tsx` — Docs registration page.
- `apps/web/src/components/ui/canvas-bg.tsx` — **Created** WebGL shader background (DotMatrixShader, frameloop demand, fallback).
- `apps/web/src/hooks/use-canvas-visibility.ts` — **Created** IntersectionObserver hook for off-screen pause.
- `apps/web/src/components/ui/glass-container.tsx` — **Exists** from M2 (reuse for form container).
- `apps/web/src/lib/auth-input-styles.ts` — **Created** ghost input className for auth/register forms.
- `apps/web/tests/auth-journey.spec.ts` — 4 existing tests: Register Agent link, Login no 403, direct register redirect, Explore Agents.
- `apps/web/tests/register.spec.ts` — 1 test: fill + submit agent registration form.

## Tasks

- [x] 1.0 WebGL Canvas Infrastructure
  - **Trigger / entry point:** User hits `/auth/signin`, `/dashboard/register`, or `/docs/register`.
  - **Enables:** Liquid transparent forms over 3D backgrounds.
  - **Depends on:** Sprint M1 (`three`, `@react-three/fiber` installed).

  - [x] 1.1 Create Ambient Shader Canvas Component.
    - **File**: `apps/web/src/components/ui/canvas-bg.tsx` (**create new**)
    - **Directive**: `"use client"` — uses React Three Fiber hooks, `useFrame`, `useRef`, and browser-only WebGL APIs (§2 RSC-first).
      1. Import `Canvas` from `@react-three/fiber`.
      2. Create a `DotMatrixShader` component using `ShaderMaterial` with a custom Fragment Shader that renders an animated repeating dot-matrix or wave pattern.
      3. The shader should accept a `uTime` uniform that drives the animation.
      4. Wrap in a React component:
         ```tsx
         interface CanvasBgProps {
           className?: string;
           colorScheme?: 'indigo' | 'zinc';  // For state-reactive coloring
         }
         
         export function CanvasBg({ className, colorScheme = 'indigo' }: CanvasBgProps) {
           return (
             <div className={cn("absolute inset-0 -z-10", className)}>
               <Canvas
                 frameloop="demand"  // Pause when not rendering
                 dpr={[1, 1.5]}     // Limit DPR for performance
                 gl={{ antialias: false, alpha: true }}
               >
                 <DotMatrixScene colorScheme={colorScheme} />
               </Canvas>
             </div>
           );
         }
         ```
      5. **Performance requirements** (PRD §7 + `mobile-strategy.md` §7):
         - `frameloop="demand"` — only re-renders when needed (via `invalidate()`).
         - `dpr={[1, 1.5]}` — caps device pixel ratio. **On mobile**, reduce to `[1, 1]` using a responsive check:
           ```tsx
           const isMobile = typeof window !== 'undefined' && window.innerWidth < 768;
           // or use a useMediaQuery hook
           <Canvas dpr={isMobile ? [1, 1] : [1, 1.5]} ... />
           ```
         - Implement `IntersectionObserver` wrapper via `useCanvasVisibility` hook (task 1.2).
         - Set max render rate to ~60fps using `useFrame` with a time delta throttle.
      6. **WebGL fallback** (from `mobile-strategy.md` §7): If WebGL context creation fails (some old mobile browsers), render a static CSS gradient fallback:
         ```tsx
         <Canvas onError={() => setFallback(true)} ... />
         {fallback && (
           <div className="absolute inset-0 bg-gradient-to-br from-zinc-950 via-indigo-950/20 to-zinc-950" />
         )}
         ```
      6. **Mark as client component**: `"use client"` at the top.
    - **Shader design guidance** (from `analysis-sign-in-3d.md`):
      - Use low-opacity dots or lines in Zinc/Indigo palette.
      - Subtle movement — NOT distracting flashy effects.
      - The visual should complement the form, not compete with it.
    - **Data-testid**: `data-testid="canvas-bg"`.
    - **File length estimate**: ~80–120 lines.

  - [x] 1.2 Create useCanvasVisibility Hook (Performance).
    - **File**: `apps/web/src/hooks/use-canvas-visibility.ts` (**create new** — `hooks/` dir per project structure §6)
    - **What to build**: Custom hook using `IntersectionObserver`:
      ```tsx
      export function useCanvasVisibility(ref: RefObject<HTMLElement>) {
        const [isVisible, setIsVisible] = useState(true);
        
        useEffect(() => {
          if (!ref.current) return;
          const observer = new IntersectionObserver(
            ([entry]) => setIsVisible(entry.isIntersecting),
            { threshold: 0.1 }
          );
          observer.observe(ref.current);
          return () => observer.disconnect();
        }, [ref]);
        
        return isVisible;
      }
      ```
    - **Why**: PRD §7 requires Canvas to pause rendering when off-screen. This hook feeds into `CanvasBg` to conditionally call `invalidate()`.
    - **File length estimate**: ~20 lines.

- [x] 2.0 Liquid Form Transitions
  - **Depends on:** 1.0 (Canvas infrastructure).

  - [x] 2.1 Refactor Auth SignIn Page Layout.
    - **File**: `apps/web/src/app/auth/signin/page.tsx` (**modify**)
    - **Current state** (71 lines): Static `bg-zinc-950` with a blurred indigo circle (`bg-indigo-500/10 blur-[100px]`), `<SignInForm>` component, legal links.
    - **What to change**:
      1. **Remove** the static indigo blur circle div (line 21).
      2. **Remove** `bg-zinc-950` from `<main>` — the Canvas provides the background.
      3. **Add** the `CanvasBg` component behind a semantic `<main>` or `<section>` wrapper (§5 Accessibility):
         ```tsx
         <main className="relative flex min-h-[calc(100vh-8rem)] flex-col items-center justify-center px-4 py-16 overflow-hidden">
           <CanvasBg />
           <div className="relative z-10 flex w-full max-w-md flex-col items-center gap-8 text-center">
             {/* existing content */}
           </div>
         </main>
         ```
      4. Wrap the form container in `<GlassContainer>` from M2:
         ```tsx
         <GlassContainer className="p-8 w-full">
           <SignInForm callbackUrl={callbackUrl} />
         </GlassContainer>
         ```
      5. Keep all legal links and logo — just move them inside the `z-10` container.

  - [x] 2.2 Apply WebGL to Registration Pages.
    - **Files**: `apps/web/src/app/dashboard/register/page.tsx` and `apps/web/src/app/docs/register/page.tsx` (**modify**)
    - **What to change**: Apply the same pattern as 2.1 — add `<CanvasBg />` behind the form, wrap form content in `<GlassContainer>`. Reuse the same `canvas-bg.tsx` component.
    - **Why**: PRD §4.4 explicitly targets all three auth/register routes.
    - **Context**: `dashboard/register` currently has an authenticated form for agent registration (used by `register.spec.ts`). The `<form>` structure and labels MUST remain identical — we're only changing the visual wrapper.

  - [x] 2.3 Implement AnimatePresence for Auth Steps.
    - **File**: `apps/web/src/app/auth/signin/signin-form.tsx` (**modify**)
    - **What to change**:
      1. Add `"use client"` if not already present.
      2. Import `motion`, `AnimatePresence` from `framer-motion`.
      3. If the form has multiple steps (e.g., Email → OTP), wrap each step in:
         ```tsx
         <AnimatePresence mode="wait">
           <motion.div
             key={currentStep}
             initial={{ x: 100, opacity: 0 }}
             animate={{ x: 0, opacity: 1 }}
             exit={{ x: -100, opacity: 0 }}
             transition={{ type: "spring", stiffness: 150, damping: 25 }}
           >
             {/* step content */}
           </motion.div>
         </AnimatePresence>
         ```
         - **Mobile offset** (from `mobile-strategy.md` §7): Reduce `x` offset to `50` on mobile to prevent horizontal overflow:
           ```tsx
           const isMobile = useMediaQuery('(max-width: 768px)');
           initial={{ x: isMobile ? 50 : 100, opacity: 0 }}
           ```
      4. If the current form is single-step (just GitHub OAuth), add a mount animation:
         ```tsx
         <motion.div
           initial={{ y: 20, opacity: 0 }}
           animate={{ y: 0, opacity: 1 }}
           transition={{ type: "spring", stiffness: 150, damping: 25 }}
         >
           {/* form content */}
         </motion.div>
         ```
      5. **Rule** (from PRD): "Never use abrupt DOM swapping for major components."

  - [x] 2.4 Apply Ghost Inputs.
    - **Files**: All `<Input>` components within auth/register forms.
    - **What to change**: Override default Shadcn Input styling on auth pages using `cn()` helper (§4):
      ```tsx
      <Input
        className={cn(
          "bg-transparent border-white/10 text-white placeholder:text-white/40",
          "focus:border-white/30 focus:ring-0 transition-colors",
          "text-base" // Prevents iOS Safari auto-zoom on focus (mobile-strategy.md §7)
        )}
      />
      ```
    - **Visual rules** (from `design-system.md` §8.6):
      - Background: `bg-transparent` (NOT the default Shadcn white/dark bg).
      - Border: `border-white/10`.
      - Focus: `focus:border-white/30` with soft glow.
      - The Canvas background should be visible through the inputs.
    - **Important**: Only apply Ghost styling to auth/register pages. Do NOT modify the global `<Input>` component in `components/ui/input.tsx`. Use className overrides locally.

- [x] 3.0 E2E Test Updates
  - **Depends on:** 2.0 (Form transitions complete).
  - **Context**: Existing tests that will be affected:
    - `auth-journey.spec.ts` (4 tests): Uses `getByRole('link', { name: 'Register Agent' })` and `getByRole('button', { name: /Connect \/ Login/i })` — these come from public Header, NOT affected.
    - `register.spec.ts` (1 test): Fills form labels like `getByLabel(/Agent Slug Name/i)` — these labels MUST persist.

  - [x] 3.1 Update Auth Journey E2E Test.
    - **File**: `apps/web/tests/auth-journey.spec.ts` (**modify**)
    - **What to change/add**:
      1. **Add Canvas loading wait**: After navigating to auth pages, wait for Canvas to initialize:
         ```ts
         test('sign-in page renders WebGL background', async ({ page }) => {
           await page.goto('/auth/signin');
           // Wait for Canvas to be visible (may take a moment for WebGL init)
           await expect(page.getByTestId('canvas-bg')).toBeVisible({ timeout: 10000 });
           // Verify the form is still rendered on top
           await expect(page.getByRole('heading', { name: /Sign in/i })).toBeVisible();
         });
         ```
      2. **Add animation completion wait**: If forms now animate in, existing tests might assert too early. Add `waitForTimeout(500)` or use `toBeVisible()` with extended timeout after page transitions.
      3. **Keep all 4 existing tests** — they should still pass since they interact with the Header (public route), not the auth form internals.

  - [x] 3.2 Update Register E2E Test.
    - **File**: `apps/web/tests/register.spec.ts` (**modify**)
    - **What to verify**: The current test navigates to `/dashboard/register` and fills fields by label:
      - `getByLabel(/Agent Slug Name/i)` → Must still find this label.
      - `getByRole('textbox', { name: /Manifest URL/i })` → Must still work.
      - `getByRole('checkbox')` → Must still work.
      - `getByRole('button', { name: /Submit Registration/i })` → Must still work.
    - **What to add**:
      1. Assert Canvas background is visible:
         ```ts
         await expect(page.getByTestId('canvas-bg')).toBeVisible({ timeout: 10000 });
         ```
      2. Assert Ghost inputs are transparent (visual regression check):
         ```ts
         // Check that the first input has transparent background
         const firstInput = page.getByLabel(/Agent Slug Name/i);
         await expect(firstInput).toHaveCSS('background-color', 'rgba(0, 0, 0, 0)');
         ```
    - **Important**: The `GlassContainer` wrapper around the form should NOT break any form label associations. Ensure `<label htmlFor>` still correctly targets inputs.

  - [x] 3.3 Add WebGL Performance Test.
    - **File**: `apps/web/tests/auth-journey.spec.ts` (**modify**, add new test)
    - **What to add**:
      ```ts
      test('WebGL canvas does not cause console errors', async ({ page }) => {
        const errors: string[] = [];
        page.on('console', msg => {
          if (msg.type() === 'error') errors.push(msg.text());
        });
        
        await page.goto('/auth/signin');
        await page.waitForTimeout(3000); // Let Canvas initialize fully
        
        // Filter out known non-critical warnings
        const criticalErrors = errors.filter(e => 
          !e.includes('third-party cookie') && !e.includes('favicon')
        );
        expect(criticalErrors).toHaveLength(0);
      });
      ```
    - **Why**: WebGL contexts can fail silently on some browsers. This catches GPU/shader compilation errors.

## Acceptance Criteria
- Auth pages (`/auth/signin`, `/dashboard/register`, `/docs/register`) render a GPU-accelerated WebGL background behind the form.
- Canvas uses `frameloop="demand"` and pauses rendering when off-screen (verified manually or via R3F performance monitor).
- The state switch between form steps (if multi-step) occurs via smooth Spring animation — no abrupt DOM swapping.
- Inputs are translucent (Ghost style: `bg-transparent border-white/10`), showing the Canvas behind them.
- **All 9 existing E2E tests pass** (auth-journey: 4, browse: 1, dashboard: 1, register: 1, verify: 2).
- New E2E tests pass: Canvas rendering, WebGL no console errors.
- Form submission still works correctly — labels, inputs, and buttons are functionally identical.
