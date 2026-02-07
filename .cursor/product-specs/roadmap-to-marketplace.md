# ASAP Protocol: Roadmap to Marketplace

> **Evolution Path**: v1.0.0 → v2.0.0 (Agent Marketplace)
>
> **Status**: STRATEGIC PLANNING
> **Horizon**: Incremental sprints post-v1.0.0
> **Created**: 2026-01-30
> **Updated**: 2026-02-05

---

## Overview

This roadmap defines the evolution from v1.0.0 (stable protocol) to v2.0.0 (Agent Marketplace). Each version builds foundational capabilities required for the marketplace vision.

**Strategic Priority**: Adoption first, monetization later.

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    ROADMAP TO AGENT MARKETPLACE                          │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  v1.0.0          v1.1           v1.2           v1.3           v2.0      │
│  ═══════        ═══════        ═══════        ═══════        ═══════    │
│    │              │              │              │              │        │
│    │ ┌──────────┐ │ ┌──────────┐ │ ┌──────────┐ │ ┌──────────┐ │        │
│    ├─│ Stable   │─┼─│ Identity │─┼─│ Trust    │─┼─│ Economy  │─┼─→ 🏪  │
│    │ │ Protocol │ │ │ +Discov  │ │ │ +PKI     │ │ │ Layer    │ │        │
│    │ └──────────┘ │ └──────────┘ │ └──────────┘ │ └──────────┘ │        │
│    │              │              │              │              │        │
│    ▼              ▼              ▼              ▼              ▼        │
│  Released     Identity       Trust          Economy      Marketplace   │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Strategic Decisions

Key architectural and business decisions made during planning. Each decision includes rationale and alternatives considered.

### SD-1: Registry Architecture — Centralized First

**Decision**: Start with a centralized registry operated by ASAP, with federation as a future option.

| Option | Considered | Rationale |
|--------|------------|-----------|
| **Centralized** | ✅ Selected | Faster to build, easier monetization, quality control |
| Federated | Deferred to v2.x+ | Complex architecture, needed only at scale |
| Fully decentralized | Rejected | Too slow for early adoption, no quality control |

**Why this matters**: Like npm/PyPI, a single official registry simplifies the developer experience. Federation can be added when there's demand from enterprises wanting private registries.

---

### SD-2: Pricing Model — Freemium First

**Decision**: Launch with Freemium model. Monetization model (Subscription, % transactions, or Hybrid) decided after traction.

| Option | Considered | Rationale |
|--------|------------|-----------|
| **Freemium** | ✅ Selected | Zero barrier for startups/devs, adoption priority |
| Subscription | Deferred | Friction for early adopters |
| % of transactions | Deferred | Requires payment rails infrastructure |

**Initial tiers**:
- **Free**: List agents, basic features
- **Verified**: $49/month (manual review, badge)

**Why this matters**: Target ICP (AI startups, individual developers) need zero friction. They often build solutions for enterprise clients who value reliable protocols.

---

### SD-3: Real-time Transport — WebSocket for v1.x

**Decision**: WebSocket for v1.x, Message Broker (NATS/Kafka) as optional premium feature in v2.0+.

| Option | Considered | Rationale |
|--------|------------|-----------|
| **WebSocket** | ✅ Selected for v1.x | Sufficient for <50 agents, simpler infrastructure |
| Message Broker | v2.0+ optional | Overkill for startups, adds infrastructure cost |

**Why this matters**: WebSocket handles direct connections well. Brokers solve the N² connection problem but require additional infrastructure most early adopters don't need.

---

### SD-4: Signing Algorithm — Ed25519

**Decision**: Use Ed25519 for manifest signing.

| Option | Considered | Rationale |
|--------|------------|-----------|
| **Ed25519** | ✅ Selected | Modern, fast, small signatures, MCP-aligned |
| ECDSA (P-256) | Rejected | Multiple curves = complexity |
| RSA-2048/4096 | Rejected | Slow, large signatures, legacy |

**Why this matters**: Ed25519 produces 64-byte signatures (vs RSA's 256+), is faster to verify, and is the modern standard used by MCP, SSH, and Signal.

---

### SD-5: PKI Strategy — 3-Tier Trust Levels

**Decision**: Three trust levels for manifest signing.

| Level | Description | Cost |
|-------|-------------|------|
| **Self-signed** | Any agent can participate | Free |
| **Verified** | ASAP reviews and signs | $49/month |
| **Enterprise** | Org uses own CA | Future |

**Why this matters**: Zero barrier for developers (self-signed accepted), clear upgrade path (Verified for credibility), enterprise flexibility (bring-your-own CA for regulated industries).

---

### SD-6: mTLS — Optional, Never Required

**Decision**: mTLS available in v1.2 as optional feature, never mandatory.

| Option | Considered | Rationale |
|--------|------------|-----------|
| mTLS required | Rejected | High friction, overkill for startups |
| **mTLS optional** | ✅ Selected | Available for enterprise/regulated use cases |
| No mTLS | Rejected | Blocks enterprise adoption |

**Why this matters**: Adoption-first strategy means minimizing friction. Enterprises needing mutual TLS can enable it; others can ignore it.

---

### SD-7: Discovery — Basic Discovery in v1.1

**Decision**: Move well-known URI and DNS-SD discovery to v1.1 (before Registry API in v1.2).

**Rationale**: WebSocket requires agents to find each other. Without basic discovery, real-time communication cannot work across dynamic agents.

---

## Release Timeline

| Version | Codename | Focus | Key Deliverables |
|---------|----------|-------|------------------|
| **v1.0.0** | Foundation | Stable protocol | ✅ Released |
| **v1.1.0** | Identity | Auth + Discovery + Real-time | OAuth2, WebSocket, Well-known URI |
| **v1.2.0** | Trust | Verification + Registry | Ed25519 signing, Registry API, Evals |
| **v1.3.0** | Economics | Metering + SLAs | Usage tracking, delegation |
| **v2.0.0** | Marketplace | Full launch | Registry service, Dashboard |

---

## v1.1.0 "Identity" — Foundation for Trust

**Goal**: Establish identity, discovery, and real-time communication.

### Features

| Feature | Priority | Purpose |
|---------|----------|---------|
| OAuth2/OIDC | P1 | Agent identity verification |
| WebSocket binding | P1 | Real-time agent-to-agent comms |
| Well-known URI discovery | P1 | Basic agent discovery |
| Webhook callbacks | P2 | Event-driven notifications |
| DNS-SD discovery | P3 | Local network discovery |

### Why This Matters

- OAuth2 enables enterprise agent identity
- WebSocket provides low-latency comms (Decision SD-3)
- Well-known URI allows agents to discover each other before Registry exists (Decision SD-7)

### Deliverables

```
src/asap/
├── auth/
│   ├── oauth2.py         # OAuth2 client & server
│   └── oidc.py           # OIDC discovery
├── transport/
│   ├── websocket.py      # WebSocket binding
│   └── webhook.py        # Webhook delivery
└── discovery/
    └── wellknown.py      # /.well-known/asap/manifest.json
```

---

## v1.2.0 "Trust" — Verified Identity

**Goal**: Enable verifiable agent identity and centralized discovery.

### Features

| Feature | Priority | Purpose |
|---------|----------|---------|
| Signed manifests (Ed25519) | P1 | Verifiable agent identity |
| Registry API | P1 | Centralized discovery |
| ASAP Compliance Harness | P1 | Protocol compliance testing |
| mTLS support (optional) | P2 | Transport-level trust |
| DeepEval integration | P2 | Intelligence evaluation |

### Why This Matters

- Signed manifests prevent agent impersonation (Decision SD-4)
- Registry API is the core of marketplace discovery (Decision SD-1)
- mTLS available for enterprise use cases (Decision SD-6)

### Manifest Signing (Ed25519)

```json
{
  "manifest": {
    "id": "urn:asap:agent:example",
    "version": "1.0.0"
  },
  "signature": {
    "algorithm": "Ed25519",
    "public_key": "base64...",
    "value": "base64..."
  },
  "trust_level": "self-signed"
}
```

### Trust Levels (Decision SD-5)

| Level | Badge | Signing |
|-------|-------|---------|
| Self-signed | None | Agent's own key |
| Verified | ✓ | ASAP-signed after review |
| Enterprise | Custom | Organization's CA |

### Registry API

```
GET  /registry/agents?skill=code_review
POST /registry/agents           # Register
PUT  /registry/agents/{id}      # Update
GET  /registry/agents/{id}/reputation
```

### Evaluation Framework

**Hybrid Strategy**: Shell (Protocol) + Brain (Intelligence)

| Layer | Tool | Validates |
|-------|------|-----------|
| Shell | pytest (ASAP native) | Handshake, Schema, State machine, SLA |
| Brain | DeepEval | Reasoning, Tool usage, Safety |

---

## v1.3.0 "Economics" — Value Exchange

**Goal**: Enable metering, billing, and economic transactions.

### Features

| Feature | Priority | Purpose |
|---------|----------|---------|
| Usage metering | P1 | Track resource consumption |
| SLA framework | P1 | Define service guarantees |
| Delegation tokens | P1 | Trust chains for sub-agents |
| Credit system | P2 | Pre-paid marketplace credits |
| Audit logging | P2 | Compliance & disputes |

### Usage Metering

```json
{
  "usage": {
    "task_id": "task_123",
    "agent": "urn:asap:agent:example",
    "metrics": {
      "tokens_in": 1500,
      "tokens_out": 2300,
      "duration_ms": 4500,
      "api_calls": 3
    }
  }
}
```

### Delegation Token

```json
{
  "delegation": {
    "delegator": "urn:asap:agent:enterprise",
    "delegate": "urn:asap:agent:research-team",
    "scopes": ["research.execute", "data.read"],
    "constraints": {
      "max_cost_usd": 100,
      "expires_at": "2026-02-28T00:00:00Z"
    },
    "signature": "..."
  }
}
```

---

## v2.0.0 "Marketplace" — The End Goal

**Goal**: Launch the complete Agent Marketplace with Web App.

### Core Components

| Component | Description |
|-----------|-------------|
| **Registry Service** | Centralized agent registration & discovery (SD-1) |
| **Trust Service** | Reputation, credentials, verification |
| **Economy Service** | Metering, billing (Freemium initially, SD-2) |
| **Message Broker** | Optional premium for scale (SD-3) |
| **Web App** | Human interface for marketplace (SD-8) |

### Web App (SD-8)

Human interface for marketplace interactions:

| Area | MVP Features |
|------|-------------|
| Landing | Hero, value prop, "Get Started" CTA |
| Registry Browser | Search, filters (skill, trust level), agent details |
| Developer Dashboard | My agents, analytics, API keys |
| Verified Signup | Stripe checkout ($49/mo), KYC minimal |
| Auth | OAuth2 (dog-fooding ASAP auth) |

**Technical Stack**:

| Layer | Choice | Rationale |
|-------|--------|-----------|
| Frontend | **Next.js 15 (App Router)** | SSR for SEO, Registry indexing |
| Backend | FastAPI (reuses ASAP) | Same stack, code sharing |
| Auth | ASAP OAuth2 | Dog-fooding |
| Payments | Stripe | SaaS standard |
| Hosting | Vercel / Railway | Simple for solo dev |
| Docs | Separate MkDocs | Keep docs simple (SD-8) |

**Domain**: asap-protocol.com (marketplace name TBD)

### Launch Criteria

- [ ] Registry handles 10,000+ agents
- [ ] Trust scores computed for all agents
- [ ] Freemium pricing live
- [ ] 100+ agents registered (beta)
- [ ] Web App live with core features
- [ ] Security audit passed

---

## Migration Guide

| Version | Action Required |
|---------|-----------------|
| v1.0 → v1.1 | Add OAuth2 config, expose well-known endpoint |
| v1.1 → v1.2 | Sign manifest with Ed25519 |
| v1.2 → v1.3 | Define SLAs, add metering hooks |
| v1.3 → v2.0 | Register in marketplace |

### Backward Compatibility

- All v1.x releases maintain backward compat
- v2.0 may have breaking changes (advance notice provided)
- Migration tools provided for each version

---

## Resolved Questions

| ID | Question | Decision | Reference |
|----|----------|----------|-----------|
| Q1 | Centralized vs federated registry? | Centralized first | SD-1 |
| Q2 | Signing algorithm? | Ed25519 | SD-4 |
| Q3 | mTLS required? | Optional only | SD-6 |
| Q4 | Discovery before Registry? | Yes, v1.1 | SD-7 |
| Q5 | Pricing model? | Freemium first | SD-2 |
| Q6 | WebSocket vs Broker? | WebSocket v1.x, Broker v2.0+ | SD-3 |
| Q7 | Docs inside Web App? | Separated (MkDocs + Web App) | SD-8 |

## Open Questions

| ID | Question | Decide By |
|----|----------|-----------|
| Q8 | Monetization model post-adoption? | After traction data |
| Q9 | Federation protocol spec? | v2.x if needed |
| Q10 | Marketplace product name? | Before v2.0 launch |

---

## Success Metrics by Version

| Version | Key Metric | Target |
|---------|------------|--------|
| v1.1 | OAuth2 adoption | 50% of users |
| v1.2 | Signed manifests | 80% of agents |
| v1.3 | SLA definitions | 90% of agents |
| v2.0 | Marketplace registrations | 1,000+ agents |

---

## Related Documents

- **Vision**: [vision-agent-marketplace.md](./vision-agent-marketplace.md)
- **Design Decisions**: [ADR.md](./ADR.md)
- **v1.1 PRD**: [prd-v1.1-roadmap.md](./prd/prd-v1.1-roadmap.md)
- **v1.2 PRD**: [prd-v1.2-roadmap.md](./prd/prd-v1.2-roadmap.md)
- **v1.3 PRD**: [prd-v1.3-roadmap.md](./prd/prd-v1.3-roadmap.md)
- **v2.0 PRD**: [prd-v2.0-roadmap.md](./prd/prd-v2.0-roadmap.md)
- **Checkpoints**: [checkpoints.md](../dev-planning/checkpoints.md)

---

## Change Log

| Date | Change |
|------|--------|
| 2026-01-30 | Initial roadmap document |
| 2026-02-05 | Added strategic decisions (SD-1 to SD-7) with rationale |
| 2026-02-05 | Added Web App to v2.0, SD-8 (docs architecture) |
