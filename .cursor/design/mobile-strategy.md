# Mobile Responsiveness Strategy (v2.0.0 Web App)

## Breakpoints (Tailwind CSS defaults)
- `sm`: 640px (Mobile Landscape / Large Phones)
- `md`: 768px (Tablets)
- `lg`: 1024px (Laptops)
- `xl`: 1280px (Desktops)

## Layout Adjustments per Screen

### 1. Landing Page
- **Hero Section**: 
  - *Mobile (`< lg`)*: Stack vertically. Headline centered, terminal window scales down and sits below the text. CTA buttons take full width.
  - *Desktop (`>= lg`)*: Side-by-side or split layout.
- **Features (Bento Grid)**: 
  - *Mobile*: 1 column grid.
  - *Tablet (`md`)*: 2 columns.
  - *Desktop (`lg`)*: 3x2 bento grid structure.
- **How it Works**:
  - *Mobile*: Vertical timeline layout.
- **Navigation**:
  - *Mobile*: Hamburger menu triggering a sliding `Sheet` (via Shadcn) for navigation links.

### 2. Registry Browser
- **Layout**:
  - *Mobile*: Search bar at the top. Filters hidden behind a "Filter" action button that opens a side `Sheet`. Agent cards in a 1-column layout.
  - *Desktop*: Persistent sidebar for filters on the left, grid of agents on the right.

### 3. Agent Detail Page
- **Header/Stats**:
  - *Mobile*: Stack logo, agent name, trust badge, and key metrics vertically for readability.
- **Content Panels**:
  - *Mobile*: Stack description, capabilities (skills), and SLA vertically. Use expandable accordions if content is too long.

### 4. Developer Dashboard
- **Navigation**:
  - *Mobile*: Simplify to a clean mobile menu (hamburger) instead of a persistent sidebar.
- **Data Display (My Agents)**:
  - *Mobile*: Transform wide tables into a card-based list, or ensure the table container has horizontal scrolling (`overflow-x-auto`).
