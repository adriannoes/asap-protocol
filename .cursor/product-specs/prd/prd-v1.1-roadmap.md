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

### 4.4 Webhook Callbacks (P2)

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
| Registry API | Part of Trust Layer | v1.2.0 |
| mTLS | Part of Trust Layer | v1.2.0 |
| Message Broker (NATS) | Overkill for startups | v2.0+ optional |
| gRPC transport | Low community demand | TBD |

---

## 6. Technical Considerations

### 6.1 New Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| httpx-oauth | ≥0.13 | OAuth2 flows |
| websockets | ≥12.0 | WebSocket transport |
| zeroconf | ≥0.80 (optional) | DNS-SD discovery |

### 6.2 Code Structure

```
src/asap/
├── auth/
│   ├── __init__.py
│   ├── oauth2.py         # OAuth2 client
│   ├── oidc.py           # OIDC discovery
│   └── middleware.py     # Token validation
├── transport/
│   ├── websocket.py      # WebSocket binding
│   └── webhook.py        # Webhook delivery
└── discovery/
    ├── wellknown.py      # Well-known endpoint
    └── dns_sd.py         # DNS-SD (optional)
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
| Test coverage | ≥95% |
| Documentation | 100% API coverage |
| Examples | 4+ (OAuth2, WebSocket, Webhook, Discovery) |

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
| Q4 | Discovery before Registry? | Yes (SD-7), well-known in v1.1 |

---

## 10. Related Documents

- **Tasks**: [tasks-v1.1.0-roadmap.md](../../dev-planning/tasks/v1.1.0/tasks-v1.1.0-roadmap.md)
- **Detailed Auth**: [tasks-v1.1.0-auth-detailed.md](../../dev-planning/tasks/v1.1.0/tasks-v1.1.0-auth-detailed.md)
- **Detailed Transport**: [tasks-v1.1.0-transport-detailed.md](../../dev-planning/tasks/v1.1.0/tasks-v1.1.0-transport-detailed.md)
- **Roadmap**: [roadmap-to-marketplace.md](../roadmap-to-marketplace.md)
- **Vision**: [vision-agent-marketplace.md](../vision-agent-marketplace.md)

---

## Change Log

| Date | Version | Change |
|------|---------|--------|
| 2026-01-30 | 0.1.0 | Initial draft from gap analysis |
| 2026-02-05 | 1.0.0 | Aligned with strategic decisions, added sprints |
