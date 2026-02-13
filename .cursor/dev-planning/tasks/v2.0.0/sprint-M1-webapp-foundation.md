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

---

## Context

The web app is the human-facing marketplace interface. This sprint sets up the project and builds the landing page.

---

## Task 1.1: Design & Prototyping (New)

### Sub-tasks

- [ ] 1.1.1 Wireframes (Low-fi)
  - Key screens: Landing, Browse, Agent Detail, Dashboard
  - **Tool**: Excalidraw or similar

- [ ] 1.1.2 High-fidelity Mockups
  - **Focus**: Visual hierarchy, Shadcn theme customization
  - **Output**: Design files or reference images

- [ ] 1.1.3 Mobile Responsiveness Plan
  - Define breakpoints and mobile layout adjustments

**Acceptance Criteria**:
- [ ] Design mockups approved
- [ ] Mobile strategy defined

- [ ] 1.1.4 Commit Design Assets
  - **Command**: `git commit -m "docs(design): add wireframes and mockups"`

---

## Task 1.2: Project Setup

### Sub-tasks

- [ ] 3.1.1 Initialize Next.js 15 (App Router)
  - **Command**: `npx create-next-app@latest apps/web --typescript --tailwind --eslint`
  - **Directory**: `apps/web/`

- [ ] 3.1.2 Set up design system
  - **Colors**: Slate (Neutral) + Indigo (Primary Brand)
  - **Typography**: Inter (Sans) via `next/font/google`
  - **Utils**: `clsx`, `tailwind-merge` (standard `cn` helper)

- [ ] 3.1.3 Setup UI Components (Shadcn/UI)
  - **Command**: `npx shadcn@latest init` (Style: New York, Base: Zinc)
  - **Install Core**: `button`, `card`, `input`, `label`, `dialog`, `dropdown-menu`, `avatar`, `separator`
  - **Icons**: `npm install lucide-react`

- [ ] 3.1.4 Configure Code Quality
  - **ESLint**: Standard Next.js config + `prettier-plugin-tailwindcss`
  - **Prettier**: `.prettierrc` with `printWidth: 100`

- [ ] 1.2.5 Set up Environment Variables
  - Create `.env.example`
  - Keys: `NEXT_PUBLIC_APP_URL`, `AUTH_SECRET`, `GITHUB_CLIENT_ID`, `GITHUB_CLIENT_SECRET`

- [ ] 1.2.6 Commit Setup
  - **Command**: `git commit -m "chore(web): initialize Next.js project structure"`

**Acceptance Criteria**:
- [ ] Project builds and runs

---

## Task 1.3: Landing Page

### Sub-tasks

- [ ] 1.3.1 Hero section
  - Value proposition, headline

- [ ] 3.2.2 Features section
  - Key benefits

- [ ] 3.2.3 How it works
  - Simple steps

- [ ] 3.2.4 CTA buttons
  - "Get Started", "Browse Agents"

- [ ] 3.2.5 Footer
  - Links, social, docs

- [ ] 3.2.6 SEO meta tags

**Acceptance Criteria**:
- [ ] Landing page complete and responsive

- [ ] 1.3.7 Commit Landing Page
  - **Command**: `git commit -m "feat(web): implement landing page"`

---

## Task 1.4: OAuth2 Login

### Sub-tasks

- [ ] 1.4.1 Integrate ASAP OAuth2

- [ ] 3.3.2 Login button and flow

- [ ] 3.3.3 Store token securely

- [ ] 3.3.4 Protected routes

- [ ] 3.3.5 Logout functionality

**Acceptance Criteria**:
- [ ] Auth flow working

- [ ] 1.4.6 Commit Auth
  - **Command**: `git commit -m "feat(auth): integrate GitHub OAuth provider"`

---

## Task 1.5: Base Layout

### Sub-tasks

- [ ] 1.5.1 Header component (`components/layout/header.tsx`)
  - **Left**: Logo (SVG) + Name -> Link to `/`
  - **Center**: Nav Links (Home, Browse, Docs)
  - **Right**:
    - Guest: "Connect / Login" Button (Trigger OAuth)
    - Auth: User Dropdown (Avatar, Dashboard, Logout)

- [ ] 3.4.2 Footer component (`components/layout/footer.tsx`)
  - **Content**: Copyright, GitHub Link, Docs Link
  - **Style**: Simple, muted text

- [ ] 3.4.3 Responsive navigation
  - **Mobile**: Hamburger menu (Sheet component) for nav links

  - `components/theme-provider.tsx` (next-themes)
  - Mode toggle in footer or header

- [ ] 1.5.5 Commit Layout
  - **Command**: `git commit -m "feat(web): add base layout and navigation"`

**Acceptance Criteria**:
- [ ] Base layout complete

---

## Task 1.6: Vercel Deployment

### Sub-tasks

- [ ] 1.6.1 Connect GitHub repo to Vercel
  - **Settings**: Root directory `apps/web`
  - **Framework**: Next.js

- [ ] 3.5.2 Configure Environment Variables (Vercel)
  - **Production Keys**:
    - `NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY` / `STRIPE_SECRET_KEY`
    - `GITHUB_CLIENT_ID` / `GITHUB_CLIENT_SECRET` (OAuth App)
    - `AUTH_SECRET` (generated via `openssl rand -hex 32`)

- [ ] 3.5.3 Verify Production Build
  - Ensure `npm run build` passes on Vercel infrastructure

- [ ] 3.5.4 Domain Configuration (Optional)
  - Connect custom domain if available

**Acceptance Criteria**:
- [ ] Live URL accessible (e.g., `asap-marketplace.vercel.app`)
- [ ] CI/CD Deployment triggers on push to main

---

## Sprint M1 Definition of Done

- [ ] Design mockups approved
- [ ] Next.js project running
- [ ] Landing page live (URL verified)
- [ ] Auth working
- [ ] Base layout complete

**Total Sub-tasks**: ~20
