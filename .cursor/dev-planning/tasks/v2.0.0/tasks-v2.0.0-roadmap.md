# Tasks: ASAP Protocol v2.0.0 Roadmap

> **High-level task overview** for v2.0.0 milestone (Marketplace + Web App)
>
> **Parent PRD**: [prd-v2.0-roadmap.md](../../../product-specs/prd/prd-v2.0-roadmap.md)
> **Prerequisite**: v1.3.0 released
> **Target Version**: v2.0.0
> **Focus**: Marketplace Core, Web App, Verified Badge, Infrastructure
>
> 💡 **For detailed step-by-step instructions**, see sprint files:
> - [M1-M2: Marketplace Core](./tasks-v2.0.0-marketplace-detailed.md)
> - [M3-M4: Web App](./tasks-v2.0.0-webapp-detailed.md)
> - [M5-M6: Launch Prep](./tasks-v2.0.0-launch-detailed.md)

---

## Sprint M1: Production Registry

**Goal**: Deploy production-grade Registry service

### Tasks

- [ ] 1.1 Production database setup
  - Goal: PostgreSQL for Registry data
  - Deliverable: Database schema, migrations

- [ ] 1.2 Registry API production deployment
  - Goal: Scalable API on Railway/similar
  - Deliverable: Deployed API with monitoring

- [ ] 1.3 Trust score integration
  - Goal: Connect Registry to Trust service
  - Deliverable: Scores visible in Registry

- [ ] 1.4 Full-text search
  - Goal: Search agents by name, description, skills
  - Deliverable: Postgres full-text or Meilisearch

### Definition of Done
- [ ] Registry deployed and accessible
- [ ] Search works across 1000+ test agents
- [ ] Trust scores displayed

---

## Sprint M2: Service Integration

**Goal**: Integrate all v1.x services

### Tasks

- [ ] 2.1 OAuth2 integration for Registry
  - Goal: Authenticated writes, public reads

- [ ] 2.2 Metering integration
  - Goal: Track Registry API usage

- [ ] 2.3 SLA integration
  - Goal: Display agent SLA in Registry

- [ ] 2.4 Audit integration
  - Goal: Log all Registry mutations

### Definition of Done
- [ ] All v1.x services integrated
- [ ] End-to-end flow working

---

## Sprint M3: Web App Foundation

**Goal**: Build Web App foundation

### Tasks

- [ ] 3.1 Project setup
  - Goal: Next.js 15 (App Router) + TailwindCSS + Shadcn/UI
  - Deliverable: `apps/web/` initialized

- [ ] 3.2 Landing page
  - Goal: Hero, value prop, CTA

- [ ] 3.3 OAuth2 login flow
  - Goal: Developer authentication

- [ ] 3.4 Base layout and navigation

### Definition of Done
- [ ] Landing page live
- [ ] Login/logout working

---

## Sprint M4: Web App Features

**Goal**: Registry browser and dashboard

### Tasks

- [ ] 4.1 Registry browser page
  - Goal: Search and filter agents

- [ ] 4.2 Agent detail page
  - Goal: Full agent info, SLA, reputation

- [ ] 4.3 Developer dashboard
  - Goal: My agents, metrics, API keys

- [ ] 4.4 Register agent flow
  - Goal: Upload manifest, register

### Definition of Done
- [ ] Browse and search working
- [ ] Developers can register agents

---

## Sprint M5: Verified Badge & Payments

**Goal**: Verified badge service with Stripe

### Tasks

- [ ] 5.1 Stripe integration
- [ ] 5.2 "Apply for Verified" flow
- [ ] 5.3 Checkout flow ($49/month)
- [ ] 5.4 ASAP CA signing on approval
- [ ] 5.5 Admin review queue

### Definition of Done
- [ ] Payment flow end-to-end
- [ ] Verified badge appears after approval

---

## Sprint M6: Launch Preparation

**Goal**: Production readiness and launch

### Tasks

- [ ] 6.1 Security audit
- [ ] 6.2 Load testing (10k+ agents)
- [ ] 6.3 Monitoring setup
- [ ] 6.4 Documentation complete
- [ ] 6.5 Beta program (100+ agents)
- [ ] 6.6 Launch!

### Definition of Done
- [ ] All launch criteria met
- [ ] Security audit passed
- [ ] Public launch

---

## Tech Debt & Performance Notes

> **Note**: The following items were identified during v1.x development and should be considered during v2.0.0 if performance bottlenecks appear.

### Consider: orjson for JSON Serialization

**Context**: If JSON serialization becomes a bottleneck with high traffic in the Marketplace, consider replacing stdlib `json` with `orjson` (Rust-based, ~10x faster).

**When to evaluate**: During M6 load testing (6.2) if API response times are slow.

**Implementation**: 
- Add `orjson>=3.9` to dependencies
- Create thin wrapper `asap.utils.json` that uses orjson
- Benchmark before/after

**Decision**: Not required unless load testing reveals bottleneck.

---

### Optional: Add bandit to CI

**Context**: bandit scans Python code for security issues (hardcoded passwords, SQL injection patterns, weak crypto). Currently only runs locally as dev dependency.

**When to add**: Before public launch (M6) when external contributors or public scrutiny increase.

**Implementation**:
- Add to `.github/workflows/ci.yml` security job
- Configure exclusions in `pyproject.toml` or `.bandit`
- Start with `--severity-level medium` to reduce noise

**Decision**: Optional - evaluate when preparing for public launch.

---

## Summary

| Sprint | Tasks | Focus | Est. Days |
|--------|-------|-------|-----------|
| M1 | 4 | Production Registry | 6-8 |
| M2 | 4 | Integration | 5-7 |
| M3 | 4 | Web Foundation | 6-8 |
| M4 | 4 | Web Features | 7-10 |
| M5 | 5 | Verified + Payments | 6-8 |
| M6 | 6 | Launch Prep | 8-12 |

**Total**: 27 tasks across 6 sprints

---

## Progress Tracking

**Overall Progress**: 0/27 tasks (0%)

**Last Updated**: 2026-02-06

---

## Related Documents

- **PRD**: [prd-v2.0-roadmap.md](../../../product-specs/prd/prd-v2.0-roadmap.md)
- **Roadmap**: [roadmap-to-marketplace.md](../../../product-specs/roadmap-to-marketplace.md)
