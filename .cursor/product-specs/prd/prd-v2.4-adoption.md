# PRD: ASAP Protocol v2.4.0 — Adoption & Integration

> **Product Requirements Document**
>
> **Version**: 2.4.0
> **Status**: VISION DRAFT
> **Created**: 2026-03-20
> **Last Updated**: 2026-03-20

---

## 1. Executive Summary

### 1.1 Purpose

v2.4.0 lowers integration barriers to accelerate adoption. With identity/auth hardened (v2.2) and the ecosystem scaled (v2.3), this release focuses on making ASAP trivially adoptable for services with existing APIs and ensuring interoperability across the agent protocol landscape.

This release delivers:
- **OpenAPI Adapter**: Auto-derive ASAP capabilities from existing OpenAPI specs (zero-code onboarding)
- **MCP Auth Bridge**: ASAP identity layer for MCP servers (solve MCP's auth gap)
- **Cross-Protocol Compatibility**: Thin adapters for interop with other agent auth protocols
- **Formal ASAP Specification Document**: RFC-style specification for standardization track

> [!CAUTION]
> **Triggers required before starting this PRD**:
> 1. v2.3 Scale released (TypeScript SDK, Registry API Backend, capability escalation stable)
> 2. Demand from services wanting zero-code integration (3+ requests for OpenAPI onboarding)
> 3. MCP ecosystem growth warrants auth bridge investment

### 1.2 Strategic Context

v2.4 is the **adoption multiplier** — it makes ASAP accessible to services that would never manually implement a protocol, and ensures ASAP can interoperate with adjacent standards.

| Layer | v2.4 Investment |
|-------|----------------|
| Integration (Adapters) | **Primary focus** — OpenAPI, MCP, cross-protocol |
| Specification | Formal RFC-style document |
| Protocol | No new protocol features (stabilization) |
| Marketplace | No changes |

---

## 2. Goals

| Goal | Metric | Priority |
|------|--------|----------|
| Zero-code onboarding | 20+ services onboarded via OpenAPI adapter | P1 |
| MCP auth solved | ASAP identity layer operational for MCP servers | P2 |
| Formal specification | Complete spec document published | P2 |
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

### 4.1 OpenAPI Adapter (P1)

Auto-derive ASAP capabilities from existing OpenAPI specs. Each OpenAPI operation becomes a capability.

| ID | Requirement | Priority |
|----|-------------|----------|
| OA-001 | `create_from_openapi(spec)` — generates capabilities, execution handler, and provider config from OpenAPI spec | MUST |
| OA-002 | OpenAPI `operationId` → capability `name` mapping | MUST |
| OA-003 | OpenAPI `description`/`summary` → capability `description` | MUST |
| OA-004 | OpenAPI parameters + request body → capability `input` (JSON Schema) | MUST |
| OA-005 | OpenAPI 200/201 response body → capability `output` (JSON Schema) | MUST |
| OA-006 | Execution handler maps arguments back to path params, query params, headers, request body | MUST |
| OA-007 | `default_capabilities` filter: by HTTP method (`"GET"`, `["GET", "HEAD"]`), all, or callback | MUST |
| OA-008 | `approval_strength` per capability or per HTTP method (`GET` → `session`, `POST` → `webauthn`) | SHOULD |
| OA-009 | `resolve_headers` callback for upstream auth (e.g., inject `Authorization: Bearer` for user) | MUST |
| OA-010 | Auto-detect response types: `202` → async, `text/event-stream` → streaming, `application/json` → sync | SHOULD |
| OA-011 | Python package: `asap.adapters.openapi` | MUST |
| OA-012 | TypeScript package: `@asap-protocol/openapi` | SHOULD |

**Usage Example (Python)**:
```python
from asap.adapters.openapi import create_from_openapi

config = create_from_openapi(
    spec_url="https://api.example.com/openapi.json",
    default_capabilities=["GET", "HEAD"],
    approval_strength={"POST": "webauthn", "DELETE": "webauthn"},
    resolve_headers=lambda session: {"Authorization": f"Bearer {get_token(session.user_id)}"},
)
```

**Usage Example (TypeScript)**:
```typescript
import { createFromOpenAPI } from "@asap-protocol/openapi";

const config = await createFromOpenAPI({
  specUrl: "https://api.example.com/openapi.json",
  defaultCapabilities: ["GET", "HEAD"],
});
```

---

### 4.2 MCP Auth Bridge (P2)

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

### 4.3 Cross-Protocol Compatibility (P3)

Thin adapters for interoperability with other agent authentication protocols.

| ID | Requirement | Priority |
|----|-------------|----------|
| COMPAT-001 | Translation layer: accept external agent JWTs and map to ASAP agent sessions | SHOULD |
| COMPAT-002 | Capability mapping: translate external capability grants to ASAP grants | SHOULD |
| COMPAT-003 | Discovery bridge: serve ASAP well-known alongside other protocol discovery endpoints | SHOULD |
| COMPAT-004 | Documentation: interoperability guide for multi-protocol environments | MUST |

---

### 4.4 Formal ASAP Specification Document (P2)

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
