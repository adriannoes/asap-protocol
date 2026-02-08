# Sprint S2: Well-Known Discovery

> **Goal**: Implement basic discovery before Registry (serve and consume manifests)
> **Prerequisites**: Sprint S1 completed
> **Parent Roadmap**: [tasks-v1.1.0-roadmap.md](./tasks-v1.1.0-roadmap.md)

---

## Relevant Files

- `src/asap/discovery/__init__.py` - Discovery module init (created)
- `src/asap/discovery/wellknown.py` - Well-known endpoint handler (created)
- `src/asap/discovery/validation.py` - Manifest validation (created)
- `src/asap/discovery/dns_sd.py` - DNS-SD support (optional)
- `src/asap/transport/client.py` - Client discover() method (added), get_manifest()
- `src/asap/discovery/registry.py` - Lite Registry client (SD-11)
- `tests/discovery/__init__.py` - Discovery test package (created)
- `tests/discovery/test_wellknown.py` - Well-known endpoint tests (created)
- `tests/discovery/test_discovery_client.py` - Client discovery tests (created)
- `tests/discovery/test_dnssd.py` - DNS-SD tests (optional)

---

## Context

Well-known discovery enables agents to find each other without prior configuration. An agent can query `https://agent.example.com/.well-known/asap/manifest.json` to get capabilities, endpoints, and version info. This is the foundation for the Registry in v1.2.0.

---

## Task 2.1: Well-Known Endpoint ✅

**Goal**: Serve agent manifest at standardized well-known URI.

**Context**: Following RFC 8615 (Well-Known URIs), we establish `/.well-known/asap/manifest.json` as the discovery endpoint for ASAP agents.

**Prerequisites**: Sprint S1 completed

### Sub-tasks

- [x] 2.1.1 Create discovery module
  - **File**: `src/asap/discovery/__init__.py` (create new)
  - **File**: `src/asap/discovery/wellknown.py` (create new)
  - **What**: Create discovery module with wellknown endpoint handler
  - **Why**: Separates discovery concerns from auth and transport
  - **Pattern**: Follow `src/asap/auth/` module structure
  - **Verify**: `from asap.discovery import wellknown` imports

- [x] 2.1.2 Implement well-known route handler
  - **File**: `src/asap/discovery/wellknown.py` (modify)
  - **What**: Create FastAPI route:
    - `GET /.well-known/asap/manifest.json`
    - Returns server's `Manifest` as JSON
    - Sets `Content-Type: application/json`
  - **Why**: Standard endpoint for agent discovery
  - **Reference**: RFC 8615 - Well-Known URIs
  - **Verify**: Curl returns valid JSON manifest

- [x] 2.1.3 Integrate with ASAPServer
  - **File**: `src/asap/transport/server.py` (modify existing)
  - **What**: Auto-register well-known route when manifest provided:
    - If `ASAPServer(manifest=my_manifest)` → register /.well-known/asap/manifest.json
    - If no manifest → skip (for client-only scenarios)
  - **Why**: Seamless integration with existing server setup
  - **Pattern**: Similar to how other routes are registered in `create_app()`
  - **Verify**: Server with manifest serves well-known endpoint

- [x] 2.1.4 Add HTTP caching headers
  - **File**: `src/asap/discovery/wellknown.py` (modify)
  - **What**: Add response headers:
    - `Cache-Control: public, max-age=300` (5 minutes)
    - `ETag` based on manifest hash
    - Support `If-None-Match` for 304 responses
  - **Why**: Reduces load on agent servers, speeds up discovery
  - **Pattern**: Standard HTTP caching patterns
  - **Verify**: Second request with ETag returns 304

- [x] 2.1.5 Write tests
  - **File**: `tests/discovery/__init__.py` (create new)
  - **File**: `tests/discovery/test_wellknown.py` (create new)
  - **What**: Test scenarios:
    - Endpoint returns valid manifest JSON
    - Content-Type is application/json
    - Cache headers present and correct
    - ETag conditional requests work
  - **Why**: Discovery is critical for agent ecosystem
  - **Verify**: `pytest tests/discovery/test_wellknown.py -v` all pass

- [x] 2.1.6 Commit milestone
  - **Command**: `git commit -m "feat(discovery): add well-known manifest endpoint"`
  - **Scope**: discovery/, test_wellknown.py, server.py changes
  - **Verify**: `git log -1` shows correct message

**Acceptance Criteria**:
- [x] Well-known endpoint serves manifest
- [x] Caching headers reduce repeated requests
- [x] Integration with ASAPServer is seamless

---

## Task 2.2: Manifest Discovery Client

**Goal**: Enable clients to discover agents from their base URL.

**Context**: The counterpart to Task 2.1 - this enables clients to fetch manifests. It's the "consuming side" of well-known discovery.

**Prerequisites**: Task 2.1 completed

### Sub-tasks

- [x] 2.2.1 Add discover method to ASAPClient
  - **File**: `src/asap/transport/client.py` (modify existing)
  - **What**: Add method:
    - `async def discover(base_url: str) -> Manifest`
    - Fetches `{base_url}/.well-known/asap/manifest.json`
    - Parses response into `Manifest` model
    - Respects Cache-Control and ETag
  - **Why**: Standard way to discover agent capabilities
  - **Pattern**: Similar to existing `send()` method patterns
  - **Verify**: Client can discover manifest from test server

- [x] 2.2.2 Cache discovered manifests
  - **File**: `src/asap/transport/client.py` (modify)
  - **What**: Integrate with existing `ManifestCache`:
    - Store discovered manifests with TTL
    - Key by base URL
    - Respect Cache-Control max-age if provided
  - **Why**: Avoid repeated discovery requests
  - **Pattern**: Use existing `ManifestCache` from `src/asap/models/entities.py`
  - **Verify**: Second discover() call uses cached manifest

- [x] 2.2.3 Add manifest validation
  - **File**: `src/asap/discovery/validation.py` (create new)
  - **What**: Validate discovered manifests:
    - Schema validation (required fields present)
    - Version compatibility check
    - Capability matching (does agent support requested skill?)
  - **Why**: Prevent runtime errors from malformed manifests
  - **Verify**: Invalid manifest raises descriptive error

- [x] 2.2.4 Write integration tests
  - **File**: `tests/discovery/test_discovery_client.py` (create new)
  - **What**: Test scenarios:
    - Client discovers manifest from running server
    - Cache is used on subsequent requests
    - Invalid manifest raises clear error
    - Network errors handled gracefully
  - **Why**: Discovery is foundational for agent interaction
  - **Verify**: `pytest tests/discovery/test_discovery_client.py -v` all pass

- [x] 2.2.5 Commit milestone
  - **Command**: `git commit -m "feat(discovery): add client-side manifest discovery"`
  - **Scope**: client.py changes, validation.py, test_discovery_client.py
  - **Verify**: `git log -1` shows correct message

**Acceptance Criteria**:
- [x] Client can discover agents from URL
- [x] Manifests are cached
- [x] Invalid manifests produce clear errors

---

## Task 2.3: DNS-SD Support

**Goal**: Enable local network agent discovery via mDNS/DNS-SD.

**Context**: For development and LAN scenarios, agents can advertise themselves via DNS-SD (like how printers use Bonjour). This is Optional/P3 - can be deferred to v1.1.1+.

**Prerequisites**: Tasks 2.1, 2.2 completed

### Sub-tasks

- [x] 2.3.1 Add zeroconf dependency
  - **File**: `pyproject.toml` (modify)
  - **What**: Add to optional dependencies: `[project.optional-dependencies] dns-sd = ["zeroconf>=0.80"]`
  - **Why**: zeroconf is the Python library for mDNS/DNS-SD
  - **Command**: `uv add --optional "zeroconf>=0.80"`
  - **Verify**: `uv run python -c "import zeroconf"` with dns-sd extra

- [x] 2.3.2 Implement service registration
  - **File**: `src/asap/discovery/dnssd.py` (create new)
  - **What**: Create `DNSSDAdvertiser` class:
    - Service type: `_asap._tcp.local.`
    - TXT records: `version`, `capabilities`, `manifest_url`
    - `start()` / `stop()` lifecycle methods
  - **Why**: Allows LAN discovery without registry
  - **Reference**: https://www.dns-sd.org/
  - **Verify**: Service appears in Bonjour browser

- [x] 2.3.3 Implement service browser
  - **File**: `src/asap/discovery/dnssd.py` (modify)
  - **What**: Create `DNSSDDiscovery` class:
    - `async def browse() -> List[AgentInfo]`
    - Event callbacks: `on_service_added`, `on_service_removed`
    - Parse TXT records into AgentInfo
  - **Why**: Complementary to advertiser - discover nearby agents
  - **Verify**: Browser finds advertised test agent

- [x] 2.3.4 Write tests (with mocking)
  - **File**: `tests/discovery/test_dnssd.py` (create new)
  - **What**: Test with mocked zeroconf:
    - Service registration works
    - Browser discovers services
    - TXT records parsed correctly
  - **Note**: Network tests may need skip markers for CI
  - **Verify**: `pytest tests/discovery/test_dnssd.py -v` passes

- [x] 2.3.5 Commit milestone
  - **Command**: `git commit -m "feat(discovery): add DNS-SD/mDNS support (optional)"`
  - **Scope**: dnssd.py, test_dnssd.py, pyproject.toml
  - **Verify**: `git log -1` shows correct message

**Acceptance Criteria**:
- [x] Agents can advertise via DNS-SD
- [x] Agents can discover nearby agents
- [x] Works offline (no internet needed)

---

## Task 2.4: Lite Registry Client (SD-11)

**Goal**: Implement SDK method to discover agents from the static Lite Registry.

**Context**: The Lite Registry is a `registry.json` file hosted on GitHub Pages. Developers submit agents via PR. This bridges the "Discovery Abyss" between v1.1 (identity + direct discovery) and v1.2 (full Registry API). See [SD-11](../../../product-specs/roadmap-to-marketplace.md) and [ADR-15](../../../product-specs/ADR.md#question-15-lite-registry-for-v11-discovery-gap).

**Prerequisites**: Task 2.2 completed (client-side discovery exists)

### Sub-tasks

- [ ] 2.4.1 Define Lite Registry schema model
  - **File**: `src/asap/discovery/registry.py` (create new)
  - **What**: Pydantic v2 models:
    - `RegistryEntry`: id, name, description, endpoints (dict[str, str]), skills (list[str]), asap_version
    - `LiteRegistry`: version, updated_at, agents (list[RegistryEntry])
  - **Why**: Typed models ensure schema compliance and validation
  - **Pattern**: Follow manifest model pattern in `models/entities.py`
  - **Verify**: Models validate with Pydantic, serialize to JSON

- [ ] 2.4.2 Implement `discover_from_registry()` method
  - **File**: `src/asap/discovery/registry.py` (modify)
  - **What**: Create function:
    - `async def discover_from_registry(registry_url: str = DEFAULT_REGISTRY_URL) -> LiteRegistry`
    - Fetches and parses `registry.json` from URL
    - Default URL: `https://asap-protocol.github.io/registry/registry.json` (or similar)
    - Caches result with TTL (default: 15 minutes)
  - **Why**: Programmatic discovery of listed agents
  - **Verify**: Method fetches and parses registry correctly

- [ ] 2.4.3 Add filtering methods
  - **File**: `src/asap/discovery/registry.py` (modify)
  - **What**: Add convenience methods:
    - `find_by_skill(registry: LiteRegistry, skill: str) -> list[RegistryEntry]`
    - `find_by_id(registry: LiteRegistry, agent_id: str) -> RegistryEntry | None`
  - **Why**: Enables agent discovery by capability
  - **Verify**: Filtering returns correct results

- [ ] 2.4.4 Create registry entry template and validator
  - **File**: `src/asap/discovery/registry.py` (modify)
  - **What**: Add:
    - `generate_registry_entry(manifest: Manifest, endpoints: dict[str, str]) -> RegistryEntry`
    - Generates a registry entry from an existing manifest + endpoints
    - Validates against schema
  - **Why**: Makes it easy for developers to create their PR submission
  - **Verify**: Generated entry is valid JSON

- [ ] 2.4.5 Write tests
  - **File**: `tests/discovery/test_registry.py` (create new)
  - **What**: Test scenarios:
    - Schema validation (valid/invalid entries)
    - Fetch and parse from mock URL
    - Filter by skill returns correct agents
    - Cache works (second call doesn't fetch)
    - Network error handled gracefully
  - **Verify**: `pytest tests/discovery/test_registry.py -v` all pass

- [ ] 2.4.6 Commit milestone
  - **Command**: `git commit -m "feat(discovery): add Lite Registry client (SD-11, ADR-15)"`
  - **Scope**: registry.py, test_registry.py
  - **Verify**: `git log -1` shows correct message

**Acceptance Criteria**:
- [ ] Lite Registry schema validates with Pydantic
- [ ] `discover_from_registry()` fetches and parses correctly
- [ ] Filtering by skill works
- [ ] Registry entry generation from manifest works
- [ ] Test coverage >95%

---

## Task 2.5: Agent Liveness / Health

**Goal**: Implement health endpoint for agent liveness detection.

**Context**: Without liveness, the Registry (v1.2) will list dead agents, creating a "graveyard" of stale entries. The SLA Framework (v1.3) defines `availability` claims but has no measurement mechanism. A simple health endpoint solves both problems with minimal cost. See [SD-10](../../../product-specs/roadmap-to-marketplace.md) and [ADR-14](../../../product-specs/ADR.md).

**Prerequisites**: Task 2.1 completed (well-known endpoint infrastructure)

### Sub-tasks

- [ ] 2.5.1 Create health endpoint handler
  - **File**: `src/asap/discovery/health.py` (create new)
  - **What**: Create FastAPI route:
    - `GET /.well-known/asap/health`
    - Returns JSON: `{ "status": "healthy", "agent_id": "...", "version": "...", "asap_version": "1.1.0", "uptime_seconds": N }`
    - Optional: `load` object with `active_tasks` and `queue_depth`
    - Status code: 200 (healthy), 503 (unhealthy)
  - **Why**: Foundation for Registry liveness (v1.2) and SLA monitoring (v1.3)
  - **Pattern**: Kubernetes `/healthz` pattern, simple and fast
  - **Verify**: Curl returns valid JSON health response

- [ ] 2.5.2 Add ttl_seconds to Manifest model
  - **File**: `src/asap/models/entities.py` (modify existing)
  - **What**: Add optional field to Manifest:
    - `ttl_seconds: int = 300` — how long to consider agent "alive" without re-check
    - Default 5 minutes (300s) — reasonable for most agents
    - Discovery client uses TTL to decide when to re-check health
  - **Why**: Without TTL, clients must poll health constantly
  - **Verify**: Manifest serializes with ttl_seconds field

- [ ] 2.5.3 Integrate with ASAPServer
  - **File**: `src/asap/transport/server.py` (modify existing)
  - **What**: Auto-register health route alongside well-known:
    - If `ASAPServer(manifest=my_manifest)` → register both endpoints
    - Track server start time for `uptime_seconds`
    - Optionally expose active task count if handler provides it
  - **Why**: Zero-config health endpoint
  - **Pattern**: Same integration as well-known endpoint (Task 2.1.3)
  - **Verify**: Server with manifest serves health endpoint

- [ ] 2.5.4 Add health_check client method
  - **File**: `src/asap/transport/client.py` (modify existing)
  - **What**: Add method:
    - `async def health_check(base_url: str) -> HealthStatus`
    - Fetches `{base_url}/.well-known/asap/health`
    - Returns typed `HealthStatus` model
    - Respects manifest `ttl_seconds` for caching
  - **Why**: Programmatic health checking for Registry and consumers
  - **Verify**: Client can check agent health

- [ ] 2.5.5 Write tests
  - **File**: `tests/discovery/test_health.py` (create new)
  - **What**: Test scenarios:
    - Healthy response with correct fields
    - Uptime increases over time
    - 503 when agent marks itself unhealthy
    - Client health_check parses response
    - TTL caching works correctly
  - **Verify**: `pytest tests/discovery/test_health.py -v` all pass

- [ ] 2.5.6 Commit milestone
  - **Command**: `git commit -m "feat(discovery): add agent health/liveness endpoint"`
  - **Scope**: health.py, entities.py, server.py, client.py, test_health.py
  - **Verify**: `git log -1` shows correct message

**Acceptance Criteria**:
- [ ] Health endpoint returns agent status
- [ ] Manifest includes ttl_seconds field
- [ ] Client can check agent health programmatically
- [ ] Integration with ASAPServer is automatic

---

## Task 2.6: Mark Sprint S2 Complete

**Goal**: Finalize Sprint S2 deliverables.

**Context**: Checkpoint task to verify all S2 deliverables are complete and update tracking.

**Prerequisites**: All tasks 2.1-2.5 completed (DNS-SD is optional)

### Sub-tasks

- [ ] 2.6.1 Update roadmap progress
  - **File**: `tasks-v1.1.0-roadmap.md` (modify)
  - **What**: Mark S2 tasks as complete `[x]`, update progress percentage
  - **Verify**: Progress shows 100% for S2

- [ ] 2.6.2 Verify all acceptance criteria met
  - **What**: Manually verify:
    - Well-known endpoint serves manifest ✓
    - Client discovery works ✓
    - Health endpoint returns agent status ✓
    - DNS-SD works (if implemented) ✓
  - **Verify**: All criteria checked off

- [ ] 2.6.3 Run full test suite
  - **Command**: `pytest tests/discovery -v --cov`
  - **What**: Verify all new tests pass with >95% coverage
  - **Verify**: No failures, coverage target met

- [ ] 2.6.4 Commit checkpoint
  - **Command**: `git commit -m "chore: mark v1.1.0 S2 complete"`
  - **Verify**: Clean commit with progress updates

**Acceptance Criteria**:
- [ ] All S2 tasks complete
- [ ] Test suite passes
- [ ] Progress tracked in roadmap

---

## Sprint S2 Definition of Done

- [ ] Well-known endpoint serving manifest
- [ ] Client discovery method working
- [ ] Manifests cached with proper TTL
- [ ] Lite Registry client functional (SD-11, ADR-15)
- [ ] Health/liveness endpoint functional
- [ ] Manifest includes ttl_seconds field
- [ ] DNS-SD support (Optional — defer to v1.1.1+)
- [ ] Test coverage >95%
- [ ] Progress tracked in roadmap

**Total Sub-tasks**: ~32
