# Sprint M3: Web App Foundation

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

## Task 3.1: Project Setup

### Sub-tasks

- [ ] 3.1.1 Initialize Next.js 15 (App Router)
  - **Command**: `npx create-next-app@latest apps/web --typescript --tailwind --eslint`
  - **Directory**: `apps/web/`

- [ ] 3.1.2 Set up design system
  - Colors, typography, spacing

- [ ] 3.1.3 Setup UI Components (Shadcn)
  - **Command**: `npx shadcn@latest init`
  - **Install**: `button`, `card`, `input`, `dialog`
  - **Theme**: Slate/Zinc with CSS variables

- [ ] 3.1.4 Configure ESLint, Prettier

- [ ] 3.1.5 Set up environment variables

**Acceptance Criteria**:
- [ ] Project builds and runs

---

## Task 3.2: Landing Page

### Sub-tasks

- [ ] 3.2.1 Hero section
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

---

## Task 3.3: OAuth2 Login

### Sub-tasks

- [ ] 3.3.1 Integrate ASAP OAuth2

- [ ] 3.3.2 Login button and flow

- [ ] 3.3.3 Store token securely

- [ ] 3.3.4 Protected routes

- [ ] 3.3.5 Logout functionality

**Acceptance Criteria**:
- [ ] Auth flow working

---

## Task 3.4: Base Layout

### Sub-tasks

- [ ] 3.4.1 Header component
  - Logo, nav, user menu

- [ ] 3.4.2 Footer component

- [ ] 3.4.3 Responsive navigation

- [ ] 3.4.4 Dark mode (optional)

**Acceptance Criteria**:
- [ ] Base layout complete

---

## Sprint M3 Definition of Done

- [ ] Next.js project running
- [ ] Landing page live
- [ ] Auth working
- [ ] Base layout complete

**Total Sub-tasks**: ~20
