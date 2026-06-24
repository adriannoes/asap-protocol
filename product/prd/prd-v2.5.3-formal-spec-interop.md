# PRD: ASAP Protocol v2.5.3 — Formal Spec & Interop

> **Product Requirements Document**
>
> **Version**: 2.5.3
> **Status**: PLANNED
> **Created**: 2026-03-20 (origin in `prd-v2.4-adoption.md`); **rescoped**: 2026-06-22
> **Parent train**: [prd-v2.5-roadmap.md](./prd-v2.5-roadmap.md)
> **Predecessor**: [prd-v2.5.2-distribution-loop.md](./prd-v2.5.2-distribution-loop.md)
> **Successor**: [prd-v3.0-economy.md](./prd-v3.0-economy.md)

---

## 1. Purpose

v2.5.3 closes the **standards-track loop** deferred since v2.3: formal RFC-style specification, capability-aware introspection, privacy considerations, and thin cross-protocol compatibility — **after** MCP Auth Bridge (v2.5.0) stabilizes the MCP integration surface.

---

## 2. Goals

| Goal | Metric | Priority |
|------|--------|----------|
| Formal specification | Published at `docs.asap-protocol.com/specification` | P1 |
| Capability-Aware Introspection | RFC 7662-style endpoint operational | P2 |
| Privacy spec | Formal Privacy Considerations section | P2 |
| Cross-protocol interop | ≥1 adapter + interoperability guide | P3 |

---

## 3. Functional requirements

### 3.1 Formal ASAP Specification (P1)

| ID | Requirement | Priority |
|----|-------------|----------|
| SPEC-001 | Complete spec: identity, registration, capabilities, approval, lifecycle, transport, discovery | MUST |
| SPEC-002 | RFC 2119 conformance keywords | MUST |
| SPEC-003 | Data models: Host, Agent, Capability Grant, Envelope | MUST |
| SPEC-004 | Authentication flows (Host JWT, Agent JWT, algorithms) | MUST |
| SPEC-005 | Error format + error code registry | MUST |
| SPEC-006 | Security considerations | MUST |
| SPEC-007 | Privacy considerations (see §3.3) | MUST |
| SPEC-008 | Published at `docs.asap-protocol.com/specification` | SHOULD |
| SPEC-009 | MCP Auth Bridge section referencing v2.5.0 implementation | SHOULD |

### 3.2 Capability-Aware Introspection (P2)

| ID | Requirement | Priority |
|----|-------------|----------|
| INTRO-001 | `POST /asap/agent/introspect` — agent JWT → active/inactive + compact grants | MUST |
| INTRO-002 | Response: `agent_id`, `host_id`, `user_id`, `agent_capability_grants`, `mode` | MUST |
| INTRO-003 | Compact grants only (capability + status) | MUST |
| INTRO-004 | Endpoint protected (shared secret, mTLS, or IP restriction) | SHOULD |

### 3.3 Privacy Considerations (P2)

| ID | Requirement | Priority |
|----|-------------|----------|
| PRIV-001 | Host key correlation risk documentation | SHOULD |
| PRIV-002 | Data retention guidance for agent activity logs | SHOULD |
| PRIV-003 | Capability requests as behavioral signals | SHOULD |
| PRIV-004 | `reason` field PII sensitivity | SHOULD |

### 3.4 Cross-Protocol Compatibility (P3)

| ID | Requirement | Priority |
|----|-------------|----------|
| COMPAT-001 | Accept external agent JWTs → ASAP agent sessions | SHOULD |
| COMPAT-002 | Translate external capability grants → ASAP grants | SHOULD |
| COMPAT-003 | Discovery bridge: ASAP well-known alongside other protocol endpoints | SHOULD |
| COMPAT-004 | Interoperability guide for multi-protocol environments | MUST |
| COMPAT-005 | A2A Agent Card → ASAP Manifest mapping (runtime bridge or documented gateway) | SHOULD |

### 3.5 TypeScript OpenAPI Adapter (P3 — conditional)

Ship only if `@asap-protocol/openapi` did not land in v2.3:

| ID | Requirement | Priority |
|----|-------------|----------|
| TSOA-001 | TypeScript port of `asap.adapters.openapi` as `@asap-protocol/openapi` | SHOULD |
| TSOA-002 | API parity with Python `createFromOpenAPI(spec)` | SHOULD |

---

## 4. Non-goals

Same as v2.5 train — economy, federated registry, gRPC. MCP Auth Bridge is **not** in this PRD (shipped in v2.5.0).

---

## 5. Prerequisites

| Prerequisite | Source |
|-------------|--------|
| v2.5.0 MCP Auth Bridge shipped | Stable MCP adapter API for SPEC-009 |
| v2.5.1/v2.5.2 adoption learnings | Optional narrative inputs for spec examples |
| Identity/capability model stable | v2.2+ |

---

## 6. Related documents

- **MCP Auth Bridge**: [prd-v2.5.0-mcp-auth-bridge.md](./prd-v2.5.0-mcp-auth-bridge.md)
- **Legacy**: [prd-v2.4-adoption.md](./prd-v2.4-adoption.md)

---

## Change Log

| Date | Change |
|------|--------|
| 2026-06-22 | Split from `prd-v2.4-adoption.md` §4.2–4.6; renumbered to v2.5.3 |
