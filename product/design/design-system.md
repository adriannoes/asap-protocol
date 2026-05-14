# ASAP Protocol Design System

## 1. Core Philosophy & Goals
- **Theme Name**: "The Clean Architect" (Vercel Inspired)
- **Goal**: Provide a clean, modern, highly functional, and seamless user experience for agent builders and developers.
- **Aesthetics**: Minimalist, high contrast, focus on typography and clear visual hierarchy.

## 2. Technology Stack
- **Framework**: Next.js 16 (App Router) + React 19
- **Styling**: Tailwind CSS v4
- **UI Components**: Shadcn/UI (Style: `new-york`)
- **Animation**: Framer Motion (`framer-motion`)
- **WebGL/3D**: Three.js (`three`) + React Three Fiber (`@react-three/fiber`)
- **Icons**: `lucide-react`
- **Class Merging**: `clsx`, `tailwind-merge`

## 3. Typography
We use the Vercel Geist font family to maintain a sleek, developer-focused aesthetic.
- **Sans-serif (Primary)**: Geist Sans (`var(--font-geist-sans)`)
- **Monospace (Code/Data)**: Geist Mono (`var(--font-geist-mono)`)

## 4. Color Palette (OKLCH)
The application uses a semantic OkLCH color palette natively supported by Tailwind v4. The base is **Zinc** (Neutral).

### Light Mode
- **Background**: `oklch(1 0 0)` (White)
- **Foreground**: `oklch(0.145 0 0)` (Near Black)
- **Primary**: `oklch(0.205 0 0)`
- **Primary Foreground**: `oklch(0.985 0 0)`
- **Muted**: `oklch(0.97 0 0)`
- **Border / Input**: `oklch(0.922 0 0)`
- **Destructive**: `oklch(0.577 0.245 27.325)` (Red)
- **Ring**: `oklch(0.708 0 0)`

### Dark Mode
- **Background**: `oklch(0.145 0 0)` (Near Black)
- **Foreground**: `oklch(0.985 0 0)` (White)
- **Primary**: `oklch(0.922 0 0)`
- **Primary Foreground**: `oklch(0.205 0 0)`
- **Muted**: `oklch(0.269 0 0)`
- **Border / Input**: `oklch(1 0 0 / 10%)`, `oklch(1 0 0 / 15%)`
- **Destructive**: `oklch(0.704 0.191 22.216)` (Red)
- **Ring**: `oklch(0.556 0 0)`

*Note: Indigo / Violet (`indigo-500`, `violet-500`) are used for accents, brand highlights, and visual elements where primary neutral is too stark.*

## 5. Spacing, Layout & Radii
- **Radii**: The base border-radius is `0.625rem` (10px). All components derive their curve from `--radius`. We strictly avoid generic "pill-shape" (`rounded-full`) layouts for main content areas to maintain a sharp, technical aesthetic.
- **Breakpoints**: Standard Tailwind breakpoints (`sm`, `md`, `lg`, `xl`, `2xl`).
- **Mobile Strategy**: Hamburger menu triggering a sliding `Sheet` component for navigation links to ensure a responsive developer experience.

## 6. Component Guidelines (Shadcn/UI)
- **Buttons**: High contrast primary buttons. Outline and Ghost variants for secondary actions. Avoid heavy gradients on standard buttons.
- **Cards**: Minimal borders (`border-white/10`), subtle shadows in light mode, clean separation in dark mode. Never use default heavy drop-shadows.
- **Forms**: Clear labels, distinct focus rings (`outline-ring/50`).
- **Dark Mode**: Fully supported via Next-Themes (`components/theme-provider.tsx`), avoiding harsh pure blacks but using dark greys (`oklch(0.145...`) to reduce eye strain.

## 7. Structural Layout, Tables & State

### 7.1. Global Shell (Sidebar)
- **Component**: Utilize the official Shadcn `Sidebar` component (`v0.8.0+`) for the application shell.
- **Behavior**: 
  - Desktop: Persistent or collapsible left-rail. 
  - Mobile: Automatically transitions to a draggable `Sheet` or hidden drawer.
- **Aesthetics**: The sidebar should blend with the `bg-background` or use a very subtle `bg-sidebar` token to maintain the Clean Architect feel without heavy visual separation.

### 7.2. Data Presentation (Tables & Lists)
- **Internal Dashboards (Tables)**: Utilize Shadcn `DataTable` (powered by TanStack Table) strictly for internal data management (e.g., "My Agents", API Logs). Tables must include functional Pagination, Column Sorting, and minimal global filtering (Search). Table rows should maintain subtle hover states (`hover:bg-muted/50`).
- **Public Marketplaces (Cards)**: Utilize Bento Grid styles and Cards for public-facing discovery pages (e.g., the `/browse` Agent Registry and Landing Pages). These cards should leverage the high-end interaction physics defined in Section 8 (e.g., `-translate-y-0.5`, `backdrop-blur` layers, fluid badges) to present a premium storefront feel.

### 7.3. Forms & Intermediary Actions
- **Component**: Utilize Shadcn `Dialog` (Centered Modal) for standard creation forms (e.g., Registering a new agent). Use `Sheet` (Side Drawer) only for deep context flows where the user needs to reference the underlying page.
- **Style**: Dialogs should feature strong `backdrop-blur-sm` overlays to focus attention, removing background distraction.

### 7.4. Empty States & Loading Feedback
- **Loading (Skeletons)**: Never use generic spinners for layout loading. Always use Shadcn `Skeleton` components that map to the exact shape of the incoming data (e.g., a grid of Card Skeletons).
- **Empty States**: If a table or grid has no data, present a centralized, beautifully formatted Empty State indicating exactly what to do next, utilizing `lucide-react` icons (light opacity) and a primary Call to Action button.

## 8. Motion & Micro-interactions (Premium UI)
To elevate the developer experience and provide an "Apple/Vercel-tier" feel, we adopt specific advanced micro-interactions for Hero sections and high-value interactive areas. These rely heavily on `framer-motion` and advanced Tailwind utilities.

### 8.1. Glassmorphism & Depth
- **Containers**: Nested gradients with `backdrop-blur`. 
  - Outer Wrapper: Creates a 1px pseudo-border using `bg-gradient-to-b from-black/10 to-white/10 p-px rounded-2xl backdrop-blur-lg`.
  - Inner Element: `bg-white/95 backdrop-blur-md` (or dark mode equivalents) to create a translucent, frosted glass effect over complex backgrounds.
- **Ambient Shadows**: Very soft but wide shadow fade-ins on hover (`hover:shadow-[0_2px_12px_rgba(0,0,0,0.03)]`), providing depth without harsh contrast.

### 8.2. "Bento" Cards & Nested Reveals
*(Note on Shadcn Compatibility: The Bento grid pattern is NOT a replacement for Shadcn `<Card>`, but an extension of it. The base of a Bento item should still utilize standard Shadcn classes or structures, enhanced only by the specific hover physics defined below for high-impact dashboard areas.)*

- **The Lift**: Cards and interactive panels should lift softly on hover using `-translate-y-0.5` combined with `will-change-transform` for 60fps smoothness.
- **Complex Reveals**: High-value cards (Data, Metrics, Features) utilize absolute, `opacity-0` background layers containing radial grids (`bg-[radial-gradient(...)]`) or gradient "gleams" that transition to `opacity-100` on `group-hover`.
- **Micro-components (Tags/Badges)**: 
  - Fluid badges use extreme transparency (`bg-black/5 dark:bg-white/10`) with `backdrop-blur-sm`.
  - Nested Interaction: Badges inside hovering cards have their own localized hover states (`hover:bg-black/10`) creating a satisfying, layered interaction model.

### 8.3. Anti-Boilerplate Signatures
To ensure the ASAP Protocol UI does not look like a generic AI-generated template (e.g., Lovable, v0 defaults), strictly enforce these signatures:
- **Monochromatic Discipline**: Do not mix multiple primary colors (e.g., blue buttons + green tags + red alerts). Rely heavily on Zinc/Greyscale for 90% of the UI, reserving the Indigo accent ONLY for interactive focal points.
- **Micro-Borders**: Rely on 1px translucent borders (`border-white/10` or `border-black/5`) instead of drop-shadows to separate overlapping elements.
- **Typography Leading**: Keep line-heights (`leading-snug` or `leading-tight`) closer than default Tailwind prose to maintain a dense, "dashboard-first" feel rather than a "blog-first" feel.

### 8.4. Typography Motion
- **Hero Headers**: Prominent text should use staggered letter-by-letter or word-by-word reveals using Framer Motion `spring` physics (`stiffness: 150`, `damping: 25`).
- **Gradient Text**: High-impact text utilizes `bg-clip-text text-transparent bg-gradient-to-r from-neutral-900 to-neutral-700/80` (or `dark:from-white dark:to-white/80`).

### 8.5. Interactive Hover States (Buttons/Links)
- **Lift**: Subtle negative Y-translation on hover (`group-hover:-translate-y-0.5`).
- **Icon Handoff**: Icons inside interactive elements should push outwards slightly to indicate directionality (`group-hover:translate-x-1.5 transition-all duration-300`).

### 8.6. Authentication & Focus Flows (WebGL)
For high-impact, single-focus pages like Login, Sign-up, or initial Onboarding, we utilize immersive 3D backgrounds to create a memorable entry point.
- **Canvas Environments**: Utilize `<Canvas>` (from React Three Fiber) with custom Fragment Shaders (`ShaderMaterial`) to create deep, animated backgrounds (e.g., repeating dot matrices, particle flows).
- **State-Reactive**: The 3D environment must react to the user's progress. For example, reversing the animation flow when an OTP is completed, or shifting colors on success.
- **Liquid Form Transitions**: Authentication steps (Email → OTP → Success) should never swap abruptly. Use `AnimatePresence` to slide forms out left (`x: -100`, `opacity: 0`) and slide new forms in from the right (`x: 100`, `opacity: 1`) using spring or easeOut easing.
- **Ghost Inputs**: Form fields on these pages should use extreme transparency (`bg-transparent border-white/10`) to let the 3D canvas shine through, glowing slightly only on focus.

## 9. Next Steps for Expansion
*(To be detailed in future sprints)*
- Extended data visualization color scales (Charts 1-5 currently defined in globals.css).
- Standardized error boundaries and toast notification logic.
