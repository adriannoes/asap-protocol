# Design Lock: MCP Auth Bridge (v2.5.0)

> **Status**: LOCKED (S0)
> **PRD**: [prd-v2.5.0-mcp-auth-bridge.md](../../../product/prd/prd-v2.5.0-mcp-auth-bridge.md)
> **Sprint**: [sprint-S0-design-lock.md](./sprint-S0-design-lock.md) → enables [sprint-S1-core-middleware.md](./sprint-S1-core-middleware.md)

---

## 1. Context

`MCPServer` (`src/asap/mcp/server.py`) dispatches `tools/call` through `_handle_tools_call` with no auth gate. v2.5.0 adds opt-in protection via `protect_server(server, config)` (MCP-AUTH-005, MCP-AUTH-006).

**Constraint (MCP-AUTH-006):** Do not fork the JSON-RPC protocol loop (`serve_stdio`, `_dispatch_request`, notification handling). Only intercept `tools/call` before the user handler runs.

**Default:** Unprotected `MCPServer` usage remains valid; protection is explicit (MCP-DOC-004).

---

## 2. Decision: Hook strategy

### Chosen: `ProtectedMCPServer` subclass + factory

`protect_server` returns a `ProtectedMCPServer` that **subclasses** `MCPServer` and **overrides `_handle_tools_call` only**. The factory copies registration state from the input server (`_tools`, `_server_info`, `_instructions`).

### Rejected: In-place monkey-patch of `_handle_tools_call`

Replacing `server._handle_tools_call` on the caller's instance would work mechanically but:

- Mutates a private method on an object the operator may still reference elsewhere.
- Harder to reason about identity (`protect_server` return vs original `server`).
- Complicates testing and “unprotect” scenarios.

### Rejected: Forking `_dispatch_request` / `serve_stdio`

Duplicates protocol-loop logic and violates MCP-AUTH-006.

### Implementation layout (S1)

| Module | Responsibility |
|--------|----------------|
| `auth_middleware.py` | `MCPAuthConfig`, `protect_server` factory |
| `protected_server.py` | `ProtectedMCPServer` class; auth + grant checks in `_handle_tools_call` |
| `jwt_extractor.py` | `default_jwt_extractor` (S0) |
| `errors.py` | MCP-facing `asap:*` codes (S0) |

`protect_server` signature (locked):

```python
def protect_server(server: MCPServer, config: MCPAuthConfig) -> MCPServer:
    """Return a protected server; input server is not mutated."""
```

---

## 3. Decision: JWT carriage (`_meta`)

### Chosen: Typed `CallToolRequestParams.meta` with Pydantic alias `_meta`

S0 adds to `CallToolRequestParams`:

```python
meta: dict[str, Any] | None = Field(default=None, alias="_meta")
```

Middleware and `default_jwt_extractor` **MUST** read `params.meta`, not raw `dict` access on RPC params. Key: `asap_agent_jwt` (PRD §4.3, §6.3).

Dev-only fallback: ``ASAP_AGENT_JWT`` is read only when
``MCPAuthConfig.allow_env_jwt_fallback=True`` (default ``False``). S1 middleware
MUST use :func:`resolve_jwt_extractor` so env reads cannot bypass auth in production.

### Deferred: `initialize` session-token handshake

PRD §4.3 lists `initialize` params extension as **SHOULD**. Not in S0–S1 scope. Track as follow-up (S3 docs may describe pattern; implementation post-v2.5.0 unless S1 capacity allows).

---

## 4. Decision: `CapabilityRegistry` injection

### Chosen: Single registry via `MCPAuthConfig.capability_registry`

- Operators pass the same `CapabilityRegistry` used for A2A grants.
- **No** parallel MCP-specific grant store in v2.5.0.
- `host_store` and `agent_store` on config support `verify_agent_jwt` and identity resolution.

Audit: log `agent_id` from verified JWT `sub` on each protected `tools/call` (MCP-AUTH-004).

---

## 5. Decision: Grant-check API (task 3.3)

### Primary API (S2 enforcement)

```python
CapabilityRegistry.check_grant(agent_id, capability, arguments) -> GrantCheckResult
```

Located in `src/asap/auth/capabilities.py`. This method already:

1. Resolves grant by `agent_id` + `capability`
2. Validates grant status and expiry
3. Runs `validate_constraints(grant.constraints, arguments)` on tool arguments

**S1–S2 middleware MUST use `check_grant` as the single grant + constraint gate** before delegating to the inner handler.

### When to call `validate_constraints` directly

Only in **focused unit tests** of constraint helpers — not in MCP middleware paths. Avoid duplicating grant-resolution logic outside `CapabilityRegistry`.

### Tool → capability resolution

1. `config.tool_capability_map.get(tool_name, tool_name)` (default identity map, MCP-MAP-001)
2. Optional per-tool metadata from bridge registry in S2 (`register_tool` capability metadata — MCP-MAP-002)

---

## 6. Decision: `tools/list` filtering

### Deferred (default off)

`MCPAuthConfig.hide_unauthorized_tools` defaults to `False` (PRD §6.1). MCP-MAP-004 is **MAY**.

- **S0–S1:** `tools/list` unchanged — lists all registered tools.
- **S2+:** If implemented, filter in `ProtectedMCPServer._handle_tools_list` override using JWT from list request context (TBD: list carries no standard `_meta` today — needs design before implementation).

Do not block S1 on list filtering.

---

## 7. Protected `tools/call` flow (S1 target)

```text
tools/call params
    → CallToolRequestParams (incl. meta / _meta)
    → jwt_extractor via resolve_jwt_extractor(config)
    → missing token? → CallToolResult isError + asap:auth_required (unless public_tools)
    → verify_agent_jwt(host_store, agent_store, jti_cache, audience)
    → invalid? → asap:invalid_token
    → resolve tool_name → capability
    → capability_registry.check_grant(agent_id, capability, arguments)
    → denied / violations? → asap:capability_denied / asap:constraint_violation
    → super()._handle_tools_call(params)  # schema validate + handler
```

Unknown tool errors remain the inner `MCPServer` behavior (PRD §4.6).

---

## 8. Consequences

| Area | Impact |
|------|--------|
| S1 | Implement `ProtectedMCPServer` per §2; no `MCPServer` core edits beyond S0 `_meta` typing |
| S2 | Wire `check_grant` + `tool_capability_map`; optional startup validation (MCP-MAP-003) |
| S3 | Document token carriage; note deferred initialize session-token |
| Tests | Middleware tests mock `CapabilityRegistry.check_grant`; constraint unit tests may call `validate_constraints` directly |
| Breaking change | None for unwrapped servers |

---

## 9. References

- `src/asap/mcp/server.py` — `_handle_tools_call` interception point
- `src/asap/auth/agent_jwt.py` — `verify_agent_jwt`, `JtiReplayCache`
- `src/asap/auth/capabilities.py` — `CapabilityRegistry.check_grant`, `validate_constraints`
- `engineering/tasks/v2.5.0/sprint-S1-core-middleware.md` — implementation tasks
