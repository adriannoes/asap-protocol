# Sprint S1: Core Auth Middleware (v2.5.0)

**PRD**: [MCP-AUTH-001..004, 006 and auth portions of MCP-AUTH-007](../../../product/prd/prd-v2.5.0-mcp-auth-bridge.md)
**Branch**: `feat/v2.5.0-s1-middleware` → merge into **`release/2.5.0`**
**Depends on**: [S0 design lock](./sprint-S0-design-lock.md) complete — [ADR](./design-lock-mcp-auth-bridge.md)

**Trigger:** MCP client sends `tools/call` to a protected server.
**Enables:** S2 capability mapping; authenticated tool execution path.
**Depends on:** S0 `MCPAuthConfig`, `_meta` on params; `verify_agent_jwt`.

---

## Relevant Files

### New / modify
- `src/asap/adapters/mcp/auth_middleware.py` — implement `protect_server`
- `src/asap/adapters/mcp/protected_server.py` — optional: wrapper class if design lock chooses delegation
- `tests/adapters/mcp/test_auth_middleware.py`
- `tests/adapters/mcp/conftest.py` — fixtures: test host/agent keys, mint Agent JWT

### Reference
- `src/asap/auth/agent_jwt.py` — `verify_agent_jwt`, `create_agent_jwt`, `JtiReplayCache`
- `src/asap/auth/identity.py` — `HostStore`, `AgentStore`
- `src/asap/auth/capabilities.py` — `CapabilityRegistry` fixture setup
- `tests/auth/test_agent_jwt.py` — JWT mint/verify patterns

---

## Tasks

### 1.0 Test fixtures (TDD)

- [ ] 1.1 Add MCP auth test fixtures
  - **File**: `tests/adapters/mcp/conftest.py` (create)
  - **What**: Pytest fixtures: `host_identity`, `agent_session`, `capability_registry`, `mint_agent_jwt()`, minimal `MCPServer` with `echo` tool
  - **Why**: S1 tests need valid/invalid tokens without duplicating crypto setup
  - **Pattern**: Follow `tests/auth/` JWT fixtures
  - **Verify**: Fixtures load in `pytest tests/adapters/mcp/ --collect-only`

- [ ] 1.2 Write failing tests for auth paths
  - **File**: `tests/adapters/mcp/test_auth_middleware.py` (create)
  - **What**: Cases: missing JWT → `asap:auth_required`; expired JWT → `asap:invalid_token`; tampered JWT → `asap:invalid_token`; valid JWT on `public_tools` tool → success without token; valid JWT → handler runs
  - **Verify**: Red before implementation

### 2.0 `protect_server` implementation

- [ ] 2.1 Implement wrapper per design lock
  - **File**: `src/asap/adapters/mcp/auth_middleware.py` + optional `protected_server.py`
  - **What**: Intercept `tools/call` before `_handle_tools_call` executes user handler. Use `resolve_jwt_extractor(config)` (or `config.jwt_extractor` when set)
  - **Why**: MCP-AUTH-001, MCP-AUTH-006
  - **Pattern**: Minimal diff to `MCPServer`; prefer composition over editing `server.py` core loop
  - **Verify**: Green on 1.2 tests

- [ ] 2.2 Integrate `verify_agent_jwt`
  - **File**: `src/asap/adapters/mcp/auth_middleware.py`
  - **What**: Call `await verify_agent_jwt(token, host_store=..., agent_store=..., jti_replay_cache=config.jti_replay_cache, expected_audience=config.expected_audience)`; map `JwtVerifyResult` to error constants
  - **Why**: MCP-AUTH-002
  - **Verify**: Test rejects tampered token

- [ ] 2.3 `public_tools` allowlist
  - **File**: `src/asap/adapters/mcp/auth_middleware.py`
  - **What**: Skip JWT when `parsed.name in config.public_tools`
  - **Why**: MCP-AUTH-001 exception path
  - **Verify**: Dedicated test

### 3.0 Observability

- [ ] 3.1 Log agent URN on successful auth
  - **File**: `src/asap/adapters/mcp/auth_middleware.py`
  - **What**: Structured log `mcp.tool.authorized` with `agent_id`, `tool_name` (no JWT value)
  - **Why**: MCP-AUTH-004; security doc redaction
  - **Verify**: Caplog test or log capture asserts fields present, token absent

---

## Acceptance Criteria (S1)

- [ ] `protect_server` returns server that enforces JWT on non-public tools
- [ ] Missing/invalid JWT returns MCP result with `isError: true` and `asap:*` prefix
- [ ] Unprotected `MCPServer` unchanged when `protect_server` not used
- [ ] `pytest tests/adapters/mcp/test_auth_middleware.py -v` green
- [ ] `uv run mypy src/asap/adapters/mcp/` clean
