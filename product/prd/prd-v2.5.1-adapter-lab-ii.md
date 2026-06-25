# PRD: ASAP Protocol v2.5.1 — Adapter Lab II

> **Product Requirements Document**
>
> **Version**: 2.5.1
> **Status**: PLANNED (v2.5.0 shipped 2026-06-24; adoption signal pending)
> **Created**: 2026-04-28 (as v2.3.2); **renumbered**: 2026-06-22
> **Parent train**: [prd-v2.5-roadmap.md](./prd-v2.5-roadmap.md)
> **Predecessor**: [prd-v2.5.0-mcp-auth-bridge.md](./prd-v2.5.0-mcp-auth-bridge.md)
> **Successor**: [prd-v2.5.2-distribution-loop.md](./prd-v2.5.2-distribution-loop.md)
>
> **Migration note**: Formerly `product/prd/private/prd-v2.3.2-enterprise-workflow-adapters.md` (v2.3.2). Renumbered post-v2.4.1; executes after MCP Auth Bridge.

---

## 1. Purpose

v2.5.1 expands adoption testing into **enterprise and workflow-heavy ecosystems** after v2.5.0 delivers MCP auth and v2.3.1 (Adapter Lab I) validated high-signal TypeScript frameworks.

**Question to answer:** which teams need ASAP because their agents must cross organizational, cloud, or workflow boundaries?

---

## 2. Scope

| Candidate | Priority | Hypothesis | Deliverable |
|-----------|----------|------------|-------------|
| Microsoft Agent Framework / Semantic Kernel | P0 if Azure demand | Enterprise/.NET/Azure needs identity + capability grants | Interop spike + .NET guide |
| Haystack | P1 | RAG teams need discoverable retrieval agents | Provider recipe |
| Letta | P1 | Persistent-memory assistants need scoped remote tool access | Capability + memory safety guide |
| n8n / Activepieces-style automation | P1 | Workflow builders expose automations as agent capabilities | Connector prototype |
| Zapier / Make | P2 | Broad audience; partnership risk | Research only unless demand |

---

## 3. Carry-over from v2.5.0: `@asap-protocol/mcp-auth`

> **Decision (2026-06-24, S4 spike):** Ship `@asap-protocol/mcp-auth` in a **future npm patch** (TBD git tag — **not** tag `v2.5.0.1`, which published **`asap-compliance` 1.3.0** only), **not** in v2.5.0 and **not** as part of v2.5.1 Adapter Lab II scope.
>
> **Spike:** [typescript-mcp-auth-spike.md](../../engineering/tasks/v2.5.0/typescript-mcp-auth-spike.md)
> **Source requirements:** [prd-v2.5.0-mcp-auth-bridge.md §5.4](./prd-v2.5.0-mcp-auth-bridge.md#54-typescript-should) (MCP-TS-001..003)

### 3.1 Rationale

| Factor | Detail |
|--------|--------|
| PRD priority | MCP-TS-001..003 are **SHOULD**; Python MCP-AUTH-* / MCP-DOC-* are **MUST** for v2.5.0 |
| Release gate | v2.5.0 ships the Python stdio MCP Auth Bridge (`protect_server`, example, compliance profile) |
| Implementation gap | No `packages/typescript/mcp-auth/`, no public `verifyAgentJwt()` on `@asap-protocol/client`, no HTTP/SSE MCP example or publish CI for a fourth npm package |
| SDK fit | `@modelcontextprotocol/sdk` Bearer middleware targets OAuth transport errors; ASAP needs per-`tools/call` grant checks and `CallToolResult` codes — requires a composed wrapper, not a drop-in |

Deferring does **not** block v2.5.0 Definition of Done or v2.5.1 planning. The npm middleware may ship as a patch after v2.5.0 without delaying Adapter Lab II (**v2.5.1** is a separate **minor** train, not yet started).

### 3.2 Minimum scope (npm patch TBD)

When implemented, the package MUST satisfy MCP-TS-001..003 at minimum:

| ID | Requirement | Priority |
|----|-------------|----------|
| MCP-TS-001 | Publish `@asap-protocol/mcp-auth` with `createMcpAuthMiddleware(config)` for HTTP/SSE MCP servers | SHOULD (carried from v2.5.0) |
| MCP-TS-002 | Bearer extraction from `Authorization` header + same `asap:*` error mapping as Python (`asap:auth_required`, `asap:invalid_token`, `asap:capability_denied`, `asap:constraint_violation`) on `tools/call` | SHOULD (carried from v2.5.0) |
| MCP-TS-003 | Re-export types compatible with `@modelcontextprotocol/sdk` middleware signatures | SHOULD (carried from v2.5.0) |

**Explicitly out of minimum v2.5.0.1 scope:** stdio `_meta.asap_agent_jwt` in TypeScript (Python-only for v2.5.0), full `CapabilityRegistry` port (inject `checkGrant` callback), `hide_unauthorized_tools` / `tools/list` filtering.

### 3.3 Relation to v2.5.1 (LAB2-006)

LAB2-006 applies to **Python Auth Bridge patterns** where Adapter Lab II work exposes MCP. It does not require shipping `@asap-protocol/mcp-auth`; HTTP/SSE TypeScript adopters should wait for v2.5.0.1 or use Python reference semantics manually until the npm package ships.

---

## 4. Requirements

| ID | Requirement | Priority |
|----|-------------|----------|
| LAB2-001 | Reuse v2.3.0/v2.3.1/v2.5.0 adapter interfaces; no protocol fork | MUST |
| LAB2-002 | Ship ≥1 enterprise/workflow example converting workflow/API → ASAP capabilities | MUST |
| LAB2-003 | Document security for automation connectors (secrets, least privilege, HTTPS/TLS) | MUST |
| LAB2-004 | Homepage/site updates routing to new guides | MUST |
| LAB2-005 | Capture learning: open adapters vs hosted control-plane vs enterprise deployment | MUST |
| LAB2-006 | Where MCP is exposed, use v2.5.0 Auth Bridge patterns | SHOULD |

---

## 5. Open Core notes

**Likely public:** SDK adapter interfaces, connector examples, Compliance Harness guidance.

**Likely private/paid later:** hosted registry workflows, org policy engine, SSO/RBAC, audit exports at scale.

---

## 6. Success metrics

| Metric | Target |
|--------|--------|
| Enterprise/workflow prototype | 1+ |
| Security guide for automation connectors | Published |
| External demand signal | 3+ asks or 1 credible partner conversation |

---

## 7. Related documents

- **v2.3.1 (shipped)**: `product/prd/private/prd-v2.3.1-adapter-lab.md`
- **Adoption foundation**: [prd-v2.3-scale.md](./prd-v2.3-scale.md)

---

## Change Log

| Date | Change |
|------|--------|
| 2026-06-24 | §3: Record S4 defer of `@asap-protocol/mcp-auth` to v2.5.0.1 (MCP-TS-001..003) |
| 2026-06-22 | Renumbered v2.3.2 → v2.5.1; blocked on v2.5.0 |
