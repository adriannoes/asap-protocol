# Design Inspiration Analysis: `BentoGrid`

## 1. Overview
The user provided a React component (`BentoGrid` from 21st.dev) to serve as a baseline for the level of micro-interações and visual fidelity desired for cards and grids in the ASAP Protocol UI.

**Component Highlights**:
- Bento-style asymmetric grid layout.
- Deep nested hover states with radial gradient backgrounds.
- Persistent hover variants for highlighted cards.
- Highly detailed micro-components inside the cards (status tags, icon wrappers).

## 2. Technical Requirements
To support this level of UI in our existing `apps/web` (Next.js 15 + Tailwind v4 + Shadcn), we need to ensure the following:

- **Lucide React**: Already in our stack, used heavily here for iconography.
- **Tailwind classes**: 
  - Standard utilities like `backdrop-blur-sm`, `bg-[radial-gradient(...)]`, and `will-change-transform`.
  - The use of arbitrary values like `bg-[length:4px_4px]` and explicit shadow declarations `shadow-[0_2px_12px_rgba(0,0,0,0.03)]` works perfectly with our Tailwind JIT compiler.
- **Utils**: Relies on `cn` from `clsx`/`tailwind-merge` to handle complex conditional classes cleanly.

## 3. Design Patterns Extracted
To formalize this in our `design-system.md` (Section 7: Motion & Micro-interactions), we should extract these core patterns specifically for **Cards & Data Modules**:

### A. The "Bento" Grid System
- **Layout**: `grid grid-cols-1 md:grid-cols-3 gap-3`. Cards can span multiple columns (`md:col-span-2`) to create an engaging, asymmetric visual hierarchy.

### B. Nested Card Hover Physics
- **Base State**: `border border-gray-100/80 dark:border-white/10 bg-white dark:bg-black`. 
- **The Lift**: Cards lift on hover using `-translate-y-0.5` combined with `will-change-transform` for 60fps smoothness.
- **The Ambient Shadow**: A very soft but wide shadow fade-in `hover:shadow-[0_2px_12px_rgba(0,0,0,0.03)]`.

### C. Complex Reveal Backgrounds
- **Radial Grid Reveal**: Inside the card, an absolute container fades from `opacity-0` to `opacity-100` on `group-hover`. This container holds a repeating radial gradient dot pattern.
- **Gleam Border**: A secondary absolute layer behind the content creates a subtle gradient "gleam" (`bg-gradient-to-br from-transparent via-gray-100/50 to-transparent`) that also reveals on hover.

### D. Micro-components (Tags & Badges)
- **Fluid Badges**: Using extreme transparency with background blur: `bg-black/5 dark:bg-white/10 backdrop-blur-sm`.
- **Badge Hover**: Badges themselves have hover states even inside a hovered card (`hover:bg-black/10 dark:hover:bg-white/20`), creating a satisfying layered interaction model.

## 4. Integration Strategy
1. The existing stack fully supports this; no new npm packages are needed beyond `lucide-react` which we have.
2. Create `apps/web/src/components/ui/bento-grid.tsx` when we build the dashboard or feature pages.
3. Update `design-system.md` to include these specific **Card Interaction** standards, focusing heavily on the "nested hover reveal" concept (revealing textures/gradients on card hover).
