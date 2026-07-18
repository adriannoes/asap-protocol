# Sprint S3: Homepage narrative & CTA routing (v2.5.4)

**PRD**: DIST-001, DIST-002, DIST-005 (homepage link remainder), DIST-006  
**Branch**: `feat/v2.5.4-s3-homepage-routing` → **`release/2.5.4`**  
**Depends on**: [S1](./sprint-S1-starter-pack.md), [S2](./sprint-S2-build-for-agents-guide.md)  
**Status**: Planned

**Trigger:** Guide and starters available for primary CTAs.  
**Enables:** S5 public web surface.  
**Depends on:** [docs-review-checklist.md](./docs-review-checklist.md) web/CTA sections.

---

## Goal

Apply D1 hierarchy on the homepage: agent-first primary story and CTAs into the guide/starters; keep marketplace browse/register secondary. Complete docs routing for homepage sections without a full design-system rewrite. **DIST-005 remainder:** link the homepage primary CTA → `docs/guides/build-for-agents.md` (S2 shipped the guide + MkDocs + starters-index + docs/index; homepage link is owned here with DIST-001/002).

---

## Design constraints

- Copy and routing first; avoid full Design System Revamp scope.
- Preserve stable `data-cta` IDs in `homepage-cta-ids.ts` (add only when necessary; do not rename casually).
- Do not invent pages—link to shipped guide/starters/docs.
- DIST-006 continuous review on all public strings touched.

---

## Tasks

- [ ] **4.1 Hero & metadata (DIST-001 + DIST-005 remainder)**
  - [ ] Update `HeroSection.tsx` / `HeroTerminal.tsx` for agent-first primary narrative
  - [ ] Primary CTAs → `docs/guides/build-for-agents.md` (DIST-005 homepage half) and/or `examples/starters/`
  - [ ] Secondary CTAs may remain Explore Agents / Register Agent
  - [ ] Fix stale version strings (terminal/badge/metadata) toward train version policy
  - [ ] Align `page.tsx` OG/metadata with D1 (not marketplace-only)

- [ ] **4.2 Section routing (DIST-002)**
  - [ ] WhatsNew / Features / How it Works: each primary action links to concrete docs, starter, or example
  - [ ] Audit Lab II CTAs still live; fill gaps on feature/DX cards that lack `docsHref`
  - [ ] Keep GitHub docs URLs on `main` (or documented tag policy)

- [ ] **4.3 Telemetry IDs**
  - [ ] Update/extend `homepage-cta-ids.ts` if new CTAs added
  - [ ] Confirm `CtaClickTracker` / `data-cta` still fire

- [ ] **4.4 DIST-006 copy gate**
  - [ ] Grep/review homepage + related landing copy for pricing/fundraising/private GTM
  - [ ] Do not pull content from `product/strategy/` or private PRDs

- [ ] **4.5 Docs review web sections**
  - [ ] Complete web/CTA items in [docs-review-checklist.md](./docs-review-checklist.md)

---

## Acceptance criteria

- [ ] Hero matches D1 hierarchy
- [ ] Primary CTAs resolve to live guide/starter/example URLs (including homepage → build-for-agents for DIST-005 remainder)
- [ ] Marketplace paths remain available but secondary
- [ ] `data-cta` coherent; no broken primary links
- [ ] DIST-001, DIST-002, DIST-005 (homepage link), DIST-006 satisfied
- [ ] Web quality gates pass when run (`lint`, `tsc`, vitest, build)

## Reviews

| Date | Tier | Verdict | Report |
|------|------|---------|--------|
| — | — | — | — |

## Relevant files

- `apps/web/src/app/page.tsx`
- `apps/web/src/components/landing/HeroSection.tsx`
- `apps/web/src/components/landing/HeroTerminal.tsx`
- `apps/web/src/components/landing/HowItWorksSection.tsx`
- `apps/web/src/components/landing/WhatsNewRibbon.tsx`
- `apps/web/src/components/landing/FeaturesSection.tsx`
- `apps/web/src/lib/telemetry/homepage-cta-ids.ts`
- `apps/web/src/app/developer-experience/page.tsx` (only if CTA gaps)
- `docs/guides/build-for-agents.md`
- `examples/starters/README.md`
