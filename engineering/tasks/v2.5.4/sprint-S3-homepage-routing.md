# Sprint S3: Homepage narrative & CTA routing (v2.5.4)

**PRD**: DIST-001, DIST-002, DIST-005 (homepage link remainder), DIST-006
**Branch**: `feat/v2.5.4-s3-s5-homepage-telemetry-release` → **`release/2.5.4`**
**Depends on**: [S1](./sprint-S1-starter-pack.md), [S2](./sprint-S2-build-for-agents-guide.md)
**Status**: Done (implementation; no commit in this pass)

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

- [x] **4.1 Hero & metadata (DIST-001 + DIST-005 remainder)**
  - [x] Update `HeroSection.tsx` / `HeroTerminal.tsx` for agent-first primary narrative
  - [x] Primary CTAs → `docs/guides/build-for-agents.md` (DIST-005 homepage half) and/or `examples/starters/`
  - [x] Secondary CTAs may remain Explore Agents / Register Agent
  - [x] Fix stale version strings (terminal/badge/metadata) toward train version policy
  - [x] Align `page.tsx` OG/metadata with D1 (not marketplace-only)

- [x] **4.2 Section routing (DIST-002)**
  - [x] WhatsNew / Features / How it Works: each primary action links to concrete docs, starter, or example
  - [x] Audit Lab II CTAs still live; fill gaps on feature/DX cards that lack `docsHref`
  - [x] Keep GitHub docs URLs on `main` (or documented tag policy)

- [x] **4.3 Telemetry IDs**
  - [x] Update/extend `homepage-cta-ids.ts` if new CTAs added
  - [x] Confirm `CtaClickTracker` / `data-cta` still fire

- [x] **4.4 DIST-006 copy gate**
  - [x] Grep/review homepage + related landing copy for pricing/fundraising/private GTM
  - [x] Do not pull content from `product/strategy/` or private PRDs

- [x] **4.5 Docs review web sections**
  - [x] Complete web/CTA items in [docs-review-checklist.md](./docs-review-checklist.md)

---

## Acceptance criteria

- [x] Hero matches D1 hierarchy
- [x] Primary CTAs resolve to live guide/starter/example URLs (including homepage → build-for-agents for DIST-005 remainder)
- [x] Marketplace paths remain available but secondary
- [x] `data-cta` coherent; no broken primary links
- [x] DIST-001, DIST-002, DIST-005 (homepage link), DIST-006 satisfied
- [x] Web quality gates pass when run (`lint`, `tsc`, vitest, build)

## Reviews

| Date | Tier | Verdict | Report |
|------|------|---------|--------|
| 2026-07-18 | T2 | Approved with caveats | [review-v2.5.4-S3-S5-homepage-telemetry-release-20260718.md](../../code-review/private/review-v2.5.4-S3-S5-homepage-telemetry-release-20260718.md) |

## Relevant files

- `apps/web/src/app/page.tsx`
- `apps/web/src/app/layout.tsx`
- `apps/web/src/components/landing/HeroSection.tsx`
- `apps/web/src/components/landing/HeroTerminal.tsx`
- `apps/web/src/components/landing/HowItWorksSection.tsx`
- `apps/web/src/components/landing/WhatsNewRibbon.tsx`
- `apps/web/src/components/landing/FeaturesSection.tsx`
- `apps/web/src/lib/landing/dist-loop-links.ts`
- `apps/web/src/lib/telemetry/homepage-cta-ids.ts`
- `apps/web/src/lib/telemetry/homepage-cta-ids.test.ts`
- `apps/web/tests/auth-journey.spec.ts` (hero heading assertion)
- `docs/guides/build-for-agents.md`
- `examples/starters/README.md`
- `engineering/tasks/v2.5.4/docs-review-checklist.md`
- `engineering/tasks/v2.5.4/tasks-v2.5.4-roadmap.md`
