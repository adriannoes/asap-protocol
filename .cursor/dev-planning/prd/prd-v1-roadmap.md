# PRD: ASAP Protocol v1.0 Roadmap

> **Status**: Planning (v0.5.0 complete)
> **Current Version**: v0.5.0 (released 2026-01-28)
> **Target**: v1.0.0 (Production-Ready Release)
> **Intermediate Milestone**: v0.5.0 (Security-Hardened Release) ✅

---

## 1. Introduction/Overview

This PRD covers the roadmap from **v0.1.0** (initial alpha) to **v1.0.0** (production-ready) of the ASAP Protocol Python implementation.

**Context**: The v0.1.0 release established the foundation with core models, state management, HTTP transport, and basic examples. However, a comprehensive security review and codebase analysis identified several areas requiring hardening, enhancement, and expansion before the protocol can be considered production-ready.

**Problem**: While functionally complete for basic agent-to-agent communication, the current implementation has:
1. **Security gaps**: Missing authentication enforcement, rate limiting, replay attack prevention, and sensitive data protection
2. **Scalability concerns**: Lack of connection pooling, caching, and batch operations
3. **DX limitations**: Limited debugging tools, examples, and testing utilities
4. **Documentation gaps**: Missing deployment guides, troubleshooting resources, and advanced tutorials
5. **Integration opportunities**: Incomplete MCP implementation, no observability integrations

**Solution**: A phased roadmap with two major milestones:
- **v0.5.0**: Security-hardened release addressing all critical and high-priority vulnerabilities
- **v1.0.0**: Production-ready release with complete feature set, performance optimizations, and enterprise-grade tooling

---

## 2. Goals

### v0.5.0 Goals (Security-Hardened)

| Goal | Metric | Priority |
|------|--------|----------|
| **Authentication enforcement** | Bearer token auth fully implemented and tested | CRITICAL ✅ |
| **Dependency monitoring** | Dependabot configured with daily security checks | CRITICAL |
| **DoS prevention** | Rate limiting (100 req/min) + 10MB payload limits | HIGH |
| **Replay attack prevention** | Timestamp validation (5min window) + optional nonce | HIGH |
| **HTTPS enforcement** | Client validates HTTPS in production mode | HIGH |
| **Retry improvements** | Exponential backoff with jitter implemented | HIGH |
| **Test coverage** | Maintain >95% coverage with new security features | HIGH |
| **No breaking changes** | Backward compatible with v0.1.0 API | CRITICAL |

### v1.0.0 Goals (Production-Ready)

| Goal | Metric | Priority |
|------|--------|----------|
| **All security hardening** | All CRIT+HIGH+MED+LOW issues resolved | CRITICAL |
| **Performance** | <10ms overhead vs raw FastAPI, connection pooling | HIGH |
| **Developer Experience** | 10+ real-world examples, debugging tools, testing utilities | HIGH |
| **Test robustness** | Property-based tests, load tests, chaos engineering | HIGH |
| **Documentation completeness** | Deployment guides, ADRs, troubleshooting, tutorials | HIGH |
| **Observability integration** | OpenTelemetry, Prometheus, Grafana dashboards | MEDIUM |
| **MCP feature parity** | Complete MCP server/client implementation | MEDIUM |
| **Cloud-native readiness** | Docker, K8s manifests, health checks | MEDIUM |

---

## 3. User Stories

### Security Engineer
> As a **security engineer deploying ASAP agents**, I want to **enforce authentication, rate limiting, and HTTPS** so that **my production services are protected from unauthorized access and DoS attacks**.

### Platform Engineer
> As a **platform engineer building multi-agent systems**, I want to **monitor agent communication with distributed tracing and metrics** so that **I can debug issues across agent boundaries and optimize performance**.

### Application Developer
> As a **developer building agent applications**, I want to **use high-quality examples, testing utilities, and debugging tools** so that **I can build reliable agents faster without guessing best practices**.

### DevOps Engineer
> As a **DevOps engineer**, I want to **deploy ASAP agents to Kubernetes with proper health checks and auto-scaling** so that **I can run production workloads with confidence**.

### Open Source Contributor
> As a **contributor to the ASAP protocol**, I want to **understand architectural decisions and have comprehensive test coverage** so that **I can safely improve the codebase without breaking existing functionality**.

---

## 4. Functional Requirements

### 4.1 Security Hardening (v0.5.0 - CRITICAL/HIGH Priority)

#### Authentication & Authorization
1. ✅ **COMPLETED**: Authentication middleware with Bearer token support ([PR #8](https://github.com/adriannoes/asap-protocol/pull/8))
2. **PENDING**: Authorization scheme validation ([Issue #13](https://github.com/adriannoes/asap-protocol/issues/13))
   - Validate `manifest.auth` schemes match supported implementations
   - Reject manifests with unsupported/malformed auth schemes
   - Add schema validation for `AuthScheme` model

#### Dependency Security
3. **PENDING**: Dependabot configuration ([Task 2.0](../tasks/tasks-security-review-report.md#20-critical-security---dependency-monitoring-setup-crit-02))
   - Create `.github/dependabot.yml` for daily security updates
   - Initially security-only (version updates added post-v0.5.0)
   - Document dependency update process in CONTRIBUTING.md

#### DoS Prevention
4. **PENDING**: Rate limiting implementation ([Task 3.0](../tasks/tasks-security-review-report.md#30-high-priority---dos-prevention-high-01-high-02))
   - Add `slowapi` dependency for rate limiting
   - Default: 100 requests/minute per sender
   - HTTP 429 with `Retry-After` header
   - Configurable limits via environment variables

5. **PENDING**: Request size validation ([Task 3.3](../tasks/tasks-security-review-report.md#30-high-priority---dos-prevention-high-01-high-02))
   - 10MB default maximum request size
   - Validate `Content-Length` header before reading body
   - Return JSON-RPC parse error for oversized requests

#### Replay Attack Prevention
6. **PENDING**: Timestamp validation ([Task 4.0](../tasks/tasks-security-review-report.md#40-high-priority---replay-attack-prevention-high-03))
   - Reject envelopes older than 5 minutes
   - Reject future timestamps beyond 30-second tolerance
   - Optional nonce support for critical operations

#### HTTPS Enforcement
7. **PENDING**: Client HTTPS validation ([Task 5.0](../tasks/tasks-security-review-report.md#50-high-priority---https-enforcement-high-04))
   - `require_https=True` parameter in ASAPClient
   - Auto-detect development environment (localhost)
   - Raise clear error for HTTP in production

#### Retry Logic
8. **PENDING**: Exponential backoff ([Task 6.0](../tasks/tasks-security-review-report.md#60-high-priority---retry-logic-improvements-high-05))
   - Implement exponential backoff with jitter
   - Cap maximum delay at 60 seconds
   - Optional circuit breaker pattern

### 4.2 Additional Security (v1.0.0 - MEDIUM/LOW Priority)

#### Sensitive Data Protection
9. **PENDING**: Log sanitization ([Task 7.0](../tasks/tasks-security-review-report.md#70-medium-priority---sensitive-data-protection-med-01-med-02), [Issue #12](https://github.com/adriannoes/asap-protocol/issues/12))
   - Sanitize tokens, passwords, secrets from logs
   - Debug mode for development with full error details
   - Production mode with generic error messages

#### Input Validation
10. **PENDING**: Handler security hardening ([Task 8.0](../tasks/tasks-security-review-report.md#80-medium-priority---input-validation-hardening-med-03-med-04))
    - Document handler security requirements
    - Path traversal detection in FilePart URIs
    - Handler validation utilities

#### Code Quality
11. **PENDING**: Code improvements ([Task 9.0](../tasks/tasks-security-review-report.md#90-low-priority---code-improvements-low-01-low-02-low-03))
    - Thread safety improvements in HandlerRegistry
    - Enhanced URN validation (max length: 256 chars)
    - Task depth validation (prevent infinite recursion)

### 4.3 Performance Optimizations (v1.0.0)

#### Connection Management
12. **NEW**: Connection pooling
    - Implement persistent HTTP connection pools in ASAPClient
    - Configurable pool size and timeout
    - Automatic connection recycling
    - **Target**: Support 1000+ concurrent connections per client

13. **NEW**: Async batch operations
    - `client.send_batch()` method for multiple envelopes
    - Pipeline requests to reduce latency
    - Parallel processing with asyncio.gather
    - **Target**: 10x throughput improvement for bulk operations

#### Caching
14. **NEW**: Manifest caching
    - Cache discovered manifests with TTL (default: 5 minutes)
    - Automatic cache invalidation on errors
    - Optional persistent cache backend
    - **Target**: 90% cache hit rate for stable topologies

15. **NEW**: Compression support
    - gzip/brotli compression for large payloads
    - Automatic content negotiation
    - Configurable compression threshold (default: 1KB)
    - **Target**: 70% bandwidth reduction for JSON payloads

### 4.4 Developer Experience (v1.0.0)

#### Examples & Tutorials
16. **NEW**: Real-world examples ([Issue #11](https://github.com/adriannoes/asap-protocol/issues/11) - edge case testing)
    - Multi-agent orchestration (3+ agents)
    - Long-running task with checkpoints
    - Error recovery and retry patterns
    - WebSocket notifications (future transport)
    - MCP tool integration example
    - State migration between agents
    - Authentication patterns (OAuth2, API keys)
    - Rate limiting and backoff strategies
    - **Target**: 10+ production-ready examples

17. **NEW**: Testing utilities
    - `asap.testing` module with test helpers
    - Mock agent factory for unit tests
    - Snapshot fixtures for state testing
    - Async test context managers
    - **Target**: Reduce test boilerplate by 50%

#### Debugging Tools
18. **NEW**: Trace visualization
    - CLI command: `asap trace [trace-id]` to display request flow
    - ASCII diagram showing agent-to-agent hops
    - Timing information for each hop
    - Optional web UI for trace exploration

19. **NEW**: Development server improvements
    - Hot reload for handler changes
    - Request/response logging in debug mode
    - Built-in REPL for testing payloads
    - Swagger UI for ASAP endpoints

### 4.5 Testing Enhancements (v1.0.0)

#### Property-Based Testing
20. **NEW**: Hypothesis integration
    - Property tests for model serialization
    - Fuzz testing for envelope validation
    - State machine property verification
    - **Target**: 100+ property-based tests

#### Load & Stress Testing
21. **NEW**: Performance benchmarks expansion
    - Load tests: 1000 req/sec sustained
    - Stress tests: find breaking point
    - Latency percentiles (p50, p95, p99)
    - Memory leak detection
    - **Target**: <5ms p95 latency for localhost

22. **NEW**: Chaos engineering
    - Network partition simulation
    - Random server crashes
    - Message loss and duplication
    - Clock skew testing
    - **Target**: Verify graceful degradation

#### Contract Testing
23. **NEW**: Cross-version compatibility tests
    - Test v0.1.0 client → v1.0.0 server
    - Test v1.0.0 client → v0.1.0 server
    - Schema evolution validation
    - **Target**: Guarantee backward compatibility

### 4.6 Documentation Expansion (v1.0.0)

#### Guides & Tutorials
24. **NEW**: Step-by-step tutorials
    - "Building Your First Agent" (15-minute quickstart)
    - "Stateful Workflows with Snapshots" (intermediate)
    - "Multi-Agent Orchestration" (advanced)
    - "Production Deployment Checklist" (devops)
    - **Target**: Cover beginner → advanced journey

25. **NEW**: Architecture Decision Records (ADRs)
    - Document major design choices (ULID, async-first, etc.)
    - Explain tradeoffs and alternatives considered
    - Provide context for contributors
    - **Target**: 15+ ADRs covering all key decisions

#### Deployment Guides
26. **NEW**: Cloud-native deployment
    - Docker images with best practices
    - Kubernetes manifests (Deployment, Service, Ingress)
    - Helm chart for easy installation
    - Health check endpoints (`/health`, `/ready`)
    - **Target**: Deploy to K8s in <10 minutes

27. **NEW**: Troubleshooting guide
    - Common errors and solutions
    - Debugging checklist
    - Performance tuning tips
    - FAQ section
    - **Target**: Self-service for 80% of issues

### 4.7 Observability Integration (v1.0.0)

#### OpenTelemetry
28. **NEW**: Distributed tracing integration
    - OpenTelemetry spans for all ASAP operations
    - Context propagation across agent boundaries
    - Automatic trace ID injection
    - Export to Jaeger, Zipkin, or cloud backends
    - **Target**: Zero-config tracing for development

29. **NEW**: Structured metrics
    - OpenTelemetry metrics for counters, histograms
    - Instrument transport layer, handlers, state machine
    - Prometheus-compatible export (already exists, enhance)
    - **Target**: 20+ metrics covering all critical paths

#### Dashboards
30. **NEW**: Pre-built Grafana dashboards
    - Request rate, error rate, latency (RED metrics)
    - Agent topology visualization
    - State machine transition heatmap
    - **Target**: Production-ready monitoring in <5 minutes

### 4.8 MCP Integration (v1.0.0)

#### MCP Feature Parity
31. **NEW**: Complete MCP server implementation
    - Implement full MCP tool execution protocol
    - Resource fetching with streaming support
    - Prompt templates integration
    - **Target**: 100% MCP spec compliance

32. **NEW**: MCP client enhancements
    - Discover and call MCP tools from ASAP agents
    - Automatic schema validation for tool inputs
    - Result streaming for large responses
    - **Target**: Seamless MCP interoperability

### 4.9 GitHub Issues Resolution

#### Issue #13: Authorization Scheme Validation
- **Related to**: Task 4.1.2 (Authorization)
- **Status**: Pending
- **Target**: v0.5.0

#### Issue #12: Token Logging
- **Related to**: Task 7.1 (Log sanitization)
- **Status**: Pending
- **Target**: v1.0.0

#### Issue #11: Missing Test Coverage for Edge Cases
- **Related to**: Tasks 4.5 (Testing enhancements), 4.4.16 (Examples)
- **Status**: Pending
- **Target**: v1.0.0

#### Issue #10: Remove type: ignore in handlers.py
- **Related to**: Code quality improvements
- **Status**: Pending
- **Target**: v0.5.0 (quick win)
- **Action**: Refactor type annotations to eliminate need for `type: ignore`

#### Issue #9: Refactor handle_message into smaller helpers
- **Related to**: Code maintainability
- **Status**: Pending
- **Target**: v0.5.0 (quick win)
- **Action**: Extract smaller, testable functions from monolithic handler

#### Issue #7: Upgrade FastAPI from 0.124 to 0.128.0
- **Related to**: Dependency updates
- **Status**: Pending
- **Target**: v0.5.0 (blocked by Dependabot setup)
- **Action**: Upgrade after testing backward compatibility

---

## 5. Non-Goals (Out of Scope)

### Explicitly Deferred to v1.1.0+
- ❌ WebSocket transport binding (requires spec update)
- ❌ gRPC transport binding (low community demand)
- ❌ Message broker integration (NATS, Kafka) - can be external
- ❌ GraphQL API for agent discovery (HTTP/JSON-RPC sufficient)
- ❌ Built-in agent registry service (use external service mesh)
- ❌ OAuth2/OIDC server implementation (use existing providers)
- ❌ mTLS support (requires cert management complexity)

### Not Planned
- ❌ Synchronous-only client API (async-first is core design)
- ❌ Database-backed SnapshotStore (users can implement Protocol)
- ❌ Agent code generation from specs (not protocol responsibility)
- ❌ LLM provider integrations (orthogonal to protocol)

---

## 6. Design Considerations

### Backward Compatibility Strategy

All v0.x releases **MUST** maintain backward compatibility:
- Existing v0.1.0 and v0.3.0 clients can communicate with v0.5.0/v1.0.0 servers
- Envelope schema remains stable (only additive changes)
- New features use optional fields or separate payload types
- Deprecation warnings for 2 minor versions before removal

### Security-First Development

All new features undergo security review before merge:
- Threat modeling for new attack surfaces
- Secure defaults (e.g., `require_https=True`)
- Principle of least privilege in auth/authz
- Input validation at boundaries

### Performance Benchmarks

Establish baseline and track regressions:
- Benchmark suite runs on every PR
- Performance budget: <5% regression per feature
- Document tradeoffs (e.g., security vs latency)

### Cloud-Native Principles

Design for 12-factor app compliance:
- Configuration via environment variables
- Stateless execution (snapshot store is external)
- Graceful shutdown on SIGTERM
- Health check endpoints for orchestrators

---

## 7. Technical Considerations

### Dependency Strategy

**New Dependencies** (to be added):
- `slowapi` (≥0.1.9): Rate limiting middleware
- `opentelemetry-api` (≥1.20): Distributed tracing
- `opentelemetry-sdk` (≥1.20): Telemetry implementation
- `hypothesis` (dev, ≥6.92): Property-based testing
- `locust` (dev, ≥2.20): Load testing

**Dependency Upgrades** (planned):
- FastAPI: 0.124 → 0.128.0+ ([Issue #7](https://github.com/adriannoes/asap-protocol/issues/7))
- Pydantic: Keep ≥2.12, track for v3.0 when released
- Python: Maintain 3.13+ requirement (no backport to 3.12)

**Dependency Monitoring**:
- Dependabot for security updates (daily)
- Version updates monthly (post-v0.5.0)
- pip-audit in CI (already configured)

### Code Organization Enhancements

**New Modules**:
```
src/asap/
├── testing/           # New: Test utilities
│   ├── __init__.py
│   ├── fixtures.py    # Pytest fixtures
│   ├── mocks.py       # Mock agents
│   └── assertions.py  # Custom assertions
├── transport/
│   ├── middleware.py  # ✅ Already exists
│   ├── validators.py  # New: Timestamp, nonce validation
│   └── cache.py       # New: Manifest caching
└── observability/
    ├── tracing.py     # New: OpenTelemetry integration
    └── dashboards/    # New: Grafana dashboards
        └── asap.json
```

### Migration Path for Breaking Changes

If unavoidable breaking changes needed:
1. Deprecation warning in v0.x (2 minor versions)
2. Breaking change in v1.0.0 with migration guide
3. Compatibility layer if feasible
4. Update all examples and tests

Example:
```python
# v0.5.0 - Deprecation warning
warnings.warn(
    "create_app(manifest) is deprecated, use create_app(manifest, registry) instead",
    DeprecationWarning,
)

# v1.0.0 - Breaking change
# Old signature removed, only new signature supported
```

---

## 8. Success Metrics

### v0.5.0 Success Criteria

| Metric | Target | Measurement |
|--------|--------|-------------|
| Security coverage | 100% CRIT+HIGH resolved | Manual checklist |
| Test coverage | ≥95% | pytest-cov report |
| Performance | No regression vs v0.1.0 | Benchmark suite |
| Breaking changes | Zero | API compatibility tests |
| Documentation | All security features documented | Manual review |
| Adoption | 50+ PyPI downloads/week | PyPI stats |

### v1.0.0 Success Criteria

| Metric | Target | Measurement |
|--------|--------|-------------|
| Security coverage | 100% all issues resolved | Manual checklist |
| Test count | 800+ tests | pytest --collect-only |
| Performance | <10ms ASAP overhead | Benchmark suite |
| Examples | 10+ real-world scenarios | Directory count |
| Documentation | 100% API coverage | mkdocstrings check |
| Production usage | 5+ public projects using ASAP | GitHub search |
| Community | 20+ GitHub stars | GitHub metrics |
| Release stability | No hotfixes for 2 weeks post-release | Issue tracker |

---

## 9. Milestones & Sprints

### Milestone 1: v0.5.0 (Security-Hardened)

**Focus**: Address all CRITICAL and HIGH priority security issues

#### Sprint S1: Quick Wins & Dependency Setup
**Duration**: Flexible (estimated 3-5 days)
**Goal**: Resolve low-hanging fruit and establish dependency monitoring

**Tasks**:
- [x] ~~Authentication implementation~~ (✅ Already completed in PR #8)
- [ ] Remove `type: ignore` in handlers.py ([Issue #10](https://github.com/adriannoes/asap-protocol/issues/10))
- [ ] Refactor `handle_message` into smaller helpers ([Issue #9](https://github.com/adriannoes/asap-protocol/issues/9))
- [ ] Upgrade FastAPI to 0.128.0+ ([Issue #7](https://github.com/adriannoes/asap-protocol/issues/7))
- [ ] Configure Dependabot for security updates ([Task 2.0](../tasks/tasks-security-review-report.md#20-critical-security---dependency-monitoring-setup-crit-02))
- [ ] Update CONTRIBUTING.md with dependency process

**Definition of Done**:
- All GitHub issues #7, #9, #10 closed
- Dependabot configured and first PR merged
- CI passes with updated FastAPI version
- No breaking changes introduced

#### Sprint S2: DoS Prevention & Rate Limiting
**Duration**: Flexible (estimated 5-7 days)
**Goal**: Implement rate limiting and request size validation

**Tasks**:
- [ ] Add `slowapi` dependency to pyproject.toml ([Task 3.1](../tasks/tasks-security-review-report.md#30-high-priority---dos-prevention-high-01-high-02))
- [ ] Implement rate limiting middleware ([Task 3.2](../tasks/tasks-security-review-report.md#30-high-priority---dos-prevention-high-01-high-02))
- [ ] Add request size validation ([Task 3.3](../tasks/tasks-security-review-report.md#30-high-priority---dos-prevention-high-01-high-02))
- [ ] Make limits configurable ([Task 3.4](../tasks/tasks-security-review-report.md#30-high-priority---dos-prevention-high-01-high-02))
- [ ] Add comprehensive tests ([Task 3.5, 3.6](../tasks/tasks-security-review-report.md#30-high-priority---dos-prevention-high-01-high-02))
- [ ] Update `docs/security.md` ([Task 3.7](../tasks/tasks-security-review-report.md#30-high-priority---dos-prevention-high-01-high-02))

**Definition of Done**:
- Rate limiting working: HTTP 429 after limit exceeded
- Request size validation: 10MB default limit enforced
- Test coverage >95% maintained
- Documentation updated with configuration examples

#### Sprint S3: Replay Attack Prevention & HTTPS
**Duration**: Flexible (estimated 4-6 days)
**Goal**: Implement timestamp validation and HTTPS enforcement

**Tasks**:
- [ ] Add timestamp validation constants ([Task 4.1](../tasks/tasks-security-review-report.md#40-high-priority---replay-attack-prevention-high-03))
- [ ] Implement timestamp validation function ([Task 4.2](../tasks/tasks-security-review-report.md#40-high-priority---replay-attack-prevention-high-03))
- [ ] Integrate validation in server ([Task 4.3](../tasks/tasks-security-review-report.md#40-high-priority---replay-attack-prevention-high-03))
- [ ] Add optional nonce support ([Task 4.4](../tasks/tasks-security-review-report.md#40-high-priority---replay-attack-prevention-high-03))
- [ ] Add HTTPS validation to client ([Task 5.1-5.2](../tasks/tasks-security-review-report.md#50-high-priority---https-enforcement-high-04))
- [ ] Add tests for both features ([Task 4.5, 5.3](../tasks/tasks-security-review-report.md))
- [ ] Update documentation ([Task 4.6, 5.4](../tasks/tasks-security-review-report.md))

**Definition of Done**:
- Envelopes older than 5 minutes rejected
- Future timestamps beyond 30s rejected
- HTTPS enforced in production mode
- Test coverage >95% maintained
- Examples updated to use HTTPS

#### Sprint S4: Retry Logic & Authorization
**Duration**: Flexible (estimated 3-5 days)
**Goal**: Implement exponential backoff and authorization validation

**Tasks**:
- [ ] Implement exponential backoff ([Task 6.1-6.3](../tasks/tasks-security-review-report.md#60-high-priority---retry-logic-improvements-high-05))
- [ ] Add circuit breaker pattern (optional) ([Task 6.4](../tasks/tasks-security-review-report.md#60-high-priority---retry-logic-improvements-high-05))
- [ ] Add retry tests ([Task 6.5](../tasks/tasks-security-review-report.md#60-high-priority---retry-logic-improvements-high-05))
- [ ] Implement authorization scheme validation ([Issue #13](https://github.com/adriannoes/asap-protocol/issues/13))
- [ ] Update documentation ([Task 6.6](../tasks/tasks-security-review-report.md#60-high-priority---retry-logic-improvements-high-05))

**Definition of Done**:
- Exponential backoff with jitter working
- Max delay capped at 60 seconds
- Authorization schemes validated at manifest load
- Test coverage >95% maintained
- Documentation covers retry configuration

#### Sprint S5: v0.5.0 Release Preparation
**Duration**: Flexible (estimated 2-3 days)
**Goal**: Final testing, documentation, and release

**Tasks**:
- [ ] Run full security audit (pip-audit, bandit)
- [ ] Update CHANGELOG.md with all v0.5.0 changes
- [ ] Review all documentation for accuracy
- [ ] Run benchmark suite and verify no regressions
- [ ] Test upgrade paths from v0.1.0 → v0.5.0 and v0.3.0 → v0.5.0
- [ ] Create release notes
- [ ] Tag and publish v0.5.0 to PyPI

**Definition of Done**:
- All CRIT+HIGH security tasks completed
- Zero breaking changes vs v0.1.0
- CI passes on all platforms
- v0.5.0 published to PyPI
- GitHub release created with notes

**v0.5.0 Total Estimated Duration**: 17-26 days (3.5-5 weeks)

---

### Milestone 2: v1.0.0 (Production-Ready)

**Focus**: Complete all remaining security, add performance optimizations, DX improvements, and production tooling

#### Sprint P1: Sensitive Data Protection & Input Validation
**Duration**: Flexible (estimated 5-7 days)
**Goal**: Complete MED priority security tasks

**Tasks**:
- [ ] Implement log sanitization ([Task 7.1-7.2](../tasks/tasks-security-review-report.md#70-medium-priority---sensitive-data-protection-med-01-med-02), [Issue #12](https://github.com/adriannoes/asap-protocol/issues/12))
- [ ] Add debug mode configuration ([Task 7.3-7.4](../tasks/tasks-security-review-report.md#70-medium-priority---sensitive-data-protection-med-01-med-02))
- [ ] Add sanitization tests ([Task 7.5](../tasks/tasks-security-review-report.md#70-medium-priority---sensitive-data-protection-med-01-med-02))
- [ ] Document handler security requirements ([Task 8.1](../tasks/tasks-security-review-report.md#80-medium-priority---input-validation-hardening-med-03-med-04))
- [ ] Add FilePart URI validation ([Task 8.2](../tasks/tasks-security-review-report.md#80-medium-priority---input-validation-hardening-med-03-med-04))
- [ ] Add handler validation helpers ([Task 8.3-8.4](../tasks/tasks-security-review-report.md#80-medium-priority---input-validation-hardening-med-03-med-04))
- [ ] Update handler examples ([Task 8.5](../tasks/tasks-security-review-report.md#80-medium-priority---input-validation-hardening-med-03-med-04))

**Definition of Done**:
- Tokens/secrets redacted from logs
- Debug mode working (full errors in dev)
- Path traversal detection working
- Test coverage >95% maintained
- Security documentation complete

#### Sprint P2: Code Quality & LOW Priority Security
**Duration**: Flexible (estimated 3-4 days)
**Goal**: Complete LOW priority security and code quality improvements

**Tasks**:
- [ ] Improve HandlerRegistry thread safety ([Task 9.1](../tasks/tasks-security-review-report.md#90-low-priority---code-improvements-low-01-low-02-low-03))
- [ ] Enhance URN validation ([Task 9.2](../tasks/tasks-security-review-report.md#90-low-priority---code-improvements-low-01-low-02-low-03))
- [ ] Add task depth validation ([Task 9.3](../tasks/tasks-security-review-report.md#90-low-priority---code-improvements-low-01-low-02-low-03))
- [ ] Run full code quality audit (ruff, mypy --strict)
- [ ] Address any remaining linter warnings

**Definition of Done**:
- All security tasks (CRIT+HIGH+MED+LOW) completed
- Test coverage >95% maintained
- mypy --strict passes with zero errors
- ruff checks pass with zero warnings

#### Sprint P3: Performance - Connection & Caching
**Duration**: Flexible (estimated 5-7 days)
**Goal**: Implement connection pooling and caching

**Tasks**:
- [ ] Implement connection pooling in ASAPClient (Req 12)
- [ ] Add configurable pool size and timeout
- [ ] Implement manifest caching (Req 14)
- [ ] Add cache invalidation logic
- [ ] Benchmark connection pooling (target: 1000+ concurrent)
- [ ] Benchmark cache hit rate (target: 90%)
- [ ] Document configuration options

**Definition of Done**:
- Connection pooling supports 1000+ concurrent connections
- Manifest cache achieves 90% hit rate in stable topologies
- Benchmark results documented
- No performance regression vs v0.5.0

#### Sprint P4: Performance - Async Batch & Compression
**Duration**: Flexible (estimated 4-6 days)
**Goal**: Implement batch operations and compression

**Tasks**:
- [ ] Implement `client.send_batch()` method (Req 13)
- [ ] Add parallel processing with asyncio.gather
- [ ] Implement compression support (gzip/brotli) (Req 15)
- [ ] Add automatic content negotiation
- [ ] Benchmark batch operations (target: 10x throughput)
- [ ] Benchmark compression (target: 70% reduction)
- [ ] Document usage patterns

**Definition of Done**:
- Batch operations achieve 10x throughput improvement
- Compression reduces bandwidth by 70% for JSON
- API backward compatible
- Test coverage >95% maintained

#### Sprint P5: Developer Experience - Examples & Testing
**Duration**: Flexible (estimated 6-8 days)
**Goal**: Create real-world examples and testing utilities

**Tasks**:
- [ ] Create 10+ real-world examples (Req 16):
  - Multi-agent orchestration (3+ agents)
  - Long-running task with checkpoints
  - Error recovery patterns
  - MCP tool integration
  - State migration
  - Authentication patterns
  - Rate limiting strategies
  - WebSocket notifications (concept)
- [ ] Implement `asap.testing` module (Req 17):
  - Mock agent factory
  - Snapshot fixtures
  - Async test context managers
- [ ] Add example-specific tests
- [ ] Update README with example links

**Definition of Done**:
- 10+ production-ready examples
- Testing utilities reduce boilerplate by 50%
- All examples have passing tests
- README showcases example variety

#### Sprint P6: Developer Experience - Debugging Tools
**Duration**: Flexible (estimated 4-5 days)
**Goal**: Build debugging and development tools

**Tasks**:
- [ ] Implement `asap trace [trace-id]` command (Req 18)
- [ ] Add ASCII diagram for trace visualization
- [ ] Implement hot reload for handlers (Req 19)
- [ ] Add debug logging mode
- [ ] Add built-in REPL for testing
- [ ] Optional: Add web UI for trace exploration
- [ ] Document debugging workflows

**Definition of Done**:
- Trace command visualizes request flow
- Hot reload works for handler changes
- Debug mode provides detailed logging
- Documentation includes debugging guide

#### Sprint P7: Testing Enhancements - Property & Load Tests
**Duration**: Flexible (estimated 5-7 days)
**Goal**: Expand test coverage with advanced techniques

**Tasks**:
- [ ] Add Hypothesis dependency (Req 20)
- [ ] Implement 100+ property-based tests
- [ ] Add Locust dependency (Req 21)
- [ ] Implement load tests (1000 req/sec)
- [ ] Implement stress tests (find breaking point)
- [ ] Document latency percentiles (p50, p95, p99)
- [ ] Add memory leak detection
- [ ] Address [Issue #11](https://github.com/adriannoes/asap-protocol/issues/11) - edge case coverage

**Definition of Done**:
- 100+ property-based tests passing
- Load tests show <5ms p95 latency
- Stress tests identify breaking point
- No memory leaks detected
- Issue #11 resolved

#### Sprint P8: Testing Enhancements - Chaos & Contract
**Duration**: Flexible (estimated 4-5 days)
**Goal**: Chaos engineering and contract testing

**Tasks**:
- [ ] Implement chaos tests (Req 22):
  - Network partition simulation
  - Random server crashes
  - Message loss/duplication
  - Clock skew testing
- [ ] Implement contract tests (Req 23):
  - v0.1.0 client → v1.0.0 server
  - v1.0.0 client → v0.1.0 server
  - Schema evolution validation
- [ ] Document resilience patterns

**Definition of Done**:
- Chaos tests verify graceful degradation
- Contract tests guarantee backward compatibility
- Test suite >800 tests total
- Documentation covers resilience

#### Sprint P9: Documentation - Tutorials & ADRs
**Duration**: Flexible (estimated 5-6 days)
**Goal**: Create comprehensive tutorials and ADRs

**Tasks**:
- [ ] Write step-by-step tutorials (Req 24):
  - "Building Your First Agent" (15 min)
  - "Stateful Workflows with Snapshots"
  - "Multi-Agent Orchestration"
  - "Production Deployment Checklist"
- [ ] Write 15+ ADRs (Req 25):
  - ULID choice
  - Async-first design
  - JSON-RPC binding
  - Pydantic models
  - State machine design
  - Security defaults
  - (others as needed)
- [ ] Update docs navigation

**Definition of Done**:
- 4+ tutorials covering beginner→advanced
- 15+ ADRs documenting key decisions
- Docs site well-organized
- All content reviewed for accuracy

#### Sprint P10: Documentation - Deployment & Troubleshooting
**Duration**: Flexible (estimated 4-5 days)
**Goal**: Deployment guides and troubleshooting

**Tasks**:
- [ ] Create Docker images (Req 26)
- [ ] Write Kubernetes manifests
- [ ] Create Helm chart
- [ ] Add health check endpoints (`/health`, `/ready`)
- [ ] Write troubleshooting guide (Req 27):
  - Common errors
  - Debugging checklist
  - Performance tuning
  - FAQ section
- [ ] Test K8s deployment (<10 min)

**Definition of Done**:
- Docker images published to registry
- K8s deployment works in <10 minutes
- Troubleshooting guide covers 80% of issues
- Health checks working

#### Sprint P11: Observability - OpenTelemetry Integration
**Duration**: Flexible (estimated 5-7 days)
**Goal**: Distributed tracing and metrics

**Tasks**:
- [ ] Add OpenTelemetry dependencies (Req 28)
- [ ] Implement tracing integration
- [ ] Add context propagation
- [ ] Implement structured metrics (Req 29)
- [ ] Enhance Prometheus export
- [ ] Test with Jaeger/Zipkin
- [ ] Document zero-config setup

**Definition of Done**:
- OpenTelemetry tracing working
- 20+ metrics instrumented
- Zero-config for development
- Production export tested
- Documentation complete

#### Sprint P12: Observability - Dashboards & MCP
**Duration**: Flexible (estimated 4-5 days)
**Goal**: Grafana dashboards and MCP feature parity

**Tasks**:
- [ ] Create Grafana dashboards (Req 30):
  - RED metrics (rate, errors, duration)
  - Agent topology
  - State machine heatmap
- [ ] Implement complete MCP server (Req 31)
- [ ] Enhance MCP client (Req 32)
- [ ] Test MCP interoperability
- [ ] Document MCP integration

**Definition of Done**:
- Grafana dashboards working
- MCP server 100% spec compliant
- MCP client supports all features
- Documentation complete

#### Sprint P13: v1.0.0 Release Preparation
**Duration**: Flexible (estimated 5-7 days)
**Goal**: Final testing, polish, and release

**Tasks**:
- [ ] Run full test suite (800+ tests)
- [ ] Run full benchmark suite
- [ ] Run full security audit
- [ ] Review all documentation
- [ ] Test all examples
- [ ] Test upgrade paths (v0.1.0 → v1.0.0, v0.3.0 → v1.0.0, v0.5.0 → v1.0.0)
- [ ] Create comprehensive release notes
- [ ] Update CHANGELOG.md
- [ ] Review and merge open PRs
- [ ] Tag and publish v1.0.0 to PyPI
- [ ] Announce release (blog post, social media)

**Definition of Done**:
- All success metrics met (Section 8)
- Zero critical bugs
- Documentation 100% complete
- v1.0.0 published to PyPI
- Release announcement live
- Community notified

**v1.0.0 Total Estimated Duration**: 60-80 days (12-16 weeks) *after* v0.5.0 release

---

## 10. Design Decisions

> **Note**: These decisions have been confirmed and are reflected in the task lists for v0.5.0 and v1.0.0.

### v0.5.0 Decisions

#### DD-001: WebSocket Transport
**Decision**: ✅ Defer to v1.1.0+

**Rationale**:
- Requires ASAP spec update for WebSocket binding definition
- HTTP transport sufficient for v1.0.0 production use
- Focus v0.5.0/v1.0.0 on security and stability

**Impact**: 
- v1.0.0 will include WebSocket example concept only (Sprint P5, Task 5.1.8)
- Real implementation postponed to future release

---

#### DD-002: Rate Limiting Strategy
**Decision**: ✅ Per-sender (agent URN), not per-IP

**Rationale**:
- Agent URN provides better control in multi-agent scenarios
- IP-based limiting problematic with proxies/load balancers
- Aligns with ASAP's agent-centric model

**Implementation**:
- v0.5.0 Sprint S2: `limiter = Limiter(key_func=lambda: envelope.sender)`
- Default: 100 requests/minute per sender
- Configurable via `create_app(rate_limit="100/minute")`

---

#### DD-003: Nonce Store TTL
**Decision**: ✅ 10 minutes (2x max envelope age)

**Rationale**:
- Max envelope age: 5 minutes (prevents replay attacks)
- Nonce TTL: 10 minutes ensures overlap for clock skew tolerance
- Balances security (short window) vs reliability (clock drift)

**Implementation**:
- v0.5.0 Sprint S3: `TTL = MAX_ENVELOPE_AGE_SECONDS * 2`
- Optional nonce validation (disabled by default)

---

### v1.0.0 Decisions

#### DD-004: Snapshot Store Implementations
**Decision**: ✅ Protocol-based, no Redis/PostgreSQL in core library

**Rationale**:
- Keep core library lightweight and dependency-free
- `SnapshotStore` Protocol already supports any backend
- Users can implement Redis/PostgreSQL/S3 as needed
- Provide reference implementation examples in docs

**Impact**:
- Core ships with `InMemorySnapshotStore` only
- Documentation will include Redis example implementation
- No additional dependencies for database backends

---

#### DD-005: HTTP/2 Support
**Decision**: ✅ Yes, leverage uvicorn's built-in HTTP/2

**Rationale**:
- uvicorn ≥0.34 already supports HTTP/2
- Zero additional dependencies needed
- Performance benefits for batch operations (multiplexing)

**Implementation**:
- v1.0.0 Sprint P4: HTTP/2 multiplexing for `send_batch()` method
- Automatic negotiation (falls back to HTTP/1.1)
- Documented in performance tuning guide

---

#### DD-006: Official Docker Images
**Decision**: ✅ Yes, publish to GitHub Container Registry (ghcr.io)

**Rationale**:
- Free for public repositories
- Integrated with GitHub releases
- Industry standard for production deployments

**Implementation**:
- v1.0.0 Sprint P10: Create Dockerfile with best practices
- v1.0.0 Sprint P13: Publish on release
- Tags: `latest`, `v1.0.0`, `v1.0`, `v1`

---

#### DD-007: Kubernetes Operator
**Decision**: ✅ Defer to v1.1.0+ (separate project)

**Rationale**:
- Operators are complex, require separate maintenance
- Basic K8s manifests + Helm chart sufficient for v1.0.0
- Operator would need CRDs, controller, reconciliation logic
- Better as community-driven project after protocol stabilizes

**v1.0.0 Scope**:
- Kubernetes manifests (Deployment, Service, Ingress)
- Helm chart for easy installation
- Health check endpoints (`/health`, `/ready`)

**Future Consideration** (v1.1.0+):
- Separate `asap-operator` repository
- Auto-scaling based on task queue depth
- Service mesh integration (Istio, Linkerd)

---

#### DD-008: HMAC Request Signing
**Decision**: ✅ Defer to v1.1.0+

**Rationale** (Sprint S3 Review - 2026-01-27):
- Current security stack (TLS + Bearer token auth + timestamp validation + nonce) provides adequate protection
- HMAC adds implementation complexity for both client and server
- Key management overhead negates benefits for most use cases
- Real-world threat model addressed by existing mitigations:
  - **Replay attacks**: Timestamp validation (5min window) + optional nonce
  - **Man-in-the-middle**: TLS 1.2+ requirement
  - **Unauthorized access**: Bearer token authentication with sender verification
  - **Message tampering**: TLS provides integrity, HMAC would be redundant

**Impact**:
- v1.0.0 ships without HMAC support
- Documentation will note HMAC as optional spec feature not yet implemented
- Users requiring HMAC can implement via envelope extensions

**Future Consideration** (v1.1.0+):
- Add `asap.security.signing` module with Ed25519/HMAC-SHA256
- Automatic signature injection in ASAPClient
- Signature verification middleware for server
- Key rotation utilities

---

#### DD-009: Connection Pool Size Defaults
**Decision**: ✅ Default pool size = 100 connections (`pool_connections=100`, `pool_maxsize=100`)

**Rationale** (Sprint P3 Review - 2026-01-30):
- Benchmarks validate that 100 connections support 1000+ concurrent requests via connection reuse
- Optimal balance between resource usage and performance for single-agent deployments
- httpx default (`max_connections=100`) aligns with our default, providing consistency
- Connection reuse rate >90% achieved when concurrency exceeds pool size

**Benchmark Results** (Task 3.1):
- **Single-agent**: 100 connections = optimal default
  - Supports 1000+ concurrent requests via reuse
  - Low memory footprint (~10MB per 100 connections)
  - Fast connection acquisition (<5ms pool timeout)
- **Small cluster** (3-5 agents): 200-500 connections recommended
  - Multiple base URLs require separate pools
  - Higher concurrency across agents
- **Large cluster** (10+ agents): 500-1000 connections recommended
  - High-throughput scenarios
  - Can be tuned per deployment needs

**Implementation**:
- v1.0.0 Sprint P3: `ASAPClient(pool_connections=100, pool_maxsize=100, pool_timeout=5.0)`
- Configurable via constructor parameters
- Documented in `ASAPClient` docstring and performance tuning guide
- Pool timeout: 5.0s (prevents indefinite blocking when pool exhausted)

**Configuration Guidance**:
```python
# Single-agent (default)
client = ASAPClient("http://agent.example.com")  # pool_connections=100

# Small cluster
client = ASAPClient("http://agent.example.com", pool_connections=200, pool_maxsize=200)

# Large cluster / high-throughput
client = ASAPClient("http://agent.example.com", pool_connections=500, pool_maxsize=1000)
```

---

#### DD-010: Authentication Scheme for Examples
**Decision**: ✅ Use **both** Bearer (simple) and Bearer + OAuth2 discovery (realistic) in examples.

**Rationale** (Sprint P5 Review - 2026-01-31):
- **Bearer-only**: Covers simple demos, local dev, and minimal setup; single token_validator with create_app.
- **Bearer + OAuth2 concept**: Covers realistic deployments; ASAP validates Bearer; clients obtain tokens via OAuth2; manifest exposes oauth2 discovery (authorization_url, token_url, scopes).
- Example complexity is manageable: `auth_patterns.py` already demonstrates both without extra dependencies.
- Custom validators (static map, env-based) remain documented for testing and small fixed sets.

**Implementation** (v1.0.0 Sprint P5):
- `src/asap/examples/auth_patterns.py`: Bearer-only manifest, OAuth2-concept manifest, static/env validators, create_app with token_validator.
- Docs and README reference Bearer for quick start and OAuth2 concept for production-style auth.

**Options considered**:
- Bearer only: Rejected as too narrow; real deployments often use OAuth2.
- OAuth2 only: Rejected; Bearer-only is better for onboarding and tests.
- Both: **Chosen** — comprehensive and matches current example set.

---

### Sprint S1-S3 Learnings

> **Review Date**: 2026-01-27 (End of Sprint S3)

#### What Went Well

1. **Test-Driven Approach**: Writing tests before implementation for validators and HTTPS enforcement led to cleaner APIs and caught edge cases early.

2. **Incremental Complexity**: Starting with simpler tasks (constants, validators) before integration (server, client) reduced debugging time.

3. **Isolated Test Infrastructure** (Sprint S2.5): Refactoring test structure to use isolated fixtures eliminated global state interference. The `NoRateLimitTestBase` pattern enabled true unit tests.

4. **Documentation-First for Security**: Writing security.md sections alongside implementation ensured comprehensive coverage and identified API inconsistencies.

5. **Metrics Protection**: Implementing payload_type whitelisting in Sprint S2 prevented a potential metrics cardinality DoS vector before it became an issue.

#### Challenges Encountered

1. **Rate Limiter State Leakage**: Global rate limiter state caused 33 test failures (Issue #17). Resolved by creating isolated fixtures and `NoRateLimitTestBase`.

2. **Timestamp Validation Edge Cases**: Clock skew handling required careful consideration of tolerances. The 30-second future tolerance was chosen after testing with real-world network conditions.

3. **Dependency Deprecation Warnings**: `slowapi` uses deprecated `asyncio.iscoroutinefunction` (slated for removal in Python 3.16). Tracking for upstream fix.

#### Adjustments for S4-S5

1. **Focus on Integration Testing**: Sprint S4 (retry logic) will benefit from more integration tests to validate exponential backoff behavior under realistic conditions.

2. **Performance Baseline**: Establish benchmark suite before S4 changes to track any performance impact from retry/circuit breaker code.

3. **Documentation Consolidation**: Review all documentation changes across S1-S3 before S5 release to ensure consistency.

---

## 11. Open Questions

> **Note**: These are genuine open questions that will be answered during development.
> 
> **Review Schedule**:
> - **During v0.5.0**: Review at end of Sprint S3 (after core security features)
> - **Mid v1.0.0**: Review at end of Sprint P6 (after DX improvements)
> - **Pre-release**: Review at start of Sprint P13 (before final release)
> - **Post v1.0.0**: Review 2 weeks after release based on community feedback

### Performance & Scalability
1. ✅ ~~What is the optimal default connection pool size for different deployment scenarios?~~
   - **Decision**: See DD-009 in Section 10
   - **Resolved**: 2026-01-30 (End of Sprint P3)
   - **Default**: 100 connections (`pool_connections=100`, `pool_maxsize=100`)
   - **Recommendations**: Single-agent=100, Small cluster=200-500, Large cluster=500-1000

2. ❓ Should we implement adaptive rate limiting based on server load?
   - **Action**: Monitor during load testing (Sprint P7)
   - **Consider**: Dynamic limits that increase/decrease with server capacity
   - **Review Point**: End of Sprint P7 → Decide for v1.0.0 or defer to v1.1.0

### Security
3. ✅ ~~Should we add optional request signing (HMAC) in v1.0.0 or defer to v1.1.0?~~
   - **Status**: RESOLVED - See DD-008 (Defer to v1.1.0+)
   - **Decision Date**: 2026-01-27 (Sprint S3 Review)
   - **Rationale**: Current security stack (TLS + Bearer + timestamp/nonce) is sufficient

4. ✅ ~~What should be the default authentication scheme for examples?~~
   - **Decision**: See DD-010 in Section 10
   - **Resolved**: 2026-01-31 (End of Sprint P5, Task 5.3)
   - **Choice**: Both — Bearer (simple demos) and Bearer + OAuth2 concept (realistic deployments)

### Developer Experience
5. ❓ Should trace visualization CLI tool support JSON export for external tools?
   - **Action**: Gather feedback during Sprint P6 implementation
   - **Consider**: JSON export for integration with observability platforms
   - **Review Point**: End of Sprint P6 → Decide and implement if valuable

6. ✅ ~~Should we provide pytest plugins for easier testing?~~
   - **Decision**: Defer `pytest-asap` plugin to v1.1.0
   - **Resolved**: 2026-01-31 (End of Sprint P5, Task 5.3)
   - **Rationale**: `asap.testing` (fixtures, MockAgent, assertions) already reduces boilerplate; 8+ test files refactored with ~50% less boilerplate. A plugin would add markers/auto-discovery; better to gather v1.0.0 feedback and add plugin in v1.1.0 if demand exists.

### Documentation
7. ❓ Should we create video tutorials in addition to written docs?
   - **Context**: YouTube tutorials for "Building Your First Agent"
   - **Action**: Defer decision to post-v1.0.0 based on community demand
   - **Review Point**: 2 weeks after v1.0.0 → Check GitHub Discussions feedback

8. ❓ What languages should we support for i18n documentation?
   - **Options**: English-only, English + Portuguese, English + multiple
   - **Action**: Assess based on PyPI download geography post-v0.5.0
   - **Review Point**: Start of Sprint P9 → Review PyPI stats, decide i18n scope

### Community & Ecosystem
9. ❓ Should we create a Discord/Slack community for ASAP developers?
   - **Action**: Decide based on GitHub Discussions activity
   - **Threshold**: If >50 active users, consider dedicated chat
   - **Review Point**: 1 month after v1.0.0 → Check Discussions engagement

10. ❓ Should we apply for sponsorship/foundation support?
    - **Options**: OpenSSF, NumFOCUS, independent
    - **Action**: Reassess after v1.0.0 release and adoption metrics
    - **Review Point**: 3 months after v1.0.0 → Check adoption (PyPI downloads, GitHub stars)

### Future Features (Post-v1.0.0)
11. ❓ Priority for next transport binding after WebSocket?
    - **Options**: gRPC (high performance), SSE (simple streaming), MQTT (IoT)
    - **Action**: Community poll after v1.0.0 release
    - **Review Point**: Start of v1.1.0 planning → Create GitHub Discussion poll

12. ❓ Should we support message encryption at protocol level?
    - **Context**: End-to-end encryption for sensitive agent communication
    - **Action**: Security review during v1.1.0 planning
    - **Review Point**: v1.1.0 kickoff → Conduct security threat modeling session

---

## 12. References

### Related Documents
- [Original PRD: ASAP Implementation](./prd-asap-implementation.md)
- [Original Tasks](../tasks/tasks-prd-asap-implementation.md)
- [Security Review Tasks](../tasks/tasks-security-review-report.md)
- [Security Review Report](../code-review/security-review-report.md)
- **[v0.5.0 Roadmap Tasks](../tasks/tasks-v0.5.0-roadmap.md)** - 64 tasks across 5 sprints
- **[v1.0.0 Roadmap Tasks](../tasks/tasks-v1.0.0-roadmap.md)** - 126 tasks across 13 sprints

### GitHub Issues (Mapped to Sprints)
- [Issue #7: Upgrade FastAPI](https://github.com/adriannoes/asap-protocol/issues/7) → **Sprint S1** (v0.5.0)
- [Issue #9: Refactor handle_message](https://github.com/adriannoes/asap-protocol/issues/9) → **Sprint S1** (v0.5.0)
- [Issue #10: Remove type: ignore](https://github.com/adriannoes/asap-protocol/issues/10) → **Sprint S1** (v0.5.0)
- [Issue #11: Missing test coverage](https://github.com/adriannoes/asap-protocol/issues/11) → **Sprint P7** (v1.0.0)
- [Issue #12: Token logging](https://github.com/adriannoes/asap-protocol/issues/12) → **Sprint P1** (v1.0.0)
- [Issue #13: Authorization scheme validation](https://github.com/adriannoes/asap-protocol/issues/13) → **Sprint S4** (v0.5.0)

### External Resources
- [Conventional Commits](https://www.conventionalcommits.org/)
- [Semantic Versioning](https://semver.org/)
- [OWASP API Security Top 10](https://owasp.org/www-project-api-security/)
- [12-Factor App](https://12factor.net/)
- [OpenTelemetry Python](https://opentelemetry.io/docs/instrumentation/python/)
- [MADR - Markdown ADR](https://adr.github.io/madr/) - Format for Architecture Decision Records

---

## 13. Changelog

| Date | Version | Change | Author |
|------|---------|--------|--------|
| 2026-01-24 | 1.0 | Initial PRD created | ASAP Team |
| 2026-01-24 | 1.1 | Converted "Open Questions" to "Design Decisions" with confirmed choices | ASAP Team |
| 2026-01-24 | 1.1 | Added new "Open Questions" section with genuine pending decisions | ASAP Team |
| 2026-01-24 | 1.1 | Enhanced References section with task file links and sprint mappings | ASAP Team |
| 2026-01-24 | 1.2 | Added review schedule and checkpoints to all Open Questions | ASAP Team |
| 2026-01-24 | 1.2 | Created PRD review tasks in v0.5.0 (1 checkpoint) and v1.0.0 (7 checkpoints) | ASAP Team |
| 2026-01-24 | 1.2 | Added final retrospective and post-release review tasks to Sprint P13 | ASAP Team |
| 2026-01-27 | 1.3 | Sprint S3 Review: Added DD-008 (HMAC deferred to v1.1.0+) | ASAP Team |
| 2026-01-27 | 1.3 | Sprint S3 Review: Resolved Open Question Q3 | ASAP Team |
| 2026-01-27 | 1.3 | Sprint S3 Review: Added S1-S3 Learnings section | ASAP Team |
| 2026-01-30 | 1.4 | Sprint P1 Checkpoint: Confirmed Q3/DD-008 (HMAC defer to v1.1.0+) | ASAP Team |

---

## Appendix A: Sprint Task Breakdown

Detailed task lists have been created in separate files:

### v0.5.0 Security-Hardened Release
**File**: [tasks-v0.5.0-roadmap.md](../tasks/tasks-v0.5.0-roadmap.md)
- **Sprints**: 5 (S1-S5)
- **Tasks**: 64
- **Duration**: 17-26 days (estimated)
- **Focus**: CRITICAL + HIGH priority security issues

### v1.0.0 Production-Ready Release  
**File**: [tasks-v1.0.0-roadmap.md](../tasks/tasks-v1.0.0-roadmap.md)
- **Sprints**: 13 (P1-P13)
- **Tasks**: 126
- **Duration**: 60-80 days (estimated)
- **Focus**: Complete security + performance + DX + production tooling

**Total Roadmap**: 18 sprints, 190 tasks, 77-106 days

---

## Appendix B: Risk Assessment

### High Risks
1. **Performance regression**: New security features may impact latency
   - **Mitigation**: Benchmark every PR, establish performance budget (<5% regression threshold)
   - **Owner**: Sprint leads for P3-P4
   
2. **Breaking changes**: Unintentional API changes during refactoring
   - **Mitigation**: Contract tests (Sprint P8), semantic versioning, deprecation warnings
   - **Owner**: All sprint leads
   
3. **Dependency conflicts**: New dependencies may conflict with user projects
   - **Mitigation**: Minimal dependency additions, test in isolated environments
   - **New Dependencies**: slowapi, opentelemetry-*, hypothesis, locust (dev-only)

### Medium Risks
4. **Community expectations**: Users may expect features not in scope
   - **Mitigation**: Clear roadmap in README, manage expectations via GitHub Discussions
   - **Reference**: Section 5 (Non-Goals) explicitly lists deferred features
   
5. **Testing complexity**: 800+ tests may slow down CI
   - **Mitigation**: Parallelize tests, use pytest markers for fast/slow tests
   - **Target**: Keep CI runtime <10 minutes
   
6. **Sprint timeline variance**: Flexible timelines may extend indefinitely
   - **Mitigation**: Set maximum duration for each sprint (2x estimate)
   - **Owner**: Project maintainers

### Low Risks
7. **Documentation debt**: Docs may lag behind implementation
   - **Mitigation**: Documentation sprints (P9-P10), review docs in all PRs
   - **Requirement**: All PRs touching public API must update docs

8. **Design decision reversal**: May need to change confirmed decisions
   - **Mitigation**: Document rationale in Section 10 (Design Decisions)
   - **Process**: If reversal needed, update PRD and create migration plan

---

**Document Status**: ✅ Active (Living Document)
**Last Updated**: 2026-01-27  
**Version**: 1.3  
**Next Review Schedule**:
- ~~**Sprint S3** (v0.5.0): Security decisions checkpoint~~ ✅ COMPLETED (2026-01-27)
- **Sprint P3** (v1.0.0): Performance decisions checkpoint  
- **Sprint P13** (v1.0.0): Final review before release
- **Post-Release**: 2 weeks after v1.0.0 (community feedback)

**Maintenance Process**:
1. Review open questions at designated sprint checkpoints
2. Document decisions as new DD-XXX entries in Section 10
3. Update task lists if decisions impact implementation
4. Create retrospective after major milestones

---

**END OF PRD**
