# Sprint S1: OpenAPI Adapter (Python)

**PRD**: [v2.3 §4.1](../../../product-specs/prd/prd-v2.3-scale.md) — OA-001..011 (P0)
**Branch**: `feat/openapi-adapter-python`
**PR Scope**: Auto-derive ASAP capabilities from OpenAPI 3.x specs. Python package `asap.adapters.openapi` with one-call API + reference example.
**Depends on**: v2.2 capability model + constraints + streaming detection

## Relevant Files

### New Files
- `src/asap/adapters/__init__.py` — adapters namespace
- `src/asap/adapters/openapi/__init__.py` — public API: `create_from_openapi`, `OpenAPIAdapterConfig`
- `src/asap/adapters/openapi/spec_loader.py` — fetch + parse via `openapi-pydantic`
- `src/asap/adapters/openapi/capability_mapper.py` — operationId → capability name; schemas → input/output JSON Schema
- `src/asap/adapters/openapi/handler.py` — Execution handler proxying to upstream HTTP API
- `src/asap/adapters/openapi/approval.py` — `approval_strength` per HTTP method/operation
- `tests/adapters/openapi/test_capability_mapper.py`
- `tests/adapters/openapi/test_handler.py`
- `tests/adapters/openapi/integration/test_e2e_petstore.py` — E2E with PetStore OpenAPI spec
- `examples/openapi_petstore/` — runnable example onboarding the public PetStore spec

### Modified Files
- `pyproject.toml` — Add `openapi-pydantic>=0.5` dependency (optional extra `[openapi]`)
- `src/asap/__init__.py` — Re-export `create_from_openapi` for convenience
- `docs/adapters/openapi.md` — Adapter usage guide

## Tasks

### 1.0 Scaffolding & Dependencies (TDD-first)

- [ ] 1.1 Add `openapi-pydantic` optional extra
  - **File**: `pyproject.toml`
  - **What**: `[project.optional-dependencies] openapi = ["openapi-pydantic>=0.5"]`
  - **Verify**: `uv sync --extra openapi`

- [ ] 1.2 Write failing E2E test (TDD)
  - **File**: `tests/adapters/openapi/integration/test_e2e_petstore.py`
  - **What**: Load `https://petstore3.swagger.io/api/v3/openapi.json` (or fixture), call `create_from_openapi(spec_url=...)`, register against test ASAP server, invoke `findPetsByStatus` capability, assert response shape
  - **Verify**: Red

### 2.0 Spec Loading & Capability Mapping

- [ ] 2.1 Spec loader
  - **File**: `src/asap/adapters/openapi/spec_loader.py`
  - **What**: `async def load_spec(url_or_path) -> OpenAPI` using `openapi-pydantic`. Support both URL (httpx) and local file. Validate version 3.x.
  - **Verify**: Unit tests with fixture specs

- [ ] 2.2 Capability mapper (OA-002, OA-003, OA-004, OA-005)
  - **File**: `src/asap/adapters/openapi/capability_mapper.py`
  - **What**: For each operation: `operationId` → capability name; `summary`/`description` → description; merge `parameters` + `requestBody.content[application/json].schema` → input JSON Schema; `responses["200"].content[application/json].schema` (fallback `"201"`) → output JSON Schema
  - **Verify**: Unit tests covering: GET with path/query params, POST with JSON body, response with `$ref`, missing operationId fallback to `<method>_<path>`

- [ ] 2.3 `default_capabilities` filter (OA-007)
  - **What**: Accept `"GET"`, `["GET", "HEAD"]`, `"all"`, or callable `(operation) -> bool`. Apply at capability selection time.
  - **Verify**: Three test cases per filter type

### 3.0 Execution Handler

- [ ] 3.1 Handler skeleton (OA-001, OA-006)
  - **File**: `src/asap/adapters/openapi/handler.py`
  - **What**: `async def execute(capability_name, args, session) -> dict`. Map args back to path params (template substitution), query params, headers, request body. Use `httpx.AsyncClient` for upstream call.
  - **Verify**: Unit tests with mocked httpx

- [ ] 3.2 `resolve_headers` callback (OA-009)
  - **What**: Accept callable `(session) -> dict[str, str]`. Inject into upstream request headers (e.g., `Authorization: Bearer <user-token>`).
  - **Verify**: Test that headers are merged correctly; unauthorized callback raises `RecoverableError`

- [ ] 3.3 Response type auto-detection (OA-010)
  - **What**: Inspect `responses[].content[]` keys. `text/event-stream` → register as streaming handler; `202` (`Accepted`) with `Location` → register as async with polling; default → sync.
  - **Verify**: Three test scenarios

### 4.0 Approval Strength Mapping

- [ ] 4.1 `approval_strength` configuration (OA-008)
  - **File**: `src/asap/adapters/openapi/approval.py`
  - **What**: Accept dict by HTTP method `{"GET": "session", "POST": "webauthn", "DELETE": "webauthn"}` OR by operationId. Wire into capability registration so write operations require fresh-session/WebAuthn (per v2.2.1).
  - **Verify**: Unit tests; integration test that `DELETE` requires WebAuthn assertion when `agent_controls_browser=True`

### 5.0 Reference Example & Docs

- [ ] 5.1 PetStore example
  - **File**: `examples/openapi_petstore/`
  - **What**: README + `main.py` invoking `create_from_openapi` against PetStore spec, registering capabilities, running an agent that calls `findPetsByStatus`. Include Compliance Harness v2 check.
  - **Verify**: `uv run python examples/openapi_petstore/main.py` succeeds end-to-end

- [ ] 5.2 Documentation
  - **File**: `docs/adapters/openapi.md`
  - **What**: Architecture overview, usage examples, configuration reference, common pitfalls (auth, polymorphism, large specs)
  - **Verify**: Reviewed by another contributor; cross-linked from `docs/index.md`

## Acceptance Criteria

- [ ] All tests pass (red → green)
- [ ] Coverage ≥90% on `src/asap/adapters/openapi/`
- [ ] `uv run mypy` clean
- [ ] `uv run ruff check` clean
- [ ] PetStore example runs end-to-end
- [ ] Compliance Harness v2 score 1.0 against the example
- [ ] OpenAPI 3.0 and 3.1 both supported

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| OpenAPI specs vary wildly in quality | Document supported subset; surface clear warnings for unsupported constructs (oneOf/anyOf at top level, etc.) |
| Upstream API requires complex auth | Provide `resolve_headers` callback; document patterns (Bearer, API key, OAuth2 client credentials) |
| Large specs (Stripe, AWS) generate hundreds of capabilities | Document `default_capabilities` filtering; warn on >100 operations |
| `text/event-stream` upstream conflicts with ASAP streaming envelope format | Document the bridging behavior; provide a `stream_passthrough=True` option for raw passthrough |
