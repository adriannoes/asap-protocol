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
│                    ROADMAP TO AGENT MARKETPLACE                         │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  v1.0.0          v1.1           v1.2           v1.3           v2.0      │
│  ═══════        ═══════        ═══════        ═══════        ═══════    │
│    │              │              │              │              │        │
│    │ ┌──────────┐ │ ┌──────────┐ │ ┌──────────┐ │ ┌──────────┐ │        │
│    ├─│ Stable   │─┼─│ Identity │─┼─│ Verified │─┼─│ Observe  │─┼─→ 🏪   │
│    │ │ Protocol │ │ │ +Discov  │ │ │ Identity │ │ │ +Deleg   │ │        │
│    │ └──────────┘ │ └──────────┘ │ └──────────┘ │ └──────────┘ │        │
│    │              │              │              │              │        │
│    ▼              ▼              ▼              ▼              ▼        │
│  Released     Identity       Verified     Observability   Marketplace   │
│                                                                         │
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
**Hardening**: We mandate **JCS (RFC 8785)** for canonicalization and **Strict Verification (RFC 8032)** to prevent malleability attacks.

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

**Decision**: Move well-known URI and DNS-SD discovery to v1.1 (before Registry API Backend in v2.1).

**Rationale**: WebSocket requires agents to find each other. Without basic discovery, real-time communication cannot work across dynamic agents.

---

### SD-8: Documentation Architecture — Separated Docs

**Decision**: Keep documentation (MkDocs) separate from the Web App (Next.js).

| Option | Considered | Rationale |
|--------|------------|-----------|
| Docs inside Web App | Rejected | Mixing concerns, slower iteration on docs vs product |
| **Separated (MkDocs + Web App)** | ✅ Selected | Independent deploy cycles, docs can ship faster |
| Docs in GitHub Wiki | Rejected | Poor DX, no custom styling, limited search |

**Why this matters**: Documentation needs to ship independently of the marketplace. API docs, guides, and examples should be deployable without a full Web App release. MkDocs provides a fast, markdown-first authoring experience while the Web App focuses on interactive marketplace features.

---

### SD-9: State Management — Hybrid Strategy

**Decision**: ASAP defines storage interfaces and provides reference implementations. Agent task state is the agent's responsibility. Marketplace metadata is managed centrally.

| Layer | Data | Owner |
|-------|------|-------|
| **Protocol Interface** | `SnapshotStore`, `MeteringStore` | ASAP SDK (open source) |
| **Reference Impls** | SQLite, Redis adapters | Separate packages |
| **Marketplace Metadata** | Manifests, trust scores, SLA | ASAP centrally (v2.0) |
| **Agent Task State** | Snapshots, artifacts | Agent developer's choice |
| **ASAP Cloud** (future) | Managed storage | Premium feature |

| Option | Considered | Rationale |
|--------|------------|-----------|
| State-as-a-Service | Rejected | Data sovereignty burden, massive infra cost, contradicts adoption-first |
| Communication only | Rejected | v1.3 Economics impossible without storage interfaces, poor DX |
| **Hybrid** | ✅ Selected | Extends existing `SnapshotStore` pattern, no lock-in, enables ASAP Cloud monetization |

**Why this matters**: Without defined storage interfaces, v1.3 (metering, audit logging) and v2.0 (reputation, SLA tracking) become impossible. The hybrid approach keeps ASAP lightweight while enabling the full marketplace vision.

**Reference**: [ADR-13](../decision-records/01-architecture.md)

---

### SD-10: Agent Liveness — Health Protocol in v1.1

**Decision**: Agents SHOULD expose `GET /.well-known/asap/health` with TTL field in manifest.

| Option | Considered | Rationale |
|--------|------------|-----------|
| No health protocol | Rejected | Registry shows stale agents, SLA unverifiable |
| Full health framework | Rejected | Over-engineering for current stage |
| **Simple health endpoint + TTL** | ✅ Selected | Low cost, high value, Kubernetes-aligned |

**Why this matters**: Without liveness, the Registry (v1.2) becomes a graveyard of dead agents. The Reputation System (v2.0) cannot calculate uptime, and SLA monitoring (v1.3) has no measurement mechanism.

**Reference**: [ADR-14](../decision-records/01-architecture.md)

---

### SD-11: Lite Registry — Bridging the Discovery Abyss

**Decision**: Bridge the gap between v1.1 (Identity + Direct Discovery) and v2.1 (Registry API Backend) with a static `registry.json` file hosted on GitHub Pages. Agents are listed via PR.

| Option | Considered | Rationale |
|--------|------------|-----------|
| **Static JSON on GitHub Pages** | ✅ Selected | Zero infrastructure, PR-based social proof, machine-readable |
| DNS-based discovery | Rejected | Complex for developers, no browsing/search |
| Do nothing (accept gap) | Rejected | Kills early adoption momentum, network effect is zero |

**Why this matters**: In v1.1, agents have identity (OAuth2) and serve manifests (well-known), but no one can find them unless they already know the URL. The Lite Registry provides immediate discoverability with zero infrastructure cost. The v2.1 Registry API Backend can seed itself from this file when scale demands it.

**Key design**: Schema uses `endpoints` dict (not single `url`) to support HTTP + WebSocket transports introduced in v1.1.

**Reference**: [ADR-15](../decision-records/05-product-strategy.md)

---

## Release Timeline

| Version | Codename | Focus | Key Deliverables |
|---------|----------|-------|------------------|
| **v1.0.0** | Foundation | Stable protocol | ✅ Released |
| **v1.1.0** | Identity | Auth + Discovery + Real-time | OAuth2, WebSocket, Well-known URI, Lite Registry, MessageAck |
| **v1.2.0** | Verified Identity | Signing + Compliance | Ed25519 signing, Compliance Harness, mTLS (opt) |
| **v1.3.0** | Observability | Metering + SLAs + Delegation | Observability metering, SLA framework, delegation tokens |
| **v2.0.0** | Marketplace | Full launch | Web App, Lite Registry integration, Verified Badge |

---

## v1.1.0 "Identity" — Foundation for Trust

**Goal**: Establish identity, discovery, state persistence, and real-time communication.

### Features

| Feature | Priority | Purpose |
|---------|----------|---------|
| OAuth2/OIDC + Custom Claims binding | P1 | Agent identity verification + identity mapping (ADR-17) |
| Well-known URI discovery | P1 | Basic agent discovery |
| Lite Registry (GitHub Pages) | P1 | Bridge discovery gap before v1.2 Registry (SD-11) |
| Agent health/liveness | P1 | Prevent stale agent entries (SD-10) |
| State Storage Interface + SQLite | P1 | Persistent state foundation (SD-9) |
| WebSocket binding + MessageAck | P1 | Real-time comms + reliable delivery for critical messages (ADR-16) |
| Webhook callbacks | P2 | Event-driven notifications |
| DNS-SD discovery | P3 | Local network discovery (defer to v1.1.1+) |

### Why This Matters

- OAuth2 enables enterprise agent identity; Custom Claims binding maps IdP subjects to agent IDs (ADR-17)
- Well-known URI allows agents to discover each other before Registry exists (Decision SD-7)
- Lite Registry provides early discoverability via GitHub Pages (Decision SD-11)
- Health/liveness prevents Registry from listing dead agents (Decision SD-10)
- State Storage Interface is foundational for v1.3 metering and v2.0 marketplace (Decision SD-9)
- WebSocket provides low-latency comms (Decision SD-3); MessageAck ensures reliable delivery for critical messages (ADR-16)

### Deliverables

```
src/asap/
├── auth/
│   ├── oauth2.py         # OAuth2 client & server
│   └── oidc.py           # OIDC discovery
├── state/
│   ├── snapshot.py        # SnapshotStore interface (exists) + SQLite impl
│   └── stores/
│       ├── sqlite.py      # SQLite reference implementation
│       └── memory.py      # InMemorySnapshotStore (moved)
├── transport/
│   ├── websocket.py      # WebSocket binding
│   └── webhook.py        # Webhook delivery
└── discovery/
    ├── wellknown.py      # /.well-known/asap/manifest.json
    ├── health.py         # /.well-known/asap/health
    └── registry.py       # Lite Registry client (SD-11)
```

---

## v1.2.0 "Verified Identity" — Cryptographic Trust

**Goal**: Enable verifiable agent identity and protocol compliance certification.

### Features

| Feature | Priority | Purpose |
|---------|----------|---------|
| Signed manifests (Ed25519) | P1 | Verifiable agent identity |
| ASAP Compliance Harness | P1 | Protocol compliance testing |
| mTLS support (optional) | P2 | Transport-level trust |

> [!NOTE]
> **Deferred from v1.2**: Registry API Backend (to v2.1), DeepEval Intelligence (to v2.2+). See [deferred-backlog.md](./deferred-backlog.md).

### Why This Matters

- Signed manifests prevent agent impersonation (Decision SD-4)
- Compliance Harness certifies agents as "good citizens" of the network
- mTLS available for enterprise use cases (Decision SD-6)
- Lite Registry (v1.1, SD-11) provides discovery — no backend API needed yet

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

### Compliance Harness

**Shell-only strategy**: Protocol compliance testing via ASAP-native pytest harness.

| Layer | Tool | Validates |
|-------|------|-----------|
| Shell | pytest (ASAP native) | Handshake, Schema, State machine, SLA |

---

## v1.3.0 "Observability" — Visibility & Delegation

**Goal**: Enable usage visibility, service guarantees, and trust delegation.

### Features

| Feature | Priority | Purpose |
|---------|----------|---------|
| Observability metering | P1 | Track resource consumption (visibility, not billing) |
| SLA framework | P1 | Define service guarantees |
| Delegation tokens | P1 | Trust chains for sub-agents |

> [!NOTE]
> **Deferred from v1.3**: Credit system (to v3.0), Audit logging (to v2.1+). See [deferred-backlog.md](./deferred-backlog.md).

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

**Goal**: Launch the Agent Marketplace as a Web App powered by the Lite Registry.

### Core Components

| Component | Description |
|-----------|-------------|
| **Web App** | Human interface for marketplace (SD-8) |
| **Lite Registry** | GitHub Pages JSON as data source (SD-11) |
| **Verified Badge** | Stripe-powered trust verification (SD-2) |
| **Message Broker** | Optional premium for scale (SD-3) |

> [!NOTE]
> **Lean approach**: v2.0 reads from Lite Registry (`registry.json`) instead of a backend API. Registry API Backend is deferred to v2.1. See [deferred-backlog.md](./deferred-backlog.md).

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
| Data Source | Lite Registry (GitHub JSON) | No backend needed for MVP |
| Auth | ASAP OAuth2 | Dog-fooding |
| Payments | Stripe | SaaS standard |
| Hosting | Vercel | Simple for solo dev |
| Docs | Separate MkDocs | Keep docs simple (SD-8) |

**Domain**: asap-protocol.com (marketplace name TBD)

### Launch Criteria

- [ ] Lite Registry has 100+ agents
- [ ] Verified badge flow working (Stripe + ASAP CA signing)
- [ ] Web App live with core features (browse, search, register)
- [ ] Security audit passed
- [ ] Documentation complete

---

## Migration Guide

| Version | Action Required |
|---------|-----------------|
| v1.0 → v1.1 | Add OAuth2 config (with Custom Claims), expose well-known + health endpoints, choose storage backend, register in Lite Registry |
| v1.1 → v1.2 | Sign manifest with Ed25519, run compliance harness |
| v1.2 → v1.3 | Define SLAs, add metering hooks (using `MeteringStore` interface), configure delegation |
| v1.3 → v2.0 | Register in marketplace Web App, consider Verified badge ($49/mo) |

### Backward Compatibility

- All v1.x releases maintain backward compat
- v2.0 may have breaking changes (advance notice provided)
- Migration tools provided for each version

---

## Risks & Blind Spots

Strategic risks identified during the v1.1.0 planning review (2026-02-07):

| Risk | Severity | Mitigation | Status |
|------|----------|------------|--------|
| **State persistence gap** | Critical | SD-9 Hybrid strategy, SQLite impl in v1.1 | ✅ Addressed |
| **Stale agents in Registry** | High | SD-10 Liveness protocol in v1.1 | ✅ Addressed |
| **Multi-agent workflow orchestration** | Medium | Saga/choreography patterns needed. Define in v1.2+ | ⏳ Tracked |
| **Agent capability versioning** | Medium | Define version negotiation for skills. Target v1.2 | ⏳ Tracked |
| **Storage backend alignment** | Medium | v1.1 defines interfaces; v1.2/v1.3/v2.0 reuse them | ✅ Addressed |
| **p95 latency (17-21ms vs 5ms target)** | Low | Documented in v1.0 retro. Horizontal scaling recommended. | ⏳ Tracked |

### Blind Spots to Monitor

| Area | Concern | When to Address |
|------|---------|-----------------|
| **Data residency** | Enterprise customers may require regional storage | v2.0 if enterprise traction |
| **Agent migration** | What happens when an agent moves to a different host? | v1.2 (Registry should handle re-registration) |
| **Rate limiting across transports** | HTTP has rate limiting, WebSocket does not | v1.1 Sprint S3 |
| **Conflict resolution** | Multi-agent parallel work on same task | v1.2+ (define in orchestration patterns) |

---

## Resolved Questions

> **Note**: These are strategic roadmap questions (SQ). Architecture decisions are tracked separately in [Decision Records](../decision-records/README.md) with their own numbering (Q1-Q14).

| ID | Question | Decision | Reference |
|----|----------|----------|-----------|
| SQ-1 | Centralized vs federated registry? | Centralized first | SD-1 |
| SQ-2 | Signing algorithm? | Ed25519 | SD-4 |
| SQ-3 | mTLS required? | Optional only | SD-6 |
| SQ-4 | Discovery before Registry? | Yes, v1.1 | SD-7 |
| SQ-5 | Pricing model? | Freemium first | SD-2 |
| SQ-6 | WebSocket vs Broker? | WebSocket v1.x, Broker v2.0+ | SD-3 |
| SQ-7 | Docs inside Web App? | Separated (MkDocs + Web App) | SD-8 |
| SQ-8 | State management strategy? | Hybrid: Interface + Ref Impls + Managed | SD-9 |
| SQ-9 | Agent liveness protocol? | Health endpoint + TTL in manifest | SD-10 |
| SQ-10 | Discovery gap between v1.1 and v1.2? | Lite Registry on GitHub Pages | SD-11 |
| SQ-11 | WebSocket message reliability? | Selective ack for state-changing messages + AckAwareClient | ADR-16 |
| SQ-12 | Identity mapping (IdP sub → agent_id)? | Custom Claims + allowlist fallback | ADR-17 |

## Open Questions

| ID | Question | Decide By |
|----|----------|-----------|
| SQ-13 | Monetization model post-adoption? | After traction data |
| SQ-14 | Federation protocol spec? | v2.x if needed |
| SQ-15 | Marketplace product name? | Before v2.0 launch |

---

## Success Metrics by Version

| Version | Key Metric | Target |
|---------|------------|--------|
| v1.1 | OAuth2 adoption | 50% of users |
| v1.2 | Signed manifests | 80% of agents |
| v1.3 | SLA definitions | 60% of agents |
| v2.0 | Marketplace registrations | 100+ agents |

---

## Related Documents

- **Vision**: [vision-agent-marketplace.md](./vision-agent-marketplace.md)
- **Deferred Backlog**: [deferred-backlog.md](./deferred-backlog.md)
- **Repository Strategy**: [repository-strategy.md](./repository-strategy.md)
- **Design Decisions**: [Decision Records](../decision-records/README.md)
- **v1.1 PRD**: [prd-v1.1-roadmap.md](../prd/prd-v1.1-roadmap.md)
- **v1.2 PRD**: [prd-v1.2-roadmap.md](../prd/prd-v1.2-roadmap.md)
- **v1.3 PRD**: [prd-v1.3-roadmap.md](../prd/prd-v1.3-roadmap.md)
- **v2.0 PRD**: [prd-v2.0-roadmap.md](../prd/prd-v2.0-roadmap.md)
- **Checkpoints**: [checkpoints.md](../../dev-planning/checkpoints.md)

---

## Change Log

| Date | Change |
|------|--------|
| 2026-01-30 | Initial roadmap document |
| 2026-02-05 | Added strategic decisions (SD-1 to SD-7) with rationale |
| 2026-02-05 | Added Web App to v2.0, SD-8 (docs architecture) |
| 2026-02-07 | Strategic review: added SD-9 (State Management Hybrid), SD-10 (Agent Liveness) |
| 2026-02-07 | Added Risks & Blind Spots section, updated v1.1 features |
| 2026-02-07 | Resolved Q8 (state management) and Q9 (liveness), renumbered open questions |
| 2026-02-07 | Added SD-11 (Lite Registry), resolved SQ-10/11/12, updated v1.1 features |
| 2026-02-12 | **Lean Marketplace pivot**: v1.2 renamed "Verified Identity" (removed Registry API, DeepEval), v1.3 renamed "Observability" (removed credit system, audit logging), v2.0 simplified to Web App + Lite Registry (removed backend services). Added deferred-backlog.md reference |
| 2026-02-13 | **Security Hardening**: Updated SD-4 to include JCS (RFC 8785) and Strict Verification (RFC 8032) |
