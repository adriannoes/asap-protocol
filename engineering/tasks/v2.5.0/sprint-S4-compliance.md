# Sprint S4: Compliance Harness (v2.5.0)

**PRD**: [MCP-DISC-003, MCP-AUTH-007, §7 DoD, §9 metrics](../../../product/prd/prd-v2.5.0-mcp-auth-bridge.md)
**Branch**: `feat/v2.5.0-s4-compliance` → merge into **`release/2.5.0`**
**Depends on**: [S3 example](./sprint-S3-docs-examples.md)

**Trigger:** Release gate for v2.5.0.
**Enables:** S5 version bump and PyPI publish.
**Depends on:** `asap-compliance` package; protected stdio MCP example from S3.

---

## Relevant Files

### New / modify
- `asap-compliance/asap_compliance/validators/mcp_auth.py` — MCP auth bridge checks
- `asap-compliance/tests/test_mcp_auth.py`
- `examples/mcp_auth_bridge/` — ensure stdio subprocess or script hook can be driven by `asap-compliance`
- `asap-compliance/asap_compliance/validators/__init__.py` — export new validator
- `engineering/tasks/v2.5.0/typescript-mcp-auth-spike.md` — spike result or defer rationale

### Reference
- `asap-compliance/asap_compliance/validators/handshake.py` — result/check structure precedent, not the MCP auth gate itself
- `examples/openapi_petstore/` — example package structure pattern

---

## Tasks

### 1.0 Validator design

- [ ] 1.1 Lock compliance gate
  - **File**: `asap-compliance/asap_compliance/validators/mcp_auth.py` (create)
  - **What**: Treat `asap-compliance` profile `mcp-auth-bridge` as the release gate for stdio MCP. Do not rely on `src/asap/testing/compliance.py` unless S4 explicitly adds shared HTTP/ASGI support.
  - **Why**: v2.5.0 validates native MCP stdio auth, while the existing harness v2 is HTTP/ASGI-focused.
  - **Verify**: S4 README or test output names `mcp-auth-bridge` as the gate.

- [ ] 1.2 Define MCP auth compliance checks
  - **File**: `asap-compliance/asap_compliance/validators/mcp_auth.py` (create)
  - **What**: Black-box checks: (a) unauthenticated `tools/call` on protected tool returns error; (b) valid JWT succeeds; (c) wrong capability denied; (d) constraint violation returns `asap:constraint_violation`. Config: stdio subprocess or test server URL.
  - **Why**: MCP-AUTH-007
  - **Pattern**: Reuse the `CheckResult` shape from `validators/handshake.py`; wrap checks in an MCP-specific result object if the CLI needs summary metadata.
  - **Verify**: Unit tests with mocked server responses first

- [ ] 1.3 Define manifest alignment compliance check
  - **File**: `asap-compliance/asap_compliance/validators/mcp_auth.py` (create)
  - **What**: Validate manifest-declared tool/capability names are a subset of registered MCP tools or mapped capabilities, using example fixture data when a live manifest URL is unavailable.
  - **Why**: MCP-DISC-003
  - **Verify**: Unit test fails when manifest declares an unknown tool/capability.

### 2.0 Integration with harness

- [ ] 2.1 Wire validator into compliance CLI
  - **File**: `asap-compliance/asap_compliance/validators/__init__.py` + main runner if exists
  - **What**: Optional profile `mcp-auth-bridge` targeting the stdio example server. If shared `src/asap/testing/compliance.py` support is needed, add it explicitly rather than assuming the HTTP harness covers stdio MCP.
  - **Verify**: `uv run` compliance against `examples/mcp_auth_bridge` passes required checks

- [ ] 2.2 Example compliance script or README section
  - **File**: `examples/mcp_auth_bridge/README.md`
  - **What**: Document command to run the `asap-compliance` `mcp-auth-bridge` profile and expected pass/fail checks.
  - **Verify**: CI or local script passes

### 3.0 Regression tests

- [ ] 3.1 Full adapter test suite in CI
  - **File**: root CI workflow or existing pytest job
  - **What**: Ensure `tests/adapters/mcp/` runs on every PR to `release/2.5.0`
  - **Verify**: PR check green

- [ ] 3.2 End-to-end stdio integration test
  - **File**: `tests/adapters/mcp/test_auth_middleware.py` or `tests/adapters/mcp/test_stdio_integration.py`
  - **What**: Exercise protected `MCPServer` over stdio/subprocess with a real Agent JWT in `_meta.asap_agent_jwt`, including one success and one denied call.
  - **Why**: PRD DoD requires unit + integration tests with mock Agent JWT.
  - **Verify**: Test runs headless in the normal pytest suite.

### 4.0 TypeScript middleware spike

- [ ] 4.1 Decide ship vs defer for `@asap-protocol/mcp-auth`
  - **File**: `engineering/tasks/v2.5.0/typescript-mcp-auth-spike.md` (create)
  - **What**: Check current `packages/typescript/` layout, `@modelcontextprotocol/sdk` compatibility, package naming, and minimum implementation needed for Bearer extraction + error mapping.
  - **Why**: MCP-TS-001..003 are SHOULD, but the release must record a deliberate ship/defer decision.
  - **Verify**: S5 has either shipped package tasks or a linked v2.5.0.1 defer note in CHANGELOG/backlog.

---

## Acceptance Criteria (S4)

- [ ] MCP auth validator returns pass/fail `CheckResult` for auth required, valid JWT, wrong capability, and constraint violation paths
- [ ] Manifest alignment check covers manifest tools/capabilities ⊆ registered MCP tools/mapped capabilities
- [ ] `asap-compliance` `mcp-auth-bridge` profile is the documented release gate for stdio MCP
- [ ] Protected stdio MCP integration test passes in pytest
- [ ] TypeScript middleware spike has a recorded ship/defer decision
- [ ] Example passes the documented MCP auth compliance profile
- [ ] `pytest asap-compliance/tests/test_mcp_auth.py -v` green
