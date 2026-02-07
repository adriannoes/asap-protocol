# PRD: ASAP Protocol v2.0.0 — Marketplace + Web App

> **Product Requirements Document**
>
> **Version**: 2.0.0
> **Status**: APPROVED
> **Created**: 2026-02-06
> **Last Updated**: 2026-02-06

---

## 1. Executive Summary

### 1.1 Purpose

v2.0.0 is **The End Goal** — the complete Agent Marketplace with human-facing Web App. This release delivers:

- **Marketplace Core**: Production Registry with full trust and economy integration
- **Web App**: Human interface for agent discovery, registration, and management
- **Verified Badge**: ASAP-signed verification service ($49/month)
- **Payment Integration**: Stripe checkout for Verified badge
- **Production Infrastructure**: Scalable, secure, monitored

### 1.2 Strategic Context

All previous versions (v1.0-v1.3) built foundational capabilities:
- v1.0: Core protocol
- v1.1: Identity (OAuth2, WebSocket, Discovery)
- v1.2: Trust (Ed25519, Registry, Evals)
- v1.3: Economics (Metering, Delegation, SLA, Audit)

v2.0 integrates everything into a cohesive marketplace product.

**Domain**: asap-protocol.com (marketplace product name TBD — Open Question Q10)

---

## 2. Goals

| Goal | Metric | Priority |
|------|--------|----------|
| Registry handles scale | 10,000+ agents | P1 |
| Web App live | Core flows functional | P1 |
| Verified badge operational | Payment flow works | P1 |
| Trust scores computed | All registered agents | P1 |
| 100+ beta registrations | Before public launch | P1 |
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

### 4.1 Marketplace Core (P1)

| ID | Requirement | Priority |
|----|-------------|----------|
| MARKET-001 | Production Registry deployment | MUST |
| MARKET-002 | Registry scaling (10k+ agents) | MUST |
| MARKET-003 | Trust score integration | MUST |
| MARKET-004 | Full-text agent search | MUST |
| MARKET-005 | Reputation display | MUST |
| MARKET-006 | Real-time status (online/offline) | SHOULD |

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
| INFRA-001 | Production deployment (Vercel/Railway) | MUST |
| INFRA-002 | Database (Postgres or SQLite scaling) | MUST |
| INFRA-003 | CDN for static assets | SHOULD |
| INFRA-004 | Monitoring (Prometheus + Grafana) | MUST |
| INFRA-005 | Error tracking (Sentry or similar) | MUST |
| INFRA-006 | Automated backups | MUST |

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
| Federation | After centralized proves ROI | v2.x+ |
| Advanced analytics dashboard | Post-MVP | v2.1+ |
| Mobile app | Web-first | TBD |
| Multiple payment providers | Stripe is enough | TBD |
| Enterprise SSO | After enterprise traction | v2.1+ |

---

## 6. Technical Considerations

### 6.1 Tech Stack (Decision SD-8)

| Layer | Technology | Rationale |
|-------|------------|-----------|
| Frontend | **Next.js 15 (App Router)** | SSR for Registry SEO, React Server Components |
| Styling | **TailwindCSS v4 + Shadcn** | Premium UI velocity (Exception to no-Tailwind rule) |
| Backend API | FastAPI (existing ASAP code) | Code reuse, same stack |
| Database | PostgreSQL | Production-grade |
| Auth | ASAP OAuth2 + **GitHub (TBD)** | Dog-fooding + Bootstrap ease (See Q11) |
| Payments | Stripe | SaaS standard |
| Hosting | Vercel (frontend) + Railway (API) | Simple, scalable |
| Docs | Separate MkDocs | Per SD-8 decision |

### 6.2 Architecture

```
┌───────────────────────────────────────────────────────────────────┐
│                        WEB LAYER                                   │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐               │
│  │   Landing   │  │  Registry   │  │  Dashboard  │               │
│  │    Page     │  │   Browser   │  │   (Auth)    │               │
│  └─────────────┘  └─────────────┘  └─────────────┘               │
└───────────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌───────────────────────────────────────────────────────────────────┐
│                        API LAYER (FastAPI)                         │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐               │
│  │  Registry   │  │   Trust     │  │  Economy    │               │
│  │    API      │  │    API      │  │    API      │               │
│  └─────────────┘  └─────────────┘  └─────────────┘               │
└───────────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌───────────────────────────────────────────────────────────────────┐
│                       DATA LAYER                                   │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐               │
│  │  PostgreSQL │  │   Stripe    │  │   Metrics   │               │
│  │             │  │   (SaaS)    │  │ (Prometheus)│               │
│  └─────────────┘  └─────────────┘  └─────────────┘               │
└───────────────────────────────────────────────────────────────────┘
```

### 6.3 Repository Structure

```
asap-protocol/
├── src/asap/              # Protocol library (existing)
├── apps/
│   ├── web/               # Next.js 15 Web App (App Router)
│   │   ├── src/
│   │   │   ├── pages/
│   │   │   ├── components/
│   │   │   └── styles/
│   │   └── package.json
│   └── api/               # FastAPI production API
│       ├── main.py
│       ├── routers/
│       └── Dockerfile
└── infra/
    ├── docker-compose.yml
    └── k8s/               # Optional K8s manifests
```

---

## 7. Success Metrics

| Metric | Target |
|--------|--------|
| Registry agents | 1,000+ at launch |
| Web App uptime | 99.9% |
| Verified conversions | 5% of registered agents |
| Page load time | <2s (p95) |
| Security audit | Zero critical findings |

---

## 8. Launch Criteria

Before announcing v2.0.0:

- [ ] Registry handles 10,000+ agents (load test)
- [ ] Trust scores computed for all agents
- [ ] Freemium pricing live (Verified at $49/mo)
- [ ] 100+ agents registered (beta)
- [ ] Web App live with core features
- [ ] Security audit passed
- [ ] Monitoring dashboards operational
- [ ] Documentation complete

---

## 9. Related Documents

- **Tasks**: [tasks-v2.0.0-roadmap.md](../../dev-planning/tasks/v2.0.0/tasks-v2.0.0-roadmap.md)
- **Roadmap**: [roadmap-to-marketplace.md](../roadmap-to-marketplace.md)
- **Vision**: [vision-agent-marketplace.md](../vision-agent-marketplace.md)
- **v1.3 PRD**: [prd-v1.3-roadmap.md](./prd-v1.3-roadmap.md)

---

## Change Log

| Date | Version | Change |
|------|---------|--------|
| 2026-02-06 | 1.0.0 | Initial PRD for v2.0.0 |
