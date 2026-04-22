# PRD: ASAP Protocol v2.2.0 — Protocol Hardening

> **Product Requirements Document**
>
> **Version**: 2.2.0
> **Status**: ✅ SHIPPED (2026-04-15, tag `v2.2.0`, GitHub Release 2026-04-16)
> **Created**: 2026-03-13
> **Last Updated**: 2026-04-17
> **Supersedes**: [prd-v2.2-scale.md](./prd-v2.2-scale.md) (scope revised per strategic review)
>
> **Delivery Summary**: 38/38 MUST + 17/18 SHOULD entregues. Único pendente: SELF-002 (WebAuthn real — hoje placeholder via `WebAuthnVerifier` Protocol). 2 COULD adiados (COMP-006 CLI `asap compliance-check`, AUD-005 export CLI dedicado).
>
> **Evidence (merged PRs)**: #92 (A2H), #102 (Identity S0), #105 (Capabilities/Lifecycle S1), #106 (Approval/Self-Auth S2), #110 (Errors/Streaming S3), #115 (Versioning/Async S4), #121 (Batch/Audit/Compliance S5), #122 (regression + CVE-2026-4539). ADR-019-unified-versioning publicado (resolve VER-007).

---

## 1. Executive Summary

### 1.1 Purpose

v2.2.0 is the most transformative release since v2.0. It rebalances investment from marketplace to protocol, delivering both **identity/authorization hardening** and **protocol maturity**. Since v2.0, the protocol core has not received new capabilities — v2.0 focused on the Web App, v2.1 on the Consumer SDK and integrations. The original v2.2 scope (Registry API Backend, Auto-Registration) was deferred because its triggers were not met. This release delivers:

**Identity & Authorization Hardening**:
- **Per-Runtime-Agent Identity**: Host→Agent hierarchy; each conversation/session gets its own Ed25519 keypair (SD-12)
- **Capability-Based Authorization**: Fine-grained capabilities with constraint operators replacing coarse OAuth scopes (SD-13)
- **Agent Lifecycle Management**: Session TTL, max lifetime, absolute lifetime with reactivation as security checkpoint
- **Approval Flows**: RFC 8628 Device Authorization, CIBA, and WebAuthn proof-of-presence for user consent (SD-14)
- **Self-Authorization Prevention**: Biometric/hardware proof for agents controlling the browser

**Protocol Maturity**:
- **Streaming/SSE**: Server-Sent Events for incremental task responses
- **Error Taxonomy Evolution**: Recovery hints and structured retry semantics (extending existing ADR-012 hierarchy)
- **Unified Versioning**: Content negotiation and resolution of the SemVer vs CalVer conflict (ADR-016 vs Q6)
- **Async Protocol Resolution**: Formal dual-protocol for SnapshotStore (resolving the CP-1 open decision)
- **A2H Integration Completion**: Finalizing the 90%-complete Human-in-the-Loop integration
- **Batch Operations**: Implementing JSON-RPC 2.0 native batch (noted as "future" in ADR-003)
- **Compliance Harness v2**: Expanding certification to cover new protocol features
- **Audit Logging**: Tamper-evident logs (kept from original v2.2 scope)

> [!NOTE]
> **Strategic context**: The original v2.2 PRD (`prd-v2.2-scale.md`) required triggers that have not been met: (1) 500+ real agents in Lite Registry, (2) IssueOps as adoption bottleneck. Those items move to v2.3. This revised scope follows the project's established "Lean/Defer" pattern (v1.2 deferred Registry API, v2.0 deferred PostgreSQL).

### 1.2 Strategic Context

v2.2 invests in the **Identity/Auth Layer** and **Protocol Layer** to establish enterprise-grade security and resolve open technical debt before scaling in v2.3.

| Layer | v2.2 Investment |
|-------|----------------|
| Identity & Auth | **Primary focus** — Per-agent identity, capabilities, approval, lifecycle |
| Protocol (Transport, Models, Errors) | **Primary focus** — Streaming, Batch, Versioning |
| State (Persistence) | Async Protocol resolution |
| Trust (Compliance) | Harness v2 |
| Marketplace | Deferred to v2.3 (triggers not met) |

---

## 2. Goals

| Goal | Metric | Priority |
|------|--------|----------|
| Per-agent identity | Agent registration with own Ed25519 keypair under Host | P0 |
| Capability authorization | Capabilities with constraint enforcement operational | P0 |
| Agent lifecycle | Session TTL, max lifetime, reactivation working | P0 |
| Approval flows | Device Auth (RFC 8628) consent flow operational | P1 |
| Self-auth prevention | WebAuthn integration for browser-controlling agents | P1 |
| Streaming responses | SSE endpoint functional with e2e tests | P1 |
| Error recoverability | All 6 error categories have RecoverableError/FatalError classification | P1 |
| Version negotiation | Client/Server negotiate ASAP-Version 2.1 <-> 2.2 | P1 |
| Async persistence | AsyncSnapshotStore Protocol adopted; sync deprecated | P1 |
| A2H complete | All pending commits merged | P1 |
| Batch throughput | JSON-RPC batch endpoint handles N requests in single POST | P2 |
| Compliance coverage | Harness covers identity, capabilities, streaming, errors, versioning, batch | P2 |
| Audit compliance | All write operations logged in tamper-evident chain | P2 |

---

## 3. User Stories

### Enterprise Platform (Agent Identity)
> As an **enterprise platform**, I want **each runtime agent (conversation, task, session) to have its own cryptographic identity** so that **I can audit, scope, and revoke individual agents without affecting others**.

### Agent Developer (Capabilities)
> As an **agent developer**, I want to **define fine-grained capabilities with constraints** (e.g., "transfer up to $1,000 in USD") so that **consumers grant precisely scoped access instead of blanket permissions**.

### SDK Consumer (Approval)
> As a **SDK consumer**, I want **user consent via Device Authorization or CIBA before an agent acts on my behalf** so that **I maintain control over what agents can do with my resources**.

### Security Engineer (Self-Auth Prevention)
> As a **security engineer**, I want to **require WebAuthn proof-of-presence for agents that control the browser** so that **agents cannot auto-approve their own capability requests**.

### Agent Developer (Streaming)
> As an **agent developer**, I want to **stream task results incrementally via SSE** so that **consumers see partial progress without waiting for full completion**.

### SDK Consumer (Error Recovery)
> As a **SDK consumer**, I want to **receive structured recovery hints in error responses** (retry_after_ms, alternative_agents) so that **my orchestration loop can self-heal without manual intervention**.

### Protocol Integrator (Version Negotiation)
> As a **protocol integrator**, I want to **negotiate ASAP protocol versions via headers** so that **my agent can communicate with both v2.1 and v2.2 servers transparently**.

### Agent Developer (Batch)
> As an **agent developer**, I want to **send multiple task requests in a single HTTP call** so that **orchestration loops reduce network overhead**.

### Enterprise Admin (Audit)
> As an **enterprise admin**, I want to **retrieve tamper-evident audit logs of all protocol write operations** so that **I can satisfy compliance requirements**.

---

## 4. Functional Requirements

### 4.1 Per-Runtime-Agent Identity (P0)

Each runtime agent gets its own Ed25519 keypair under a persistent Host identity. This separates the long-lived client environment (Host) from the individual runtime actor (Agent).

| ID | Requirement | Priority |
|----|-------------|----------|
| ID-001 | `HostIdentity` model — persistent client environment identity with Ed25519 keypair, optional `user_id`, default capabilities | MUST |
| ID-002 | `AgentSession` model — runtime agent with own keypair, `host_id` FK, mode (`delegated`/`autonomous`), status, lifetime clocks | MUST |
| ID-003 | `POST /asap/agent/register` — register agent under host with Host JWT containing agent public key | MUST |
| ID-004 | `GET /asap/agent/status` — return agent status, capability grants, and lifecycle info | MUST |
| ID-005 | `POST /asap/agent/revoke` — permanently revoke an agent; host revocation cascades to all agents | MUST |
| ID-006 | `POST /asap/agent/rotate-key` — replace agent's public key (host-authenticated) | SHOULD |
| ID-007 | Host JWT (`typ: host+jwt`) and Agent JWT (`typ: agent+jwt`) with distinct verification flows | MUST |
| ID-008 | Backward compatibility — existing OAuth2 flow remains valid alongside new identity model | MUST |
| ID-009 | `jti` replay detection with in-memory cache (90s TTL window) | MUST |

**Data Model**:
```python
class HostIdentity(BaseModel):
    host_id: str
    name: str | None = None
    public_key: dict  # JWK
    user_id: str | None = None
    default_capabilities: list[str] = []
    status: Literal["active", "pending", "revoked"]

class AgentSession(BaseModel):
    agent_id: str
    host_id: str
    public_key: dict  # JWK
    mode: Literal["delegated", "autonomous"]
    status: Literal["pending", "active", "expired", "revoked"]
    session_ttl: timedelta | None = None
    max_lifetime: timedelta | None = None
    absolute_lifetime: timedelta | None = None
```

---

### 4.2 Capability-Based Authorization (P0)

Upgrades from coarse OAuth scopes (`READ/EXECUTE/ADMIN`) to fine-grained capabilities with constraint operators.

| ID | Requirement | Priority |
|----|-------------|----------|
| CAP-001 | `CapabilityDefinition` model — name, description, input/output JSON schemas, optional location | MUST |
| CAP-002 | `CapabilityGrant` model — per-agent grant with status (`active`/`pending`/`denied`), optional constraints | MUST |
| CAP-003 | `CapabilityConstraint` — operators: `max`, `min`, `in` (allowed values), `not_in` (blocked values), exact value | MUST |
| CAP-004 | Constraint enforcement on capability execution with `constraint_violated` error including `violations` array | MUST |
| CAP-005 | `GET /asap/capability/list` — lightweight capability listing (name, description, grant_status) | MUST |
| CAP-006 | `GET /asap/capability/describe?name=` — full detail with input/output schemas | MUST |
| CAP-007 | `POST /asap/capability/execute` — gateway endpoint; validates JWT, checks grants, enforces constraints | MUST |
| CAP-008 | Backward compatibility — existing OAuth scopes map to capabilities (`SCOPE_READ` → read capabilities, etc.) | MUST |
| CAP-009 | Partial approval — user may approve some capabilities and deny others during registration | SHOULD |

**Constraint Example**:
```json
{
  "capability": "transfer_funds",
  "status": "active",
  "constraints": {
    "amount": { "max": 1000 },
    "currency": { "in": ["USD", "EUR"] },
    "destination": "acc_456"
  }
}
```

---

### 4.3 Agent Lifecycle Management (P0)

Three independent clocks govern agent lifetimes. Reactivation is a security checkpoint.

| ID | Requirement | Priority |
|----|-------------|----------|
| LIFE-001 | Session TTL — measured from last request; agent expires if idle | MUST |
| LIFE-002 | Max lifetime — measured from last activation; caps continuous use | MUST |
| LIFE-003 | Absolute lifetime — measured from creation; hard limit, agent permanently revoked | MUST |
| LIFE-004 | `POST /asap/agent/reactivate` — reactivate expired agent; escalated capabilities decay to host defaults | MUST |
| LIFE-005 | Each authenticated request extends session TTL (`last_used_at` update) | MUST |
| LIFE-006 | Configurable defaults per server (e.g., 30min session, 24h max, 7d absolute) | SHOULD |

---

### 4.4 Approval Flows (P1)

Protocol-level user consent for agent registration and capability escalation.

| ID | Requirement | Priority |
|----|-------------|----------|
| APPR-001 | Device Authorization (RFC 8628) — baseline; returns `verification_uri` + `user_code` | MUST |
| APPR-002 | Client polls `GET /asap/agent/status` at `interval` until status changes from `pending` | MUST |
| APPR-003 | CIBA support — server pushes notification; returns `binding_message` | SHOULD |
| APPR-004 | Approval object schema in registration/reactivation responses when consent required | MUST |
| APPR-005 | Integration with existing A2H infrastructure as approval channel | SHOULD |
| APPR-006 | `preferred_method` hint in registration request (server decides final method) | SHOULD |

---

### 4.5 Self-Authorization Prevention (P1)

Agents controlling the browser can navigate to approval URLs and auto-approve. Mitigations required.

| ID | Requirement | Priority |
|----|-------------|----------|
| SELF-001 | Fresh authentication requirement on approval endpoints (stale sessions rejected) | MUST |
| SELF-002 | WebAuthn integration for high-risk capability approval (`userVerification: "required"`) | SHOULD |
| SELF-003 | CIBA preference when agent controls browser (approval on separate device) | SHOULD |
| SELF-004 | Documented threat model in security considerations | MUST |
| SELF-005 | `freshSessionWindow` configuration (default: 300 seconds) | SHOULD |

---

### 4.6 Streaming/SSE (P1)

Builds on: Q5 (`stream_uri` for large payloads), Q16 (streaming does not require ack), `tech-stack-decisions.md` §2.3 (WebSocket rationale).

| ID | Requirement | Priority |
|----|-------------|----------|
| STR-001 | `POST /asap/stream` — accepts JSON-RPC request, returns `text/event-stream` response | MUST |
| STR-002 | New payload type `TaskStream` with incremental chunks (text, data, progress) | MUST |
| STR-003 | `ASAPClient.stream()` — async generator consuming SSE events | MUST |
| STR-004 | Each SSE event is a valid `Envelope[TaskStream]` with correlation_id | MUST |
| STR-005 | Stream termination event with final status (completed/failed) | MUST |
| STR-006 | WebSocket streaming continues as bidirectional alternative (SSE is additive) | MUST |
| STR-007 | Streaming responses do NOT require MessageAck (per Q16 decision) | MUST |
| STR-008 | Content-Type negotiation: client sends `Accept: text/event-stream` for streaming | SHOULD |

**SSE Event Format**:
```
event: task_stream
data: {"id":"...","payload_type":"task_stream","payload":{"chunk":"partial result...","progress":0.5,"final":false}}

event: task_stream
data: {"id":"...","payload_type":"task_stream","payload":{"chunk":"final result","progress":1.0,"final":true,"status":"completed"}}
```

---

### 4.7 Error Taxonomy Evolution (P1)

Builds on: ADR-012 (`docs/adr/`) defines `ASAPError` with categories `asap:protocol`, `asap:routing`, `asap:capability`, `asap:execution`, `asap:resource`, `asap:security`. Q7 (`decision-records/02-protocol.md`) documents the same taxonomy.

This is an EVOLUTION of the existing hierarchy, not a rewrite.

| ID | Requirement | Priority |
|----|-------------|----------|
| ERR-001 | `RecoverableError` and `FatalError` subclasses of `ASAPError` | MUST |
| ERR-002 | Recovery hints in error `data` field: `retry_after_ms`, `alternative_agents[]`, `fallback_action` | MUST |
| ERR-003 | ASAP-specific numeric codes mapped to JSON-RPC range (-32000 to -32099) | MUST |
| ERR-004 | All existing error classes classified as Recoverable or Fatal | MUST |
| ERR-005 | Error code registry document (public, like HTTP status codes) | SHOULD |
| ERR-006 | `ASAPClient` auto-retry on `RecoverableError` with `retry_after_ms` hint | SHOULD |

**Error Code Ranges**:
```
-32000 to -32009: Protocol errors (invalid version, malformed envelope)
-32010 to -32019: Routing errors (agent not found, endpoint unreachable)
-32020 to -32029: Capability errors (unsupported skill, version mismatch)
-32030 to -32039: Execution errors (timeout, overloaded, task failed)
-32040 to -32049: Resource errors (quota exceeded, storage full)
-32050 to -32059: Security errors (auth failed, token expired, forbidden)
```

---

### 4.8 Unified Versioning (P1)

Builds on: ADR-016 (`docs/adr/`) defines SemVer + `asap_version` + contract tests. Q6 (`decision-records/05-product-strategy.md`) proposes Major.CalVer hybrid. There is no ADR reconciling the two.

**Requires new ADR** before implementation.

| ID | Requirement | Priority |
|----|-------------|----------|
| VER-001 | `ASAP-Version` header in all HTTP requests and responses | MUST |
| VER-002 | Content negotiation: client sends supported versions, server responds with best match | MUST |
| VER-003 | Backward compatibility: server accepts `ASAP-Version: 2.1` and responds in that format | MUST |
| VER-004 | Manifest `supported_versions` field: `["2.1", "2.2"]` | MUST |
| VER-005 | Default behavior when no header: assume current version | MUST |
| VER-006 | Contract tests expanded to cover version negotiation scenarios | MUST |
| VER-007 | Resolve SemVer (library) vs protocol version numbering in a unified ADR | MUST |

---

### 4.9 Async Protocol Resolution (P1)

Builds on: `tech-stack-decisions.md` §5.3 documented 3 options (keep sync, evolve to async, dual protocol). Decision was deferred to CP-1 (post-v1.1) and never resolved. v2.1.1 added `save_async`/`get_async` to `SQLiteSnapshotStore` but the formal `Protocol` remains sync.

| ID | Requirement | Priority |
|----|-------------|----------|
| ASYNC-001 | `AsyncSnapshotStore` Protocol (runtime-checkable) with async methods | MUST |
| ASYNC-002 | `AsyncMeteringStore` Protocol with async methods | MUST |
| ASYNC-003 | `AsyncSLAStorage` Protocol with async methods | SHOULD |
| ASYNC-004 | Existing sync Protocols remain for backward compatibility (deprecated) | MUST |
| ASYNC-005 | `create_async_snapshot_store()` factory function | MUST |
| ASYNC-006 | Deprecation warnings on sync Protocol usage | SHOULD |

---

### 4.10 A2H Integration Completion (P1)

Pending commits from tasks-a2h-integration.md: 1.4, 2.5, 3.7, 4.4, 5.7.

| ID | Requirement | Priority |
|----|-------------|----------|
| A2H-001 | All pending A2H commits merged and passing CI | MUST |
| A2H-002 | A2H integration documented in SDK guides | MUST |
| A2H-003 | Example `a2h_approval` complete and functional | MUST |

---

### 4.11 Batch Operations (P2)

Builds on: ADR-003 (`docs/adr/`) chose JSON-RPC 2.0, which natively supports batch requests (array of objects). Mentioned as "future" in the original decision.

| ID | Requirement | Priority |
|----|-------------|----------|
| BATCH-001 | `POST /asap` accepts JSON array of Request objects (JSON-RPC 2.0 batch) | MUST |
| BATCH-002 | Response is JSON array of Response objects (matching by id) | MUST |
| BATCH-003 | Rate limiting counts batch as N individual requests | MUST |
| BATCH-004 | `ASAPClient.batch()` method for sending multiple requests | SHOULD |
| BATCH-005 | Batch size limit (configurable, default 50) | SHOULD |

---

### 4.12 Compliance Harness v2 (P2)

Builds on: Original harness (v1.2 T3) covers handshake, schema, state machine.

| ID | Requirement | Priority |
|----|-------------|----------|
| COMP-001 | Streaming compliance checks (SSE endpoint, event format, termination) | MUST |
| COMP-002 | Error handling checks (RecoverableError/FatalError classification, recovery hints) | MUST |
| COMP-003 | Version negotiation checks (ASAP-Version header, backward compat) | MUST |
| COMP-004 | Batch checks (array request/response, size limits) | SHOULD |
| COMP-005 | Exportable compliance report (JSON format with score) | SHOULD |
| COMP-006 | CLI: `asap compliance-check --url https://agent.example.com` | COULD |

---

### 4.13 Audit Logging (P2)

Kept from original v2.2 PRD. Originally v1.3 E4, deferred to v2.1+ (deferred-backlog.md §3).

| ID | Requirement | Priority |
|----|-------------|----------|
| AUD-001 | Append-only, tamper-evident audit log (hash chain) | MUST |
| AUD-002 | Log all protocol write operations (task creation, state transitions, delegations) | MUST |
| AUD-003 | `AuditStore` Protocol following SnapshotStore pattern | MUST |
| AUD-004 | `GET /audit?urn=&start=&end=` — query audit log by agent URN and time range | SHOULD |
| AUD-005 | Export audit log as JSON | COULD |

---

## 5. Non-Goals (Out of Scope)

| Feature | Reason | When |
|---------|--------|------|
| Delegated/Autonomous mode formalization | Identity foundation needed first | v2.3 |
| Runtime capability escalation | Requires capability model stable | v2.3 |
| TypeScript SDK | Requires stable identity/auth API | v2.3 |
| Intent-based directory search | Requires Registry API Backend | v2.3 |
| Registry API Backend (PostgreSQL) | Trigger not met (500+ agents) | v2.3 |
| Auto-Registration | Depends on Registry API Backend | v2.3 |
| DeepEval Intelligence Layer | Trigger not met (user demand) | v2.3+ (conditional) |
| Orchestration Primitives | Complex; requires streaming first | v2.3 |
| OpenAPI adapter | Requires stable capability model | v2.4 |
| Economy Settlement / Billing | No live transactions yet | v3.0 |
| Node.js / Go SDKs | Demand-driven | TBD |

---

## 6. Technical Considerations

### 6.1 Streaming Architecture

| Component | Choice | Rationale |
|-----------|--------|-----------|
| SSE Transport | `starlette.responses.StreamingResponse` | Native FastAPI support, no additional deps |
| Event Format | JSON-RPC envelope per event | Consistency with existing protocol |
| Client | `httpx.stream()` with async iteration | Already a dependency (ADR-008) |

### 6.2 Backward Compatibility

- All changes are **additive** — no existing endpoints or models are removed
- Version negotiation defaults to current version when no header is present
- Sync Protocols remain functional (deprecated, not removed)
- Existing error classes gain new attributes but maintain existing interface

### 6.3 New Dependencies

None required. All features use existing dependencies (FastAPI, httpx, Pydantic v2).

---

## 7. Success Metrics

| Metric | Target |
|--------|--------|
| Agent registration with own keypair | Host→Agent identity flow e2e operational |
| Capability grants with constraints | Constraint enforcement with violation reporting |
| Agent lifecycle clocks | Session TTL, max lifetime, reactivation working |
| Device Authorization approval | RFC 8628 consent flow e2e operational |
| Self-auth prevention | WebAuthn integration for sensitive capabilities |
| Streaming SSE functional with e2e tests | TaskStream end-to-end via HTTP and WebSocket |
| Error codes with recovery hints | All 6 existing categories with RecoverableError/FatalError |
| Version negotiation active | Client/Server negotiate v2.1 <-> v2.2 |
| AsyncSnapshotStore Protocol | Dual protocol implemented; sync deprecated |
| Compliance Harness v2 | Checks for identity, capabilities, streaming, errors, versioning, batch |
| A2H complete and integrated | All pending commits merged |
| Audit log operational | All write ops logged with hash chain |

---

## 8. Prerequisites

| Prerequisite | Source |
|-------------|--------|
| v2.1.1 Tech Debt & Security Cleared | Completed |
| A2H Integration 90% complete | v2.2 tasks (in progress) |
| ADR-identity (per-runtime-agent) created and accepted | New (this PRD, SD-12) |
| ADR-capabilities (constraint-based authz) created and accepted | New (this PRD, SD-13) |
| ADR-approval (Device Auth + CIBA + WebAuthn) created and accepted | New (this PRD, SD-14) |
| ADR-streaming created and accepted | New (this PRD) |
| ADR-versioning created and accepted | New (this PRD) |

---

## 9. Related Documents

- **Superseded PRD**: [prd-v2.2-scale.md](./prd-v2.2-scale.md) (marketplace scope deferred to v2.3)
- **Next Version**: [prd-v2.3-scale.md](./prd-v2.3-scale.md)
- **Previous Version**: [prd-v2.1-ecosystem.md](./prd-v2.1-ecosystem.md)
- **Deferred Backlog**: [deferred-backlog.md](../strategy/deferred-backlog.md)
- **Vision**: [vision-agent-marketplace.md](../strategy/vision-agent-marketplace.md)
- **Roadmap**: [roadmap-to-marketplace.md](../strategy/roadmap-to-marketplace.md)
- **Error Taxonomy**: [ADR-012](../../../docs/adr/ADR-012-error-taxonomy.md)
- **Versioning Policy**: [ADR-016](../../../docs/adr/ADR-016-versioning-policy.md)
- **JSON-RPC Binding**: [ADR-003](../../../docs/adr/ADR-003-jsonrpc20-binding.md)

---

## Change Log

| Date | Version | Change |
|------|---------|--------|
| 2026-03-13 | 1.0.0 | Initial DRAFT — strategic review re-scoped v2.2 from "Scale & Registry" to "Protocol Hardening". Marketplace items deferred to v2.3 (triggers not met). |
| 2026-03-20 | 2.0.0 | **Identity & Auth Hardening**: Added §4.1–4.5 (Per-Runtime-Agent Identity, Capability-Based Authorization, Agent Lifecycle, Approval Flows, Self-Authorization Prevention). Renumbered existing sections to §4.6–4.13. Updated goals, user stories, non-goals, success metrics, and prerequisites. |
| 2026-04-17 | 2.1.0 | **Status update to SHIPPED**. v2.2.0 released on 2026-04-15. Delivery confirmed against PRs #92, #102, #105, #106, #110, #115, #121, #122. Carry-over backlog (small): SELF-002 WebAuthn real implementation (SHOULD), COMP-006 `asap compliance-check` CLI subcommand (COULD), AUD-005 audit export CLI (COULD) → candidates for v2.2.1 patch or fold into the next minor release. |
