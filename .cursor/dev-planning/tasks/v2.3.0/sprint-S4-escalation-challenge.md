# Sprint S4: Capability Escalation + ASAP Challenge

**PRD**: [v2.3 §4.4](../../../product-specs/prd/prd-v2.3-scale.md) — ESC-001..004 (P1); [v2.3 §4.5](../../../product-specs/prd/prd-v2.3-scale.md) — CHAL-001..004 (P2)
**Branch**: `feat/escalation-challenge`
**PR Scope**: Runtime capability escalation endpoint + WWW-Authenticate ASAP challenge middleware. Both supporting features for OpenAPI-derived agents and silent uplift of existing APIs.
**Depends on**: S1 (OpenAPI Adapter — escalation client tool) + S2 (TypeScript SDK `requestCapability`)

## Relevant Files

### New Files
- `src/asap/transport/escalation_routes.py` — `POST /asap/agent/request-capability` endpoint
- `src/asap/transport/challenge.py` — `WWWAuthenticateASAPMiddleware` + `WWWAuthenticateASAPChallenge` model
- `tests/transport/test_escalation_routes.py`
- `tests/transport/test_challenge_middleware.py`
- `tests/transport/integration/test_escalation_flow.py` — End-to-end: agent requests new capability → approval flow → grant active
- `docs/capabilities/escalation.md` — Capability escalation guide
- `docs/transport/asap-challenge.md` — WWW-Authenticate ASAP guide

### Modified Files
- `src/asap/transport/server.py` — Register escalation routes + challenge middleware
- `src/asap/auth/capabilities.py` — Add `request_capability(agent_id, capabilities)` helper
- `src/asap/transport/client.py` — Python `request_capability` client tool (ESC-004)
- `packages/typescript/client/src/connection.ts` — TS `requestCapability` (already in S2 TS-005, this sprint validates it)
- `src/asap/adapters/openapi/handler.py` — Auto-emit ASAP challenge on 401 from upstream (CHAL-004)

## Tasks

### 1.0 Capability Escalation (ESC-001..004)

- [ ] 1.1 Write failing E2E test (TDD)
  - **File**: `tests/transport/integration/test_escalation_flow.py`
  - **What**: Active agent calls `POST /asap/agent/request-capability` with new capability list. Approval flow triggers (Device Auth or A2H). User approves. Status transitions to `active` for new grants. Original capabilities remain untouched.
  - **Verify**: Red

- [ ] 1.2 Endpoint implementation (ESC-001, ESC-002, ESC-003)
  - **File**: `src/asap/transport/escalation_routes.py`
  - **What**: `POST /asap/agent/request-capability` with body `{capabilities: [{name, constraints}]}`. Validate Agent JWT. For each capability: if it requires consent, create `ApprovalObject` with `pending` status; otherwise mark `active`. Agent itself remains `active`.
  - **Verify**: Three test scenarios: all auto-grant, all need approval, mixed

- [ ] 1.3 Python client tool (ESC-004)
  - **File**: `src/asap/transport/client.py` (modify)
  - **What**: `async def request_capability(self, agent_id, capabilities) -> CapabilityRequestReceipt`. Polls `/asap/agent/status` until grant resolution.
  - **Verify**: Integration test with mocked approval

- [ ] 1.4 Validate TS client tool
  - **File**: `packages/typescript/client/src/connection.ts`
  - **What**: Cross-check S2 TS-005 implementation matches Python semantics. Add additional TS test if missing.
  - **Verify**: TS Vitest covers escalation flow with mocked server

### 2.0 WWW-Authenticate ASAP Challenge (CHAL-001..004)

- [ ] 2.1 Challenge middleware (CHAL-001)
  - **File**: `src/asap/transport/challenge.py`
  - **What**: `WWWAuthenticateASAPMiddleware` injects `WWW-Authenticate: ASAP discovery="..."` header on 401 responses from protected routes. Configurable: `discovery_url` per route, fallback to global default.
  - **Verify**: Unit test with `httpx`/`starlette` test client

- [ ] 2.2 Client recognition (CHAL-002)
  - **File**: `src/asap/transport/client.py` (modify)
  - **What**: On 401 with `WWW-Authenticate: ASAP`, parse `discovery="..."`, fetch manifest, kick off registration flow if no agent identity present. Configurable: `auto_register: bool` (default False — opt-in for safety).
  - **Verify**: Integration test simulating unknown agent hitting protected endpoint

- [ ] 2.3 403 capability_not_granted (CHAL-003)
  - **What**: When JWT present but capability missing, return 403 with `error.code = "capability_not_granted"` + `error.data.required_capability`. Client SDK can then call `request_capability` automatically (opt-in).
  - **Verify**: Two test cases: no token vs. token without capability

- [ ] 2.4 OpenAPI adapter integration (CHAL-004)
  - **File**: `src/asap/adapters/openapi/handler.py` (modify)
  - **What**: When upstream API returns 401, the OpenAPI handler emits the ASAP challenge in its own response. This lets ASAP clients silently discover and onboard against APIs proxied via the adapter.
  - **Verify**: E2E test: client hits OpenAPI-derived capability without auth → ASAP challenge → registration → retry succeeds

### 3.0 Documentation

- [ ] 3.1 Capability escalation guide
  - **File**: `docs/capabilities/escalation.md`
  - **What**: Use cases (long-running agent expanding scope), flow diagram, Python + TS examples, approval interaction
  - **Verify**: Cross-link from `docs/capabilities/index.md`

- [ ] 3.2 ASAP Challenge guide
  - **File**: `docs/transport/asap-challenge.md`
  - **What**: Resource-server middleware setup, client opt-in (`auto_register`), security considerations (open registration vs. rate-limited), interaction with v2.2.1 WebAuthn
  - **Verify**: Cross-link from main transport docs

## Acceptance Criteria

- [ ] All tests pass (TDD red → green)
- [ ] Coverage ≥90% on new modules
- [ ] `uv run mypy` and `ruff check` clean
- [ ] TS Vitest green for escalation flow
- [ ] At least one reference resource server (the OpenAPI PetStore example from S1) emits ASAP challenge on 401
- [ ] Client `auto_register` opt-in clearly documented as security consideration

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Capability escalation flooding approval queue | Reuse v2.2 rate limiting on registration; per-agent escalation cap |
| `auto_register` enabled by default would create attack surface | Default to `False`; require explicit opt-in; document the trade-off |
| ASAP challenge leaks discovery URL on every 401 | Document opt-out per route; only emit challenge for routes that support ASAP |
| Race between escalation request and agent expiry | Escalation extends `last_used_at` per LIFE-005; document the side effect |
