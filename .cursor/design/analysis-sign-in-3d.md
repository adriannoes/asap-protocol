# Design Inspiration Analysis: `SignInPage` (3D WebGL)

## 1. Overview
The user provided a highly advanced React component (`SignInPage` from 21st.dev) to serve as a baseline for the authentication flow in the ASAP Protocol UI.

**Component Highlights**:
- Full-screen WebGL background powered by Three.js and custom Fragment Shaders.
- Interactive, state-driven animations (the background shader reverses direction when the user completes the OTP code).
- Step-based form transitions (`AnimatePresence` with Framer Motion) moving smoothly from Email -> OTP Code -> Success states.
- Floating, minimalist Glassmorphic UI overlays (`MiniNavbar`) and inputs.

## 2. Technical Requirements
To support this "Apple/Vercel-level" 3D authentication page in our `apps/web` (Next.js 15), we need to introduce WebGL capabilities:

- **Three.js & React Three Fiber (R3F)**:
  - `three`
  - `@react-three/fiber`
- **Framer Motion**: Already identified in previous steps, heavily used here for form layout transitions (`<AnimatePresence>`).
- **Tailwind configurations**: Standard utilities only. The component makes excellent use of backdrop-blurs (`backdrop-blur-[2px]`) and extreme transparency (`bg-white/5`).

## 3. Design Patterns Extracted
To formalize this in our `design-system.md` (Section 7: Motion & Micro-interactions), we should extract these core patterns specifically for **Authentication & Focus Flows**:

### A. Immersive Canvas Backgrounds
- **WebGL Shaders**: For high-impact, single-focus pages like Login or Onboarding, using a `<Canvas>` with custom shaders provides unparalleled visual depth.
- **State-Reactive Backgrounds**: The environment should react to user progress. For example, changing the color palette or reversing the shader animation speed when a form step is successfully completed.

### B. Liquid Form Transitions
- **AnimatePresence**: Form steps (Email, Code, Password) should never abruptly swap. They must exit and enter smoothly.
  - Typical pattern: Exit left (`x: -100`, `opacity: 0`), Enter from right (`x: 100`, `opacity: 1`) using `easeOut` easing over `0.4s`.
- **Auto-focus**: Input fields should automatically capture focus (`setTimeout` with `refs`) after the transition completes, reducing friction.

### C. Ghost & Glass Form Controls
- **Inputs**: Transparent backgrounds with subtle borders (`bg-transparent border-white/10`) that glow slightly on focus (`focus:border-white/30`).
- **Interaction Arrows**: Submit buttons using an overflow-hidden trick where the arrow icon translates out to the right and a new one translates in from the left on hover (`group-hover:translate-x-full`).

## 4. Integration Strategy
1. Install `three` and `@react-three/fiber` in `apps/web`.
2. Abstract the `CanvasRevealEffect` and `DotMatrix` into reusable `components/ui/canvas-reveal.tsx`.
3. Update `design-system.md` to establish rules for when it is appropriate to use heavy WebGL effects (hint: only on focus/auth pages, not dashboard interiors).
