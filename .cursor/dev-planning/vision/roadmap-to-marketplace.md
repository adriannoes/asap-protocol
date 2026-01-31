# ASAP Protocol: Roadmap to Marketplace

> **Evolution Path**: v1.0.0 → v2.0.0 (Agent Marketplace)
>
> **Status**: STRATEGIC PLANNING
> **Horizon**: 12-18 months post-v1.0.0
> **Created**: 2026-01-30

---

## Overview

This roadmap defines the evolution from v1.0.0 (stable protocol) to v2.0.0 (Agent Marketplace). Each version builds foundational capabilities required for the marketplace vision.

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
│    │ │ Protocol │ │ │ Layer    │ │ │ Layer    │ │ │ Layer    │ │        │
│    │ └──────────┘ │ └──────────┘ │ └──────────┘ │ └──────────┘ │        │
│    │              │              │              │              │        │
│    ▼              ▼              ▼              ▼              ▼        │
│  Released      +6 weeks       +12 weeks      +18 weeks      +24 weeks   │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Release Timeline

| Version | Codename | Focus | Timeline |
|---------|----------|-------|----------|
| **v1.0.0** | Foundation | Stable, production-ready protocol | ✅ Released |
| **v1.1.0** | Identity | OAuth2, WebSocket, Webhooks | v1.0 + 6 weeks |
| **v1.2.0** | Trust | Signed manifests, Registry API | v1.0 + 12 weeks |
| **v1.3.0** | Economics | Metering, SLAs, Delegation | v1.0 + 18 weeks |
| **v2.0.0** | Marketplace | Full marketplace launch | v1.0 + 24 weeks |

---

## v1.1.0 "Identity" — Foundation for Trust

**Goal**: Establish robust identity and communication infrastructure.

### Features

| Feature | Priority | Purpose for Marketplace |
|---------|----------|------------------------|
| OAuth2/OIDC | P1 | Agent identity verification |
| WebSocket binding | P1 | Real-time communication |
| Webhook callbacks | P2 | Event-driven notifications |
| State storage interface | P2 | Standardized persistence |

### Why This Matters

- OAuth2 enables enterprise agent identity
- WebSocket provides low-latency agent-to-agent comms
- Webhooks enable marketplace notifications

### Deliverables

```
src/asap/
├── auth/
│   ├── oauth2.py         # OAuth2 client & server
│   └── oidc.py           # OIDC discovery
├── transport/
│   ├── websocket.py      # WebSocket binding
│   └── webhook.py        # Webhook delivery
└── storage/
    └── interface.py      # Storage ABC
```

---

## v1.2.0 "Trust" — Verified Identity

**Goal**: Enable verifiable agent identity and centralized discovery.

### Features

| Feature | Priority | Purpose for Marketplace |
|---------|----------|------------------------|
| Signed manifests | P1 | Verifiable agent identity |
| Registry API | P1 | Centralized discovery |
| mTLS support | P2 | Transport-level trust |
| DNS-SD discovery | P3 | Local network discovery |

### Why This Matters

- Signed manifests prevent agent impersonation
- Registry API is the core of marketplace discovery
- mTLS provides zero-trust network security

### Manifest Signing

```json
{
  "manifest": {
    "id": "urn:asap:agent:example",
    "version": "1.0.0",
    "...": "..."
  },
  "signature": {
    "algorithm": "Ed25519",
    "public_key": "base64...",
    "value": "base64..."
  },
  "certificate_chain": ["..."]
}
```

### Registry API (Preview)

```
GET  /registry/agents?skill=code_review
POST /registry/agents           # Register
PUT  /registry/agents/{id}      # Update
GET  /registry/agents/{id}/reputation
```

---

## v1.3.0 "Economics" — Value Exchange

**Goal**: Enable metering, billing, and economic transactions.

### Features

| Feature | Priority | Purpose for Marketplace |
|---------|----------|------------------------|
| Usage metering | P1 | Track resource consumption |
| SLA framework | P1 | Define service guarantees |
| Delegation tokens | P1 | Trust chains for sub-agents |
| Credit system | P2 | Pre-paid marketplace credits |
| Audit logging | P2 | Compliance & disputes |

### Why This Matters

- Metering enables pay-per-use models
- SLAs define what agents guarantee
- Delegation allows agent teams

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
    },
    "cost": {
      "amount": 0.045,
      "currency": "USD"
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

**Goal**: Launch the complete Agent Marketplace.

### Core Components

| Component | Description |
|-----------|-------------|
| **Registry Service** | Agent registration & discovery |
| **Trust Service** | Reputation, credentials, verification |
| **Economy Service** | Billing, credits, settlements |
| **Governance** | Policies, disputes, moderation |
| **Dashboard** | Web UI for marketplace |

### Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         MARKETPLACE v2.0                                 │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐            │
│  │    Registry     │ │     Trust       │ │    Economy      │            │
│  │    Service      │ │    Service      │ │    Service      │            │
│  ├─────────────────┤ ├─────────────────┤ ├─────────────────┤            │
│  │ • Register      │ │ • Verify        │ │ • Meter         │            │
│  │ • Search        │ │ • Rate          │ │ • Bill          │            │
│  │ • Match         │ │ • Certify       │ │ • Settle        │            │
│  └────────┬────────┘ └────────┬────────┘ └────────┬────────┘            │
│           │                   │                   │                      │
│           └───────────────────┼───────────────────┘                      │
│                               ▼                                          │
│                    ┌─────────────────────┐                               │
│                    │   ASAP Protocol     │                               │
│                    │   v2.0 Extensions   │                               │
│                    └─────────────────────┘                               │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

### New Payload Types (v2.0)

| Payload | Purpose |
|---------|---------|
| `AgentRegister` | Register agent in marketplace |
| `AgentDiscover` | Search for agents by criteria |
| `TrustQuery` | Check agent reputation |
| `BillingEvent` | Report usage for billing |
| `DisputeFile` | Initiate dispute resolution |

### Launch Criteria

- [ ] Registry handles 10,000+ agents
- [ ] Trust scores computed for all agents
- [ ] Billing system tested with real transactions
- [ ] Governance policies published
- [ ] 100+ agents registered (beta)
- [ ] Dashboard fully functional
- [ ] Security audit passed

---

## Migration Guide

### For Agent Developers

| Version | Action Required |
|---------|-----------------|
| v1.0 → v1.1 | Add OAuth2 config to manifest |
| v1.1 → v1.2 | Sign your manifest |
| v1.2 → v1.3 | Define SLAs, add metering hooks |
| v1.3 → v2.0 | Register in marketplace |

### Backward Compatibility

- All v1.x releases maintain backward compat
- v2.0 may have breaking changes (1 year notice)
- Migration tools provided for each version

---

## Open Questions

| ID | Question | Decide By |
|----|----------|-----------|
| Q1 | Centralized vs federated registry? | v1.2 |
| Q2 | Credit system or direct billing? | v1.3 |
| Q3 | Foundation or DAO governance? | v2.0-alpha |
| Q4 | What's the revenue model? | v2.0-beta |

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
- **v1.1 PRD**: [prd-v1.1-planning.md](../prd/prd-v1.1-planning.md)
- **v1.0 PRD**: [prd-v1-roadmap.md](../prd/prd-v1-roadmap.md)

---

## Change Log

| Date | Change |
|------|--------|
| 2026-01-30 | Initial roadmap document |
