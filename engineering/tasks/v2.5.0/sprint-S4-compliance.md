# Sprint S4: Compliance Harness (v2.5.0)

**PRD**: [MCP-DISC-003, MCP-AUTH-007, §7 DoD, §9 metrics](../../../product/prd/prd-v2.5.0-mcp-auth-bridge.md)
**Branch**: `feat/v2.5.0-s4-compliance` → merge into **`release/2.5.0`**
**Depends on**: [S3 example](./sprint-S3-docs-examples.md)

**Trigger:** Release gate for v2.5.0.
**Enables:** S5 version bump and PyPI publish.
**Depends on:** `asap-compliance` package; protected stdio MCP example from S3.

---

## Execution notes

> **Status:** S4 gate green on `feat/v2.5.0-s4-compliance` — acceptance criteria satisfied locally; PR into `release/2.5.0` pending merge.
> **Branch:** `feat/v2.5.0-s4-compliance` → PR into `release/2.5.0`.

### Dependency phases

```text
Phase 1 (parallel)                 Phase 2 (parallel)              Phase 3 (gate)
──────────────────                 ──────────────────              ──────────────
1.1 lock gate            ──────►  1.2 + 1.3 + 2.1              Final verify + acceptance
3.2 stdio integration             2.2 README (draft → final)
3.1 CI release/2.5.0              (README finalizes after 2.1 command)
4.1 TS spike doc
```

### Sequential vs parallel summary

| Must be sequential | Safe to parallelize |
|--------------------|---------------------|
| **1.1 → 1.2 → 1.3 → 2.1** (single validator module + harness wire-up) | Stdio integration, CI, and TS spike can proceed from day one |
| **2.1 → 2.2 finalize** (README documents exact compliance command) | Compliance lock, stdio integration, CI, and TS spike can proceed in Phase 1 |
| **All → acceptance** (profile green against example + pytest suite) | README draft can proceed before the 2.1 command is locked |

### Implementation notes

- **Release gate:** Profile name is **`mcp-auth-bridge`** (not `mcp_auth`). Implement in `asap-compliance`, not `src/asap/testing/compliance.py` (HTTP/ASGI harness v2 stays unchanged unless S4 explicitly adds shared support).
- **Black-box checks (MCP-AUTH-007):** (a) unauthenticated `tools/call` on protected tool → error; (b) valid JWT → success; (c) wrong capability → denied; (d) constraint violation → `asap:constraint_violation`. Start with **mocked** MCP responses in unit tests; add subprocess driver against `examples/mcp_auth_bridge/server.py` in 2.1 verify.
- **Manifest alignment (MCP-DISC-003):** manifest-declared tools/capabilities ⊆ registered MCP tools / mapped capabilities; use fixture JSON when live `manifest_url` unavailable.
- **Stdio driver pattern:** subprocess `uv run python examples/mcp_auth_bridge/server.py`, JSON-RPC on stdin/stdout; mirror JWT minting from `tests/adapters/mcp/conftest.py` (copy setup, do not import test modules from example code).
- **Example tools:** `echo` = public; `secure_action` = protected — same as S3 example.
- **CI gap:** `ci.yml` currently triggers only on `main`; task 3.1 adds `release/2.5.0` (and optionally `release/**`) so PRs into the integration branch run `tests/adapters/mcp/`. Full suite already includes them via `uv run pytest -n auto`; explicit step is optional but documents the gate.
- **TS spike (SHOULD):** Survey `packages/typescript/` layout, `@modelcontextprotocol/sdk` version/compatibility, package name `@asap-protocol/mcp-auth`; record **ship vs defer** for S5 with minimum scope (Bearer extraction + error mapping).
- **No secrets:** Generate keys at runtime in tests; never commit JWTs or private keys.
- **Verify gate:** `uv run pytest asap-compliance/tests/test_mcp_auth.py -v`; `uv run pytest tests/adapters/mcp/ -v`; compliance profile against example documented in README.

---

## Relevant Files

### New / modify
- `asap-compliance/asap_compliance/validators/mcp_auth.py` — MCP auth bridge checks (profile `mcp-auth-bridge`)
- `asap-compliance/asap_compliance/config.py` — `McpAuthComplianceConfig` + stdio subprocess defaults
- `asap-compliance/asap_compliance/harness.py` — exports `validate_mcp_auth` / `validate_mcp_auth_async`
- `asap-compliance/asap_compliance/validators/__init__.py` — export new validator
- `asap-compliance/tests/test_mcp_auth.py` — mocked + subprocess integration tests
- `asap-compliance/tests/fixtures/mcp_auth_bridge_manifest.json` — MCP-DISC-003 fixture
- `examples/mcp_auth_bridge/server.py` — `ASAP_MCP_COMPLIANCE=1` probe JWT emission on stderr
- `src/asap/mcp/client.py` — optional `subprocess_env` for compliance driver
- `tests/adapters/mcp/test_stdio_integration.py` — end-to-end stdio protected MCPServer integration (task 3.2)
- `engineering/tasks/v2.5.0/typescript-mcp-auth-spike.md` — spike result or defer rationale

### Reference
- `asap-compliance/asap_compliance/validators/handshake.py` — result/check structure precedent, not the MCP auth gate itself
- `examples/openapi_petstore/` — example package structure pattern

---

## Tasks

### 1.0 Validator design

- [x] 1.1 Lock compliance gate
  - **File**: `asap-compliance/asap_compliance/validators/mcp_auth.py` (create)
  - **What**: Treat `asap-compliance` profile `mcp-auth-bridge` as the release gate for stdio MCP. Do not rely on `src/asap/testing/compliance.py` unless S4 explicitly adds shared HTTP/ASGI support.
  - **Why**: v2.5.0 validates native MCP stdio auth, while the existing harness v2 is HTTP/ASGI-focused.
  - **Verify**: S4 README or test output names `mcp-auth-bridge` as the gate.

- [x] 1.2 Define MCP auth compliance checks
  - **File**: `asap-compliance/asap_compliance/validators/mcp_auth.py` (create)
  - **What**: Black-box checks: (a) unauthenticated `tools/call` on protected tool returns error; (b) valid JWT succeeds; (c) wrong capability denied; (d) constraint violation returns `asap:constraint_violation`. Config: stdio subprocess or test server URL.
  - **Why**: MCP-AUTH-007
  - **Pattern**: Reuse the `CheckResult` shape from `validators/handshake.py`; wrap checks in an MCP-specific result object if the CLI needs summary metadata.
  - **Verify**: Unit tests with mocked server responses first

- [x] 1.3 Define manifest alignment compliance check
  - **File**: `asap-compliance/asap_compliance/validators/mcp_auth.py` (create)
  - **What**: Validate manifest-declared tool/capability names are a subset of registered MCP tools or mapped capabilities, using example fixture data when a live manifest URL is unavailable.
  - **Why**: MCP-DISC-003
  - **Verify**: Unit test fails when manifest declares an unknown tool/capability.

### 2.0 Integration with harness

- [x] 2.1 Wire validator into compliance CLI
  - **File**: `asap-compliance/asap_compliance/validators/__init__.py` + main runner if exists
  - **What**: Optional profile `mcp-auth-bridge` targeting the stdio example server. If shared `src/asap/testing/compliance.py` support is needed, add it explicitly rather than assuming the HTTP harness covers stdio MCP.
  - **Verify**: `uv run` compliance against `examples/mcp_auth_bridge` passes required checks

- [x] 2.2 Example compliance script or README section
  - **File**: `examples/mcp_auth_bridge/README.md`
  - **What**: Document command to run the `asap-compliance` `mcp-auth-bridge` profile and expected pass/fail checks.
  - **Verify**: CI or local script passes

### 3.0 Regression tests

- [x] 3.1 Full adapter test suite in CI
  - **File**: root CI workflow or existing pytest job
  - **What**: Ensure `tests/adapters/mcp/` runs on every PR to `release/2.5.0`
  - **Verify**: PR check green

- [x] 3.2 End-to-end stdio integration test
  - **File**: `tests/adapters/mcp/test_auth_middleware.py` or `tests/adapters/mcp/test_stdio_integration.py`
  - **What**: Exercise protected `MCPServer` over stdio/subprocess with a real Agent JWT in `_meta.asap_agent_jwt`, including one success and one denied call.
  - **Why**: PRD DoD requires unit + integration tests with mock Agent JWT.
  - **Verify**: Test runs headless in the normal pytest suite.

### 4.0 TypeScript middleware spike

- [x] 4.1 Decide ship vs defer for `@asap-protocol/mcp-auth`
  - **File**: `engineering/tasks/v2.5.0/typescript-mcp-auth-spike.md` (create)
  - **What**: Check current `packages/typescript/` layout, `@modelcontextprotocol/sdk` compatibility, package naming, and minimum implementation needed for Bearer extraction + error mapping.
  - **Why**: MCP-TS-001..003 are SHOULD, but the release must record a deliberate ship/defer decision.
  - **Verify**: S5 has either shipped package tasks or a linked v2.5.0.1 defer note in CHANGELOG/backlog.

---

## Acceptance Criteria (S4)

- [x] MCP auth validator returns pass/fail `CheckResult` for auth required, valid JWT, wrong capability, and constraint violation paths
- [x] Manifest alignment check covers manifest tools/capabilities ⊆ registered MCP tools/mapped capabilities
- [x] `asap-compliance` `mcp-auth-bridge` profile is the documented release gate for stdio MCP
- [x] Protected stdio MCP integration test passes in pytest
- [x] TypeScript middleware spike has a recorded ship/defer decision
- [x] Example passes the documented MCP auth compliance profile
- [x] `pytest asap-compliance/tests/test_mcp_auth.py -v` green
