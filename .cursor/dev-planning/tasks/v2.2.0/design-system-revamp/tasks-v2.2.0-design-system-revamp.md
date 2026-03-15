# v2.2.0 Roadmap: Design System Revamp

## Goal
Execute the Application-Wide Design System Revamp across all `apps/web` routes, elevating the UI to the "Clean Architect" standard with Glassmorphism, WebGL, and precise micro-interactions.

## Execution Strategy
To ensure high-quality code reviews and zero downtime, the revamp is strictly broken down into 5 sequential sprints. Each sprint represents a single, atomic Pull Request.

## Sprints

1. **[Sprint M1: Foundation & Dependencies](./sprint-M1-base-dependencies.md)**
   - Lock in OKLCH palette, Geist typography, and install all required heavy dependencies (`framer-motion`, `three.js`) and Shadcn components (`sidebar`, `skeleton`, `table`, `dialog`). Note: `DataTable` is a recipe, scaffolded in M3.
2. **[Sprint M2: Structural Shell & Feedback](./sprint-M2-structural-shell.md)**
   - Implement the global `<Sidebar>` layout (per `mobile-strategy.md`), standardize loading (`<Skeleton>`) and empty states, create reusable `GlassContainer`, and update navigation E2E tests.
3. **[Sprint M3: Data Tables & Bento Cards](./sprint-M3-bento-cards.md)**
   - Scaffold the DataTable wrapper (TanStack Table recipe), refactor registries to use it, and upgrade `dashboard` + `features/[slug]` cards to the interactive Bento Grid pattern.
4. **[Sprint M4: Authentication flow (WebGL)](./sprint-M4-webgl-auth.md)**
   - Replace static login/register pages (`auth/signin`, `dashboard/register`, `docs/register`) with immersive 3D Canvas and Framer Motion sliding forms. Include viewport-aware rendering and auth E2E test updates.
5. **[Sprint M5: Hero Animations & Polish](./sprint-M5-hero-animations.md)**
   - Add ambient Animated SVG Backgrounds to landing page and `developer-experience` page, and perform final anti-boilerplate QA.

## Technical Rules
- **Anti-Boilerplate**: Strict adherence to `.cursor/design/design-system.md`. No generic pill-shapes or heavy neon glows.
- **Testing**: Ensure existing E2E tests (`playwright`) are updated if data-testids or critical routing changes during the structural updates.
