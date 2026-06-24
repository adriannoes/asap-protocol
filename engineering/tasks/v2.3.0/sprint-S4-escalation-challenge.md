# Sprint S4: Capability Escalation + ASAP Challenge

**PRD**: [v2.3 §4.4](../../../product/prd/prd-v2.3-scale.md) — ESC-001..004 (P1); [v2.3 §4.5](../../../product/prd/prd-v2.3-scale.md) — CHAL-001..004 (P2)
**Branch**: `feat/s4-escalation-challenge` (implementation); legacy doc name `feat/escalation-challenge`)
**PR Scope**: Runtime capability escalation endpoint + WWW-Authenticate ASAP challenge middleware. Both supporting features for OpenAPI-derived agents and silent uplift of existing APIs.
**Depends on**: S1 (OpenAPI Adapter — escalation client tool) + S2 (TypeScript SDK `requestCapability`)

## Relevant Files

### New Files
- `src/asap/transport/escalation_routes.py` — `POST /asap/agent/request-capability` (Agent JWT, Device/CIBA escalation approvals)
- `src/asap/transport/challenge.py` — `WWWAuthenticateASAPMiddleware`, `WWWAuthenticateASAPChallenge`, parse/format helpers, default discovery URL builder
- `tests/transport/test_escalation_routes.py` — ESC auto / all-approval / mixed scenarios
- `tests/transport/test_challenge_middleware.py` — CHAL-001 middleware + parse roundtrip + `request.state` override
- `tests/transport/integration/test_escalation_flow.py` — E2E: escalate → approve → status shows new active grants
- `tests/adapters/openapi/test_handler_upstream_401_challenge.py` — CHAL-004: upstream 401 adds `_www_authenticate_asap` on `FatalError`
- `docs/capabilities/index.md` — Capabilities doc index (links to escalation)
- `docs/capabilities/escalation.md` — Escalation guide (flow, Python/TS pointers)
- `docs/transport/asap-challenge.md` — Challenge + client `auto_register_on_asap_challenge` + OpenAPI JSON-RPC header behavior

### Modified Files
- `src/asap/transport/server.py` — `create_escalation_router()`, `WWWAuthenticateASAPMiddleware` (`asap_challenge_*` kwargs), JSON-RPC error strips internal `_www_authenticate_asap` into `WWW-Authenticate` response header
- `src/asap/auth/capabilities.py` — `escalation_requires_user_consent`, `partition_escalation_capability_specs` (ESC consent vs auto-grant split)
- `src/asap/auth/approval.py` — `ApprovalKind`, `approval_kind` on state/store `create`/`remove`, idempotent device/CIBA by kind
- `src/asap/transport/agent_routes.py` — Escalation apply-on-status + escalation pending UX; `_needs_registration_approval` → `escalation_requires_user_consent`
- `src/asap/transport/capability_routes.py` — CHAL-003 structured `403` `error.code = capability_not_granted` + `required_capability`
- `src/asap/transport/client.py` — `CapabilityRequestReceipt`, `request_capability()`, `auto_register_on_asap_challenge`, `_ingest_asap_challenge_401`, `last_asap_challenge_discovery_url`
- `src/asap/adapters/openapi/handler.py` — `asap_challenge_discovery_url` on upstream handler; 401 → challenge detail
- `src/asap/adapters/openapi/factory.py` — `asap_challenge_discovery_url` kwarg; default discovery from `asap_endpoint`
- `tests/transport/test_capability_routes.py` — Assertions for CHAL-003 + 401 `WWW-Authenticate` includes `ASAP`
- `packages/typescript/client/test/connection-errors.test.ts` — ESC TS parity: mocked active escalation JSON
- `docs/transport.md` — Link to `docs/transport/asap-challenge.md`

## Tasks

### 1.0 Capability Escalation (ESC-001..004)

- [x] 1.1 Write failing E2E test (TDD)
  - **File**: `tests/transport/integration/test_escalation_flow.py`
  - **What**: Active agent calls `POST /asap/agent/request-capability` with new capability list. Approval flow triggers (Device Auth or A2H). User approves. Status transitions to `active` for new grants. Original capabilities remain untouched.
  - **Verify**: Green

- [x] 1.2 Endpoint implementation (ESC-001, ESC-002, ESC-003)
  - **File**: `src/asap/transport/escalation_routes.py`
  - **What**: `POST /asap/agent/request-capability` with body `{capabilities: [{name, constraints}]}`. Validate Agent JWT. For each capability: if it requires consent, create `ApprovalObject` with `pending` status; otherwise mark `active`. Agent itself remains `active`.
  - **Verify**: Three test scenarios: all auto-grant, all need approval, mixed

- [x] 1.3 Python client tool (ESC-004)
  - **File**: `src/asap/transport/client.py` (modify)
  - **What**: `async def request_capability(self, agent_id, capabilities) -> CapabilityRequestReceipt`. Polls `/asap/agent/status` until grant resolution.
  - **Verify**: Implemented (Host JWT bearer for polling); integration covered via server tests; dedicated client+mock poll test optional follow-up

- [x] 1.4 Validate TS client tool
  - **File**: `packages/typescript/client/src/connection.ts`
  - **What**: Cross-check S2 TS-005 implementation matches Python semantics. Add additional TS test if missing.
  - **Verify**: Vitest `connection-errors.test.ts` — mocked active escalation response

### 2.0 WWW-Authenticate ASAP Challenge (CHAL-001..004)

- [x] 2.1 Challenge middleware (CHAL-001)
  - **File**: `src/asap/transport/challenge.py`
  - **What**: `WWWAuthenticateASAPMiddleware` injects `WWW-Authenticate: ASAP discovery="..."` header on 401 responses from protected routes. Configurable: `discovery_url` per route, fallback to global default.
  - **Verify**: `TestClient` in `test_challenge_middleware.py`

- [x] 2.2 Client recognition (CHAL-002)
  - **File**: `src/asap/transport/client.py` (modify)
  - **What**: On 401 with `WWW-Authenticate: ASAP`, parse `discovery="..."`, fetch manifest, kick off registration flow if no agent identity present. Configurable: `auto_register: bool` (default False — opt-in for safety).
  - **Verify**: `auto_register_on_asap_challenge` + best-effort `get_manifest(discovery)` on HTTP 401 from `POST /asap`; documented in `docs/transport/asap-challenge.md` (dedicated transport integration test optional)

- [x] 2.3 403 capability_not_granted (CHAL-003)
  - **What**: When JWT present but capability missing, return 403 with `error.code = "capability_not_granted"` + `error.data.required_capability`. Client SDK can then call `request_capability` automatically (opt-in).
  - **Verify**: `test_execute_no_grant_returns_403` + `test_execute_no_auth_returns_401` (Bearer + ASAP on `/asap/capability/execute`)

- [x] 2.4 OpenAPI adapter integration (CHAL-004)
  - **File**: `src/asap/adapters/openapi/handler.py` (modify)
  - **What**: When upstream API returns 401, the OpenAPI handler emits the ASAP challenge in its own response. This lets ASAP clients silently discover and onboard against APIs proxied via the adapter.
  - **Verify**: `test_handler_upstream_401_challenge.py` (FatalError details); JSON-RPC path adds `WWW-Authenticate` via `build_jsonrpc_error_for_asap_exception`. Full live PetStore E2E left as optional hardening.

### 3.0 Documentation

- [x] 3.1 Capability escalation guide
  - **File**: `docs/capabilities/escalation.md`
  - **What**: Use cases (long-running agent expanding scope), flow diagram, Python + TS examples, approval interaction
  - **Verify**: Cross-link from `docs/capabilities/index.md`

- [x] 3.2 ASAP Challenge guide
  - **File**: `docs/transport/asap-challenge.md`
  - **What**: Resource-server middleware setup, client opt-in (`auto_register`), security considerations (open registration vs. rate-limited), interaction with v2.2.1 WebAuthn
  - **Verify**: Cross-link from `docs/transport.md`

## Acceptance Criteria

- [x] All tests pass (TDD red → green) — targeted pytest + Vitest `connection-errors.test.ts`
- [ ] Coverage ≥90% on new modules — use full `pytest --cov=asap` in CI; **narrow** `--cov=asap.transport.escalation_routes` triggers a pytest-cov + `joserfc` `OKPKey`/`isinstance` interaction that breaks Host JWT signing in tests (do not use module-scoped cov for JWT-heavy tests alone)
- [x] `uv run mypy` and `ruff check` clean on touched transport/OpenAPI/client paths
- [x] TS Vitest green for escalation flow (`npx vitest run test/connection-errors.test.ts`)
- [x] OpenAPI adapter emits ASAP challenge metadata on upstream 401 (factory default discovery URL; handler unit test)
- [x] Client `auto_register` opt-in clearly documented as security consideration (`docs/transport/asap-challenge.md`)

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Capability escalation flooding approval queue | Reuse v2.2 rate limiting on registration; per-agent escalation cap |
| `auto_register` enabled by default would create attack surface | Default to `False`; require explicit opt-in; document the trade-off |
| ASAP challenge leaks discovery URL on every 401 | Document opt-out per route; only emit challenge for routes that support ASAP |
| Race between escalation request and agent expiry | Escalation extends `last_used_at` per LIFE-005; document the side effect |
