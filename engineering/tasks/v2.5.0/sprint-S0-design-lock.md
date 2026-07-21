# Sprint S0: Design Lock & Package Scaffold (v2.5.0)

**PRD**: [v2.5.0 §6, MCP-AUTH-005](../../../product/prd/prd-v2.5.0-mcp-auth-bridge.md)
**Branch**: `feat/v2.5.0-s0-design-lock` → merge into **`release/2.5.0`**
**Depends on**: v2.4.1 shipped; `MCPServer` + `verify_agent_jwt` + `CapabilityRegistry` in tree

**Trigger:** Start of v2.5.0 MCP Auth Bridge initiative.
**Enables:** S1 `protect_server` implementation.
**Depends on:** Stable auth modules (`auth/agent_jwt.py`, `auth/capabilities.py`).

---

## Execution notes

> **Status:** S0 complete — ready for S1.

### Dependency phases

```text
Phase 1 (gate)     Phase 2 (parallel)              Phase 3           Phase 4
──────────────     ──────────────────              ───────           ───────
1.1 + 3.3  ──────► 2.1 (protocol)  ─────────────► 4.1 + tests
  Design lock       4.2 (errors)        │          (jwt_extractor)
                    3.2 (MCPAuthConfig) │
                           │            │
                           └────────────┼──► 3.4 (stub protect_server)
                                        └──► 3.1 (__init__ exports)
```

### Sequential vs parallel summary

| Must be sequential | Safe to parallelize (after 1.1) |
|--------------------|----------------------------------|
| **1.1 → 3.3** (same ADR file) | **2.1** ∥ **4.2** ∥ **3.2** |
| **3.2 → 3.4 → 3.1** (package exports need config + stub) | Agents B, C, D in parallel |
| **2.1 → 4.1** (extractor reads `_meta` field) | — |
| Entire S0 before S1 merge | — |

### Implementation notes

- **1.1 and 3.3** are the same deliverable (`design-lock-mcp-auth-bridge.md`); keep them together.
- **3.1** is last in the scaffold track — re-export only after 3.2, 3.4, 4.2 exist.
- **No `MCPServer` behavior change** in S0; unprotected servers remain default (PRD MCP-AUTH-006).
- S1 ([sprint-S1-core-middleware.md](./sprint-S1-core-middleware.md)) is blocked until S0 acceptance criteria pass.

---

## Relevant Files

### New
- `src/asap/adapters/mcp/__init__.py`
- `src/asap/adapters/mcp/auth_middleware.py` — stubs + `MCPAuthConfig`, `protect_server` signature
- `src/asap/adapters/mcp/jwt_extractor.py` — `default_jwt_extractor`
- `src/asap/adapters/mcp/errors.py` — `asap:auth_required`, etc.
- `src/asap/adapters/mcp/grants.py` — optional thin helpers around `CapabilityRegistry.check_grant`
- `engineering/tasks/v2.5.0/design-lock-mcp-auth-bridge.md` — hook strategy decision (short ADR)
- `tests/adapters/mcp/__init__.py`
- `tests/adapters/mcp/test_jwt_extractor.py`

### Modify
- `src/asap/mcp/protocol.py` — add optional `_meta` on `CallToolRequestParams`
- `src/asap/adapters/__init__.py` — note `mcp` subpackage (optional re-export later)

### Reference
- `src/asap/adapters/openapi/` — package layout
- `src/asap/mcp/server.py` — `_handle_tools_call` interception point

---

## Tasks

### 1.0 Design lock document

- [x] 1.1 Write design lock ADR
  - **File**: `engineering/tasks/v2.5.0/design-lock-mcp-auth-bridge.md` (create new)
  - **What**: Document chosen hook: **wrapper** `ProtectedMCPServer` delegating to inner `MCPServer` OR **monkey-patch** `_handle_tools_call` via `protect_server`. Record decision on `_meta` field vs raw dict access, `CapabilityRegistry` injection, `initialize` session-token support, and whether `tools/list` filtering is implemented or deferred. Note: unprotected servers must remain default.
  - **Why**: S1 implementers need a single pattern; PRD MCP-AUTH-006 forbids forking protocol loop
  - **Verify**: Reviewed; linked from sprint-S1

### 2.0 Protocol types for JWT carriage

- [x] 2.1 Extend `CallToolRequestParams` with optional `_meta`
  - **File**: `src/asap/mcp/protocol.py` (modify)
  - **What**: Add `meta: dict[str, Any] | None = Field(default=None, alias="_meta")` with same `model_config` as other MCP models
  - **Why**: PRD §4.3 MUST path — `_meta.asap_agent_jwt` on `tools/call`
  - **Pattern**: Follow existing `CallToolResult` alias style
  - **Verify**: `pytest tests/mcp/ -k call_tool -v` (add test if missing)

### 3.0 Package scaffold

- [x] 3.1 Create `asap.adapters.mcp` package
  - **File**: `src/asap/adapters/mcp/__init__.py` (create)
  - **What**: Export `MCPAuthConfig`, `protect_server`, `default_jwt_extractor`, error code constants
  - **Pattern**: Mirror `adapters/openapi/__init__.py` minimal exports
  - **Verify**: `python -c "from asap.adapters.mcp import MCPAuthConfig"`

- [x] 3.2 Define `MCPAuthConfig` dataclass
  - **File**: `src/asap/adapters/mcp/auth_middleware.py` (create)
  - **What**: Fields per PRD §6.1 (`host_store`, `agent_store`, `capability_registry`, `tool_capability_map`, `public_tools`, `enforce_grants`, `hide_unauthorized_tools`, `validate_tools_at_startup`, `jwt_extractor`, `jti_replay_cache`, `expected_audience`, `manifest_url`)
  - **Why**: Central configuration for S1–S2
  - **Verify**: mypy clean on new module

- [x] 3.3 Lock grant-check interface
  - **File**: `engineering/tasks/v2.5.0/design-lock-mcp-auth-bridge.md` (create new)
  - **What**: State that S2 uses `CapabilityRegistry.check_grant(agent_id, capability, arguments)` as the primary grant/constraint API; call `validate_constraints` directly only in focused unit tests.
  - **Why**: Avoid parallel grant-store implementations and keep MCP enforcement aligned with existing ASAP auth.
  - **Verify**: S2 tasks reference this decision.

- [x] 3.4 Stub `protect_server` raising `NotImplementedError`
  - **File**: `src/asap/adapters/mcp/auth_middleware.py`
  - **What**: Signature `def protect_server(server: MCPServer, config: MCPAuthConfig) -> MCPServer` with docstring referencing PRD
  - **Verify**: Import succeeds; test expects NotImplementedError until S1

### 4.0 JWT extractor & error constants

- [x] 4.1 Implement `default_jwt_extractor`
  - **File**: `src/asap/adapters/mcp/jwt_extractor.py` (create)
  - **What**: Read `_meta.asap_agent_jwt` from `CallToolRequestParams`; fallback `os.environ.get("ASAP_AGENT_JWT")` for dev only
  - **Why**: PRD §6.3; stdio token carriage
  - **Verify**: `pytest tests/adapters/mcp/test_jwt_extractor.py -v`

- [x] 4.2 Define MCP-facing error code constants
  - **File**: `src/asap/adapters/mcp/errors.py` (create)
  - **What**: `AUTH_REQUIRED`, `INVALID_TOKEN`, `CAPABILITY_DENIED`, `CONSTRAINT_VIOLATION` string constants + helper `tool_error_result(code, detail) -> dict`
  - **Why**: PRD §4.6 consistent mapping
  - **Verify**: Unit test builds `CallToolResult`-shaped dict with `isError: true`

---

## Acceptance Criteria (S0)

- [x] Design lock doc committed with explicit hook strategy
- [x] `CallToolRequestParams` accepts `_meta`
- [x] `asap.adapters.mcp` importable; `MCPAuthConfig` typed with identity, grant, replay-cache, and audience fields
- [x] `default_jwt_extractor` tests pass
- [x] `uv run mypy src/asap/adapters/mcp/` clean
- [x] No behavior change to unwrapped `MCPServer`
