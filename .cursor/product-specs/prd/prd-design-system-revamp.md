# PRD: Application-Wide Design System Revamp

## 1. Introduction/Overview
The ASAP Protocol currently lacks a unified, premium visual identity across its web applications. We have recently formalized a new Design System (`.cursor/design/design-system.md`) focused on a "Clean Architect" aesthetic, utilizing Next.js 15, Tailwind v4, Shadcn, Framer Motion, and WebGL. 
The goal of this initiative is to perform a comprehensive revamp of all existing UI screens and flows to strictly adhere to this new Design System, elevating the developer experience to an "Apple/Vercel-tier" of polish.

## 2. Goals
- Apply the new Zinc/Indigo OKLCH color palette universally.
- Implement Glassmorphism and Depth patterns (nested blur containers) on all dashboard and feature cards.
- Integrate WebGL/3D Canvas effects specifically into Authentication and Onboarding flows.
- Ensure all interactive elements (buttons, cards) use the newly defined physics-based micro-interactions (staggered springs, hover lifts).
- Establish 100% adherence to `.cursor/rules/frontend-best-practices.mdc` across the frontend codebase.

## 3. User Stories
- **As a developer entering the platform**: I want to be greeted by an immersive, high-quality WebGL authentication screen so that I immediately feel I am using a premium, cutting-edge protocol.
- **As a user navigating the dashboard**: I want cards and data modules to respond smoothly to my cursor with nested hover reveals and soft shadows, making the data feel tactile and accessible.
- **As a UI contributor**: I want clear, enforced rules and a components library so that any new feature I build automatically inherits these high-end animations and styles without complex manual CSS.

## 4. Functional Requirements
1. **Theme Standardization**: Update `globals.css` and Next-Themes providers to enforce the new OKLCH Light/Dark color variables defined in the Design System.
2. **Typography Update**: Ensure all headers use `Geist Sans` with appropriate tracking, and all code/data blocks use `Geist Mono`. Apply Framer Motion staggered reveals to all "Hero" page headers.
3. **Card Component Refactor (BentoGrid Pattern)**: Refactor standard cards to include the default `-translate-y-0.5` lift, ambient shadows, and optional radial gradient reveals. Apply this specifically to:
   - `dashboard/page.tsx`
   - `features/[slug]/page.tsx`
4. **Auth Flow Replacement (WebGL Pattern)**: Replace standard login/signup pages with the WebGL flow (Canvas backgrounds, AnimatePresence sliding forms, ghost inputs). Apply this specifically to:
   - `auth/signin/page.tsx`
   - `dashboard/register/page.tsx`
   - `docs/register/page.tsx`
5. **Hero Patterns (BackgroundPaths)**: Implement advanced SVG background animations on high-impact entry points:
   - `page.tsx` (Landing Page)
   - `developer-experience/page.tsx`
6. **Application Shell (Sidebar)**: Implement the official Shadcn `<Sidebar>` component to replace or standardize the current navigation shell across all `dashboard/*` routes.
7. **Data Tables & Forms**: Convert standard lists (e.g., `/browse`) into Shadcn `<DataTable>` components (TanStack Table recipe) with pagination and sorting. The `/browse` route uses **DataTable** for tabular agent listing; the **Bento Grid** pattern is reserved for high-value dashboard summaries and feature showcases. Ensure all creation flows (like Registering) open in a centered `<Dialog>` or have dedicated focus pages.
8. **Loading & Empty States**: Implement Shadcn `<Skeleton>` placeholders for all async data fetching components. Define premium empty states for unpopulated grids/tables.
9. **Dependency Integration**: Install and configure `framer-motion`, `three`, `@react-three/fiber`, and required Shadcn components (`sidebar`, `skeleton`, `table`, `dialog`) in `apps/web`. Note: `DataTable` is a Shadcn recipe (TanStack Table), not a CLI component — scaffolded in Sprint M3.

## 5. Non-Goals (Out of Scope)
- Developing brand new product features (e.g., adding an entirely new analytics system). This is strictly a UI/UX visual revamp of *existing* or *planned* core flows.
- Backend infrastructure changes, unless strictly required to support the new UI state (e.g., providing an auth status faster for the WebGL transition).
- **Structural refactoring of secondary routes**: Pages like `legal/*`, `demos/`, `test-register/`, `browse/load-test/`, and `agents/[id]/` are out of scope for structural UI work. They will passively inherit the new OKLCH color tokens and Geist typography via `globals.css` updates (Sprint M1) but receive no layout, animation, or component refactoring.

## 6. Design Considerations
- **Source of Truth**: All implementations MUST strictly follow `.cursor/design/design-system.md`.
- **Mobile Strategy**: Responsive behavior MUST follow `.cursor/design/mobile-strategy.md` (Sidebar → hamburger, Bento Grid → single-column, etc.).
- **References**:
  - `analysis-bento-grid.md` (Card interactions)
  - `analysis-background-paths.md` (Hero ambient effects)
  - `analysis-sign-in-3d.md` (Auth Canvas flows)

## 7. Technical Considerations
- **Stack**: Next.js 15, React 19, Tailwind CSS v4, Shadcn/UI.
- **Performance**: WebGL Canvas elements MUST include a `maxFps` limit (e.g., 60fps) and should unmount or pause rendering when out of viewport to preserve battery life and CPU.
- **Consult**: `.cursor/rules/frontend-best-practices.mdc` (Updated to forbid heavy neon glows and enforce the new Clean Architect rules).

## 8. Success Metrics
- 100% of visible `apps/web` pages utilize the new color tokens and typography.
- Auth flow successfully transitions states using Framer Motion without full page reloads.
- No regression in Lighthouse performance scores (excluding expected minor hits from 3D Canvas on the auth page).

## 9. Resolved Questions
- ~~Do we need to migrate any existing custom SVG icons to Lucide React, or can they coexist if they fit the aesthetic?~~ **Resolved**: **Lucide React is the canonical icon library** (per `design-system.md` §2). Custom SVGs that have a direct Lucide equivalent MUST be migrated during the Sprint M5 anti-boilerplate QA sweep. Custom SVGs without a Lucide equivalent MAY coexist only if they strictly follow the monochromatic Zinc/Indigo discipline (§8.3) and use `currentColor` for theme compatibility.
- ~~Should the `BentoGrid` pattern replace standard list views, or only be used for high-level dashboard summaries?~~ **Resolved**: Bento Grid is for high-value dashboard summaries and feature showcases (§4.3). Standard list views use DataTable (§4.7).
