# Mobile Responsiveness Strategy (v2.2.0 Design System Revamp)

## Breakpoints (Tailwind CSS v4 defaults)
- `sm`: 640px (Mobile Landscape / Large Phones)
- `md`: 768px (Tablets)
- `lg`: 1024px (Laptops — Sidebar breakpoint)
- `xl`: 1280px (Desktops)

> **Source of Truth**: This file governs ALL responsive layout decisions for the Design System Revamp. Referenced by Sprint M2 (Sidebar), M3 (DataTable/Bento), M4 (WebGL), and M5 (Hero Animations).

---

## Global Components

### Navigation (Shadcn `<Sidebar>`)
- **Desktop (`>= lg`)**: Persistent or collapsible left-rail `<Sidebar>` (Shadcn) for all `/dashboard/*` routes. Public routes (`/`, `/browse`, `/features/*`) keep the `<Header>` nav.
- **Mobile (`< lg`)**: Sidebar auto-hides. A `<SidebarTrigger>` hamburger button appears. Clicking it opens the Sidebar as a Shadcn `<Sheet>` drawer (slide-in from left). This is native Shadcn Sidebar behavior — no custom implementation needed.
- **Touch targets**: All Sidebar menu items must meet 44×44px minimum touch area.

### GlassContainer
- **All breakpoints**: The `backdrop-blur` effect is GPU-intensive. On low-end mobile devices, `backdrop-blur-lg` may cause frame drops.
- **Mitigation**: Use `backdrop-blur-md` as the default (already specified in `design-system.md` §8.1). Do NOT stack multiple blur layers on mobile — limit to 1 level of GlassContainer per view.

### Theme Toggle
- **Mobile**: Always exposed in the Header (never hidden behind hamburger). Users must be able to switch themes without opening the Sidebar.

---

## Page-Specific Behavior

### 1. Landing Page (`/`)
- **Hero Section**:
  - *Mobile (`< lg`)*: Stack vertically. Headline centered with full-width CTA buttons. `BackgroundPaths` SVG animations **remain active** — they are lightweight SVG strokes, not GPU-heavy Canvas.
  - *Desktop (`>= lg`)*: Side-by-side or split layout with BackgroundPaths behind.
- **AnimatedText (Hero H1)**:
  - *Mobile*: Animation runs normally — Framer Motion `spring` is performant on mobile. Reduce `pathCount` to 3-4 (vs 6 on desktop) to limit SVG complexity.
- **Features (Bento Grid)**:
  - *Mobile (`< md`)*: 1 column grid (`grid-cols-1`). BentoCards stack vertically.
  - *Tablet (`md`)*: 2 columns (`md:grid-cols-2`).
  - *Desktop (`lg`)*: 3 columns (`lg:grid-cols-3`).
- **How it Works**:
  - *Mobile*: Vertical timeline layout (unchanged).

### 2. Browse/Registry (`/browse`)
- **DataTable** (from Sprint M3):
  - *Mobile (`< md`)*: The DataTable renders as a responsive table with `overflow-x-auto` on the container, enabling horizontal scroll. Column headers remain visible.
  - *Alternative*: If horizontal scrolling feels poor on small screens, hide non-essential columns (Version, Skills) on mobile using Tailwind responsive `hidden sm:table-cell` on `<TableCell>`.
  - *Search*: Search input at full width above the table. URL state (`?search=`) persists across page reloads.
  - *Pagination*: "Previous"/"Next" buttons at full width below the table.
- **Filters**:
  - *Mobile*: Filter sidebar hidden behind a "Filter" action `<Button>` that opens a `<Sheet>` (slide-in from right). Filter selections synced with URL params.
  - *Desktop*: Persistent sidebar for filters on the left, DataTable on the right.

### 3. Agent Detail Page (`/agents/[id]`)
- **Header/Stats**:
  - *Mobile*: Stack logo, agent name, trust badge, and key metrics vertically.
- **Content Panels**:
  - *Mobile*: Stack vertically. Use expandable `<Accordion>` (Shadcn) for long sections (Description, Capabilities, SLA).

### 4. Developer Dashboard (`/dashboard`)
- **Navigation**: Handled by the global `<Sidebar>` behavior described above (hamburger → Sheet on mobile).
- **Bento Grid (Metrics Cards)**:
  - *Mobile (`< md`)*: 1 column. BentoCards stack vertically. `md:col-span-2` spans are ignored (single-column).
  - *Touch interaction*: Hover effects (`-translate-y-0.5`, radial gradient reveals) do NOT activate on touch devices. Use `@media (hover: hover)` to scope these effects to pointer devices only:
    ```css
    @media (hover: hover) {
      .group:hover { /* hover effects */ }
    }
    ```
  - *Alternative for touch*: Consider adding a subtle `active:scale-[0.98]` press effect as a mobile-only interaction.
- **Empty State**: Full-width centered on all breakpoints. CTA button at full width on mobile.
- **Skeleton Loading**: Skeleton grid adjusts to 1 column on mobile.

### 5. Features Page (`/features/[slug]`)
- **Bento Cards**: Same responsive behavior as Dashboard — 1 column on mobile, 3 columns on desktop.
- **Touch interactions**: Same `@media (hover: hover)` scoping as Dashboard.

### 6. Developer Experience (`/developer-experience`)
- **BackgroundPaths**: Same behavior as Landing Page — SVG animations remain active, reduce `pathCount` on mobile via a responsive prop or `useMediaQuery()`.
- **AnimatedText**: Runs normally on all breakpoints.

### 7. Authentication Flow (`/auth/signin`, `/dashboard/register`, `/docs/register`)
- **WebGL Canvas**:
  - *Mobile*: The `<Canvas>` component (React Three Fiber) is **GPU-intensive**. On mobile:
    - Lower `dpr` to `[1, 1]` (instead of `[1, 1.5]`) to reduce pixel workload.
    - Reduce shader complexity or animation speed.
    - Ensure `frameloop="demand"` is active (already specified in M4).
    - `useCanvasVisibility` hook pauses rendering when off-screen.
  - *Fallback*: If WebGL context creation fails (some old mobile browsers), render a **static CSS gradient** fallback instead of a blank background. Use a `try/catch` around Canvas init or R3F's `onCreated` callback.
- **Ghost Inputs**:
  - *Mobile*: Input fields remain transparent (`bg-transparent border-white/10`). Ensure the font size is at least `16px` to prevent iOS auto-zoom on focus.
  - **Important**: Add `font-size: 16px` (or Tailwind `text-base`) to all auth inputs to prevent Safari's zoom-on-focus behavior.
- **Form Layout**:
  - *Mobile*: Forms take `w-full max-w-md` — naturally constrained on large screens, full-width on small.
  - *AnimatePresence*: Slide transitions work on all breakpoints. Ensure `x` offset is reduced on mobile (e.g., `x: 50` instead of `x: 100`) to prevent overflow scroll.

---

## Performance Guidelines

| Concern | Desktop | Mobile |
|---|---|---|
| `backdrop-blur` layers | Up to 2 levels | Max 1 level |
| WebGL `dpr` | `[1, 1.5]` | `[1, 1]` |
| BackgroundPaths `pathCount` | 6 | 3–4 |
| BentoCard hover effects | Active | `@media (hover: hover)` only |
| AnimatePresence `x` offset | `100px` | `50px` |
| Auth input `font-size` | Any | `>= 16px` (prevent iOS zoom) |

---

## Testing Requirements
- **E2E**: Sprint M2 adds a mobile viewport test (375×812) for Sidebar → Sheet behavior.
- **Playwright config**: `Mobile Chrome` (Pixel 5) project available in `playwright.config.ts` (currently commented out — recommend enabling for the Design System Revamp sprints).
- **Manual**: Test on real iOS Safari to verify `backdrop-blur` performance and input zoom behavior.
