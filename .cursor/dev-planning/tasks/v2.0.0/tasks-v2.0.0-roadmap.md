# Tasks: ASAP Protocol v2.0.0 Roadmap

> **High-level task overview** for v2.0.0 milestone (Lean Marketplace + Web App)
>
> **Parent PRD**: [prd-v2.0-roadmap.md](../../../product-specs/prd/prd-v2.0-roadmap.md)
> **Prerequisite**: v1.3.0 released
> **Target Version**: v2.0.0
> **Focus**: Web App, Lite Registry integration, Verified Badge
>
> 💡 **For detailed step-by-step instructions**, see sprint files:
> - [M1: Web App Foundation](./sprint-M1-webapp-foundation.md)
> - [M2: Web App Features](./sprint-M2-webapp-features.md)
> - [M3: Verified Badge & Payments](./sprint-M3-verified-payments.md)
> - [M4: Launch Preparation](./sprint-M4-launch-prep.md)
>
> **Lean Marketplace Pivot**: Production Registry backend (formerly M1/M2) removed. Web App reads from Lite Registry (`registry.json` on GitHub Pages). No FastAPI backend, no PostgreSQL, no Railway. See [deferred-backlog.md](../../../product-specs/strategy/deferred-backlog.md).

---

## Strategic Context

v2.0.0 launches the Lean Marketplace — a Web App that reads from the Lite Registry:
- **Web App**: Next.js 15 frontend on Vercel (SSG/ISR from `registry.json`)
- **Lite Registry**: GitHub Pages JSON as the sole data source (no backend API)
- **Verified Badge**: Stripe-powered trust verification
- **No Backend**: All dynamic features (write API, real-time search) deferred to v2.1

> [!NOTE]
> **Deferred from v2.0**: Registry API Backend (to v2.1), Economy Settlement (to v3.0). See [deferred-backlog.md](../../../product-specs/strategy/deferred-backlog.md).

---

## Sprint M1: Web App Foundation

**Goal**: Build Web App foundation with Lite Registry integration

### Tasks

- [ ] 1.1 Design & Prototyping
  - Goal: Wireframes and High-fidelity mockups for core pages

- [ ] 1.2 Project setup
  - Goal: Next.js 15 (App Router) + TailwindCSS + Shadcn/UI
  - Deliverable: `apps/web/` initialized

- [ ] 1.2 Lite Registry data layer
  - Goal: Fetch and parse `registry.json` (SSG/ISR)
  - Deliverable: TypeScript types + data fetching utilities

- [ ] 1.3 Landing page
  - Goal: Hero, value prop, CTA

- [ ] 1.4 OAuth2 login flow
  - Goal: Developer authentication (GitHub Sign-In)

- [ ] 1.5 Base layout and navigation

### Definition of Done
- [ ] Landing page live on Vercel
- [ ] `registry.json` parsed and agents displayable
- [ ] Login/logout working

---

## Sprint M2: Web App Features

**Goal**: Registry browser and developer dashboard

### Tasks

- [ ] 2.1 Registry browser page
  - Goal: Search and filter agents from Lite Registry data
  - Note: Client-side filtering of static JSON

- [ ] 2.2 Agent detail page
  - Goal: Full agent info, skills, SLA, trust level

- [ ] 2.3 Developer dashboard
  - Goal: My agents, metrics overview

- [ ] 2.4 "Register agent" instructions
  - Goal: Guide developers to submit PR to Lite Registry
  - Note: No write API — registration is via GitHub PR

### Definition of Done
- [ ] Browse and search working
- [ ] Agent details page complete
- [ ] PR submission flow documented

---

## Sprint M3: Verified Badge & Payments

**Goal**: Verified badge service with Stripe

### Tasks

- [ ] 3.1 Stripe integration
- [ ] 3.2 "Apply for Verified" flow
- [ ] 3.3 Checkout flow ($49/month)
- [ ] 3.4 ASAP CA signing on approval
- [ ] 3.5 Admin review queue

### Definition of Done
- [ ] Payment flow end-to-end
- [ ] Verified badge appears after approval

---

## Sprint M4: Launch Preparation

**Goal**: Production readiness and launch

### Tasks

- [ ] 4.1 Security audit
- [ ] 4.2 Performance testing (100+ agents in Lite Registry)
- [ ] 4.3 Monitoring setup (Vercel analytics)
- [ ] 4.4 Documentation complete
- [ ] 4.5 Beta program (20+ registered agents)
- [ ] 4.6 Launch!

### Definition of Done
- [ ] All launch criteria met (per PRD)
- [ ] Security audit passed
- [ ] Public launch

---

## Tech Debt & Performance Notes

> **Note**: The following items were identified during v1.x development and should be considered during v2.0.0 if performance bottlenecks appear.

### Resolved by M3: sign_with_ca Simulation → Real CA Service

**Context**: [Issue #44](https://github.com/adriannoes/asap-protocol/issues/44) — `sign_with_ca` in `src/asap/crypto/trust.py` is a simulation (caller provides CA key). Acceptable for v1.2.0; must be integrated into a real flow for v2.0.

**Resolved by**: Task 3.4 (ASAP CA Signing Automation) — GitHub Action + Stripe approval flow will use the CA key from secrets to sign manifests. When implementing 3.4, close #44 and add a comment linking to this task.

### Consider: orjson for JSON Serialization

**Context**: If JSON serialization becomes a bottleneck with high traffic in the Marketplace, consider replacing stdlib `json` with `orjson` (Rust-based, ~10x faster).

**When to evaluate**: During M4 performance testing (4.2) if API response times are slow.

**Implementation**: 
- Add `orjson>=3.9` to dependencies
- Create thin wrapper `asap.utils.json` that uses orjson
- Benchmark before/after

**Decision**: Not required unless testing reveals bottleneck.

---

### Optional: Add bandit to CI

**Context**: bandit scans Python code for security issues (hardcoded passwords, SQL injection patterns, weak crypto). Currently only runs locally as dev dependency.

**When to add**: Before public launch (M4) when external contributors or public scrutiny increase.

**Implementation**:
- Add to `.github/workflows/ci.yml` security job
- Configure exclusions in `pyproject.toml` or `.bandit`
- Start with `--severity-level medium` to reduce noise

**Decision**: Optional - evaluate when preparing for public launch.

---

## Summary

| Sprint | Tasks | Focus | Est. Days |
|--------|-------|-------|-----------|
| M1 | 5 | Web Foundation + Lite Registry | 6-8 |
| M2 | 4 | Web Features | 5-7 |
| M3 | 5 | Verified + Payments | 6-8 |
| M4 | 6 | Launch Prep | 6-10 |

**Total**: 20 tasks across 4 sprints

---

## Progress Tracking

**Overall Progress**: 0/20 tasks (0%)

**Last Updated**: 2026-02-12

---

## Related Documents

- **PRD**: [prd-v2.0-roadmap.md](../../../product-specs/prd/prd-v2.0-roadmap.md)
- **Deferred Backlog**: [deferred-backlog.md](../../../product-specs/strategy/deferred-backlog.md)
- **Roadmap**: [roadmap-to-marketplace.md](../../../product-specs/strategy/roadmap-to-marketplace.md)
- **Vision**: [vision-agent-marketplace.md](../../../product-specs/strategy/vision-agent-marketplace.md)

---

## Change Log

| Date | Change |
|------|--------|
| 2026-02-06 | Initial task roadmap |
| 2026-02-12 | **Lean Marketplace pivot**: Removed Production Registry sprints (M1/M2), removed Service Integration sprint, Web App reads from Lite Registry, reduced from 6 sprints (27 tasks) to 4 sprints (20 tasks), scale targets reduced to 100+ agents |
