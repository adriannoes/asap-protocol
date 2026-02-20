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
> - [M3: Developer Experience (IssueOps)](./sprint-M3-developer-experience.md)
> - [M4: Launch Preparation](./sprint-M4-launch-prep.md)
>
> **Lean Marketplace Pivot**: Production Registry backend (formerly M1/M2) removed. Web App reads from Lite Registry (`registry.json` on GitHub Pages). No FastAPI backend, no PostgreSQL, no Railway. See [deferred-backlog.md](../../../product-specs/strategy/deferred-backlog.md).
>
> **Usage & Control**: For evolution of usage storage (local → central) and consumer dashboard, see [v2.0-marketplace-usage-foundation.md](./v2.0-marketplace-usage-foundation.md).

---

## Strategic Context

v2.0.0 launches the Lean Marketplace — a Web App that reads from the Lite Registry:
- **Web App**: Next.js 15 frontend on Vercel (SSG/ISR from `registry.json`)
- **Lite Registry**: GitHub Pages JSON as the sole data source (no backend API)
- **Verified Badge**: Operations-based trust verification (Manual Review)
- **No Backend**: All dynamic features (write API, real-time search) deferred to v2.1

> [!NOTE]
> **Deferred from v2.0**: Registry API Backend (to v2.1), Economy Settlement (to v3.0). See [deferred-backlog.md](../../../product-specs/strategy/deferred-backlog.md).

---

## Sprint M1: Web App Foundation

**Goal**: Build Web App foundation with Lite Registry integration

### Tasks

- [x] 1.1 Design & Prototyping
  - Goal: Wireframes and High-fidelity mockups for core pages

- [x] 1.2 Project setup
  - Goal: Next.js 15 (App Router) + TailwindCSS + Shadcn/UI
  - Deliverable: `apps/web/` initialized

- [x] 1.2 Lite Registry data layer
  - Goal: Fetch and parse `registry.json` (SSG/ISR)
  - Deliverable: TypeScript types + data fetching utilities

- [x] 1.3 Landing page
  - Goal: Hero, value prop, CTA

- [x] 1.4 OAuth2 login flow
  - Goal: Developer authentication (GitHub Sign-In)

- [x] 1.5 Base layout and navigation

- [x] 1.6 Vercel deployment
  - Goal: Production deploy, env vars, CI/CD on push to main

### Definition of Done
- [x] Landing page live on Vercel
- [x] `registry.json` parsed and agents displayable
- [x] Login/logout working

---

## Sprint M2: Web App Features

**Goal**: Registry browser and developer dashboard

**Pre-M2 Validation** (2026-02-19): ✅ Complete — registry fetch, GitHub PR flow, OAuth token in JWT. See [pre-M2-validation-guide.md](./pre-M2-validation-guide.md).

### Tasks

- [x] 2.1 Registry browser page
  - Goal: Search and filter agents from Lite Registry data
  - Note: Client-side filtering of static JSON

- [x] 2.2 Agent detail page
  - Goal: Full agent info, skills, SLA, trust level

- [x] 2.3 Developer dashboard
  - Goal: My agents, metrics overview

- [x] 2.4 "Register agent" instructions
  - Goal: Guide developers to submit PR to Lite Registry
  - Note: No write API — registration is via GitHub PR

### Definition of Done
- [x] Browse and search working
- [x] Agent details page complete
- [x] PR submission flow documented

---

## Sprint M3: Developer Experience (IssueOps)

**Goal**: Low-friction registration flow

### Tasks

- [ ] 3.1 GitHub Issue Template configured
  - Goal: YAML template for agent registration

- [ ] 3.2 Registration Form (Web)
  - Goal: Web form that validates input and links to GitHub Issue creation

- [ ] 3.3 Registration Action (GitHub Actions)
 - Goal: Parse Issue YAML, validate Zod schema, update `registry.json`, close issue

- [ ] 3.4 Developer Dashboard (with Verified status)
 - Goal: "My Agents" list derived from `maintainers` field in registry
 - Status: Listed, Pending, Verified

- [ ] 3.5 Verified Badge Request (New)
 - Goal: IssueOps flow for requesting verification (No payments)

### Definition of Done
- [ ] User can register agent via Web Form -> GitHub Issue flow
- [ ] User can request verification via Web Form -> GitHub Issue flow
- [ ] Action automatically merges valid agents
---

## Sprint M4: Launch Preparation

**Goal**: Production readiness and launch

### Tasks

- [ ] 4.1 Security audit
- [ ] 4.2 Performance testing (100+ agents in Lite Registry)
- [ ] 4.3 Monitoring setup (Vercel analytics)
- [ ] 4.4 Documentation complete
- [ ] 4.5 Launch!

### Definition of Done
- [ ] All launch criteria met (per PRD)
- [ ] Security audit passed
- [ ] Public launch

---

## Tech Debt & Performance Notes

> **Note**: The following items were identified during v1.x development and should be considered during v2.0.0 if performance bottlenecks appear.

### Resolved by M3: sign_with_ca Simulation → Real CA Service

**Context**: [Issue #44](https://github.com/adriannoes/asap-protocol/issues/44) — `sign_with_ca` in `src/asap/crypto/trust.py` is a simulation (caller provides CA key). Acceptable for v1.2.0; must be integrated into a real flow for v2.0.

**Resolved by**: Task 3.4 (ASAP CA Signing Automation) — GitHub Action + Admin approval flow will use the CA key from secrets to sign manifests. When implementing 3.4, close #44 and add a comment linking to this task.

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
| M1 | 6 | Web Foundation + Lite Registry + Deploy | 6-8 |
| M2 | 4 | Web Features | 5-7 |
| M3 | 5 | Verified Flow + IssueOps | 6-8 |
| M4 | 6 | Launch Prep | 6-10 |

**Total**: 20 tasks across 4 sprints

---

## Progress Tracking

**Overall Progress**: 10/20 tasks (50%) — Sprints M1 & M2 complete

**Last Updated**: 2026-02-20

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
| 2026-02-20 | **Sprint M1 complete**: All tasks 1.1–1.6 and Definition of Done marked done; roadmap progress 6/20 (30%) |
| 2026-02-20 | **Sprint M2 complete**: All tasks 2.1–2.4 and Definition of Done marked done; roadmap progress 10/20 (50%) |
