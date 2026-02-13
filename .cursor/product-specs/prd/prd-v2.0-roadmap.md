# PRD: ASAP Protocol v2.0.0 — Lean Marketplace + Web App

> **Product Requirements Document**
>
> **Version**: 2.0.0
> **Status**: APPROVED
> **Created**: 2026-02-06
> **Last Updated**: 2026-02-12

---

## 1. Executive Summary

### 1.1 Purpose

v2.0.0 is **The End Goal** — the Agent Marketplace with human-facing Web App. This release delivers:

- **Web App**: Human interface for agent discovery, registration, and management
- **Lite Registry Integration**: Web App reads from `registry.json` (GitHub Pages)
- **Verified Badge**: ASAP-signed verification service ($49/month)
- **Payment Integration**: Stripe checkout for Verified badge

> [!NOTE]
> **Lean Marketplace approach**: No backend API. The Web App reads from the Lite Registry (SD-11). A full Registry API Backend is deferred to v2.1. See [deferred-backlog.md](../strategy/deferred-backlog.md).

### 1.2 Strategic Context

All previous versions (v1.0-v1.3) built foundational capabilities:
- v1.0: Core protocol
- v1.1: Identity (OAuth2, WebSocket, Discovery, Lite Registry)
- v1.2: Verified Identity (Ed25519, Compliance Harness)
- v1.3: Observability (Metering, Delegation, SLA)

v2.0 wraps the Lite Registry in a Web App with Verified badge as the first revenue stream.

**Domain**: asap-protocol.com (marketplace product name TBD — Open Question Q10)

---

## 2. Goals

| Goal | Metric | Priority |
|------|--------|----------|
| Web App live | Core flows functional | P1 |
| Lite Registry browsable | Agents searchable in Web App | P1 |
| Verified badge operational | Payment flow works | P1 |
| 100+ agents in Lite Registry | Before launch | P1 |
| Security audit passed | No critical findings | P1 |

---

## 3. User Stories

### Agent Developer (Provider)
> As an **agent developer**, I want to **register my agent in the marketplace via Web App** so that **consumers can discover and use my agent**.

### Agent Consumer
> As an **agent consumer**, I want to **browse agents by skill and trust level** so that **I find reliable agents for my workflows**.

### Verified Agent Developer
> As a **developer seeking trust**, I want to **apply for Verified badge and pay via Stripe** so that **my agent displays a trust badge**.

### Platform Admin (ASAP Team)
> As a **platform admin**, I want to **review and approve Verified applications** so that **only quality agents get the badge**.

---

## 4. Functional Requirements

### 4.1 Lite Registry Integration (P1)

| ID | Requirement | Priority |
|----|-------------|----------|
| REG-001 | Fetch and parse `registry.json` from GitHub Pages | MUST |
| REG-002 | Agent search by skill, trust level | MUST |
| REG-003 | Agent detail view (manifest, SLA, status) | MUST |
| REG-004 | Real-time status (online/offline via health endpoint) | SHOULD |
| REG-005 | Cache registry data with configurable TTL | MUST |

---

### 4.2 Web App — Landing & Discovery (P1)

| ID | Requirement | Priority |
|----|-------------|----------|
| WEB-001 | Landing page with value proposition | MUST |
| WEB-002 | Agent search/browse page | MUST |
| WEB-003 | Skill and trust level filters | MUST |
| WEB-004 | Agent detail page (manifest, SLA, reputation) | MUST |
| WEB-005 | "Get Started" developer CTA | MUST |
| WEB-006 | SEO optimization | SHOULD |

---

### 4.3 Web App — Developer Dashboard (P1)

| ID | Requirement | Priority |
|----|-------------|----------|
| DASH-001 | OAuth2 login (dog-fooding ASAP auth) | MUST |
| DASH-002 | "My Agents" list with status | MUST |
| DASH-003 | Register new agent flow | MUST |
| DASH-004 | Edit agent manifest | MUST |
| DASH-005 | View usage metrics per agent | SHOULD |
| DASH-006 | API key management | MUST |

---

### 4.4 Verified Badge Service (P1)

| ID | Requirement | Priority |
|----|-------------|----------|
| VERIFY-001 | "Apply for Verified" button in dashboard | MUST |
| VERIFY-002 | Stripe checkout ($49/month) | MUST |
| VERIFY-003 | Minimal KYC (email, name, URL check) | MUST |
| VERIFY-004 | Manual review queue for ASAP team | MUST |
| VERIFY-005 | ASAP-sign manifest on approval | MUST |
| VERIFY-006 | Badge visible in Registry and Web App | MUST |
| VERIFY-007 | Subscription management (cancel, upgrade) | SHOULD |

---

### 4.5 Infrastructure (P1)

| ID | Requirement | Priority |
|----|-------------|----------|
| INFRA-001 | Production deployment (Vercel) | MUST |
| INFRA-002 | CDN for static assets | SHOULD |
| INFRA-003 | Monitoring (uptime, error rates) | MUST |
| INFRA-004 | Error tracking (Sentry or similar) | MUST |

---

### 4.6 Security (P1)

| ID | Requirement | Priority |
|----|-------------|----------|
| SEC-001 | Security audit before launch | MUST |
| SEC-002 | HTTPS everywhere | MUST |
| SEC-003 | Rate limiting on all endpoints | MUST |
| SEC-004 | CSRF protection on Web App | MUST |
| SEC-005 | Secure Stripe integration | MUST |

---

## 5. Non-Goals (Out of Scope)

| Feature | Reason | When |
|---------|--------|------|
| Registry API Backend | Lite Registry sufficient for MVP | v2.1 |
| Federation | After centralized proves ROI | v2.x+ |
| Advanced analytics dashboard | Post-MVP | v2.1+ |
| Mobile app | Web-first | TBD |
| Multiple payment providers | Stripe is enough | TBD |
| Enterprise SSO | After enterprise traction | v2.1+ |
| Economy Settlement | Requires live marketplace transactions | v3.0 |

---

## 6. Technical Considerations

### 6.1 Tech Stack (Decision SD-8)

| Layer | Technology | Rationale |
|-------|------------|-----------|
| Frontend | **Next.js 15 (App Router)** | SSR for Registry SEO, React Server Components |
| Styling | **TailwindCSS v4 + Shadcn** | Premium UI velocity (Exception to no-Tailwind rule) |
| Data Source | Lite Registry (`registry.json`) | No backend needed for MVP |
| Auth | ASAP OAuth2 + **GitHub (TBD)** | Dog-fooding + Bootstrap ease (See Q11) |
| Payments | Stripe | SaaS standard |
| Hosting | Vercel | Simple, scalable |
| Docs | Separate MkDocs | Per SD-8 decision |

### 6.2 Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        WEB LAYER (Next.js)                          │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐               │
│  │   Landing   │  │  Registry   │  │  Dashboard  │               │
│  │    Page     │  │   Browser   │  │   (Auth)    │               │
│  └─────────────┘  └─────────────┘  └─────────────┘               │
└─────────────────────────────────────────────────────────────────┘
                            │
              ┌────────────┼────────────┐
              ▼                         ▼
┌───────────────────────┐  ┌───────────────────────┐
│  LITE REGISTRY (SD-11)    │  │  EXTERNAL SERVICES        │
│  ┌───────────────────┐  │  │  ┌───────────────────┐  │
│  │  registry.json     │  │  │  │ Stripe (Payments)  │  │
│  │  (GitHub Pages)    │  │  │  └───────────────────┘  │
│  └───────────────────┘  │  │  ┌───────────────────┐  │
└───────────────────────┘  │  │ Sentry (Errors)    │  │
                               │  └───────────────────┘  │
                               └───────────────────────┘
```

> **Note**: No backend API in v2.0. The Web App fetches `registry.json` at build time (SSG) or at request time (ISR) from GitHub Pages. Agent registration is still PR-based. A full Registry API Backend is planned for v2.1 when scale demands it.

### 6.3 Repository Structure

```
asap-protocol/
├── src/asap/              # Protocol library (existing)
├── apps/
│   └── web/               # Next.js 15 Web App (App Router)
│       ├── src/
│       │   ├── app/           # App Router pages
│       │   ├── components/
│       │   ├── lib/           # Data fetching (registry.json)
│       │   └── styles/
│       └── package.json
└── infra/
    └── vercel.json
```

---

## 7. Success Metrics

| Metric | Target |
|--------|--------|
| Lite Registry agents | 100+ at launch |
| Web App uptime | 99.9% |
| Verified conversions | 5% of registered agents |
| Page load time | <2s (p95) |
| Security audit | Zero critical findings |

---

## 8. Launch Criteria

Before announcing v2.0.0:

- [ ] Lite Registry has 100+ agents
- [ ] Verified badge flow working (Stripe + ASAP CA signing)
- [ ] Web App live with core features (browse, search, register)
- [ ] Security audit passed
- [ ] Monitoring operational
- [ ] Documentation complete

---

## 9. Related Documents

- **Tasks**: [tasks-v2.0.0-roadmap.md](../../dev-planning/tasks/v2.0.0/tasks-v2.0.0-roadmap.md)
- **Deferred Backlog**: [deferred-backlog.md](../strategy/deferred-backlog.md)
- **Roadmap**: [roadmap-to-marketplace.md](../strategy/roadmap-to-marketplace.md)
- **Vision**: [vision-agent-marketplace.md](../strategy/vision-agent-marketplace.md)
- **v1.3 PRD**: [prd-v1.3-roadmap.md](./prd-v1.3-roadmap.md)

---

## Change Log

| Date | Version | Change |
|------|---------|--------|
| 2026-02-06 | 1.0.0 | Initial PRD for v2.0.0 |
| 2026-02-07 | 1.1.0 | Updated architecture diagram with Storage Layer (SD-9), ASAP Cloud reference |
| 2026-02-12 | 1.2.0 | **Lean Marketplace pivot**: Replaced Production Registry with Lite Registry integration, removed FastAPI backend/PostgreSQL, simplified architecture to Next.js + GitHub Pages JSON, updated goals/launch criteria (100+ instead of 10k+), added Economy Settlement to non-goals (v3.0) |
