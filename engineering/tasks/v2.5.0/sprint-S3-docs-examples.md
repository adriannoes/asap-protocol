# Sprint S3: Docs, Example & Discovery (v2.5.0)

**PRD**: [MCP-DOC-*, MCP-DISC-*, §7](../../../product/prd/prd-v2.5.0-mcp-auth-bridge.md)
**Branch**: `feat/v2.5.0-s3-docs-examples` → merge into **`release/2.5.0`**
**Depends on**: [S2 capability mapping](./sprint-S2-capability-mapping.md)

**Trigger:** Developers adopt MCP Auth Bridge.
**Enables:** S4 compliance harness; S5 release notes.
**Depends on:** Working `protect_server` from S1–S2.

---

## Relevant Files

### New
- `docs/adapters/mcp-auth-bridge.md`
- `examples/mcp_auth_bridge/README.md`
- `examples/mcp_auth_bridge/server.py`
- `examples/mcp_auth_bridge/client.py` (optional minimal caller)
- `tests/examples/test_mcp_auth_bridge_example.py` — smoke import or subprocess

### Modify
- `docs/index.md` — link adapter guide
- `src/asap/adapters/mcp/__init__.py` — stable public exports
- `src/asap/__init__.py` — optional convenience re-export (if project convention)
- `AGENTS.md` — mention `asap.adapters.mcp` in integrations list

---

## Tasks

### 1.0 Reference example

- [ ] 1.1 Protected MCP server example
  - **File**: `examples/mcp_auth_bridge/server.py` (create)
  - **What**: Register 2 tools (`echo` public, `secure_action` protected); `protect_server` with in-memory stores; print startup instructions
  - **Why**: MCP-DOC-001 one-command demo
  - **Pattern**: Follow `examples/openapi_petstore/main.py` structure
  - **Verify**: `uv run python examples/mcp_auth_bridge/server.py` starts without error (short timeout or `--help`)

- [ ] 1.2 Example README
  - **File**: `examples/mcp_auth_bridge/README.md` (create)
  - **What**: How to mint Agent JWT, pass via `_meta.asap_agent_jwt`, env fallback for dev
  - **Why**: MCP-DOC-002
  - **Verify**: Steps reproducible by reviewer

### 2.0 Documentation

- [ ] 2.1 Adapter guide
  - **File**: `docs/adapters/mcp-auth-bridge.md` (create)
  - **What**: Architecture diagram (stdio MCP → JWT → capability), API reference for `MCPAuthConfig` / `protect_server`, error code table, security notes (no JWT in logs)
  - **Why**: MCP-DOC-003
  - **Verify**: Linked from `docs/index.md`

- [ ] 2.2 Manifest / discovery note (SHOULD)
  - **File**: `docs/adapters/mcp-auth-bridge.md` § Discovery
  - **What**: Document optional `manifest_url` in config; how MCP tool names relate to manifest `skills` when bridging
  - **Why**: MCP-DISC-001
  - **Verify**: Cross-link to registry docs if applicable

### 3.0 Public API polish

- [ ] 3.1 Finalize `__all__` exports
  - **File**: `src/asap/adapters/mcp/__init__.py`
  - **What**: Export only supported public symbols; hide internals
  - **Verify**: `python -c "from asap.adapters.mcp import protect_server, MCPAuthConfig"`

---

## Acceptance Criteria (S3)

- [ ] Example runs locally with documented JWT flow
- [ ] `docs/adapters/mcp-auth-bridge.md` complete and indexed
- [ ] No secrets in example files; use `.env.example` pattern if needed
