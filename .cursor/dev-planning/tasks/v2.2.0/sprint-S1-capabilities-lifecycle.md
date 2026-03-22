# Sprint S1: Capabilities & Lifecycle

**PRD**: §4.2 Capability-Based Authorization (P0), §4.3 Agent Lifecycle Management (P0)
**Branch**: `feat/capabilities-lifecycle`
**PR Scope**: Capability model, constraint operators, grant enforcement, lifecycle clocks, reactivation
**Depends on**: Sprint S0 (Agent Identity)

## Relevant Files

### New Files
- `src/asap/auth/capabilities.py` — `CapabilityDefinition`, `CapabilityGrant`, `CapabilityConstraint`, enforcement logic
- `src/asap/auth/lifecycle.py` — Lifetime clocks, expiry checker, reactivation logic
- `tests/auth/test_capabilities.py` — Capability and constraint tests
- `tests/auth/test_lifecycle.py` — Lifecycle clock tests

### Modified Files
- `src/asap/transport/server.py` — Capability endpoints, reactivation endpoint
- `src/asap/auth/identity.py` — Add capability grants to `AgentSession`
- `src/asap/auth/agent_jwt.py` — Capability restriction in JWT verification

---

## Tasks

### 1.0 Capability Models & Constraints

- [ ] 1.1 Create `CapabilityDefinition` model
  - **File**: `src/asap/auth/capabilities.py` (create)
  - **What**: `name: str`, `description: str`, `input_schema: dict | None` (JSON Schema), `output_schema: dict | None`, `location: str | None`. `ConfigDict(extra="forbid")`.
  - **Verify**: Model validates, rejects extra fields

- [ ] 1.2 Create `CapabilityConstraint` and operator logic
  - **File**: `src/asap/auth/capabilities.py` (extend)
  - **What**: Constraint value types — exact value or operator object. Operators: `max` (number, ≤), `min` (number, ≥), `in` (list, value must be in), `not_in` (list, value must not be in). Operators can combine on a single field. `validate_constraints(constraints, arguments)` function that returns list of violations.
  - **Verify**: Test each operator independently and combined

- [ ] 1.3 Create `CapabilityGrant` model
  - **File**: `src/asap/auth/capabilities.py` (extend)
  - **What**: `capability: str`, `status: Literal["active", "pending", "denied"]`, `constraints: dict[str, Any] | None`, `granted_by: str | None`, `reason: str | None`, `expires_at: datetime | None`. `ConfigDict(extra="forbid")`.
  - **Verify**: Active/pending/denied states, constraint attachment

- [ ] 1.4 Create `CapabilityRegistry` for server-side capability management
  - **File**: `src/asap/auth/capabilities.py` (extend)
  - **What**: `CapabilityRegistry` class — `register(definition)`, `list_capabilities(agent_id=None)`, `describe(name)`, `grant(agent_id, capability, constraints=None)`, `check_grant(agent_id, capability, arguments=None)`. The `check_grant` method enforces constraints and returns violations.
  - **Verify**: Grant checking with and without constraints

- [ ] 1.5 Write capability tests
  - **File**: `tests/auth/test_capabilities.py` (create)
  - **What**: Tests for each constraint operator, combined constraints, violation reporting, grant status transitions, `check_grant` with valid/invalid arguments, `constraint_violated` error with `violations` array.
  - **Verify**: `uv run pytest tests/auth/test_capabilities.py`

### 2.0 Agent Lifecycle Management

- [ ] 2.1 Create lifetime clock logic
  - **File**: `src/asap/auth/lifecycle.py` (create)
  - **What**:
    - `check_agent_expiry(agent: AgentSession) -> Literal["active", "expired", "revoked"]` — Evaluates 3 clocks:
      - Session TTL: `now - last_used_at > session_ttl` → expired
      - Max lifetime: `now - activated_at > max_lifetime` → expired
      - Absolute lifetime: `now - created_at > absolute_lifetime` → revoked (permanent)
    - `extend_session(agent: AgentSession) -> AgentSession` — Updates `last_used_at` to now
    - `reactivate_agent(agent: AgentSession, host: HostIdentity) -> AgentSession` — Resets session TTL and max lifetime clocks; capabilities decay to host defaults; absolute lifetime NOT reset; fails if absolute lifetime exceeded
  - **Verify**: Each clock independently, combined, reactivation behavior

- [ ] 2.2 Integrate lifecycle into JWT verification
  - **File**: `src/asap/auth/agent_jwt.py` (modify)
  - **What**: After verifying agent JWT, call `check_agent_expiry()`. If expired, return `403 agent_expired`. If revoked, return `403 agent_revoked`. On success, call `extend_session()` to update `last_used_at`.
  - **Verify**: Expired agent gets 403, active agent's session extends

- [ ] 2.3 Write lifecycle tests
  - **File**: `tests/auth/test_lifecycle.py` (create)
  - **What**: Test session TTL expiry, max lifetime expiry, absolute lifetime revocation, reactivation success, reactivation failure (absolute exceeded), capability decay on reactivation.
  - **Verify**: `uv run pytest tests/auth/test_lifecycle.py`

### 3.0 Capability & Lifecycle Endpoints

- [ ] 3.1 Add `GET /asap/capability/list` endpoint
  - **File**: `src/asap/transport/server.py` (modify)
  - **What**: Returns lightweight capability listing. Three auth modes: no auth (public caps), Host JWT (user's caps), Agent JWT (caps with grant_status). Supports `query`, `cursor`, `limit` params.
  - **Verify**: Test all three auth modes

- [ ] 3.2 Add `GET /asap/capability/describe` endpoint
  - **File**: `src/asap/transport/server.py` (modify)
  - **What**: `?name=<capability_name>`. Returns full detail with input/output schemas. 404 if not found.
  - **Verify**: Existing and non-existing capability names

- [ ] 3.3 Add `POST /asap/capability/execute` endpoint
  - **File**: `src/asap/transport/server.py` (modify)
  - **What**: Agent JWT auth. Validates JWT → checks agent has active grant → enforces constraints → executes capability → returns result. On constraint violation, returns `403` with `constraint_violated` error and `violations` array.
  - **Verify**: Success, no grant (403), constraint violated (403 with violations)

- [ ] 3.4 Add `POST /asap/agent/reactivate` endpoint
  - **File**: `src/asap/transport/server.py` (modify)
  - **What**: Host JWT auth. Reactivates expired agent. Capabilities decay to host defaults. Returns agent status with grants. Fails for non-expired agents (active → no-op, revoked → 403).
  - **Verify**: Reactivation success, absolute lifetime exceeded failure

- [ ] 3.5 Update agent registration to include capabilities
  - **File**: `src/asap/transport/server.py` (modify)
  - **What**: `POST /asap/agent/register` now accepts `capabilities` field (list of capability names or objects with constraints). Returns `agent_capability_grants` array in response.
  - **Verify**: Registration with capabilities, partial approval (some granted, some denied)

- [ ] 3.6 Backward compatibility: OAuth scope → capability mapping
  - **File**: `src/asap/auth/capabilities.py` (extend)
  - **What**: `map_scopes_to_capabilities(scopes: list[str]) -> list[CapabilityGrant]` — Maps `SCOPE_READ` → all read capabilities, `SCOPE_EXECUTE` → all execute capabilities, `SCOPE_ADMIN` → all capabilities. Existing OAuth2 agents auto-get grants based on their scopes.
  - **Verify**: Existing OAuth2 tests still pass

---

## Definition of Done

- [ ] `CapabilityDefinition`, `CapabilityGrant`, `CapabilityConstraint` models working
- [ ] All constraint operators (`max`, `min`, `in`, `not_in`, exact) tested
- [ ] Constraint violation returns detailed `violations` array
- [ ] Three lifetime clocks (session, max, absolute) operational
- [ ] Reactivation with capability decay to host defaults
- [ ] `/capability/list`, `/capability/describe`, `/capability/execute` endpoints working
- [ ] `/agent/reactivate` endpoint working
- [ ] OAuth scope → capability mapping preserves backward compat
- [ ] Test coverage >= 90% for new code
- [ ] `uv run mypy src/asap/auth/` passes
