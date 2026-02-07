# Sprint S2: Well-Known Discovery

> **Goal**: Implement basic discovery before Registry (serve and consume manifests)
> **Prerequisites**: Sprint S1 completed
> **Parent Roadmap**: [tasks-v1.1.0-roadmap.md](./tasks-v1.1.0-roadmap.md)

---

## Relevant Files

- `src/asap/discovery/__init__.py` - Discovery module init
- `src/asap/discovery/wellknown.py` - Well-known endpoint
- `src/asap/discovery/validation.py` - Manifest validation
- `src/asap/discovery/dns_sd.py` - DNS-SD support (optional)
- `src/asap/transport/client.py` - Client discover() method
- `tests/discovery/__init__.py` - Discovery test package
- `tests/discovery/test_wellknown.py` - Well-known endpoint tests
- `tests/discovery/test_discovery_client.py` - Client discovery tests
- `tests/discovery/test_dnssd.py` - DNS-SD tests (optional)

---

## Context

Well-known discovery enables agents to find each other without prior configuration. An agent can query `https://agent.example.com/.well-known/asap/manifest.json` to get capabilities, endpoints, and version info. This is the foundation for the Registry in v1.2.0.

---

## Task 2.1: Well-Known Endpoint

**Goal**: Serve agent manifest at standardized well-known URI.

**Context**: Following RFC 8615 (Well-Known URIs), we establish `/.well-known/asap/manifest.json` as the discovery endpoint for ASAP agents.

**Prerequisites**: Sprint S1 completed

### Sub-tasks

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

## Task 2.2: Manifest Discovery Client

**Goal**: Enable clients to discover agents from their base URL.

**Context**: The counterpart to Task 2.1 - this enables clients to fetch manifests. It's the "consuming side" of well-known discovery.

**Prerequisites**: Task 2.1 completed

### Sub-tasks

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

## Task 2.3: DNS-SD Support (Optional P3)

**Goal**: Enable local network agent discovery via mDNS/DNS-SD.

**Context**: For development and LAN scenarios, agents can advertise themselves via DNS-SD (like how printers use Bonjour). This is Optional/P3 - can be deferred to v1.1.1+.

**Prerequisites**: Tasks 2.1, 2.2 completed

### Sub-tasks

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

## Task 2.4: Mark Sprint S2 Complete

**Goal**: Finalize Sprint S2 deliverables.

**Context**: Checkpoint task to verify all S2 deliverables are complete and update tracking.

**Prerequisites**: All tasks 2.1-2.3 completed

### Sub-tasks

- [ ] 2.4.1 Update roadmap progress
  - **File**: `tasks-v1.1.0-roadmap.md` (modify)
  - **What**: Mark S2 tasks as complete `[x]`, update progress percentage
  - **Verify**: Progress shows 100% for S2

- [ ] 2.4.2 Verify all acceptance criteria met
  - **What**: Manually verify:
    - Well-known endpoint serves manifest ✓
    - Client discovery works ✓
    - DNS-SD works (if implemented) ✓
  - **Verify**: All criteria checked off

- [ ] 2.4.3 Run full test suite
  - **Command**: `pytest tests/discovery -v --cov`
  - **What**: Verify all new tests pass with >95% coverage
  - **Verify**: No failures, coverage target met

- [ ] 2.4.4 Commit checkpoint
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
- [ ] DNS-SD support (Optional - can defer)
- [ ] Test coverage >95%
- [ ] Progress tracked in roadmap

**Total Sub-tasks**: ~20
