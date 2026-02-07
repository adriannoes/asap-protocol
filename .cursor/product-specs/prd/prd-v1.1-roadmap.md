# PRD: ASAP Protocol v1.1.0 — Identity Layer

> **Product Requirements Document**
>
> **Version**: 1.1.0
> **Created**: 2026-01-30
> **Last Updated**: 2026-02-05

---

## 1. Executive Summary

### 1.1 Purpose

v1.1.0 establishes the **Identity Layer** for the ASAP Protocol Agent Marketplace. This release delivers:
- **Authentication**: OAuth2/OIDC for enterprise agent identity
- **Discovery**: Well-known URI for agents to find each other (before Registry)
- **Real-time Communication**: WebSocket transport binding

### 1.2 Strategic Context

v1.1.0 is the first step toward the Agent Marketplace (v2.0). See [roadmap-to-marketplace.md](../roadmap-to-marketplace.md) for evolution path.

**Key Strategic Decisions** (from strategy review):
- **SD-3**: WebSocket for v1.x, Message Broker optional in v2.0+
- **SD-7**: Basic discovery (well-known URI) before Registry API

### 1.3 Target Audience (ICP)

| Priority | Segment | Why |
|----------|---------|-----|
| 1 | AI Startups | Build products for enterprise using ASAP |
| 2 | Individual Developers | Experiment, prototype, contribute |

---

## 2. Goals

| Goal | Metric | Priority |
|------|--------|----------|
| OAuth2 client_credentials flow | Token acquisition <1s | P1 |
| WebSocket binding | Message latency <50ms (p95) | P1 |
| Well-known discovery | Manifest fetch <500ms | P1 |
| OIDC auto-discovery | Auto-configure from provider | P2 |
| Webhook delivery | >99.9% success with retries | P2 |

---

## 3. User Stories

### Agent Developer
> As an **agent developer**, I want to **use OAuth2 tokens for authentication** so that **my agents can work in enterprise environments with existing identity providers**.

### Platform Engineer
> As a **platform engineer**, I want to **discover agents via well-known URIs** so that **I can find and connect to agents without a centralized registry**.

### Real-time Application Developer
> As a **developer building real-time applications**, I want to **communicate via WebSocket** so that **I get low-latency bidirectional messaging between agents**.

---

## 4. Functional Requirements

### 4.1 OAuth2/OIDC Integration (P1)

| ID | Requirement | Priority |
|----|-------------|----------|
| OAUTH-001 | Client credentials flow support | MUST |
| OAUTH-002 | Authorization code flow support | SHOULD |
| OAUTH-003 | Automatic token refresh before expiry | MUST |
| OAUTH-004 | OIDC discovery from /.well-known/openid-configuration | SHOULD |
| OAUTH-005 | JWT signature validation | MUST |
| OAUTH-006 | Scope-based authorization (asap:read, asap:execute) | MUST |
| OAUTH-007 | Token introspection for opaque tokens | SHOULD |

**Provider Support**:
| Provider | Priority |
|----------|----------|
| Auth0 | High (example + docs) |
| Keycloak | High (example + docs) |
| Google | Medium (example) |
| Azure AD | Medium (example) |

---

### 4.2 WebSocket Transport (P1)

| ID | Requirement | Priority |
|----|-------------|----------|
| WS-001 | WebSocket server endpoint (/asap/ws) | MUST |
| WS-002 | WebSocket client connection | MUST |
| WS-003 | Bidirectional JSON-RPC over WebSocket | MUST |
| WS-004 | Automatic reconnection with exponential backoff | MUST |
| WS-005 | Heartbeat/keepalive (ping every 30s) | SHOULD |
| WS-006 | Connection pooling and reuse | SHOULD |
| WS-007 | Graceful shutdown with close frame | MUST |

**Architecture**:
```
┌─────────────────────────────────────────────────────────────────┐
│                    WebSocket Architecture                        │
├─────────────────────────────────────────────────────────────────┤
│   Client                              Server                     │
│   ┌─────────────┐                    ┌─────────────┐            │
│   │ WS Client   │ ←──── wss:// ────→ │ WS Server   │            │
│   │ - connect() │                    │ - accept()  │            │
│   │ - send()    │                    │ - dispatch()│            │
│   │ - receive() │                    │ - broadcast │            │
│   └─────────────┘                    └─────────────┘            │
└─────────────────────────────────────────────────────────────────┘
```

**Success Metrics**:
- Connection establishment <500ms
- Message latency <50ms (p95)
- Reconnection success >99% within 30s

---

### 4.3 Well-Known Discovery (P1)

| ID | Requirement | Priority |
|----|-------------|----------|
| DISC-001 | Serve /.well-known/asap/manifest.json | MUST |
| DISC-002 | Client discover(base_url) method | MUST |
| DISC-003 | Cache manifests with 5min TTL | SHOULD |
| DISC-004 | ETag/Cache-Control headers | SHOULD |
| DISC-005 | DNS-SD/mDNS for local discovery | MAY |

**Rationale** (SD-7): WebSocket requires agents to find each other. Without basic discovery, real-time communication cannot work across dynamic agents.

---

### 4.4 State Storage Interface (P1)

| ID | Requirement | Priority |
|----|-------------|----------|
| STATE-001 | `SnapshotStore` Protocol remains the abstract interface | MUST |
| STATE-002 | SQLite reference implementation (`asap-storage-sqlite`) | MUST |
| STATE-003 | `MeteringStore` Protocol for v1.3 usage tracking | MUST |
| STATE-004 | Storage backend auto-detection (env-based) | SHOULD |
| STATE-005 | Migration utilities (InMemory → SQLite) | SHOULD |
| STATE-006 | Redis reference implementation | MAY |

**Rationale** (SD-9): The v0 spec listed "First-class persistent state" as a key design goal. The `SnapshotStore` Protocol exists in v1.0, but only `InMemorySnapshotStore` is implemented. Without persistent storage, v1.3 metering, audit logging, and v2.0 marketplace reputation are impossible.

**Architecture (Hybrid Strategy)**:
```
┌─────────────────────────────────────────────────────────────────┐
│                    STORAGE ARCHITECTURE (SD-9)                    │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Protocol Layer (ASAP SDK)                                       │
│  ┌──────────────────┐  ┌──────────────────┐                     │
│  │  SnapshotStore   │  │  MeteringStore   │  ← Interfaces       │
│  │  (Protocol)      │  │  (Protocol)      │                     │
│  └────────┬─────────┘  └────────┬─────────┘                     │
│           │                     │                                │
│  Reference Implementations (separate packages)                   │
│  ┌────────┴──┐ ┌────────┴──┐ ┌──────────┐                      │
│  │  SQLite   │ │   Redis   │ │ Postgres │                      │
│  │  (v1.1)   │ │  (v1.2+)  │ │ (v2.0)   │                      │
│  └───────────┘ └───────────┘ └──────────┘                      │
│                                                                  │
│  Agent's Responsibility                    ASAP Centrally        │
│  ┌───────────────────┐                    ┌──────────────────┐  │
│  │ Task snapshots    │                    │ Registry data    │  │
│  │ Event history     │                    │ Trust scores     │  │
│  │ Artifacts         │                    │ SLA metrics      │  │
│  └───────────────────┘                    └──────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

---

### 4.5 Agent Liveness / Health (P1)

| ID | Requirement | Priority |
|----|-------------|----------|
| HEALTH-001 | Serve `GET /.well-known/asap/health` JSON response | MUST |
| HEALTH-002 | Include `status`, `version`, `uptime_seconds` in response | MUST |
| HEALTH-003 | `ttl_seconds` field in Manifest (default: 300) | MUST |
| HEALTH-004 | Client `health_check(base_url)` method | SHOULD |
| HEALTH-005 | Auto-register health route in ASAPServer | MUST |

**Rationale** (SD-10): Without liveness, the Registry (v1.2) lists dead agents. The SLA Framework (v1.3) cannot verify `availability` claims. A simple health endpoint is low-cost and high-value.

**Health Response Schema**:
```json
{
  "status": "healthy",
  "agent_id": "urn:asap:agent:example",
  "version": "1.0.0",
  "asap_version": "1.1.0",
  "uptime_seconds": 3600,
  "capabilities": ["task.execute", "state.persist"],
  "load": {
    "active_tasks": 3,
    "queue_depth": 12
  }
}
```

---

### 4.6 Lite Registry (P1)

| ID | Requirement | Priority |
|----|-------------|----------|
| REG-001 | Static `registry.json` schema with multi-endpoint support | MUST |
| REG-002 | `discover_from_registry(registry_url)` SDK method | MUST |
| REG-003 | Default registry URL pointing to GitHub Pages | SHOULD |
| REG-004 | Registry entry validation (schema compliance) | SHOULD |
| REG-005 | CLI command to generate registry entry from manifest | MAY |

**Rationale** (SD-11): v1.1 introduces identity and direct discovery, but no one can find agents unless they know the URL. A static Lite Registry on GitHub Pages bridges this "Discovery Abyss" before the v1.2 Registry API.

**Schema** (multi-endpoint, supporting HTTP + WebSocket):
```json
{
  "version": "1.0",
  "updated_at": "2026-02-07T00:00:00Z",
  "agents": [
    {
      "id": "urn:asap:agent:example",
      "name": "Example Agent",
      "description": "Code review and summarization agent",
      "endpoints": {
        "http": "https://agent.example.com/asap",
        "ws": "wss://agent.example.com/asap/ws",
        "manifest": "https://agent.example.com/.well-known/asap/manifest.json"
      },
      "skills": ["code_review", "summarization"],
      "asap_version": "1.1.0"
    }
  ]
}
```

---

### 4.7 WebSocket Message Acknowledgment (P1)

| ID | Requirement | Priority |
|----|-------------|----------|
| ACK-001 | `MessageAck` payload type with `original_envelope_id` and `status` | MUST |
| ACK-002 | `requires_ack: bool = False` field on Envelope | MUST |
| ACK-003 | Auto-set `requires_ack=True` for state-changing payloads over WebSocket | MUST |
| ACK-004 | `AckAwareClient` with timeout/retry loop | MUST |
| ACK-005 | Configurable ack timeout (default: 30s) | SHOULD |
| ACK-006 | Max retries before circuit breaker trips | SHOULD |
| ACK-007 | HTTP transport continues implicit ack (no change) | MUST |

**Rationale** (ADR-16): WebSocket is fire-and-forget. State-changing messages (`TaskRequest`, `TaskCancel`, `StateRestore`) MUST be acknowledged to prevent task state machine inconsistencies. The `AckAwareClient` manages the timeout/retry loop — without it, the ack protocol is useless.

**Payloads requiring ack**: `TaskRequest`, `TaskCancel`, `StateRestore`, `MessageSend`
**Payloads NOT requiring ack**: `TaskUpdate` (progress), heartbeats, streaming

---

### 4.8 Identity Binding — Custom Claims (P1)

| ID | Requirement | Priority |
|----|-------------|----------|
| BIND-001 | Validate `https://asap.ai/agent_id` custom claim in JWT | MUST |
| BIND-002 | Match custom claim value against manifest `id` | MUST |
| BIND-003 | Allowlist fallback via `ASAP_AUTH_SUBJECT_MAP` env var | SHOULD |
| BIND-004 | Log warning when falling back to allowlist (encourage custom claims) | SHOULD |
| BIND-005 | Document v1.1 security model limitations explicitly | MUST |

**Rationale** (ADR-17): IdP-generated `sub` claims (`google-oauth2|12345`) don't match ASAP `agent_id` values (`urn:asap:agent:bot`). Custom Claims provide a portable, standards-based solution. Explicit documentation prevents false security expectations.

---

### 4.9 Webhook Callbacks (P2)

| ID | Requirement | Priority |
|----|-------------|----------|
| HOOK-001 | POST callbacks to registered URLs | MUST |
| HOOK-002 | SSRF prevention (block private IPs) | MUST |
| HOOK-003 | HMAC-SHA256 signature (X-ASAP-Signature) | MUST |
| HOOK-004 | Exponential backoff retry (5 attempts) | MUST |
| HOOK-005 | Event filtering by type | SHOULD |
| HOOK-006 | Rate limiting per endpoint | SHOULD |

**Event Types**:
```json
{
  "events": ["task.started", "task.progress", "task.completed", "task.failed"]
}
```

---

## 5. Non-Goals (Out of Scope)

| Feature | Reason | When |
|---------|--------|------|
| Signed manifests | Part of Trust Layer | v1.2.0 |
| Full Registry API | Part of Trust Layer (Lite Registry in v1.1 bridges gap) | v1.2.0 |
| mTLS | Part of Trust Layer | v1.2.0 |
| Agent identity verification (PKI) | Requires Ed25519 signed manifests | v1.2.0 |
| Message Broker (NATS) | Overkill for startups (SD-3) | v2.0+ optional |
| DNS-SD discovery | P3, well-known URI is sufficient | v1.1.1+ or drop |
| Redis storage impl | SQLite is sufficient for v1.1 | v1.2.0+ |
| Usage metering | Part of Economics Layer (uses `MeteringStore` interface) | v1.3.0 |
| Formal TaskHandover protocol | Requires signed state for integrity | v1.2.0 |

---

## 6. Technical Considerations

### 6.1 New Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| authlib | ≥1.3 | OAuth2 client, OIDC discovery, FastAPI integration (ADR-12) |
| joserfc | ≥1.0 | JWT/JWKS validation, modern JOSE support (ADR-12) |
| websockets | ≥12.0 | WebSocket transport |
| aiosqlite | ≥0.20 | Async SQLite for SnapshotStore reference impl (ADR-13) |

### 6.2 Code Structure

```
src/asap/
├── auth/
│   ├── __init__.py
│   ├── oauth2.py         # OAuth2 client
│   ├── oidc.py           # OIDC discovery
│   └── middleware.py     # Token validation
├── state/
│   ├── __init__.py       # Exports SnapshotStore, MeteringStore
│   ├── machine.py        # State machine (exists)
│   ├── snapshot.py        # SnapshotStore Protocol (exists)
│   ├── metering.py       # MeteringStore Protocol (new)
│   └── stores/
│       ├── __init__.py
│       ├── memory.py     # InMemorySnapshotStore (refactored from snapshot.py)
│       └── sqlite.py     # SQLiteSnapshotStore (new)
├── transport/
│   ├── websocket.py      # WebSocket binding + MessageAck + AckAwareClient
│   └── webhook.py        # Webhook delivery
└── discovery/
    ├── wellknown.py      # /.well-known/asap/manifest.json
    ├── health.py         # /.well-known/asap/health
    └── registry.py       # Lite Registry client (SD-11)
```

### 6.3 Backward Compatibility

- All v1.0.0 HTTP transport continues to work
- OAuth2 is optional (agents can still use Bearer tokens)
- WebSocket is additive (HTTP still primary)

---

## 7. Success Metrics

| Metric | Target |
|--------|--------|
| OAuth2 adoption | 50% of users |
| WebSocket latency (p95) | <50ms |
| State persistence | SQLite impl functional with >95% test coverage |
| Health endpoint response time | <10ms (p95) |
| Test coverage | ≥95% |
| Documentation | 100% API coverage |
| Lite Registry | SDK method functional, schema validated | 
| MessageAck delivery | >99% ack rate for state-changing messages |
| Custom Claims binding | Works with Auth0, Keycloak examples |
| Examples | 7+ (OAuth2, WebSocket, Webhook, Discovery, Storage, Lite Registry, Failover) |

---

## 8. Risks & Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| OAuth2 provider differences | High | Medium | Abstract provider interface |
| WebSocket complexity | Medium | High | Start basic, iterate |
| Breaking changes | Low | High | Contract testing |
| Scope creep | Medium | Medium | Fixed feature set |

---

## 9. Open Questions (Resolved)

| ID | Question | Decision |
|----|----------|----------|
| Q1 | WebSocket mandatory or optional? | Optional (HTTP remains primary) |
| Q2 | OAuth2 server or client-side? | Client-side (use existing providers) |
| Q3 | Webhook guarantees? | At-least-once with retries |
| Q4 | Discovery before Registry? | Yes (SD-7), well-known in v1.1 + Lite Registry (SD-11) |
| Q5 | WebSocket delivery guarantees? | Selective ack for critical messages (ADR-16) |
| Q6 | Identity mapping (IdP → agent_id)? | Custom Claims + allowlist fallback (ADR-17) |

---

## 10. Related Documents

- **Tasks**: [tasks-v1.1.0-roadmap.md](../../dev-planning/tasks/v1.1.0/tasks-v1.1.0-roadmap.md)
- **Detailed Auth**: [Sprint S1](../../dev-planning/tasks/v1.1.0/sprint-S1-oauth2-foundation.md)
- **Detailed Discovery**: [Sprint S2](../../dev-planning/tasks/v1.1.0/sprint-S2-wellknown-discovery.md)
- **Detailed State Storage**: [Sprint S2.5](../../dev-planning/tasks/v1.1.0/sprint-S2.5-state-storage.md)
- **Detailed Transport**: [Sprint S3](../../dev-planning/tasks/v1.1.0/sprint-S3-websocket-binding.md), [Sprint S4](../../dev-planning/tasks/v1.1.0/sprint-S4-webhooks-release.md)
- **Roadmap**: [roadmap-to-marketplace.md](../roadmap-to-marketplace.md)
- **Vision**: [vision-agent-marketplace.md](../vision-agent-marketplace.md)

---

## Change Log

| Date | Version | Change |
|------|---------|--------|
| 2026-01-30 | 0.1.0 | Initial draft from gap analysis |
| 2026-02-05 | 1.0.0 | Aligned with strategic decisions, added sprints |
| 2026-02-07 | 1.0.1 | Replaced httpx-oauth with authlib + joserfc (ADR-12) |
| 2026-02-07 | 1.1.0 | Strategic review: added State Storage Interface (SD-9, ADR-13), Agent Liveness (SD-10, ADR-14), Sprint S2.5 |
| 2026-02-07 | 1.2.0 | Added Lite Registry (SD-11, ADR-15), WebSocket MessageAck (ADR-16), Custom Claims binding (ADR-17) |
