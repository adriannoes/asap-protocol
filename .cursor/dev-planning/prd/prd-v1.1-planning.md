# PRD: ASAP Protocol v1.1 Planning

> **Product Requirements Document**
>
> **Version**: 1.1.0-planning
> **Status**: DRAFT
> **Created**: 2026-01-30
> **Last Updated**: 2026-01-30

---

## 1. Executive Summary

### 1.1 Purpose

This PRD documents features deferred from v1.0.0 and planned for the v1.1.x release series. Features were identified through gap analysis comparing the v1.0.0 roadmap against the original protocol specification (`v0-original-specs.md`).

### 1.2 Goals

1. Complete transport layer with WebSocket binding
2. Enterprise-ready authentication with OAuth2/OIDC
3. Async delivery mechanisms with webhook callbacks
4. Interoperability via standardized state storage interface
5. Scale support via message broker integration

### 1.3 Non-Goals (v1.1 Scope)

- gRPC transport binding (v1.2+)
- Federated identity/cross-domain trust (v1.2+)
- Agent marketplace infrastructure (v2.0+) — see [vision-agent-marketplace.md](../product-specs/vision-agent-marketplace.md)

> [!NOTE]
> **End Goal**: The Agent Marketplace (v2.0) is the ultimate vision for ASAP. v1.1 features (OAuth2, WebSocket) are foundational building blocks. See [roadmap-to-marketplace.md](../product-specs/roadmap-to-marketplace.md) for the full evolution path.

---

## 2. Background

### 2.1 Gap Analysis Summary

The v1.0.0 roadmap comprehensively covers the original specification with the following gaps:

| Gap | Spec Reference | v1.0.0 Status | v1.1 Scope |
|-----|----------------|---------------|------------|
| WebSocket binding | §6.3, §13.1 | Concept only | ✅ Full implementation |
| OAuth2/OIDC | §10.2, §10.3 | Schema only | ✅ Runtime support |
| Webhook callbacks | §6.3 | Not implemented | ✅ v1.1 |
| State storage interface | §13.2 | Open decision | ✅ Define interface |
| Message broker | §6.3, §7.4 | Excluded | ⏳ v1.2 (as package) |
| DNS-SD discovery | §7.4 | Deferred | ⏳ v1.2 |

### 2.2 Prerequisite

All v1.1 work requires v1.0.0 to be:
- Released on PyPI
- Stable for 30+ days
- No critical bug reports

---

## 3. Requirements

### 3.1 WebSocket Transport Binding (P1)

#### 3.1.1 Functional Requirements

| ID | Requirement | Priority |
|----|-------------|----------|
| WS-001 | Client can connect to WebSocket endpoint | MUST |
| WS-002 | Server can accept WebSocket connections | MUST |
| WS-003 | Bidirectional message exchange | MUST |
| WS-004 | Automatic reconnection with backoff | MUST |
| WS-005 | Heartbeat/keepalive mechanism | SHOULD |
| WS-006 | Compression support (permessage-deflate) | SHOULD |
| WS-007 | Graceful connection shutdown | MUST |

#### 3.1.2 Technical Design

```
┌─────────────────────────────────────────────────────────────────┐
│                    WebSocket Architecture                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│   Client                              Server                     │
│   ┌─────────────┐                    ┌─────────────┐            │
│   │ WS Client   │ ←──── wss:// ────→ │ WS Server   │            │
│   │             │                    │             │            │
│   │ - connect() │                    │ - accept()  │            │
│   │ - send()    │                    │ - handle()  │            │
│   │ - recv()    │                    │ - broadcast │            │
│   │ - close()   │                    │ - close()   │            │
│   └─────────────┘                    └─────────────┘            │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

#### 3.1.3 Success Metrics

- Connection establishment < 500ms
- Message latency < 50ms (p95)
- Reconnection success > 99% within 30s
- Zero message loss during graceful shutdown

---

### 3.2 OAuth2/OIDC Integration (P1)

#### 3.2.1 Functional Requirements

| ID | Requirement | Priority |
|----|-------------|----------|
| OAUTH-001 | Client credentials flow | MUST |
| OAUTH-002 | Authorization code flow | SHOULD |
| OAUTH-003 | Token refresh handling | MUST |
| OAUTH-004 | OIDC discovery (/.well-known/openid-configuration) | SHOULD |
| OAUTH-005 | JWT validation | MUST |
| OAUTH-006 | Scope-based authorization | MUST |

#### 3.2.2 Provider Support

| Provider | Priority | Notes |
|----------|----------|-------|
| Auth0 | High | Example + docs |
| Keycloak | High | Example + docs |
| Google | Medium | Example only |
| Azure AD | Medium | Example only |

#### 3.2.3 Success Metrics

- Token acquisition < 1s
- Token refresh before expiry 100%
- Integration examples for 2+ providers

---

### 3.3 Webhook Callbacks (P2)

#### 3.3.1 Functional Requirements

| ID | Requirement | Priority |
|----|-------------|----------|
| HOOK-001 | Register callback URL in TaskRequest | MUST |
| HOOK-002 | Filter by event type | MUST |
| HOOK-003 | HMAC-SHA256 signature | MUST |
| HOOK-004 | Retry with exponential backoff | MUST |
| HOOK-005 | Callback URL validation | MUST |
| HOOK-006 | Rate limiting per endpoint | SHOULD |

#### 3.3.2 Event Types

```json
{
  "callback_events": [
    "task.started",
    "task.progress",
    "task.completed",
    "task.failed",
    "artifact.ready"
  ]
}
```

#### 3.3.3 Success Metrics

- Delivery success > 99.9% (with retries)
- Webhook latency < 5s (p95)
- No secrets in logs

---

### 3.4 State Storage Interface (P2)

#### 3.4.1 Functional Requirements

| ID | Requirement | Priority |
|----|-------------|----------|
| STATE-001 | Abstract interface definition | MUST |
| STATE-002 | In-memory reference impl | MUST |
| STATE-003 | SQLite reference impl | SHOULD |
| STATE-004 | Redis reference impl | SHOULD |
| STATE-005 | Migration utilities | SHOULD |

#### 3.4.2 Interface Definition

```python
from abc import ABC, abstractmethod
from typing import Optional

class StateStorage(ABC):
    @abstractmethod
    async def save(self, task_id: str, version: int, data: dict) -> None: ...
    
    @abstractmethod
    async def load(self, task_id: str, version: Optional[int] = None) -> dict: ...
    
    @abstractmethod
    async def list_versions(self, task_id: str) -> list[int]: ...
    
    @abstractmethod
    async def delete(self, task_id: str) -> None: ...
```

---

## 4. Open Questions

| ID | Question | Status | Decision |
|----|----------|--------|----------|
| Q1 | Should WebSocket be mandatory or optional transport? | Open | - |
| Q2 | OAuth2 server-side or client-side token handling? | Open | - |
| Q3 | Webhook delivery guarantees (at-least-once vs exactly-once)? | Open | - |
| Q4 | State storage interface in core or separate package? | Open | - |

---

## 5. Risks & Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| WebSocket complexity | Medium | High | Start with basic impl, iterate |
| OAuth2 provider differences | High | Medium | Abstract provider interface |
| Breaking changes | Low | High | Strict contract testing |
| Scope creep | Medium | Medium | Fixed feature set, defer to v1.2 |

---

## 6. Timeline

### 6.1 Proposed Schedule

| Milestone | Target | Features |
|-----------|--------|----------|
| v1.1.0-alpha | v1.0.0 + 6 weeks | WebSocket, OAuth2 |
| v1.1.0-beta | v1.0.0 + 10 weeks | + Webhooks, State interface |
| v1.1.0 | v1.0.0 + 14 weeks | Final release |

### 6.2 Dependencies

- v1.0.0 stable release
- Community feedback on v1.0.0
- Decision on open questions (Q1-Q4)

---

## 7. Success Criteria

| Criterion | Target |
|-----------|--------|
| All P1 features implemented | 100% |
| Test coverage | ≥ 95% |
| Documentation complete | 100% |
| No regressions from v1.0.0 | 0 failures |
| Performance benchmarks met | All pass |

---

## 8. Related Documents

- **Tasks**: [v1.1-planned-features.md](../tasks/v1.1-planned-features.md)
- **v1.0.0 PRD**: [prd-v1-roadmap.md](./prd-v1-roadmap.md)
- **Original Spec**: [v0-original-specs.md](../../product-specs/v0-original-specs.md)

---

## Change Log

| Date | Version | Change |
|------|---------|--------|
| 2026-01-30 | 0.1.0 | Initial draft from gap analysis |
