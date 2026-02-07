# Sprint S1: OAuth2 Foundation

> **Goal**: Implement OAuth2 client and server support
> **Prerequisites**: v1.0.0 completed (Core Protocol)
> **Parent Roadmap**: [tasks-v1.1.0-roadmap.md](./tasks-v1.1.0-roadmap.md)

---

## Relevant Files

- `pyproject.toml` - Dependencies: authlib>=1.3, joserfc>=1.0 (ADR-12) ✅
- `src/asap/auth/__init__.py` - Auth module init (created)
- `src/asap/auth/oauth2.py` - OAuth2 client with Token model and OAuth2ClientCredentials
- `src/asap/auth/oidc.py` - OIDC discovery with 1h cache (uses Authlib OpenID client)
- `src/asap/auth/jwks.py` - JWKS validation with 24h cache, refresh on unknown kid (uses joserfc)
- `src/asap/auth/introspection.py` - Token introspection for opaque tokens (RFC 7662)
- `src/asap/auth/middleware.py` - OAuth2 JWT validation middleware (JWKS via joserfc)
- `src/asap/auth/scopes.py` - Scope constants and require_scope dependency
- `tests/auth/__init__.py` - Auth test package
- `tests/auth/test_oauth2.py` - OAuth2 unit tests
- `tests/auth/test_oidc.py` - OIDC tests
- `tests/auth/test_introspection.py` - Token introspection tests
- `tests/auth/test_jwks.py` - JWKS validation tests
- `tests/auth/test_middleware.py` - Middleware tests
- `tests/auth/test_scopes.py` - Scope dependency tests
- `tests/auth/test_server_oauth2_integration.py` - create_app with/without oauth2_config

---

## Context

v1.1.0 establishes the Identity Layer for ASAP. OAuth2/OIDC provides enterprise-grade authentication, enabling agents to authenticate with external identity providers (Auth0, Keycloak, Azure AD). This is a prerequisite for the Trust Layer (v1.2.0).

---

## Task 1.1: OAuth2 Client

**Goal**: Implement OAuth2 client that can obtain and refresh access tokens using client_credentials flow.

**Context**: Agents need to authenticate with OAuth2 providers to prove their identity. The client_credentials flow is used for machine-to-machine auth (agent-to-agent), while authorization_code is for human-in-the-loop scenarios.

**Prerequisites**: None (first task of v1.1.0)

### Sub-tasks

- [x] ~~1.1.1 Add httpx-oauth dependency~~ → Replaced by 1.1.1a
  - **Status**: Superseded by ADR-12. httpx-oauth does not support client_credentials.

- [x] 1.1.1a Replace httpx-oauth with authlib + joserfc
  - **File**: `pyproject.toml` (modify existing)
  - **What**: Replace `httpx-oauth>=0.13` with `authlib>=1.3` and `joserfc>=1.0` in dependencies
  - **Why**: Authlib provides native client_credentials, OIDC discovery, and FastAPI integration. joserfc provides modern JWT/JWKS validation. See ADR-12.
  - **Command**: `uv remove httpx-oauth && uv add "authlib>=1.3" "joserfc>=1.0"`
  - **Verify**: `uv run python -c "import authlib; import joserfc; print('OK')"` succeeds

- [x] 1.1.2 Create auth module structure
  - **File**: `src/asap/auth/__init__.py` (create new)
  - **File**: `src/asap/auth/oauth2.py` (create new)
  - **What**: Create auth module directory with empty `__init__.py` and `oauth2.py` skeleton
  - **Why**: Separates auth concerns from transport layer, enables future auth methods (mTLS, API keys)
  - **Pattern**: Follow structure of `src/asap/transport/` module
  - **Verify**: `from asap.auth import oauth2` imports without error

- [x] 1.1.3 Implement OAuth2ClientCredentials class
  - **File**: `src/asap/auth/oauth2.py` (modify)
  - **What**: Create `OAuth2ClientCredentials` class with:
    - `__init__(client_id: str, client_secret: str, token_url: str)`
    - `async def get_access_token() -> Token`
    - `Token` model with `access_token`, `expires_at`, `token_type` fields
  - **Why**: client_credentials is the standard flow for machine-to-machine auth
  - **Pattern**: Use Authlib's `AsyncOAuth2Client` internally, expose ASAP-specific `Token` model (ADR-12)
  - **Reference**: https://www.oauth.com/oauth2-servers/access-tokens/client-credentials/
  - **Verify**: Unit test can mock token endpoint and receive valid Token

- [x] 1.1.4 Implement automatic token refresh
  - **File**: `src/asap/auth/oauth2.py` (modify)
  - **What**: Add to `OAuth2ClientCredentials`:
    - `_cached_token: Optional[Token]` private field
    - `async def get_valid_token() -> Token` - returns cached if valid, refreshes if expired
    - Refresh 30 seconds before actual expiry to prevent race conditions
  - **Why**: Avoids repeated token requests, handles token expiry gracefully
  - **Pattern**: Similar to how `ManifestCache` handles TTL in `src/asap/models/entities.py`
  - **Verify**: Test shows token is reused when valid, refreshed when near expiry

- [x] 1.1.5 Add authorization_code flow skeleton (Optional P2)
  - **File**: `src/asap/auth/oauth2.py` (modify)
  - **What**: Create `OAuth2AuthorizationCode` class stub with TODO comments
  - **Why**: Placeholder for human-in-the-loop auth (not needed for agent-to-agent)
  - **Note**: Implementation deferred to v1.1.1+, only create interface now
  - **Verify**: Class exists and is importable

- [x] 1.1.6 Write comprehensive unit tests
  - **File**: `tests/auth/__init__.py` (create new)
  - **File**: `tests/auth/test_oauth2.py` (create new)
  - **What**: Test suite covering:
    - Token acquisition with mocked token endpoint
    - Token caching behavior
    - Auto-refresh before expiry
    - Error handling (invalid credentials, network errors)
  - **Why**: OAuth2 is security-critical, needs thorough testing
  - **Pattern**: Follow test patterns in `tests/transport/unit/test_client.py`
  - **Verify**: `pytest tests/auth/test_oauth2.py -v` passes with >95% coverage

- [x] 1.1.7 Commit milestone
  - **Command**: `git add src/asap/auth/ tests/auth/ pyproject.toml && git commit -m "feat(auth): add OAuth2 client with client_credentials flow"`
  - **Scope**: All files created in 1.1.1-1.1.6
  - **Verify**: `git log -1` shows correct commit message

**Acceptance Criteria**:
- [x] OAuth2 client can obtain tokens from any standard OAuth2 provider
- [x] Tokens are cached and auto-refreshed
- [x] Test coverage >95% for auth module
- [x] No breaking changes to existing API

---

## Task 1.2: OAuth2 Server Integration

**Goal**: Protect ASAP server endpoints with OAuth2 token validation.

**Context**: While Task 1.1 enables agents to obtain tokens, this task enables servers to validate incoming tokens. This is the "receiving side" of OAuth2.

**Prerequisites**: Task 1.1 completed (OAuth2 client exists)

### Sub-tasks

- [x] 1.2.1 Create token validation middleware
  - **File**: `src/asap/auth/middleware.py` (create new)
  - **What**: Create `OAuth2Middleware` class that:
    - Extracts `Authorization: Bearer <token>` header
    - Validates JWT signature using JWKS via `joserfc`
    - Extracts claims (`sub`, `scope`, `exp`)
    - Returns 401 if invalid, 403 if insufficient scope
  - **Why**: Central validation point for all protected endpoints
  - **Pattern**: Follow FastAPI middleware pattern in `src/asap/transport/server.py`. Use `joserfc.jwt.decode()` for JWT validation (ADR-12).
  - **Verify**: Middleware rejects requests without valid Bearer token

- [x] 1.2.2 Define and enforce scope-based authorization
  - **File**: `src/asap/auth/scopes.py` (create new)
  - **What**: Define scope constants and decorator:
    - `SCOPE_READ = "asap:read"` - query agent info
    - `SCOPE_EXECUTE = "asap:execute"` - send task requests
    - `SCOPE_ADMIN = "asap:admin"` - manage agent
    - `@require_scope("asap:execute")` decorator for handlers
  - **Why**: Fine-grained access control for different operations
  - **Pattern**: Similar to FastAPI's `Security` dependency
  - **Verify**: Decorator blocks requests missing required scope

- [x] 1.2.3 Integrate OAuth2 with ASAPServer
  - **File**: `src/asap/transport/server.py` (modify existing)
  - **What**: Add optional OAuth2 config to server:
    - `ASAPServer(manifest, oauth2_config=OAuth2Config(...))`
    - If config provided, apply middleware to all /asap/* routes
    - If not provided, allow unauthenticated (backward compat)
  - **Why**: Opt-in security for gradual adoption
  - **Pattern**: Similar to how rate limiting is optionally applied
  - **Verify**: Server works with and without OAuth2 config

- [x] 1.2.4 Add token introspection for opaque tokens
  - **File**: `src/asap/auth/introspection.py` (create new)
  - **What**: Implement introspection client for non-JWT tokens:
    - `async def introspect(token: str) -> TokenInfo`
    - Call provider's introspection endpoint
    - Cache results (TTL = token remaining lifetime)
  - **Why**: Some providers use opaque tokens instead of JWTs
  - **Reference**: https://www.oauth.com/oauth2-servers/token-introspection/
  - **Verify**: Introspection correctly identifies valid/invalid tokens

- [x] 1.2.5 Write integration tests
  - **File**: `tests/auth/test_middleware.py` (create new)
  - **What**: Test scenarios:
    - Protected endpoint rejects missing token (401)
    - Protected endpoint rejects expired token (401)
    - Protected endpoint rejects insufficient scope (403)
    - Valid token with correct scope succeeds (200)
  - **Why**: Auth is security-critical, needs thorough testing
  - **Pattern**: Use `pytest-httpx` for mocking, `respx` for JWKS mock
  - **Verify**: `pytest tests/auth/test_middleware.py -v` all pass

- [x] 1.2.6 Commit milestone
  - **Command**: `git add src/asap/auth/ tests/auth/ && git commit -m "feat(auth): add token validation middleware and scopes"`
  - **Scope**: middleware.py, scopes.py, introspection.py, test_middleware.py
  - **Verify**: `git log -1` shows correct message

**Acceptance Criteria**:
- [x] Middleware validates JWTs and opaque tokens
- [x] Scopes enforced per endpoint
- [x] Backward compatible (works without OAuth2)
- [x] Test coverage >95%

---

## Task 1.3: OIDC Discovery

**Goal**: Auto-configure OAuth2 client from OpenID Connect discovery endpoint.

**Context**: Instead of manually configuring token_url, jwks_uri, etc., OIDC discovery lets us fetch all configuration from `/.well-known/openid-configuration`. This simplifies integration with identity providers.

**Prerequisites**: Task 1.1 completed (OAuth2 client exists)

### Sub-tasks

- [x] 1.3.1 Implement OIDC discoverer
  - **File**: `src/asap/auth/oidc.py` (create new)
  - **What**: Create `OIDCDiscovery` class:
    - `__init__(issuer_url: str)`
    - `async def discover() -> OIDCConfig`
    - `OIDCConfig` model with `token_endpoint`, `jwks_uri`, `issuer`, `scopes_supported`
  - **Why**: Standard way to configure OAuth2 for any OIDC provider
  - **Pattern**: Leverage Authlib's OpenID client for fetching config. Wrap with ASAP-specific `OIDCConfig` model (ADR-12).
  - **Reference**: https://openid.net/specs/openid-connect-discovery-1_0.html
  - **Verify**: Can discover Auth0, Keycloak, Azure AD configs

- [x] 1.3.2 Implement JWKS validation
  - **File**: `src/asap/auth/jwks.py` (create new)
  - **What**: Create `JWKSValidator` class:
    - `async def fetch_keys(jwks_uri: str) -> List[JWK]`
    - `def validate_jwt(token: str, keys: List[JWK]) -> Claims`
    - Handle key rotation (unknown `kid` triggers refresh)
  - **Why**: JWTs must be validated with provider's public keys
  - **Pattern**: Use `joserfc` for JWT/JWK handling. See ADR-12.
  - **Verify**: Validates tokens signed by mocked JWKS

- [x] 1.3.3 Add caching for discovery and JWKS
  - **File**: `src/asap/auth/oidc.py` (modify)
  - **What**: Add caching layer:
    - Discovery config: TTL 1 hour
    - JWKS keys: TTL 24 hours, refresh on unknown `kid`
    - Use thread-safe cache (similar to `ManifestCache`)
  - **Why**: Avoid repeated HTTP calls, handle key rotation gracefully
  - **Pattern**: Follow `ManifestCache` pattern in `src/asap/models/entities.py`
  - **Verify**: Second call uses cache, unknown kid triggers refresh

- [x] 1.3.4 Write tests with mock OIDC provider
  - **File**: `tests/auth/test_jwks.py` – JWKS unit tests
  - **File**: `tests/auth/test_oidc.py` (create new)
  - **What**: Test scenarios:
    - Discovery fetches and parses config correctly
    - OIDC + JWKS integration
    - JWT validation with OIDC-discovered jwks_uri
    - Expired/invalid token rejection
  - **Why**: OIDC integration is complex, needs thorough testing
  - **Pattern**: Use httpx.MockTransport for mocking
  - **Verify**: `pytest tests/auth/test_jwks.py tests/auth/test_oidc.py -v` all pass

- [x] 1.3.5 Commit milestone
  - **Command**: `git commit -m "feat(auth): add OIDC discovery and JWKS validation"`
  - **Scope**: oidc.py, jwks.py, test_jwks.py, test_oidc.py
  - **Verify**: `git log -1` shows correct message

**Acceptance Criteria**:
- [x] OIDC discovery auto-configures OAuth2 client
- [x] JWKS validation works with key rotation
- [x] Caching reduces HTTP calls
- [x] Test coverage >95%

---

## Sprint S1 Definition of Done

- [x] OAuth2 client_credentials flow working
- [x] Token validation middleware functional
- [x] OIDC auto-discovery working
- [x] Test coverage >95%
- [x] Progress tracked in roadmap

**Total Sub-tasks**: ~25
