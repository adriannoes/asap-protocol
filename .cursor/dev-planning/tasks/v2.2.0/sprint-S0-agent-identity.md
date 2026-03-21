# Sprint S0: Per-Runtime-Agent Identity

**PRD**: §4.1 Per-Runtime-Agent Identity (P0)
**Branch**: `feat/agent-identity`
**PR Scope**: Host→Agent hierarchy, Ed25519 keypairs, registration, status, revocation, JWT verification

## Prerequisites
- [x] v2.1.1 Tech Debt cleared
- [x] A2H Integration completed
- [ ] ADR for per-runtime-agent identity created and accepted (SD-12)

## Relevant Files

### New Files
- `src/asap/auth/identity.py` — `HostIdentity`, `AgentSession` models, `HostStore`, `AgentStore` protocols, `jwk_thumbprint_sha256`, `InMemoryHostStore`, `InMemoryAgentStore`
- `src/asap/auth/agent_jwt.py` — Host/Agent JWT create + verify (`JwtVerifyResult`, `JtiReplayCache`), explicit `exp`/`iat`/`jti` checks
- `tests/auth/test_identity.py` — Identity model validation, protocol checks, in-memory store CRUD and cascade tests
- `tests/auth/test_agent_jwt.py` — JWT creation/verification tests

### Modified Files
- `src/asap/transport/server.py` — New `/asap/agent/*` endpoints
- `src/asap/auth/__init__.py` — Export new symbols
- `tests/transport/test_server.py` — Endpoint tests

---

## Tasks

### 1.0 Create Identity Models

- [x] 1.1 Create `HostIdentity` and `AgentSession` Pydantic models
  - **File**: `src/asap/auth/identity.py` (create)
  - **What**: Define models per PRD §4.1:
    - `HostIdentity` — `host_id: str`, `name: str | None`, `public_key: dict` (JWK), `user_id: str | None`, `default_capabilities: list[str]`, `status: Literal["active", "pending", "revoked"]`, `created_at: datetime`, `updated_at: datetime`
    - `AgentSession` — `agent_id: str`, `host_id: str`, `public_key: dict` (JWK), `mode: Literal["delegated", "autonomous"]`, `status: Literal["pending", "active", "expired", "revoked"]`, `session_ttl: timedelta | None`, `max_lifetime: timedelta | None`, `absolute_lifetime: timedelta | None`, `activated_at: datetime | None`, `last_used_at: datetime | None`, `created_at: datetime`
    - Both with `ConfigDict(extra="forbid")`
  - **Verify**: `uv run pytest tests/auth/test_identity.py`

- [x] 1.2 Create `HostStore` and `AgentStore` protocols
  - **File**: `src/asap/auth/identity.py` (extend)
  - **What**: `@runtime_checkable` Protocol interfaces:
    - `HostStore` — `async def save(host)`, `async def get(host_id)`, `async def get_by_public_key(thumbprint)`, `async def revoke(host_id)`
    - `AgentStore` — `async def save(agent)`, `async def get(agent_id)`, `async def list_by_host(host_id)`, `async def revoke(agent_id)`, `async def revoke_by_host(host_id)`
  - **Verify**: Protocol is runtime-checkable

- [x] 1.3 Create in-memory store implementations
  - **File**: `src/asap/auth/identity.py` (extend)
  - **What**: `InMemoryHostStore` and `InMemoryAgentStore` implementing the protocols. Simple dict-based storage for development/testing.
  - **Verify**: `uv run pytest tests/auth/test_identity.py`

- [x] 1.4 Write identity model tests
  - **File**: `tests/auth/test_identity.py` (create)
  - **What**: Test model validation, extra field rejection, protocol conformance, in-memory store CRUD, host revocation cascading to agents.
  - **Verify**: All tests pass

### 2.0 Create Agent JWT System

- [x] 2.1 Create Host JWT and Agent JWT builders
  - **File**: `src/asap/auth/agent_jwt.py` (create)
  - **What**:
    - `create_host_jwt(host_keypair, aud, agent_public_key=None)` — Signs JWT with `typ: host+jwt`, `iss` = JWK thumbprint (RFC 7638 SHA-256), includes `host_public_key` and optional `agent_public_key` claims
    - `create_agent_jwt(agent_keypair, host_thumbprint, agent_id, aud, capabilities=None)` — Signs JWT with `typ: agent+jwt`, `iss` = host thumbprint, `sub` = agent_id, 60s TTL, optional `capabilities` claim
    - Both use Ed25519 (`alg: EdDSA`)
  - **Verify**: Round-trip: create → verify signature → extract claims

- [x] 2.2 Create JWT verification functions
  - **File**: `src/asap/auth/agent_jwt.py` (extend)
  - **What**:
    - `verify_host_jwt(token, host_store)` — Checks `typ`, verifies signature against stored/inline public key, validates `exp`/`iat`/`jti`, resolves host by `iss` or dynamic registration
    - `verify_agent_jwt(token, host_store, agent_store)` — Full verification per PRD: check `typ`, resolve host by `iss`, resolve agent by `sub`, check agent status, verify signature, check `exp`/`iat`/`jti`, resolve capabilities
  - **Verify**: Tests for valid JWT, expired JWT, revoked agent, unknown host, replay (`jti` reuse)

- [x] 2.3 Implement `jti` replay detection cache
  - **File**: `src/asap/auth/agent_jwt.py` (extend)
  - **What**: `JtiReplayCache` — in-memory cache with 90s TTL window (60s JWT lifetime + 30s clock skew). Partitioned by identity (agent_id or host_id). Uses `dict` with periodic cleanup.
  - **Verify**: Duplicate `jti` within window is rejected; `jti` after window expires is accepted

- [x] 2.4 Write JWT tests
  - **File**: `tests/auth/test_agent_jwt.py` (create)
  - **What**: Tests for Host JWT creation/verification, Agent JWT creation/verification, `jti` replay detection, expired JWT rejection, `typ` mismatch rejection, `aud` validation, capability restriction in JWT.
  - **Verify**: `uv run pytest tests/auth/test_agent_jwt.py`

### 3.0 Create Agent Registration Endpoints

- [ ] 3.1 Add `POST /asap/agent/register` endpoint
  - **File**: `src/asap/transport/server.py` (modify)
  - **What**: Accepts Host JWT with agent public key. Creates `AgentSession` under the host. Returns `agent_id`, `host_id`, `status`. If host is unknown, creates it in `pending` state. Idempotent: re-registering a `pending` agent returns existing state.
  - **Verify**: `uv run pytest tests/transport/test_server.py -k "register"`

- [ ] 3.2 Add `GET /asap/agent/status` endpoint
  - **File**: `src/asap/transport/server.py` (modify)
  - **What**: Host JWT auth. Returns agent status, capability grants (empty for now — capabilities come in S1), lifecycle info. Query param `agent_id`.
  - **Verify**: Test with active, pending, expired, revoked agents

- [ ] 3.3 Add `POST /asap/agent/revoke` endpoint
  - **File**: `src/asap/transport/server.py` (modify)
  - **What**: Host JWT auth. Permanently revokes an agent. Returns `{"agent_id": "...", "status": "revoked"}`.
  - **Verify**: Revoked agent cannot authenticate

- [ ] 3.4 Add `POST /asap/agent/rotate-key` endpoint
  - **File**: `src/asap/transport/server.py` (modify)
  - **What**: Host JWT auth. Replaces agent's public key. Old key stops working immediately.
  - **Verify**: Old JWT rejected, new JWT accepted after rotation

- [ ] 3.5 Ensure backward compatibility with existing OAuth2
  - **File**: `src/asap/transport/server.py` (modify)
  - **What**: Existing `POST /asap` endpoint continues to accept OAuth2 Bearer tokens. New agent identity is opt-in, not mandatory. Both auth paths coexist.
  - **Verify**: Existing tests still pass without modification

### 4.0 Update Exports and Documentation

- [ ] 4.1 Update `auth/__init__.py` exports
  - **File**: `src/asap/auth/__init__.py` (modify)
  - **What**: Export `HostIdentity`, `AgentSession`, `HostStore`, `AgentStore`, `create_host_jwt`, `create_agent_jwt`, `verify_host_jwt`, `verify_agent_jwt`
  - **Verify**: `from asap.auth import HostIdentity, AgentSession` works

---

## Definition of Done

- [ ] `HostIdentity` and `AgentSession` models with full validation
- [ ] Host JWT and Agent JWT creation and verification working
- [ ] `jti` replay detection with 90s TTL cache
- [ ] `/asap/agent/register`, `/status`, `/revoke`, `/rotate-key` endpoints operational
- [ ] Existing OAuth2 flow unaffected (backward compatible)
- [ ] Test coverage >= 90% for new code
- [ ] `uv run mypy src/asap/auth/` passes
- [ ] `uv run ruff check src/asap/auth/` passes
