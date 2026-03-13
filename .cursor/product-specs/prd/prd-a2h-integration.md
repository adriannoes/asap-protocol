# PRD: A2H Protocol Integration — Agent-to-Human Communication

> **Product Requirements Document**
>
> **Version**: 1.1
> **Created**: 2026-03-10
> **Last Updated**: 2026-03-10
> **Target Release**: v2.2.0
> **External Spec**: [A2H Protocol v1.0](https://github.com/twilio-labs/Agent2Human)

---

## 1. Executive Summary

### 1.1 Purpose

This PRD defines the integration of the [A2H (Agent-to-Human) Protocol](https://github.com/twilio-labs/Agent2Human) into the ASAP Protocol ecosystem. A2H is a channel-agnostic protocol for agent-to-human communication covering notifications, data collection, authorization with cryptographic consent, escalation, and result reporting.

ASAP handles **Agent ↔ Agent** communication. A2H handles the **Agent → Human** "last mile." Together, they cover the full spectrum of agentic communication:

```
Agent A ──[ASAP]──▶ Agent B ──[A2H]──▶ Human (SMS/Email/Push/Voice)
                                  ◀──────── APPROVE / data
                         Agent B continues task
```

### 1.2 Strategic Context

The A2H protocol is early-stage (v1.0, 4 commits, 1 contributor) by Twilio Labs. Being an early integration partner provides:

- **Visibility**: ASAP listed as a referenced A2A protocol in the A2H ecosystem
- **Influence**: Shape A2H's interop standards while the protocol is still forming
- **Completeness**: ASAP agents gain a standardized way to reach humans during task execution
- **Ecosystem growth**: Twilio's developer reach (~300K+ monthly active developers) amplifies ASAP's discoverability

The A2H spec already includes a `links.a2a_thread` field for cross-referencing agent-to-agent protocol threads, and their v1.1 roadmap explicitly mentions "Agent framework integrations (OpenClaw, LangGraph, CrewAI)."

### 1.3 Relationship to A2H

ASAP is a **complement**, not a competitor:

| Dimension | ASAP | A2H |
|-----------|------|-----|
| Direction | Agent ↔ Agent | Agent → Human |
| Transport | JSON-RPC 2.0 (HTTP/WS) | REST API |
| State Machine | PENDING → RUNNING → COMPLETED | PENDING → SENT → WAITING_INPUT → ANSWERED |
| Identity | URN + Ed25519 signed manifests | DID + JWS signed messages |
| Discovery | `/.well-known/asap` | `/.well-known/a2h` |

---

## 2. Goals

| Goal | Metric | Priority |
|------|--------|----------|
| ASAP agents can request human approval via A2H gateways | E2E test: send AUTHORIZE → receive APPROVE | P0 |
| Zero new dependencies in `pyproject.toml` | No additions to `[project.dependencies]` or `[project.optional-dependencies]` | P0 |
| Protocol-agnostic HITL interface | `HumanApprovalProvider` Protocol usable without A2H | P0 |
| Functional example | Runnable example in `examples/a2h-approval/` | P1 |
| Community engagement | Issue opened on `twilio-labs/Agent2Human` with integration reference | P1 |

---

## 3. User Stories

### US-1: ASAP Agent Requests Human Approval
> As an **ASAP agent developer**, I want my agent to **request human approval via an A2H Gateway** (e.g., SMS, push notification) so that **high-stakes actions require explicit human consent before execution**.

**Acceptance Criteria:**
- Agent sends an AUTHORIZE intent to an A2H Gateway via `A2HClient`.
- Gateway delivers the request to the human via configured channel (SMS, email, etc.).
- Agent receives the human's response (APPROVE/DECLINE) via polling or webhook callback.
- Task resumes or aborts based on the decision.

### US-2: ASAP Agent Notifies Human
> As an **ASAP agent developer**, I want to **send fire-and-forget notifications to humans** (task completed, error occurred) so that **humans stay informed about agent activity**.

**Acceptance Criteria:**
- Agent sends an INFORM or RESULT intent via `A2HClient`.
- No response expected; method returns the `interaction_id` for tracking.

### US-3: ASAP Agent Collects Human Input
> As an **ASAP agent developer**, I want to **collect structured data from a human** (preferences, choices, form fields) so that **the agent can proceed with accurate human-provided information**.

**Acceptance Criteria:**
- Agent sends a COLLECT intent with typed components (TEXT, SELECT, etc.).
- Human fills the form via the A2H Gateway's UI.
- Agent receives structured data response.

### US-4: Custom HITL Provider
> As an **ASAP agent developer**, I want to **implement my own human-in-the-loop provider** (e.g., Slack, internal tool) so that **I'm not locked into A2H for human communication**.

**Acceptance Criteria:**
- `HumanApprovalProvider` is a Python `Protocol` (structural typing).
- `A2HApprovalProvider` is one concrete implementation.
- Developers can create custom providers without importing A2H code.

### US-5: Gateway Discovery
> As an **ASAP agent developer**, I want to **discover an A2H Gateway's capabilities before sending messages** so that **I know which channels and auth factors are available**.

**Acceptance Criteria:**
- `A2HClient.discover()` fetches `/.well-known/a2h` and returns typed `GatewayCapabilities`.
- Channels, factors, TTL, and auth methods are accessible as typed attributes.

---

## 4. Functional Requirements

### 4.1 A2H Client (`A2HClient`)

Lightweight async HTTP client wrapping the A2H REST API.

| ID | Requirement | Priority |
|----|-------------|----------|
| A2H-001 | `A2HClient(gateway_url, api_key?, oauth_token?)` — constructor with configurable auth | MUST |
| A2H-002 | `discover() -> GatewayCapabilities` — fetch `/.well-known/a2h` | MUST |
| A2H-003 | `inform(principal_id, body, channel?, ...) -> str` — send INFORM, return `interaction_id` | MUST |
| A2H-004 | `collect(principal_id, components, ...) -> A2HResponse` — send COLLECT, poll for response | MUST |
| A2H-005 | `authorize(principal_id, body, assurance?, ...) -> A2HResponse` — send AUTHORIZE, poll for response | MUST |
| A2H-006 | `escalate(principal_id, targets, ...) -> A2HResponse` — send ESCALATE, poll for response | SHOULD |
| A2H-007 | `send_result(principal_id, body, ...) -> str` — send RESULT, return `interaction_id` | MUST |
| A2H-008 | `get_status(interaction_id) -> InteractionStatus` — poll interaction state | MUST |
| A2H-009 | `cancel(interaction_id) -> bool` — cancel a pending interaction | SHOULD |
| A2H-010 | Polling with configurable interval and timeout for blocking methods (COLLECT, AUTHORIZE, ESCALATE) | MUST |
| A2H-011 | `links.a2a_thread` automatically populated with ASAP `conversation_id` when available | SHOULD |

> **Deferred**: Webhook callback registration (push-based instead of polling) deferred to follow-up. See Resolved Questions §12 Q1.

### 4.2 Pydantic Models

Typed models for the A2H protocol envelope, responses, and discovery.

| ID | Requirement | Priority |
|----|-------------|----------|
| MOD-001 | `A2HMessage` — full A2H message envelope (all intent types) | MUST |
| MOD-002 | `GatewayCapabilities` — discovery response from `/.well-known/a2h` | MUST |
| MOD-003 | `A2HResponse` — human RESPONSE message (decision, data, evidence) | MUST |
| MOD-004 | `InteractionStatus` — status polling response (state, timestamps) | MUST |
| MOD-005 | `IntentType` — enum: INFORM, COLLECT, AUTHORIZE, ESCALATE, RESULT | MUST |
| MOD-006 | `InteractionState` — enum: PENDING, SENT, WAITING_INPUT, ANSWERED, EXPIRED, CANCELLED, FAILED | MUST |
| MOD-007 | `ChannelBinding` — channel type + address + optional fallback | MUST |
| MOD-008 | `Component` — COLLECT form field (TEXT, SELECT, CHECKBOX, etc.) | MUST |
| MOD-009 | `AssuranceConfig` — assurance level + required authentication factors | SHOULD |
| MOD-010 | All models use `ConfigDict(extra="forbid")` per security standards | MUST |

### 4.3 Human-in-the-Loop Protocol (Decoupled)

Protocol-agnostic interface for human approval, placed in ASAP core (not in integrations).

| ID | Requirement | Priority |
|----|-------------|----------|
| HITL-001 | `HumanApprovalProvider` — Python `Protocol` with async `request_approval()` method | MUST |
| HITL-002 | `ApprovalResult` — Pydantic model with decision (APPROVE/DECLINE), data, evidence, timestamps | MUST |
| HITL-003 | `A2HApprovalProvider(HumanApprovalProvider)` — concrete implementation using `A2HClient` (AUTHORIZE + INFORM) | MUST |
| HITL-004 | `HumanApprovalProvider` importable from `asap.handlers` (core), not `asap.integrations` | MUST |
| HITL-005 | `A2HApprovalProvider` importable from `asap.integrations` (lazy) | MUST |

> **Decision**: HITL Protocol is **async-only** (`async def request_approval`). Matches ASAP's async-first architecture. See Resolved Questions §12 Q2.

### 4.4 Webhook Receiver — DEFERRED

> **Deferred to follow-up release.** Polling via `GET /v1/status/{id}` is sufficient for all v1 user stories. Webhook receiver (FastAPI router with HMAC-SHA256 signature verification and idempotency) will be added when real demand for push-based responses appears. See Resolved Questions §12 Q1.

---

## 5. Non-Goals (Out of Scope)

| Non-Goal | Rationale |
|----------|-----------|
| Building a full A2H Gateway | Requires channel delivery infrastructure (SMS, push, voice), WebAuthn/passkey verification, and a full state machine. This is Twilio's responsibility, not ASAP's. Scope: ~2000+ lines, paid channel APIs. |
| Channel adapters (SMS, email, push) | Gateway responsibility. ASAP is a client, not a delivery platform. |
| WebAuthn/Passkey verification | Evidence verification is the gateway's job. ASAP trusts the gateway's JWS signature. |
| A2H discovery endpoint (`/.well-known/a2h`) on ASAP servers | ASAP servers expose `/.well-known/asap`, not A2H. No endpoint collision. |
| Mandating A2H as the only HITL solution | `HumanApprovalProvider` Protocol enables any implementation (Slack, email, custom UI). |
| JWS signature verification of A2H responses | Deferred — TLS provides sufficient transport trust for v1. See Resolved Questions §12 Q3. |
| Webhook receiver (push-based responses) | Deferred — polling is sufficient for v1. See Resolved Questions §12 Q1. |

---

## 6. Design Considerations

### 6.1 Architecture: Client-Only (Not Gateway)

ASAP acts as an **A2H client with optional webhook receiver**, not a gateway:

```
┌───────────────────────────────────────────────────┐
│  ASAP Agent Handler                               │
│                                                   │
│  1. Receives ASAP TaskRequest                     │
│  2. Needs human approval                          │
│  3. Uses HumanApprovalProvider (async)            │
│     ├── A2HApprovalProvider (A2H Gateway)         │
│     ├── SlackApprovalProvider (custom)            │
│     └── EmailApprovalProvider (custom)            │
│  4. Resumes task based on decision                │
└───────────────────────────────────────────────────┘
         │ POST /v1/intent          ▲ GET /v1/status/{id}
         ▼ (send AUTHORIZE)        │ (poll until ANSWERED)
┌─────────────────────┐            │
│  A2H Gateway        │────────────┘
│  (Twilio/3rd-party) │
└─────────────────────┘
         │
         ▼
    📱 Human (SMS/Push/Email)
```

### 6.2 Why Not a Gateway?

| Factor | Client-Only | Full Gateway |
|--------|-------------|--------------|
| Scope | ~250-300 lines | ~2000+ lines |
| Dependencies | None (uses existing httpx) | Channel SDKs, WebAuthn libs, JWS signing |
| Infrastructure | None | Paid APIs (Twilio SMS, SendGrid, etc.) |
| Maintenance | Low | High (security-critical, multi-channel) |
| Strategic fit | Complement | Compete with Twilio |
| Adoption doors | Same (agents connect to any gateway) | More (ASAP itself is a gateway) |
| Time to implement | ~2-3 days | ~2-4 weeks |

The client approach opens the **same adoption doors**: any ASAP agent can connect to any A2H Gateway (Twilio's or third-party). The gateway approach would mean competing with Twilio on channel delivery — their core business.

### 6.3 Cross-Protocol Linking

A2H messages include a `links` object with an `a2a_thread` field. ASAP's `A2HClient` should automatically populate this with the ASAP `conversation_id` when available, enabling bidirectional traceability:

```json
{
  "type": "AUTHORIZE",
  "links": {
    "a2a_thread": "asap:conversation/conv-abc123"
  }
}
```

---

## 7. Technical Considerations

### 7.1 Zero New Dependencies

A2H is a REST protocol. ASAP already depends on:
- `httpx` — HTTP client for A2H API calls
- `pydantic` — models for A2H envelope, responses, capabilities

No new entries in `pyproject.toml`. This is the key architectural advantage of integrating with a REST protocol vs. a framework-specific SDK.

### 7.2 File Structure

| File | Purpose | Lines (est.) |
|------|---------|-------------|
| `src/asap/integrations/a2h.py` | `A2HClient`, Pydantic models, `A2HApprovalProvider` | ~200 |
| `src/asap/handlers/hitl.py` | `HumanApprovalProvider` Protocol (async), `ApprovalResult` model | ~40 |
| `tests/integrations/test_a2h.py` | Unit tests with mocked gateway responses (`respx`) | ~200 |
| `tests/handlers/test_hitl.py` | Unit tests for HITL Protocol conformance | ~60 |
| `examples/a2h-approval/README.md` | Usage guide + instructions for Twilio demo gateway | ~50 |
| `examples/a2h-approval/example.py` | E2E example: ASAP agent requests human approval (mock) | ~80 |

**Total estimated**: ~630 lines (under 300 per file). Reduced from ~680 by deferring webhook receiver.

### 7.3 Integration Pattern

Follows established patterns from existing integrations:

| Aspect | Existing (LangChain) | A2H Integration |
|--------|---------------------|-----------------|
| Location | `integrations/langchain.py` | `integrations/a2h.py` |
| Lazy export | `__getattr__` in `__init__.py` | Same pattern |
| Core dependency | `MarketClient`, `ResolvedAgent` | `httpx` (already in core) |
| External dependency | `langchain-core` (optional) | None |
| Pattern | Tool adapter (wraps ASAP as framework tool) | Client adapter (wraps A2H API for ASAP agents) |

### 7.4 Authentication

`A2HClient` supports the three auth methods from the A2H spec:

| Method | Implementation |
|--------|---------------|
| API Key | `X-A2H-API-Key` header |
| OAuth 2.0 Bearer | `Authorization: Bearer <token>` header |
| No Auth (dev only) | No auth headers sent |

Auth credentials are passed via constructor, never hardcoded. Follows ASAP security standards (env vars, no secrets in code).

### 7.5 Polling Strategy

For blocking operations (AUTHORIZE, COLLECT, ESCALATE), `A2HClient` polls `GET /v1/status/{id}` with:

- Default interval: 2 seconds
- Default timeout: 300 seconds (matches A2H's default `ttl_sec`)
- Both configurable per-call
- Returns `A2HResponse` on success, raises `TimeoutError` on expiry

Future enhancement: webhook-based push eliminates polling (deferred to follow-up release).

---

## 8. Community Engagement Strategy

### 8.1 Approach: Complement, Not Coupling

The engagement with Twilio Labs follows a **complement** strategy — demonstrating that ASAP + A2H together cover the full Agent ↔ Human ↔ Agent communication spectrum, without creating hard dependencies in either direction.

### 8.2 Execution Plan

| Phase | Action | Timeline |
|-------|--------|----------|
| **Phase 1** | Implement A2H integration in ASAP (this PRD) | Sprint current |
| **Phase 2** | Open GitHub Issue on `twilio-labs/Agent2Human` | After Phase 1 merge |
| **Phase 3** | If Twilio shows interest, propose PR with `examples/asap-integration/` | After Phase 2 response |

### 8.3 GitHub Issue Template

**Title**: `[Integration] ASAP Protocol — Agent-to-Agent complement for A2H`

**Content outline**:
1. Introduce ASAP Protocol (A2A complement to A2H)
2. Demonstrate the combined flow: Agent A → [ASAP] → Agent B → [A2H] → Human
3. Link to ASAP's `A2HClient` integration (our repo)
4. Reference `links.a2a_thread` as the natural cross-protocol binding
5. Offer to contribute an `examples/asap-integration/` directory to their repo
6. Emphasize: no coupling, pure complementarity of purpose

### 8.4 Value Proposition for Twilio

- A2H currently has no agent-to-agent story. ASAP fills that gap.
- A2H's `links.a2a_thread` field already anticipates A2A integration — ASAP provides a concrete binding.
- ASAP's existing integrations (LangChain, CrewAI, LlamaIndex, SmolAgents, PydanticAI) bring A2H into those ecosystems transitively.
- An ASAP agent using A2H doesn't require Twilio to change anything — it's a client-side integration.

---

## 9. Success Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| Integration code merged | PR approved and merged | GitHub |
| Unit test coverage | ≥ 90% on `a2h.py` and `hitl.py` | `pytest --cov` |
| Example runs E2E | `examples/a2h-approval/` executes without errors against mock gateway | CI |
| GitHub Issue opened | Issue created on `twilio-labs/Agent2Human` | Manual |
| Twilio engagement | Response on GitHub Issue within 30 days | Manual |

---

## 10. Testing Plan

### 10.1 Unit Tests (`tests/integrations/test_a2h.py`)

| Test | Description |
|------|-------------|
| `test_discover_capabilities` | Mock `/.well-known/a2h` response, verify `GatewayCapabilities` model |
| `test_inform_sends_correct_payload` | Verify INFORM intent envelope structure |
| `test_authorize_polls_until_answered` | Mock PENDING → WAITING_INPUT → ANSWERED, verify polling logic |
| `test_authorize_timeout_raises` | Mock WAITING_INPUT that never resolves, verify `TimeoutError` |
| `test_collect_returns_structured_data` | Verify COLLECT response maps to typed dict |
| `test_cancel_interaction` | Mock cancel endpoint, verify success/failure |
| `test_api_key_auth_header` | Verify `X-A2H-API-Key` header sent |
| `test_oauth_bearer_header` | Verify `Authorization: Bearer` header sent |
| `test_a2a_thread_link_populated` | Verify `links.a2a_thread` set when `conversation_id` provided |
| `test_models_forbid_extra_fields` | Verify `ConfigDict(extra="forbid")` on all models |

### 10.2 Unit Tests (`tests/handlers/test_hitl.py`)

| Test | Description |
|------|-------------|
| `test_protocol_conformance` | Verify `A2HApprovalProvider` satisfies `HumanApprovalProvider` Protocol |
| `test_custom_provider` | Create a mock provider, verify it satisfies the Protocol |
| `test_approval_result_model` | Verify `ApprovalResult` serialization/deserialization |

### 10.3 Example Validation

The `examples/a2h-approval/example.py` runs against a mock A2H Gateway (httpx mock or local test server) in CI to validate the E2E flow.

---

## 11. Implementation Order

```
┌─────────────────────────────────────────────────────────────┐
│  STEP 1 — HITL Protocol (core, decoupled)                   │
│  Files: src/asap/handlers/hitl.py                           │
│  Effort: ~0.5 day                                           │
│  ⬇                                                         │
│  STEP 2 — A2H Models + Client                               │
│  Files: src/asap/integrations/a2h.py                        │
│  Effort: ~1-2 days                                          │
│  ⬇                                                         │
│  STEP 3 — Tests                                             │
│  Files: tests/integrations/test_a2h.py,                     │
│         tests/handlers/test_hitl.py                         │
│  Effort: ~1 day                                             │
│  ⬇                                                         │
│  STEP 4 — Example                                           │
│  Files: examples/a2h-approval/                              │
│  Effort: ~0.5 day                                           │
│  ⬇                                                         │
│  STEP 5 — Lazy exports + Documentation                      │
│  Files: src/asap/integrations/__init__.py, AGENTS.md        │
│  Effort: ~0.5 day                                           │
│  ⬇                                                         │
│  STEP 6 — Community Engagement                              │
│  Action: Open issue on twilio-labs/Agent2Human              │
│  Effort: ~0.5 day                                           │
└─────────────────────────────────────────────────────────────┘

```

---

## 12. Resolved Questions

| # | Question | Decision | Rationale |
|---|----------|----------|-----------|
| 1 | Should `A2HClient` support webhook callback (WH-001–WH-004) in v1? | **Deferred to follow-up.** | Polling resolves all user stories. Webhook adds HMAC verification, idempotency, and router factory complexity without unblocking new scenarios. Ship the client clean first; add webhook when real demand appears. |
| 2 | Should the HITL Protocol support async-only, sync-only, or both? | **Async-only.** | ASAP is async-first (FastAPI, aiosqlite, httpx async). Handlers are async. Callers who need sync can wrap with `asyncio.run()` on their side. |
| 3 | Should we verify A2H Gateway JWS signatures on RESPONSE messages? | **Deferred to future version.** | JWS verification requires JWKS fetching and key parsing — enterprise-grade security that adds significant complexity. TLS (HTTPS) provides sufficient transport-level trust for v1. |
| 4 | Should the example use a real A2H Gateway or a mock? | **Mock for CI + instructions for real gateway.** | Twilio's demo requires Node.js — not suitable as a CI dependency. Mock via `respx` ensures deterministic tests. README includes step-by-step instructions for running against Twilio's local demo. |
| 5 | Should `A2HApprovalProvider` support all 5 intent types or only AUTHORIZE? | **AUTHORIZE + INFORM in v1.** | AUTHORIZE is the core approval flow. INFORM is fire-and-forget (zero extra complexity) and useful for notifying humans of results post-approval. COLLECT, ESCALATE, and RESULT remain accessible via `A2HClient` directly. |

---

## 13. Dependencies

| Dependency | Type | Notes |
|------------|------|-------|
| `httpx` | Existing | Already in `[project.dependencies]` — used for A2H API calls |
| `pydantic` | Existing | Already in `[project.dependencies]` — used for A2H models |
| A2H Gateway (external) | Runtime | Any A2H-compliant gateway (Twilio demo or third-party) |
| v2.2.0 tech debt cleared | Internal | [tasks-v2.2.0-tech-debt.md](../../dev-planning/tasks/v2.2.0/tasks-v2.2.0-tech-debt.md) |

---

## 14. Related Documents

- **A2H Protocol Spec**: [a2h_framework.md](https://github.com/twilio-labs/Agent2Human/blob/main/a2h_framework.md)
- **A2H OpenAPI Schema**: [a2h-protocol.yaml](https://github.com/twilio-labs/Agent2Human/blob/main/a2h-protocol.yaml)
- **ASAP v2.2 PRD**: [prd-v2.2-scale.md](./prd-v2.2-scale.md)
- **Tech Stack**: [tech-stack-decisions.md](../../dev-planning/architecture/tech-stack-decisions.md)
- **Existing Integrations Pattern**: `src/asap/integrations/langchain.py` (reference implementation)

---

## Change Log

| Date | Version | Change |
|------|---------|--------|
| 2026-03-10 | 1.0.0 | Initial DRAFT — A2H integration PRD with HITL Protocol, client-only architecture, and community engagement strategy |
| 2026-03-10 | 1.1.0 | Closed all Open Questions: webhook deferred, HITL async-only, JWS deferred, mock for CI, AUTHORIZE+INFORM for v1. Updated scope, diagrams, and estimates accordingly. |
