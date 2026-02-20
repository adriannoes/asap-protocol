# Sprint M1: Web App Foundation

> **Goal**: Next.js project setup and landing page
> **Prerequisites**: v1.3.0 completed
> **Parent Roadmap**: [tasks-v2.0.0-roadmap.md](./tasks-v2.0.0-roadmap.md)

---

## Relevant Files

- `apps/web/` - Next.js application
- `apps/web/app/page.tsx` - Landing page
- `apps/web/app/layout.tsx` - Base layout
- `apps/web/components/` - UI components
- `.cursor/design/mobile-strategy.md` - Mobile responsive layouts strategy
- `.cursor/dev-planning/tasks/v2.0.0/vercel-deploy-guide.md` - Step-by-step Vercel deploy guide (M1)

---

## Context

The web app is the human-facing marketplace interface. This sprint sets up the project and builds the landing page.

---

## Task 1.1: Design & Prototyping (New)

### Sub-tasks

- [x] 1.1.1 Wireframes (Low-fi)
  - Key screens: Landing, Browse, Agent Detail, Dashboard
  - **Tool**: Skipped (Moved to High-fi Mockups directly)

- [x] 1.1.2 High-fidelity Mockups
  - **Focus**: Visual hierarchy, Shadcn theme customization
  - **Requirement**: **Theme: "The Clean Architect" (Vercel Inspired)**
    - **Reference**: `/.cursor/design/landing-reference.png`
    - **Palette**: Pure Black (#000) or Dark Zinc (#09090b) Background.
    - **Vibe**: Clean, Sober, Professional, High-Performance.
    - **Typography**: Geist Sans + Geist Mono.
    - **Visuals**: 1px subtle borders, high contrast text (White/Grey), functional minimalism.
    - **Motion**: Snap transitions, fast and precise.
    - **⚠️ IMPORTANT**: Do NOT use the Vercel logo (triangle) or copy their exact assets. Use the **style**, not the brand.
  - **Output**: Design files or reference images

- [x] 1.1.3 Mobile Responsiveness Plan
  - Define breakpoints and mobile layout adjustments

**Acceptance Criteria**:
- [x] Design mockups approved
- [x] Mobile strategy defined

- [x] 1.1.4 Commit Design Assets
  - **Command**: `git commit -m "docs(design): add wireframes and mockups"`

---

## Task 1.2: Project Setup

### Sub-tasks

- [x] 1.2.1 Initialize Next.js 15 (App Router)
  - **Command**: `npx create-next-app@latest apps/web --typescript --tailwind --eslint`
  - **Directory**: `apps/web/`

- [x] 1.2.2 Set up design system
  - **Colors**: Zinc (Neutral) + Indigo (Primary Brand) + Violet (Accents)
  - **Typography**: `geist-font` (Sans & Mono)
  - **Mode**: Force Dark Mode by default (optional light mode toggle deep in settings)
  - **Utils**: `clsx`, `tailwind-merge`

- [x] 1.2.3 Setup UI Components (Shadcn/UI)
  - **Command**: `npx shadcn@latest init` (Style: New York, Base: Zinc)
  - **Install Core**: `button`, `card`, `input`, `badge`, `separator`, `scroll-area`, `command`
  - **Motion**: `npm install framer-motion` (for "WOW" factor)
  - **Icons**: `npm install lucide-react`

- [x] 1.2.4 Configure Code Quality
  - **ESLint**: Standard Next.js config + `prettier-plugin-tailwindcss`
  - **Prettier**: `.prettierrc` with `printWidth: 100`

- [x] 1.2.5 Set up Environment Variables
  - Create `.env.example`
  - Keys: `NEXT_PUBLIC_APP_URL`, `AUTH_SECRET`, `GITHUB_CLIENT_ID`, `GITHUB_CLIENT_SECRET`

- [x] 1.2.6 Pydantic to TypeScript Sync
  - **Goal**: Ensure frontend types match Protocol models exactly.
  - **Tool**: `datamodel-code-generator` (used json-schema-to-typescript)
  - **Script**: `scripts/generate_types.py` (reads `src/asap/schema/` -> `apps/web/src/types/protocol.d.ts`)
  - **CI**: Check for out-of-sync types on PRs.

- [x] 1.2.7 Commit Setup
  - **Command**: `git commit -m "chore(web): initialize Next.js project structure"`

- [x] 1.2.8 Setup Testing Infrastructure
  - **Unit**: Run `npm install -D vitest @testing-library/react @vitejs/plugin-react jsdom`
  - **E2E**: Run `npm init playwright@latest`
  - **Goal**: Ensure we can test components and flows from Day 1.

- [x] 1.2.9 Setup Lite Registry Data Layer
  - **Goal**: Fetch and parse `registry.json` from GitHub Pages.
  - **Tool**: Standard `fetch` with `next: { revalidate: 60 }` (ISR).
  - **Output**: `lib/registry.ts` with strongly-typed fetch functions.

**Acceptance Criteria**:
- [x] Project builds and runs (`npm run dev`)
- [x] Protocol types generated automatically
- [x] `npm test` runs (even if empty)
- [x] Data layer fetches registry.json successfully

---

## Task 1.3: Landing Page

### Sub-tasks

- [x] 1.3.1 Hero section
  - **Layout**: "The Terminal Centerpiece"
  - **Headline**: "The Marketplace for Autonomous Agents" (with soft purple glow).
  - **Visual**: Central Terminal Window showing a live agent interaction (typing effect).
  - **Composition**:
    - Left/Top: Headline & Subtitle.
    - Center: Terminal Window (Syntax highlighted code).
      - **Content**: Real Protocol Code (Python SDK) showing simplicity.
      - **Example**: `agent = await Agent.connect(...)` -> `await agent.send_task(...)`
    - Actions: "Explore Agents" (Solid Indigo) and "Register Agent" (Glass Outline).

- [x] 1.3.2 Featured Agents (Carousel)
  - **Data**: Fetch top agents from `lib/registry.ts`.
  - **Visual**: Auto-scrolling carousel of agent cards.

- [x] 1.3.3 Features section (Bento Grid)
  - **Layout**: 3x2 Bento Grid styling.
  - **Cards**: "Registry", "Trust", "Integration", "Observability".
  - **Interaction**: Cards have subtle hover glow/border reveal.

- [x] 1.3.4 How it works (Step Timeline)
  - **Visual**: Vertical connecting line (circuit board style).
  - **Steps**: "Discover" -> "Verify" -> "Integrate".

- [x] 1.3.5 CTA buttons
  - **Primary**: "Explore Agents" (Solid White).
  - **Secondary**: "Register Agent" (Dark Outline).

- [x] 1.3.6 Footer
  - **Content**: Copyright, GitHub Link, Docs Link
  - **Style**: Minimal, low contrast text.

- [x] 1.3.7 SEO meta tags

**Acceptance Criteria**:
- [x] Landing page complete and responsive

- [x] 1.3.8 Commit Landing Page
  - **Command**: `git commit -m "feat(web): implement landing page"`

---

## Task 1.4: GitHub OAuth & Identity

### Sub-tasks

- [x] 1.4.1 Configure NextAuth.js (Auth.js)
  - **Provider**: GitHub (`read:user`, `public_repo`)
  - **Goal**: Identify the developer (User ID) and allow them to create PRs for the registry.
  - **Note**: This is *not* ASAP Protocol M2M auth. It is purely for the human dashboard.

- [x] 1.4.2 Login button and flow
  - **UI**: "Sign in with GitHub" (Premium style)

- [x] 1.4.3 Store session secure cookie

- [x] 1.4.4 Protected routes middleware

- [x] 1.4.5 Logout functionality

**Acceptance Criteria**:
- [x] User can log in with GitHub
- [x] User Avatar and Name displayed in header

- [x] 1.4.6 Commit Auth
  - **Command**: `git commit -m "feat(auth): integrate GitHub OAuth provider"`

---

## Task 1.5: Base Layout

### Sub-tasks

- [x] 1.5.1 Header component (`components/layout/header.tsx`)
  - **Left**: Logo (SVG) + Name -> Link to `/`
  - **Center**: Nav Links (Home, Browse, Docs)
  - **Right**:
    - Guest: "Connect / Login" Button (Trigger OAuth)
    - Auth: User Dropdown (Avatar, Dashboard, Logout)

- [x] 1.5.2 Footer component (`components/layout/footer.tsx`)
  - **Content**: Copyright, GitHub Link, Docs Link
  - **Style**: Simple, muted text

- [x] 1.5.3 Responsive navigation
  - **Mobile**: Hamburger menu (Sheet component) for nav links

- [x] 1.5.4 Theme Provider
  - `components/theme-provider.tsx` (next-themes)
  - Mode toggle in footer or header

- [x] 1.5.5 Commit Layout
  - **Command**: `git commit -m "feat(web): add base layout and navigation"`

**Acceptance Criteria**:
- [x] Base layout complete

---

## Task 1.6: Vercel Deployment

> **Step-by-step guide**: [Vercel Deploy Guide](./vercel-deploy-guide.md)

### Sub-tasks

- [x] 1.6.1 Connect GitHub repo to Vercel
  - **Settings**: Root directory `apps/web`
  - **Framework**: Next.js

- [x] 1.6.2 Configure Environment Variables (Vercel)
  - **Production Keys**:
    - `GITHUB_CLIENT_ID` / `GITHUB_CLIENT_SECRET` (OAuth App)
    - `AUTH_SECRET` (generated via `openssl rand -hex 32`)

- [x] 1.6.3 Verify Production Build
  - Ensure `npm run build` passes on Vercel infrastructure

- [x] 1.6.4 Domain Configuration (Optional)
  - Custom domain can be added here or later in M4.

**Acceptance Criteria**:
- [x] Live URL accessible
- [x] CI/CD Deployment triggers on push to main

---

## Sprint M1 Definition of Done

- [x] Design mockups approved
- [x] Next.js project running
- [x] Landing page live (URL verified)
- [x] Auth working
- [x] Base layout complete

**Total Sub-tasks**: ~20

## Documentation Updates
- [x] **Update Roadmap**: Mark completed items in [v2.0.0 Roadmap](./tasks-v2.0.0-roadmap.md)
