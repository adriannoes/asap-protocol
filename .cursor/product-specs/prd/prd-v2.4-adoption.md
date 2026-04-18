# PRD: ASAP Protocol v2.4.0 — Spec & Interop

> **Product Requirements Document**
>
> **Version**: 2.4.0
> **Status**: VISION DRAFT (rescoped 2026-04-17)
> **Created**: 2026-03-20
> **Last Updated**: 2026-04-17
>
> **Scope change (2026-04-17)**: OpenAPI Adapter (originally §4.1) was **pulled forward into v2.3.0** (Adoption Multiplier) to attack the missing 500-agent trigger directly. v2.4 now centers on **MCP Auth Bridge**, **Formal ASAP Specification**, **Cross-Protocol Compatibility**, and **Capability-Aware Introspection (RFC 7662)** + **Privacy Considerations spec** carried over from v2.3.

---

## 1. Executive Summary

### 1.1 Purpose

v2.4.0 finalizes ASAP as a **standardizable** protocol and bridges it to adjacent ecosystems. With identity/auth hardened (v2.2), zero-code onboarding shipped (v2.3 OpenAPI Adapter), and TypeScript adoption underway (v2.3 SDK), v2.4 closes the standards-track loop and unblocks MCP integration.

This release delivers:
- **MCP Auth Bridge**: ASAP identity layer for MCP servers (solve MCP's auth gap)
- **Cross-Protocol Compatibility**: Thin adapters for interop with other agent auth protocols
- **Formal ASAP Specification Document**: RFC-style specification for standardization track
- **Capability-Aware Introspection (RFC 7662)**: carried over from v2.3 deferral list
- **Privacy Considerations spec**: formal section in the spec, carried over from v2.3 deferral list
- **TypeScript OpenAPI adapter package** *(if `@asap-protocol/openapi` did not ship in v2.3)*

> [!CAUTION]
> **Triggers required before starting this PRD**:
> 1. v2.3 Adoption Multiplier released (OpenAPI Adapter, TypeScript SDK, Auto-Registration shipped and stable)
> 2. MCP ecosystem growth warrants auth bridge investment (3+ MCP server operators asking for ASAP-style auth, or MCP working group reaching out)
> 3. Standards engagement signals (1+ standards body discussing agent protocol convergence)

### 1.2 Strategic Context

v2.4 is the **adoption multiplier** — it makes ASAP accessible to services that would never manually implement a protocol, and ensures ASAP can interoperate with adjacent standards.

| Layer | v2.4 Investment |
|-------|----------------|
| Integration (Adapters) | **Primary focus** — MCP Auth Bridge, cross-protocol |
| Specification | **Primary focus** — Formal RFC-style document + Privacy Considerations |
| Identity | Capability-Aware Introspection (RFC 7662) |
| Protocol | No new protocol features (stabilization) |
| Marketplace | No changes |

---

## 2. Goals

| Goal | Metric | Priority |
|------|--------|----------|
| MCP auth solved | ASAP identity layer operational for 3+ MCP servers | P1 |
| Formal specification | Complete spec document published at `docs.asap-protocol.com/specification` | P1 |
| Capability-Aware Introspection | RFC 7662 endpoint + reference resource server | P2 |
| Privacy spec | Formal Privacy Considerations section in spec | P2 |
| Cross-protocol interop | Adapter for at least 1 other agent protocol | P3 |

---

## 3. User Stories

### API Provider (OpenAPI)
> As an **API provider with an existing OpenAPI spec**, I want to **auto-derive ASAP capabilities from my spec** so that **agents can discover and use my API without manual capability definitions**.

### MCP Server Developer
> As an **MCP server developer**, I want to **use ASAP's identity and capability model for my MCP tools** so that **each agent connecting to my MCP server has its own identity and scoped permissions**.

### Standards Body Reviewer
> As a **standards body reviewer**, I want to **read a formal ASAP specification** so that **I can evaluate it for adoption or standardization**.

### Platform Integrator (Cross-Protocol)
> As a **platform integrator**, I want to **accept both ASAP and other agent protocol tokens on my endpoints** so that **I can serve agents from different ecosystems**.

---

## 4. Functional Requirements

> **Note (2026-04-17)**: OpenAPI Adapter (formerly §4.1) shipped in **v2.3 §4.1** as part of the Adoption Multiplier rescope. This PRD now opens with MCP Auth Bridge.

### 4.1 MCP Auth Bridge (P1) — promoted from P2

ASAP identity and capability model as the auth layer for MCP servers.

| ID | Requirement | Priority |
|----|-------------|----------|
| MCP-AUTH-001 | MCP tool calls authenticated with ASAP Agent JWTs | MUST |
| MCP-AUTH-002 | MCP tools mapped to ASAP capabilities (tool name → capability name) | MUST |
| MCP-AUTH-003 | Per-agent identity for MCP connections (not per-application) | MUST |
| MCP-AUTH-004 | Capability grants enforced before MCP tool execution | MUST |
| MCP-AUTH-005 | Python middleware: `asap.adapters.mcp.auth_middleware` | MUST |
| MCP-AUTH-006 | TypeScript middleware: `@asap-protocol/mcp-auth` | SHOULD |
| MCP-AUTH-007 | Discovery: MCP server exposes `/.well-known/asap/manifest.json` alongside MCP endpoints | SHOULD |

---

### 4.2 Cross-Protocol Compatibility (P3)

Thin adapters for interoperability with other agent authentication protocols.

| ID | Requirement | Priority |
|----|-------------|----------|
| COMPAT-001 | Translation layer: accept external agent JWTs and map to ASAP agent sessions | SHOULD |
| COMPAT-002 | Capability mapping: translate external capability grants to ASAP grants | SHOULD |
| COMPAT-003 | Discovery bridge: serve ASAP well-known alongside other protocol discovery endpoints | SHOULD |
| COMPAT-004 | Documentation: interoperability guide for multi-protocol environments | MUST |

---

### 4.3 Formal ASAP Specification Document (P1) — promoted from P2

RFC-style specification covering the complete ASAP protocol.

| ID | Requirement | Priority |
|----|-------------|----------|
| SPEC-001 | Complete specification covering: identity, registration, capabilities, approval, lifecycle, transport, discovery | MUST |
| SPEC-002 | Conformance requirements using RFC 2119 keywords (MUST, SHOULD, MAY) | MUST |
| SPEC-003 | Data model definitions (Host, Agent, Capability Grant, Envelope) | MUST |
| SPEC-004 | Authentication flows (Host JWT, Agent JWT, verification algorithms) | MUST |
| SPEC-005 | Error format and complete error code registry | MUST |
| SPEC-006 | Security considerations section (key management, replay, SSRF, self-auth) | MUST |
| SPEC-007 | Privacy considerations section | MUST |
| SPEC-008 | Published at `docs.asap-protocol.com/specification` | SHOULD |

---

### 4.4 Capability-Aware Introspection (P2) — carried over from v2.3 deferral

Extend token introspection for resource servers that validate agent JWTs (RFC 7662 style).

| ID | Requirement | Priority |
|----|-------------|----------|
| INTRO-001 | `POST /asap/agent/introspect` — accepts agent JWT, returns active/inactive + compact grants | MUST |
| INTRO-002 | Response includes `agent_id`, `host_id`, `user_id`, `agent_capability_grants`, `mode` | MUST |
| INTRO-003 | Compact grants (capability + status only) — no input/output schemas | MUST |
| INTRO-004 | Endpoint protected with server-to-server auth (shared secret, mTLS, or IP restriction) | SHOULD |

---

### 4.5 Privacy Considerations Section (P2) — carried over from v2.3 deferral

Formal privacy section in the ASAP specification.

| ID | Requirement | Priority |
|----|-------------|----------|
| PRIV-001 | Document host key correlation risk (same keypair across servers enables tracking) | SHOULD |
| PRIV-002 | Data retention policy guidance for agent activity logs | SHOULD |
| PRIV-003 | Capability requests as behavioral signals — treat with same data protection as grants | SHOULD |
| PRIV-004 | Guidance on `reason` field sensitivity (may contain PII) | SHOULD |

---

### 4.6 TypeScript OpenAPI Adapter (P3 — only if not delivered in v2.3)

If `@asap-protocol/openapi` did not ship as part of v2.3 §4.1 OA-012, complete it here.

| ID | Requirement | Priority |
|----|-------------|----------|
| TSOA-001 | TypeScript port of `asap.adapters.openapi` published as `@asap-protocol/openapi` | SHOULD |
| TSOA-002 | Same API surface: `createFromOpenAPI(spec)` with default capabilities, approval strength, resolve headers | SHOULD |

---

## 5. Non-Goals (Out of Scope)

| Feature | Reason | When |
|---------|--------|------|
| Economy Settlement / Billing | v3.0 scope | v3.0 |
| ASAP Cloud | v3.0 scope | v3.0 |
| Crypto/DeFi settlement | v4.0+ (separate repo) | v4.0+ |
| Federated Registry | Centralized approach still validates | v3.x+ |
| gRPC adapter | Low demand | TBD |

---

## 6. Technical Considerations

### 6.1 OpenAPI Adapter Architecture

| Component | Choice | Rationale |
|-----------|--------|-----------|
| Spec parsing | `openapi-pydantic` (Python), `openapi-types` (TS) | Type-safe OpenAPI 3.x parsing |
| HTTP proxying | `httpx` (Python), `fetch` (TS) | Existing dependencies |
| Schema derivation | JSON Schema subset from OpenAPI | Direct mapping, no conversion needed |

### 6.2 MCP Auth Bridge Architecture

The bridge sits between the MCP server and ASAP identity layer:

```
Agent → MCP Client → [ASAP Auth Bridge] → MCP Server
                      ↕
                   ASAP Auth Server
                   (JWT verification,
                    capability checks)
```

### 6.3 Specification Document

Format: Markdown with numbered sections, following the style of established protocol specifications. Published alongside existing docs, not replacing them.

---

## 7. Success Metrics

| Metric | Target |
|--------|--------|
| Services onboarded via OpenAPI adapter | 20+ |
| MCP servers using ASAP auth | 5+ |
| Specification document completeness | All protocol features covered |
| Cross-protocol integrations | 1+ adapter operational |

---

## 8. Prerequisites

| Prerequisite | Source |
|-------------|--------|
| v2.3.0 Scale released | This PRD |
| TypeScript SDK stable | v2.3 |
| Capability model stable | v2.2+ |
| Identity model stable | v2.2+ |
| Registry API Backend operational | v2.3 |

---

## 9. Related Documents

- **Previous Version**: [prd-v2.3-scale.md](./prd-v2.3-scale.md)
- **Next Version**: [prd-v3.0-economy.md](./prd-v3.0-economy.md)
- **Protocol Hardening**: [prd-v2.2-protocol-hardening.md](./prd-v2.2-protocol-hardening.md)
- **Vision**: [vision-agent-marketplace.md](../strategy/vision-agent-marketplace.md)
- **Roadmap**: [roadmap-to-marketplace.md](../strategy/roadmap-to-marketplace.md)

---

## Change Log

| Date | Version | Change |
|------|---------|--------|
| 2026-03-20 | 0.1.0 | Vision DRAFT — initial PRD for v2.4 Adoption & Integration. OpenAPI adapter, MCP Auth Bridge, cross-protocol compatibility, formal specification document. |
| 2026-04-17 | 0.2.0 | **Rescoped to "Spec & Interop"**. OpenAPI Adapter pulled forward into v2.3 (Adoption Multiplier). Promoted MCP Auth Bridge and Formal Specification to P1. Carried Capability-Aware Introspection (§4.4) and Privacy Considerations (§4.5) over from v2.3 deferral list. Added TS OpenAPI adapter as conditional §4.6 (only if not delivered in v2.3). |
