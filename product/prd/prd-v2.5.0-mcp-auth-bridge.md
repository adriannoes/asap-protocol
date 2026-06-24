# PRD: ASAP Protocol v2.5.0 — MCP Auth Bridge

> **Product Requirements Document**
>
> **Version**: 2.5.0
> **Status**: READY FOR IMPLEMENTATION
> **Created**: 2026-03-20 (origin); **rescoped to v2.5.0**: 2026-06-22
> **Last Updated**: 2026-06-24
>
> **Parent train**: [prd-v2.5-roadmap.md](./prd-v2.5-roadmap.md)
> **Predecessor**: [prd-v2.4.1-security-hardening.md](./prd-v2.4.1-security-hardening.md) (✅ shipped)
> **Successor**: [prd-v2.5.1-adapter-lab-ii.md](./prd-v2.5.1-adapter-lab-ii.md)

---

## 1. Executive Summary

### 1.1 Purpose

v2.5.0 delivers the **MCP Auth Bridge**: ASAP's identity and capability model as the authorization layer for **native MCP servers** (`tools/call`), not only for MCP-over-ASAP envelopes.

Today MCP has no standard auth story for per-agent, scoped tool access. ASAP already has Host/Agent JWT, capability grants with constraints, and approval flows (v2.2+). This release **exports that stack to MCP** so each connecting agent has its own identity and enforced permissions.

### 1.2 Why now

| Signal | Evidence |
|--------|----------|
| Literatura sobre taxonomias de protocolos de agentes | Convergência prevista A2A+MCP; lacuna transversal em policy enforcement |
| Implementação ASAP | Envelopes `McpToolCall` existem para A2A; `MCPServer` não valida JWT |
| v2.4.1 shipped | OAuth2 iss/aud + fail-closed identity — base estável para bridge |
| Posicionamento | ASAP como camada L1+L3 na pilha federada (identity + MCP execution auth) |

### 1.3 Deliverables

| # | Deliverable | Package / surface |
|---|-------------|-------------------|
| 1 | Python auth middleware for `MCPServer` | `asap.adapters.mcp.auth_middleware` |
| 2 | Tool → capability mapping + grant enforcement | `asap.adapters.mcp.capability_map` |
| 3 | Discovery: well-known manifest alongside MCP | docs + optional `MCPAuthConfig.manifest_url` |
| 4 | TypeScript middleware (SHOULD) | `@asap-protocol/mcp-auth` |
| 5 | Reference server + compliance tests | `examples/mcp_auth_bridge/server.py`, harness cases |
| 6 | Integration guide | `docs/adapters/mcp-auth-bridge.md` |

### 1.4 Out of scope (v2.5.0)

- Formal RFC specification → [prd-v2.5.3-formal-spec-interop.md](./prd-v2.5.3-formal-spec-interop.md)
- A2A runtime bridge → v2.5.3
- Framework adapters (Haystack, Letta…) → [prd-v2.5.1-adapter-lab-ii.md](./prd-v2.5.1-adapter-lab-ii.md)
- MCP OAuth provider implementation (we **consume** Agent JWTs; Host mints tokens)
- HTTP/SSE MCP transport in Python core (stdio first; HTTP auth patterns documented for TS)

---

## 2. Problem statement

### 2.1 MCP's auth gap

MCP (spec 2025-11-25) standardizes tool listing and invocation over stdio/SSE/HTTP. Host applications (Claude Desktop, Cursor) launch MCP servers as subprocesses. **There is no normative per-agent identity or scoped authorization** for `tools/call`:

- One server process typically serves one host application, not N distinct agents.
- Tool handlers run with full server privileges.
- Secrets are often process-wide environment variables.

### 2.2 What ASAP already solves (A2A path)

| Capability | Location | MCP gap |
|------------|----------|---------|
| Agent JWT (EdDSA, 60s TTL, capabilities claim) | `auth/agent_jwt.py` | Not checked on native MCP `tools/call` |
| Capability grants + constraints | `auth/capabilities.py` | Tools registered without grant checks |
| Envelope MCP payloads | `McpToolCall` / `McpToolResult` | Only when MCP is **inside** ASAP transport |
| `MCPServer` stdio | `mcp/server.py` | No auth hook before handler execution |

### 2.3 Target outcome

> An MCP server operator registers tools mapped to ASAP capabilities. Each `tools/call` presents an **Agent JWT**. The bridge verifies the token, checks the grant for that tool/capability (including constraints), then executes the handler or returns MCP-safe error.

---

## 3. User stories

### MCP Server Developer
> As an **MCP server developer**, I want to **wrap my `MCPServer` with ASAP auth middleware** so that **only agents with active capability grants can invoke specific tools**.

### Host / Platform Operator
> As a **host operator**, I want **per-agent MCP connections** (distinct Agent JWTs) so that **audit logs and metering attribute actions to the correct agent URN**, not to the host application.

### Security Engineer
> As a **security engineer**, I want **tool names bound to capability names** with constraint validation on arguments so that **agents cannot exceed granted limits** (e.g. `max` on token counts).

### MCP Client Integrator (Claude / Cursor)
> As an **integrator**, I want a **documented token carriage mechanism** for stdio and HTTP MCP so that **clients can pass Agent JWTs without breaking MCP JSON-RPC framing**.

---

## 4. Architecture

### 4.1 Layered placement

```
┌─────────────────────────────────────────────────────────┐
│ MCP Host (Claude Desktop, Cursor, custom)                 │
│   MCP Client ──tools/call + Agent JWT──────────────────┐  │
└────────────────────────────────────────────────────────│──┘
                                                         ▼
┌─────────────────────────────────────────────────────────┐
│ [ASAP MCP Auth Bridge]  ← v2.5.0                        │
│   1. Extract JWT                                        │
│   2. verify_agent_jwt()                                 │
│   3. resolve tool_name → capability                     │
│   4. check grant status + constraints on arguments      │
│   5. delegate to tool handler OR return auth error      │
└───────────────────────────┬─────────────────────────────┘
                            ▼
┌─────────────────────────────────────────────────────────┐
│ MCPServer (existing asap.mcp)                           │
│   register_tool() handlers                              │
└─────────────────────────────────────────────────────────┘
         ▲
         │ Host JWT minting, grant store (existing v2.2)
┌────────┴────────────────────────────────────────────────┐
│ ASAP Auth (HostIdentity, AgentStore, capabilities)      │
└─────────────────────────────────────────────────────────┘
```

### 4.2 Two integration modes (both supported)

| Mode | When | Auth flow |
|------|------|-----------|
| **A. Wrapped native MCP server** | Operator runs standalone MCP server | Bridge intercepts `tools/call` on `MCPServer` |
| **B. MCP-over-ASAP envelope** | Agent calls another agent's MCP gateway via ASAP | Existing `McpToolCall` + ASAP transport auth (v2.2+) — **no change required**; document relationship |

v2.5.0 focuses on **Mode A**. Mode B remains the A2A path documented in `docs/mcp-integration.md`.

### 4.3 Token carriage (stdio — primary)

MCP stdio cannot use HTTP headers. Supported mechanisms (implement all MUST paths for at least one; document others):

| Mechanism | Priority | Description |
|-----------|----------|-------------|
| **`_meta.asap_agent_jwt` on `tools/call` params** | MUST | Client passes JWT in MCP request metadata (forward-compatible with MCP `_meta` conventions) |
| **`initialize` params extension** | SHOULD | Short-lived session token established at handshake, referenced on subsequent calls |
| **Environment bootstrap** | MAY | Dev-only: `ASAP_AGENT_JWT` for single-agent local testing (not production pattern) |

For **HTTP/SSE MCP** (TypeScript middleware): `Authorization: Bearer <agent_jwt>` — MUST in `@asap-protocol/mcp-auth`.

### 4.4 Tool → capability mapping

Default mapping rules (configurable):

```python
# Default: tool name == capability name
"web_search" → capability "web_search"

# Optional explicit map in MCPAuthConfig
tool_capability_map: dict[str, str] = {
    "search": "web_search",
    "read_file": "filesystem.read",
}
```

Manifest alignment:

- MCP server SHOULD expose `/.well-known/asap/manifest.json` listing capabilities that mirror registered tools.
- `Skill.id` / capability `name` MUST match mapped capability names for discovery consistency.

### 4.5 Constraint enforcement

Before handler execution, bridge calls existing `CapabilityRegistry.check_grant(agent_id, capability, arguments)` from `auth/capabilities.py`.
That registry validates grant status, expiry, and constraints with `validate_constraints(grant.constraints, arguments)`:

- Operators define constraints on grants (`max`, `min`, `in`, `not_in`).
- Tool `arguments` dict is the validation input.
- Violations return MCP `CallToolResult` with `isError: true` and ASAP-namespaced error code in text (e.g. `asap:capability_denied`).

### 4.6 Error mapping (MCP-facing)

| ASAP condition | MCP result |
|----------------|------------|
| Missing JWT | `isError: true`, message `asap:auth_required` |
| Invalid/expired JWT | `isError: true`, `asap:invalid_token` |
| No grant / denied grant | `asap:capability_denied` |
| Constraint violation | `asap:constraint_violation` + field detail |
| Unknown tool | Existing `MCPServer` `CallToolResult` with `isError: true` (unchanged) |

---

## 5. Functional requirements

### 5.1 Core auth (MUST)

| ID | Requirement | Priority |
|----|-------------|----------|
| MCP-AUTH-001 | Every `tools/call` on a protected server MUST require a valid Agent JWT unless tool is in `public_tools` allowlist | MUST |
| MCP-AUTH-002 | JWT verification MUST use `verify_agent_jwt()` with replay cache (`JtiReplayCache`) | MUST |
| MCP-AUTH-003 | Resolved capability MUST be present in the Agent JWT `capabilities` claim and cross-checked against the server-side `CapabilityRegistry` grant store when `enforce_grants=True` | MUST |
| MCP-AUTH-004 | Per-agent identity: JWT `sub` / agent URN MUST appear in audit logs for each tool call | MUST |
| MCP-AUTH-005 | Python package `asap.adapters.mcp` with `MCPAuthConfig` and `protect_server(server, config)` | MUST |
| MCP-AUTH-006 | `protect_server` MUST wrap `tools/call` dispatch without forking `MCPServer` protocol loop | MUST |
| MCP-AUTH-007 | Unit tests: reject missing token, expired token, wrong capability, constraint fail, success path | MUST |

### 5.2 Capability mapping (MUST)

| ID | Requirement | Priority |
|----|-------------|----------|
| MCP-MAP-001 | Configurable `tool_capability_map: dict[str, str]`; default identity map | MUST |
| MCP-MAP-002 | `register_tool` MAY accept optional `capability: str` metadata stored in bridge registry | SHOULD |
| MCP-MAP-003 | Startup validation: every registered tool MUST resolve to a known capability or explicit map entry | SHOULD |
| MCP-MAP-004 | `tools/list` MAY redact tools for which caller lacks grant (config `hide_unauthorized_tools`) | MAY |

### 5.3 Discovery (SHOULD)

| ID | Requirement | Priority |
|----|-------------|----------|
| MCP-DISC-001 | Document pattern: MCP server + `/.well-known/asap/manifest.json` on same origin (HTTP) or linked URL in server `instructions` (stdio) | SHOULD |
| MCP-DISC-002 | Example manifest snippet mapping `skills[].id` to MCP tool names | SHOULD |
| MCP-DISC-003 | Compliance harness case: manifest tools ⊆ registered MCP tools | SHOULD |

### 5.4 TypeScript (SHOULD)

| ID | Requirement | Priority |
|----|-------------|----------|
| MCP-TS-001 | Publish `@asap-protocol/mcp-auth` with `createMcpAuthMiddleware(config)` for HTTP/SSE MCP servers | SHOULD |
| MCP-TS-002 | Bearer extraction + same error code mapping as Python | SHOULD |
| MCP-TS-003 | Re-export types compatible with `@modelcontextprotocol/sdk` | SHOULD |

### 5.5 Documentation & examples (MUST)

| ID | Requirement | Priority |
|----|-------------|----------|
| MCP-DOC-001 | `docs/adapters/mcp-auth-bridge.md` — architecture, token carriage, config reference | MUST |
| MCP-DOC-002 | `examples/mcp_auth_bridge/server.py` — runnable protected server | MUST |
| MCP-DOC-003 | Update `docs/mcp-integration.md` — distinguish Mode A vs Mode B | MUST |
| MCP-DOC-004 | Migration note: unprotected MCP servers remain valid; protection is opt-in | MUST |

---

## 6. Proposed API (Python)

### 6.1 Configuration

```python
# asap/adapters/mcp/auth_middleware.py (new)

@dataclass
class MCPAuthConfig:
    host_store: HostStore
    agent_store: AgentStore
    capability_registry: CapabilityRegistry
    tool_capability_map: dict[str, str] = field(default_factory=dict)
    public_tools: frozenset[str] = frozenset()  # no JWT required
    enforce_grants: bool = True
    hide_unauthorized_tools: bool = False
    validate_tools_at_startup: bool = False
    jwt_extractor: Callable[[CallToolRequestParams], str | None] | None = None
    jti_replay_cache: JtiReplayCache | None = None
    expected_audience: str | list[str] | None = None
    manifest_url: str | None = None  # for instructions / discovery docs
```

### 6.2 Entry point

```python
def protect_server(server: MCPServer, config: MCPAuthConfig) -> MCPServer:
    """Return server with tools/call wrapped by ASAP auth + capability checks."""
```

### 6.3 Default JWT extractor

```python
def default_jwt_extractor(params: CallToolRequestParams) -> str | None:
    meta = params.meta or {}
    token = meta.get("asap_agent_jwt")
    if isinstance(token, str) and token.strip():
        return token.strip()
    return os.environ.get("ASAP_AGENT_JWT")  # dev fallback only
```

---

## 7. Engineering tasks

> **Sprint index:** [tasks-v2.5.0-roadmap.md](../../engineering/tasks/v2.5.0/tasks-v2.5.0-roadmap.md)  
> Parent tasks **1.0–5.0** and sprint sub-tasks **S0–S5** are defined.

| Sprint | Goal | Task file |
|--------|------|-----------|
| **S0** | Design lock + scaffold | `sprint-S0-design-lock.md` |
| **S1** | Core middleware | `sprint-S1-core-middleware.md` |
| **S2** | Capability mapping | `sprint-S2-capability-mapping.md` |
| **S3** | Discovery + docs | `sprint-S3-docs-examples.md` |
| **S4** | Compliance | `sprint-S4-compliance.md` |
| **S5** | Release | `sprint-S5-release.md` |

**Definition of Done (v2.5.0):**

- [ ] `protect_server` passes unit + integration tests with mock Agent JWT
- [ ] Example server runs: `uv run python examples/mcp_auth_bridge/server.py`
- [ ] Compliance harness includes `mcp_auth` profile cases for auth, grants, constraints, and manifest alignment
- [ ] Docs published; `AGENTS.md` knowledge map updated
- [ ] No breaking change to unprotected `MCPServer` usage

---

## 8. Security considerations

| Risk | Mitigation |
|------|------------|
| JWT in `_meta` logged by naive loggers | Document: redact `asap_agent_jwt` in structured logs; short TTL (60s default) |
| stdio token replay | `JtiReplayCache` per agent partition (existing) |
| Tool name aliasing bypass | Startup validation MCP-MAP-003; manifest cross-check |
| Confused deputy (host mints token for wrong agent) | Host JWT flow unchanged; document Host responsibility |
| `ASAP_AGENT_JWT` env in production | Mark dev-only in docs; lint example servers |

---

## 9. Success metrics

| Metric | Target |
|--------|--------|
| Protected MCP example server | 1 runnable in repo |
| Test coverage on `asap.adapters.mcp` | ≥ 90% |
| External MCP servers adopting (post-release) | 3+ within 90 days (aspirational) |
| Compliance harness | New `mcp_auth` module green in CI |
| Time to ship from task kickoff | ≤ 3 weeks (solo maintainer estimate) |

---

## 10. Prerequisites

| Prerequisite | Status |
|-------------|--------|
| v2.4.1 shipped | ✅ |
| `verify_agent_jwt` stable | ✅ |
| `CapabilityRegistry.check_grant` + `validate_constraints` | ✅ |
| `MCPServer` tools/call hook point | ✅ `_handle_tools_call` exists; S0 locks wrapper strategy |
| v2.5.1+ adapter work | ❌ blocked until v2.5.0 ships |

---

## 11. Related documents

- **Train index**: [prd-v2.5-roadmap.md](./prd-v2.5-roadmap.md)
- **Execution**: [`engineering/tasks/v2.5.0/tasks-v2.5.0-roadmap.md`](../../engineering/tasks/v2.5.0/tasks-v2.5.0-roadmap.md)
- **ADR envelope MCP**: `product/decision-records/02-protocol.md` (Question 5)
- **Existing MCP guide**: [docs/mcp-integration.md](../../docs/mcp-integration.md)
- **Agent JWT**: `src/asap/auth/agent_jwt.py`
- **Legacy PRD**: [prd-v2.4-adoption.md](./prd-v2.4-adoption.md) (redirect)

---

## Change Log

| Date | Version | Change |
|------|---------|--------|
| 2026-03-20 | 0.1.0 | Original scope in `prd-v2.4-adoption.md` §4.1 |
| 2026-04-17 | 0.2.0 | Promoted to P1 in Spec & Interop rescope |
| 2026-06-22 | 1.0.0 | **Rescoped to v2.5.0**; full architecture, API, task breakdown; split from formal spec (→ v2.5.3) |
| 2026-06-22 | 1.1.0 | Parent tasks 1.0–5.0 in [tasks-v2.5.0-roadmap.md](../../engineering/tasks/v2.5.0/tasks-v2.5.0-roadmap.md) |
| 2026-06-24 | 1.2.0 | Aligned task plan with repo APIs, canonical docs/example paths, grant registry config, and compliance/doc gaps |
