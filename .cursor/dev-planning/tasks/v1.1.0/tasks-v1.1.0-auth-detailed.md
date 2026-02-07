# Tasks: ASAP v1.1.0 Auth & Discovery (S1-S2) - Detailed

> **Sprints**: S1-S2 - OAuth2, OIDC, and Discovery
> **Goal**: Identity foundation and basic agent discovery
> **Prerequisites**: v1.0.0 completed (Core Protocol)
> **Estimated Duration**: 2 weeks

---

## Relevant Files

### Sprint S1: OAuth2 Foundation
- `src/asap/auth/__init__.py` - Auth module init
- `src/asap/auth/oauth2.py` - OAuth2 client and server integration
- `src/asap/auth/oidc.py` - OIDC discovery
- `tests/auth/test_oauth2.py` - OAuth2 tests
- `tests/auth/test_oidc.py` - OIDC tests

### Sprint S2: Discovery
- `src/asap/discovery/__init__.py` - Discovery module init
- `src/asap/discovery/wellknown.py` - Well-known endpoint
- `src/asap/discovery/dns_sd.py` - DNS-SD support (optional)
- `tests/discovery/test_wellknown.py` - Discovery tests

---

## Sprint S1: OAuth2 Foundation

**Context**: v1.1.0 establishes the Identity Layer for ASAP. OAuth2/OIDC provides enterprise-grade authentication, enabling agents to authenticate with external identity providers (Auth0, Keycloak, Azure AD). This is a prerequisite for the Trust Layer (v1.2.0).

### Task 1.1: OAuth2 Client

**Goal**: Implement OAuth2 client that can obtain and refresh access tokens using client_credentials flow.

**Context**: Agents need to authenticate with OAuth2 providers to prove their identity. The client_credentials flow is used for machine-to-machine auth (agent-to-agent), while authorization_code is for human-in-the-loop scenarios.

**Prerequisites**: None (first task of v1.1.0)

#### Sub-tasks

- [ ] 1.1.1 Add httpx-oauth dependency
  - **File**: `pyproject.toml` (modify existing)
  - **What**: Add `httpx-oauth>=0.13` to dependencies section
  - **Why**: httpx-oauth provides OAuth2 client implementation compatible with our async httpx client
  - **Command**: `uv add "httpx-oauth>=0.13"`
  - **Verify**: `uv run python -c "import httpx_oauth; print(httpx_oauth.__version__)"` succeeds

- [ ] 1.1.2 Create auth module structure
  - **File**: `src/asap/auth/__init__.py` (create new)
  - **File**: `src/asap/auth/oauth2.py` (create new)
  - **What**: Create auth module directory with empty `__init__.py` and `oauth2.py` skeleton
  - **Why**: Separates auth concerns from transport layer, enables future auth methods (mTLS, API keys)
  - **Pattern**: Follow structure of `src/asap/transport/` module
  - **Verify**: `from asap.auth import oauth2` imports without error

- [ ] 1.1.3 Implement OAuth2ClientCredentials class
  - **File**: `src/asap/auth/oauth2.py` (modify)
  - **What**: Create `OAuth2ClientCredentials` class with:
    - `__init__(client_id: str, client_secret: str, token_url: str)`
    - `async def get_access_token() -> Token` - obtains new token
    - `Token` model with `access_token`, `expires_at`, `token_type` fields
  - **Why**: client_credentials is the standard flow for machine-to-machine auth
  - **Pattern**: Wrap httpx-oauth's `OAuth2ClientCredentialsClient` with ASAP-specific Token model
  - **Reference**: https://www.oauth.com/oauth2-servers/access-tokens/client-credentials/
  - **Verify**: Unit test can mock token endpoint and receive valid Token

- [ ] 1.1.4 Implement automatic token refresh
  - **File**: `src/asap/auth/oauth2.py` (modify)
  - **What**: Add to `OAuth2ClientCredentials`:
    - `_cached_token: Optional[Token]` private field
    - `async def get_valid_token() -> Token` - returns cached if valid, refreshes if expired
    - Refresh 30 seconds before actual expiry to prevent race conditions
  - **Why**: Avoids repeated token requests, handles token expiry gracefully
  - **Pattern**: Similar to how `ManifestCache` handles TTL in `src/asap/models/entities.py`
  - **Verify**: Test shows token is reused when valid, refreshed when near expiry

- [ ] 1.1.5 Add authorization_code flow skeleton (Optional P2)
  - **File**: `src/asap/auth/oauth2.py` (modify)
  - **What**: Create `OAuth2AuthorizationCode` class stub with TODO comments
  - **Why**: Placeholder for human-in-the-loop auth (not needed for agent-to-agent)
  - **Note**: Implementation deferred to v1.1.1+, only create interface now
  - **Verify**: Class exists and is importable

- [ ] 1.1.6 Write comprehensive unit tests
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

- [ ] 1.1.7 Commit milestone
  - **Command**: `git add src/asap/auth/ tests/auth/ pyproject.toml && git commit -m "feat(auth): add OAuth2 client with client_credentials flow"`
  - **Scope**: All files created in 1.1.1-1.1.6
  - **Verify**: `git log -1` shows correct commit message

**Acceptance Criteria**:
- [ ] OAuth2 client can obtain tokens from any standard OAuth2 provider
- [ ] Tokens are cached and auto-refreshed
- [ ] Test coverage >95% for auth module
- [ ] No breaking changes to existing API

---

### Task 1.2: OAuth2 Server Integration

**Goal**: Protect ASAP server endpoints with OAuth2 token validation.

**Context**: While Task 1.1 enables agents to obtain tokens, this task enables servers to validate incoming tokens. This is the "receiving side" of OAuth2.

**Prerequisites**: Task 1.1 completed (OAuth2 client exists)

#### Sub-tasks

- [ ] 1.2.1 Create token validation middleware
  - **File**: `src/asap/auth/middleware.py` (create new)
  - **What**: Create `OAuth2Middleware` class that:
    - Extracts `Authorization: Bearer <token>` header
    - Validates JWT signature using JWKS
    - Extracts claims (`sub`, `scope`, `exp`)
    - Returns 401 if invalid, 403 if insufficient scope
  - **Why**: Central validation point for all protected endpoints
  - **Pattern**: Follow FastAPI middleware pattern in `src/asap/transport/server.py`
  - **Verify**: Middleware rejects requests without valid Bearer token

- [ ] 1.2.2 Define and enforce scope-based authorization
  - **File**: `src/asap/auth/scopes.py` (create new)
  - **What**: Define scope constants and decorator:
    - `SCOPE_READ = "asap:read"` - query agent info
    - `SCOPE_EXECUTE = "asap:execute"` - send task requests
    - `SCOPE_ADMIN = "asap:admin"` - manage agent
    - `@require_scope("asap:execute")` decorator for handlers
  - **Why**: Fine-grained access control for different operations
  - **Pattern**: Similar to FastAPI's `Security` dependency
  - **Verify**: Decorator blocks requests missing required scope

- [ ] 1.2.3 Integrate OAuth2 with ASAPServer
  - **File**: `src/asap/transport/server.py` (modify existing)
  - **What**: Add optional OAuth2 config to server:
    - `ASAPServer(manifest, oauth2_config=OAuth2Config(...))`
    - If config provided, apply middleware to all /asap/* routes
    - If not provided, allow unauthenticated (backward compat)
  - **Why**: Opt-in security for gradual adoption
  - **Pattern**: Similar to how rate limiting is optionally applied
  - **Verify**: Server works with and without OAuth2 config

- [ ] 1.2.4 Add token introspection for opaque tokens
  - **File**: `src/asap/auth/introspection.py` (create new)
  - **What**: Implement introspection client for non-JWT tokens:
    - `async def introspect(token: str) -> TokenInfo`
    - Call provider's introspection endpoint
    - Cache results (TTL = token remaining lifetime)
  - **Why**: Some providers use opaque tokens instead of JWTs
  - **Reference**: https://www.oauth.com/oauth2-servers/token-introspection/
  - **Verify**: Introspection correctly identifies valid/invalid tokens

- [ ] 1.2.5 Write integration tests
  - **File**: `tests/auth/test_middleware.py` (create new)
  - **What**: Test scenarios:
    - Protected endpoint rejects missing token (401)
    - Protected endpoint rejects expired token (401)
    - Protected endpoint rejects insufficient scope (403)
    - Valid token with correct scope succeeds (200)
  - **Why**: Auth is security-critical, needs thorough testing
  - **Pattern**: Use `pytest-httpx` for mocking, `respx` for JWKS mock
  - **Verify**: `pytest tests/auth/test_middleware.py -v` all pass

- [ ] 1.2.6 Commit milestone
  - **Command**: `git add src/asap/auth/ tests/auth/ && git commit -m "feat(auth): add token validation middleware and scopes"`
  - **Scope**: middleware.py, scopes.py, introspection.py, test_middleware.py
  - **Verify**: `git log -1` shows correct message

**Acceptance Criteria**:
- [ ] Middleware validates JWTs and opaque tokens
- [ ] Scopes enforced per endpoint
- [ ] Backward compatible (works without OAuth2)
- [ ] Test coverage >95%

---

### Task 1.3: OIDC Discovery

**Goal**: Auto-configure OAuth2 client from OpenID Connect discovery endpoint.

**Context**: Instead of manually configuring token_url, jwks_uri, etc., OIDC discovery lets us fetch all configuration from `/.well-known/openid-configuration`. This simplifies integration with identity providers.

**Prerequisites**: Task 1.1 completed (OAuth2 client exists)

#### Sub-tasks

- [ ] 1.3.1 Implement OIDC discoverer
  - **File**: `src/asap/auth/oidc.py` (create new)
  - **What**: Create `OIDCDiscovery` class:
    - `__init__(issuer_url: str)`
    - `async def discover() -> OIDCConfig` - fetches `{issuer}/.well-known/openid-configuration`
    - `OIDCConfig` model with `token_endpoint`, `jwks_uri`, `issuer`, `scopes_supported`
  - **Why**: Standard way to configure OAuth2 for any OIDC provider
  - **Reference**: https://openid.net/specs/openid-connect-discovery-1_0.html
  - **Verify**: Can discover Auth0, Keycloak, Azure AD configs

- [ ] 1.3.2 Implement JWKS validation
  - **File**: `src/asap/auth/jwks.py` (create new)
  - **What**: Create `JWKSValidator` class:
    - `async def fetch_keys(jwks_uri: str) -> List[JWK]`
    - `def validate_jwt(token: str, keys: List[JWK]) -> Claims`
    - Handle key rotation (unknown `kid` triggers refresh)
  - **Why**: JWTs must be validated with provider's public keys
  - **Pattern**: Use `python-jose` or `pyjwt` for JWT handling
  - **Verify**: Validates tokens signed by mocked JWKS

- [ ] 1.3.3 Add caching for discovery and JWKS
  - **File**: `src/asap/auth/oidc.py` (modify)
  - **What**: Add caching layer:
    - Discovery config: TTL 1 hour
    - JWKS keys: TTL 24 hours, refresh on unknown `kid`
    - Use thread-safe cache (similar to `ManifestCache`)
  - **Why**: Avoid repeated HTTP calls, handle key rotation gracefully
  - **Pattern**: Follow `ManifestCache` pattern in `src/asap/models/entities.py`
  - **Verify**: Second call uses cache, unknown kid triggers refresh

- [ ] 1.3.4 Write tests with mock OIDC provider
  - **File**: `tests/auth/test_oidc.py` (create new)
  - **What**: Test scenarios:
    - Discovery fetches and parses config correctly
    - JWKS fetches and caches keys
    - JWT validation succeeds with valid token
    - JWT validation fails with expired/invalid token
    - Unknown kid triggers JWKS refresh
  - **Why**: OIDC integration is complex, needs thorough testing
  - **Pattern**: Use `respx` to mock HTTP endpoints
  - **Verify**: `pytest tests/auth/test_oidc.py -v` all pass

- [ ] 1.3.5 Commit milestone
  - **Command**: `git commit -m "feat(auth): add OIDC discovery and JWKS validation"`
  - **Scope**: oidc.py, jwks.py, test_oidc.py
  - **Verify**: `git log -1` shows correct message

**Acceptance Criteria**:
- [ ] OIDC discovery auto-configures OAuth2 client
- [ ] JWKS validation works with key rotation
- [ ] Caching reduces HTTP calls
- [ ] Test coverage >95%

---

## Sprint S2: Well-Known Discovery

**Context**: Well-known discovery enables agents to find each other without prior configuration. An agent can query `https://agent.example.com/.well-known/asap/manifest.json` to get capabilities, endpoints, and version info. This is the foundation for the Registry in v1.2.0.

### Task 2.1: Well-Known Endpoint

**Goal**: Serve agent manifest at standardized well-known URI.

**Context**: Following RFC 8615 (Well-Known URIs), we establish `/.well-known/asap/manifest.json` as the discovery endpoint for ASAP agents.

**Prerequisites**: Sprint S1 completed

#### Sub-tasks

- [ ] 2.1.1 Create discovery module
  - **File**: `src/asap/discovery/__init__.py` (create new)
  - **File**: `src/asap/discovery/wellknown.py` (create new)
  - **What**: Create discovery module with wellknown endpoint handler
  - **Why**: Separates discovery concerns from auth and transport
  - **Pattern**: Follow `src/asap/auth/` module structure
  - **Verify**: `from asap.discovery import wellknown` imports

- [ ] 2.1.2 Implement well-known route handler
  - **File**: `src/asap/discovery/wellknown.py` (modify)
  - **What**: Create FastAPI route:
    - `GET /.well-known/asap/manifest.json`
    - Returns server's `Manifest` as JSON
    - Sets `Content-Type: application/json`
  - **Why**: Standard endpoint for agent discovery
  - **Reference**: RFC 8615 - Well-Known URIs
  - **Verify**: Curl returns valid JSON manifest

- [ ] 2.1.3 Integrate with ASAPServer
  - **File**: `src/asap/transport/server.py` (modify existing)
  - **What**: Auto-register well-known route when manifest provided:
    - If `ASAPServer(manifest=my_manifest)` → register /.well-known/asap/manifest.json
    - If no manifest → skip (for client-only scenarios)
  - **Why**: Seamless integration with existing server setup
  - **Pattern**: Similar to how other routes are registered in `create_app()`
  - **Verify**: Server with manifest serves well-known endpoint

- [ ] 2.1.4 Add HTTP caching headers
  - **File**: `src/asap/discovery/wellknown.py` (modify)
  - **What**: Add response headers:
    - `Cache-Control: public, max-age=300` (5 minutes)
    - `ETag` based on manifest hash
    - Support `If-None-Match` for 304 responses
  - **Why**: Reduces load on agent servers, speeds up discovery
  - **Pattern**: Standard HTTP caching patterns
  - **Verify**: Second request with ETag returns 304

- [ ] 2.1.5 Write tests
  - **File**: `tests/discovery/__init__.py` (create new)
  - **File**: `tests/discovery/test_wellknown.py` (create new)
  - **What**: Test scenarios:
    - Endpoint returns valid manifest JSON
    - Content-Type is application/json
    - Cache headers present and correct
    - ETag conditional requests work
  - **Why**: Discovery is critical for agent ecosystem
  - **Verify**: `pytest tests/discovery/test_wellknown.py -v` all pass

- [ ] 2.1.6 Commit milestone
  - **Command**: `git commit -m "feat(discovery): add well-known manifest endpoint"`
  - **Scope**: discovery/, test_wellknown.py, server.py changes
  - **Verify**: `git log -1` shows correct message

**Acceptance Criteria**:
- [ ] Well-known endpoint serves manifest
- [ ] Caching headers reduce repeated requests
- [ ] Integration with ASAPServer is seamless

---

### Task 2.2: Manifest Discovery Client

**Goal**: Enable clients to discover agents from their base URL.

**Context**: The counterpart to Task 2.1 - this enables clients to fetch manifests. It's the "consuming side" of well-known discovery.

**Prerequisites**: Task 2.1 completed

#### Sub-tasks

- [ ] 2.2.1 Add discover method to ASAPClient
  - **File**: `src/asap/transport/client.py` (modify existing)
  - **What**: Add method:
    - `async def discover(base_url: str) -> Manifest`
    - Fetches `{base_url}/.well-known/asap/manifest.json`
    - Parses response into `Manifest` model
    - Respects Cache-Control and ETag
  - **Why**: Standard way to discover agent capabilities
  - **Pattern**: Similar to existing `send()` method patterns
  - **Verify**: Client can discover manifest from test server

- [ ] 2.2.2 Cache discovered manifests
  - **File**: `src/asap/transport/client.py` (modify)
  - **What**: Integrate with existing `ManifestCache`:
    - Store discovered manifests with TTL
    - Key by base URL
    - Respect Cache-Control max-age if provided
  - **Why**: Avoid repeated discovery requests
  - **Pattern**: Use existing `ManifestCache` from `src/asap/models/entities.py`
  - **Verify**: Second discover() call uses cached manifest

- [ ] 2.2.3 Add manifest validation
  - **File**: `src/asap/discovery/validation.py` (create new)
  - **What**: Validate discovered manifests:
    - Schema validation (required fields present)
    - Version compatibility check
    - Capability matching (does agent support requested skill?)
  - **Why**: Prevent runtime errors from malformed manifests
  - **Verify**: Invalid manifest raises descriptive error

- [ ] 2.2.4 Write integration tests
  - **File**: `tests/discovery/test_discovery_client.py` (create new)
  - **What**: Test scenarios:
    - Client discovers manifest from running server
    - Cache is used on subsequent requests
    - Invalid manifest raises clear error
    - Network errors handled gracefully
  - **Why**: Discovery is foundational for agent interaction
  - **Verify**: `pytest tests/discovery/test_discovery_client.py -v` all pass

- [ ] 2.2.5 Commit milestone
  - **Command**: `git commit -m "feat(discovery): add client-side manifest discovery"`
  - **Scope**: client.py changes, validation.py, test_discovery_client.py
  - **Verify**: `git log -1` shows correct message

**Acceptance Criteria**:
- [ ] Client can discover agents from URL
- [ ] Manifests are cached
- [ ] Invalid manifests produce clear errors

---

### Task 2.3: DNS-SD Support (Optional P3)

**Goal**: Enable local network agent discovery via mDNS/DNS-SD.

**Context**: For development and LAN scenarios, agents can advertise themselves via DNS-SD (like how printers use Bonjour). This is Optional/P3 - can be deferred to v1.1.1+.

**Prerequisites**: Tasks 2.1, 2.2 completed

#### Sub-tasks

- [ ] 2.3.1 Add zeroconf dependency
  - **File**: `pyproject.toml` (modify)
  - **What**: Add to optional dependencies: `[project.optional-dependencies] dns-sd = ["zeroconf>=0.80"]`
  - **Why**: zeroconf is the Python library for mDNS/DNS-SD
  - **Command**: `uv add --optional "zeroconf>=0.80"`
  - **Verify**: `uv run python -c "import zeroconf"` with dns-sd extra

- [ ] 2.3.2 Implement service registration
  - **File**: `src/asap/discovery/dnssd.py` (create new)
  - **What**: Create `DNSSDAdvertiser` class:
    - Service type: `_asap._tcp.local.`
    - TXT records: `version`, `capabilities`, `manifest_url`
    - `start()` / `stop()` lifecycle methods
  - **Why**: Allows LAN discovery without registry
  - **Reference**: https://www.dns-sd.org/
  - **Verify**: Service appears in Bonjour browser

- [ ] 2.3.3 Implement service browser
  - **File**: `src/asap/discovery/dnssd.py` (modify)
  - **What**: Create `DNSSDDiscovery` class:
    - `async def browse() -> List[AgentInfo]`
    - Event callbacks: `on_service_added`, `on_service_removed`
    - Parse TXT records into AgentInfo
  - **Why**: Complementary to advertiser - discover nearby agents
  - **Verify**: Browser finds advertised test agent

- [ ] 2.3.4 Write tests (with mocking)
  - **File**: `tests/discovery/test_dnssd.py` (create new)
  - **What**: Test with mocked zeroconf:
    - Service registration works
    - Browser discovers services
    - TXT records parsed correctly
  - **Note**: Network tests may need skip markers for CI
  - **Verify**: `pytest tests/discovery/test_dnssd.py -v` passes

- [ ] 2.3.5 Commit milestone
  - **Command**: `git commit -m "feat(discovery): add DNS-SD/mDNS support (optional)"`
  - **Scope**: dnssd.py, test_dnssd.py, pyproject.toml
  - **Verify**: `git log -1` shows correct message

**Acceptance Criteria**:
- [ ] Agents can advertise via DNS-SD
- [ ] Agents can discover nearby agents
- [ ] Works offline (no internet needed)

---

### Task 2.4: Mark Sprints S1-S2 Complete

**Goal**: Finalize v1.1.0 Identity Layer sprints.

**Context**: Checkpoint task to verify all S1-S2 deliverables are complete and update tracking.

**Prerequisites**: All tasks 1.1-2.3 completed

#### Sub-tasks

- [ ] 2.4.1 Update roadmap progress
  - **File**: `tasks-v1.1.0-roadmap.md` (modify)
  - **What**: Mark S1 and S2 tasks as complete `[x]`, update progress percentage
  - **Verify**: Progress shows 100% for S1-S2

- [ ] 2.4.2 Verify all acceptance criteria met
  - **What**: Manually verify:
    - OAuth2 client_credentials flow works ✓
    - Token validation middleware works ✓
    - OIDC discovery works ✓
    - Well-known endpoint serves manifest ✓
    - Client discovery works ✓
  - **Verify**: All criteria checked off

- [ ] 2.4.3 Run full test suite
  - **Command**: `pytest tests/auth tests/discovery -v --cov`
  - **What**: Verify all new tests pass with >95% coverage
  - **Verify**: No failures, coverage target met

- [ ] 2.4.4 Commit checkpoint
  - **Command**: `git commit -m "chore: mark v1.1.0 S1-S2 complete"`
  - **Verify**: Clean commit with progress updates

**Acceptance Criteria**:
- [ ] All S1-S2 tasks complete
- [ ] Test suite passes
- [ ] Progress tracked in roadmap

---

**S1-S2 Definition of Done**:
- [ ] OAuth2 client_credentials flow working
- [ ] Token validation middleware functional
- [ ] OIDC auto-discovery working
- [ ] Well-known endpoint serving manifest
- [ ] Client discovery method working
- [ ] Test coverage >95%
- [ ] Progress tracked in roadmap

**Total Sub-tasks**: ~45

