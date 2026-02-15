# Changelog

All notable changes to the ASAP Protocol will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2026-01-23

First alpha release of the ASAP Protocol Python implementation.

### Added

#### Security & Policy (Sprint 6)
- **SECURITY.md**:
  - Updated to use GitHub Private Vulnerability Reporting
  - Clarified supported versions and reporting workflow
  - Added template for vulnerability reports
- **CODE_OF_CONDUCT.md**:
  - Simplified to a "human-readable" version focusing on respect and inclusivity
  - Removed excessive legalistic text while maintaining core standards
- **Project Structure**:
  - Improved `.gitignore` with better coverage for Python/tooling artifacts
  - Cleaned up and migrated `.cursor/commands` to `.mdc` format
  - Standardized project documentation

#### Core Models (Sprint 1)
- `ASAPBaseModel` base class with frozen config and extra forbid
- ULID-based ID generation helpers (`generate_id`, `generate_task_id`, etc.)
- Entity models: `Agent`, `Manifest`, `Conversation`, `Task`, `Message`, `Artifact`, `StateSnapshot`
- Part models: `TextPart`, `DataPart`, `FilePart`, `ResourcePart`, `TemplatePart`
- Payload models: `TaskRequest`, `TaskResponse`, `TaskUpdate`, `TaskCancel`, `MessageSend`
- MCP integration payloads: `McpToolCall`, `McpToolResult`, `McpResourceFetch`, `McpResourceData`
- `Envelope` model with auto-generated ID and timestamp
- JSON Schema export for all 24 model types

#### State Management (Sprint 2)
- `TaskStatus` enum with 8 states (submitted, working, input_required, paused, completed, failed, cancelled, rejected)
- `TaskStateMachine` with valid transition rules and validation
- `SnapshotStore` interface with `InMemorySnapshotStore` implementation
- `InvalidTransitionError` exception for state machine violations

#### HTTP Transport (Sprint 3)
- FastAPI server with `POST /asap` endpoint for JSON-RPC 2.0 messages
- `GET /.well-known/asap/manifest.json` for agent discovery
- `HandlerRegistry` for extensible payload processing
- `ASAPClient` async HTTP client with retry logic and idempotency
- JSON-RPC 2.0 request/response models with proper error codes

#### End-to-End Integration (Sprint 4)
- Example `echo_agent.py` that echoes input as output
- Example `coordinator.py` that orchestrates task requests
- `run_demo.py` script for running two-agent demonstration
- E2E test suite validating full agent-to-agent communication

#### Documentation & Polish (Sprint 5)
- Comprehensive docstrings for all public classes and methods
- MkDocs site with API reference documentation
- README with quick start guide and examples
- CLI commands: `asap --version`, `export-schemas`, `list-schemas`, `show-schema`

#### Production Readiness (Sprint 6)
- **Documentation extensions**:
  - `docs/security.md` - Auth schemes, request signing, TLS guidance
  - `docs/state-management.md` - Task lifecycle, snapshots, versioning
  - `docs/transport.md` - HTTP/JSON-RPC binding details
  - `docs/migration.md` - A2A/MCP to ASAP transition guide
- **Observability**:
  - `GET /asap/metrics` endpoint in Prometheus format
  - `MetricsCollector` with request counters and latency histograms
  - `docs/metrics.md` with usage examples
- **Tooling**:
  - `asap validate-schema [file]` command for JSON validation
  - Auto-detection of envelope schema type
  - Detailed validation error messages
- **Benchmarks**:
  - `benchmarks/` directory with pytest-benchmark tests
  - Model serialization/deserialization benchmarks
  - HTTP transport latency and throughput benchmarks

### Technical Details

- **Python**: Requires Python 3.13+
- **Dependencies**: Pydantic 2.12+, FastAPI 0.124+, httpx 0.28+, structlog 24.1+
- **Type Safety**: Full mypy strict mode compliance
- **Test Coverage**: 415+ tests with comprehensive coverage
- **Linting**: Ruff for linting and formatting

## [0.3.0] - 2026-01-26

### Changed

#### Test Infrastructure Refactoring (PR #18)
- **Test Organization**:
  - Reorganized test structure with clear separation between unit, integration, and E2E tests
  - Created `tests/transport/unit/` for isolated unit tests
  - Created `tests/transport/integration/` for integration tests with proper isolation
  - Created `tests/transport/e2e/` for end-to-end tests
- **Test Stability**:
  - Fixed 33 failing tests caused by `slowapi.Limiter` global state interference
  - Implemented process isolation using `pytest-xdist` to prevent test interference
  - Added aggressive monkeypatch strategy for complete rate limiter isolation
  - Separated rate-limiting tests from core server tests to prevent cross-contamination
- **Documentation**:
  - Added comprehensive testing guide in `docs/testing.md`
  - Documented test organization strategy and isolation techniques
  - Added examples for writing unit, integration, and E2E tests

### Fixed
- Resolved `UnboundLocalError` in `server.py` related to rate limiter initialization
- Fixed test flakiness caused by global state persistence across test runs
- Improved test reliability with proper fixture isolation

### Technical Details
- **Test Count**: 578 tests (all passing)
- **Test Execution**: Process isolation via `pytest-xdist` for complete state separation
- **Test Coverage**: Maintained comprehensive coverage across all modules

## [0.5.0] - 2026-01-28

Security-hardened release with comprehensive authentication, DoS protection, replay attack prevention, and secure logging.

**Version History**: This release builds upon v0.1.0 (initial alpha) and v0.3.0 (test infrastructure improvements). All features from previous versions are preserved with zero breaking changes.

### Added

#### Security Features (Sprint S1-S4)
- **Authentication**: Bearer token authentication with configurable token validators
  - `AuthenticationMiddleware` for request authentication
  - `BearerTokenValidator` for token validation
  - Sender verification to ensure authenticated requests match envelope sender
  - Support for multiple authentication schemes via `AuthScheme` model
- **Replay Attack Prevention**:
  - Timestamp validation with 5-minute window (`MAX_ENVELOPE_AGE_SECONDS`)
  - Optional nonce validation for replay attack prevention (`require_nonce=True`)
  - `InMemoryNonceStore` for nonce tracking with configurable TTL (10 minutes)
  - Empty nonce string validation with clear error messages
- **DoS Protection**:
  - Rate limiting (100 requests/minute per sender, configurable)
  - Request size limits (10MB default, configurable via `max_request_size`)
  - Thread pool bounds via `BoundedExecutor` to prevent resource exhaustion
  - Circuit breaker pattern for client-side failure handling
- **HTTPS Enforcement**: Client-side HTTPS validation in production mode (`require_https=True`)
- **Secure Logging**: Automatic sanitization of sensitive data in logs
  - `sanitize_token()`: Masks full tokens, shows only prefix
  - `sanitize_nonce()`: Truncates nonces in error logs
  - `sanitize_url()`: Masks credentials in connection URLs
- **Input Validation**: Enhanced validation with strict schema enforcement

#### Retry Logic (Sprint S4)
- Exponential backoff with jitter for automatic retry on transient failures
- Configurable retry parameters (`max_retries`, `base_delay`, `max_delay`, `jitter`)
- `Retry-After` header support for rate-limited responses
- Circuit breaker integration for production deployments

#### Code Quality Improvements
- Removed all `type: ignore` suppressions, achieved full mypy strict compliance (Issue #10)
- Refactored `handle_message` into smaller, testable helper functions (Issue #9)
- Enhanced type safety with explicit `None` checks and proper error handling

#### Testing & Coverage
- Comprehensive test coverage: 753 tests with 95.90% coverage
- Compatibility tests for v0.1.0 and v0.3.0 upgrade paths
- Security-focused test suites for authentication, rate limiting, and validation
- Automated upgrade test scripts for version compatibility verification

#### Documentation
- Updated `docs/security.md` with comprehensive security guidance
- Enhanced `docs/transport.md` with retry configuration and circuit breaker documentation
- Added security features to README "Why ASAP?" section
- Created compatibility test documentation

### Changed

- **FastAPI Upgrade**: Upgraded from 0.124 to 0.128.0+ (Issue #7)
- **Dependency Monitoring**: Configured Dependabot for automated security updates
- **Nonce TTL**: Made configurable, derived from `MAX_ENVELOPE_AGE_SECONDS` constant (2x envelope age)
- **Rate Limiting**: Enabled by default (100/minute) with per-sender tracking
- **Request Size Limits**: Enabled by default (10MB) with configurable limits

### Security

- **Zero Breaking Changes**: All security features are opt-in for backward compatibility
- **Security Audit**: Passed `pip-audit` (no known vulnerabilities) and `bandit` (all issues addressed)
- **Log Sanitization**: Prevents sensitive data leakage in logs (Issue #12)
- **Test Coverage**: Achieved ≥95% coverage on security-critical modules (Issue #11)

### Fixed

- Fixed empty nonce string validation (now rejects with clear error message)
- Enhanced error handling for invalid Content-Length headers
- Improved exception handling in authentication middleware
- Fixed circuit breaker persistence across client instances (Red Team remediation)

### Technical Details

- **Python**: Requires Python 3.13+
- **Dependencies**: Pydantic 2.12.5+, FastAPI 0.128.0+, httpx 0.28.1+, structlog 24.1+
- **Type Safety**: Full mypy strict mode compliance
- **Test Coverage**: 753 tests with 95.90% overall coverage
- **Linting**: Ruff for linting and formatting, all checks passing
- **Issues Closed**: #7, #9, #10, #11, #12, #13

## [Unreleased]

### Added
- Future changes will be documented here

---

## [1.2.0] - 2026-02-15

Verified Identity: Ed25519 signed manifests, trust levels, optional mTLS, and compliance harness.
Backward compatible with v1.1.0.

### Added

#### Signed Manifests (T1, SD-4, SD-5)
- **Ed25519 key management**: `asap.crypto.keys` — `generate_keypair`, `serialize_private_key`, `load_private_key_from_file_sync`, `load_private_key_from_env`
- **Manifest signing**: `asap.crypto.signing` — `sign_manifest`, `verify_manifest`, JCS canonicalization (RFC 8785)
- **SignedManifest model**: `asap.crypto.models` — `SignedManifest`, `SignatureBlock` with `public_key` and `trust_level`
- **CLI**: `asap keys generate`, `asap manifest sign`, `asap manifest verify`, `asap manifest info`

#### Trust Levels (T2, SD-5)
- **Trust level model**: `asap.crypto.trust_levels` — `TrustLevel` enum (self-signed, verified, enterprise)
- **Trust detection**: `asap.crypto.trust` — `detect_trust_level`, `sign_with_ca` for Verified badge simulation
- **Client verification**: `ASAPClient` — `verify_signatures`, `trusted_manifest_keys` for optional manifest signature verification

#### mTLS (T2, SD-6)
- **Optional mTLS**: `asap.transport.mtls` — `MTLSConfig`, `create_ssl_context`, `mtls_config_to_uvicorn_kwargs`
- **Server/client support**: `create_app(mtls_config=...)`, `ASAPClient(mtls_config=...)`
- **Documentation**: `docs/security/mtls.md` — Enterprise CA, client cert configuration

#### Compliance Harness (T3)
- **asap-compliance package**: Separate PyPI package for protocol compliance testing
- **Handshake validation**: Health endpoint, manifest schema, signed manifest verification, version compatibility
- **Schema validation**: Envelope, TaskRequest, TaskResponse, McpToolResult, MessageAck; `extra="forbid"`
- **State machine validation**: Task lifecycle (PENDING → RUNNING → COMPLETED/FAILED)
- **SLA validation**: Timeout and progress schema checks
- **Usage**: `pytest --asap-agent-url https://your-agent.example.com -m asap_compliance`

#### Testing & Benchmarks (T4)
- **Cross-version compatibility**: Signed manifests with discovery; compliance harness against signed manifest agents
- **Crypto benchmarks**: `benchmarks/benchmark_crypto.py` — Ed25519 sign/verify, JCS canonicalization, compliance handshake
- **Coverage**: CLI keys/manifest tests, mTLS edge cases, integration tests

### Changed

- **Discovery validation**: `validate_signed_manifest_response` accepts plain or signed manifests; optional signature verification
- **AGENTS.md**: mTLS note updated (now implemented); crypto module and compliance harness documented

### Deferred (not in v1.2.0)

- **Registry API**: Centralized agent registry backend (planned for v2.1)
- **DeepEval integration**: Intelligence layer for compliance (planned for v2.2+)
- **Lite Registry** (v1.1) continues as discovery mechanism

### Technical Details

- **Python**: 3.13+
- **Tests**: 1940+ (asap-protocol), 54 (asap-compliance)
- **Coverage**: ~94.2% (asap-protocol)
- **New packages**: `asap-compliance` on PyPI (separate from `asap-protocol`)

---

## [1.0.0] - 2026-02-03

Production-ready release. All features from v0.5.0 preserved with backward compatibility (see contract tests: v0.1.0 → v1.0.0, v0.5.0 ↔ v1.0.0).

### Added

#### Security & Validation (P1–P2)
- **Log sanitization**: Credential and token patterns in logs; `ASAP_DEBUG` env var for controlled verbose output
- **Handler security**: `FilePart` URI validation, path traversal detection; `docs/security.md` updated
- **Thread safety**: Thread-safe `HandlerRegistry` for concurrent handler registration and execution
- **URN validation**: Max 256-character URNs, task depth limits, enhanced input validation
- **`ManifestCache` LRU eviction**: `max_size` limit with LRU eviction to prevent unbounded cache growth

#### Performance (P3–P4)
- **Connection pooling**: Configurable `ASAPClient` connection pooling; supports 1000+ concurrent connections
- **Manifest caching**: TTL-based manifest cache; `manifest_cache_size` parameter for LRU-bounded cache
- **Batch operations**: `send_batch` with HTTP/2 multiplexing for higher throughput
- **Compression**: Gzip and Brotli support; `Accept-Encoding` negotiation; ~70% bandwidth reduction for JSON

#### Developer Experience (P5–P6)
- **Examples**: 15+ real-world examples (auth patterns, rate limiting, state migration, streaming, multi-step workflow, MCP integration, MCP client, error recovery, long-running, orchestration)
- **Testing utilities**: `asap.testing` fixtures, factories, and helpers; reduced test boilerplate
- **Trace visualization**: `asap trace` CLI command; optional Web UI for trace parsing
- **Dev server**: Hot reload, debug logging, REPL mode for local development
- **CLI**: `trace`, `repl`, `export-schemas`, `list-schemas`, `show-schema`, `validate-schema` commands

#### Testing (P7–P8)
- **Property-based tests**: Hypothesis-based tests for models, IDs, and edge cases
- **Load testing**: Locust-based load tests; RPS and latency benchmarks
- **Chaos tests**: Failure injection, message reliability under faults
- **Contract tests**: v0.1.0 → v1.0.0 and v0.5.0 ↔ v1.0.0 upgrade paths; schema evolution and rollback coverage
- **Integration tests**: Batch + auth + pooling; MCP server + ASAP protocol; compression edge cases

#### Documentation (P9–P10)
- **Tutorials**: 5 step-by-step tutorials (beginner → advanced → DevOps)
- **ADRs**: 17 Architecture Decision Records (ULID, async-first, JSON-RPC, Pydantic, state machine, security, FastAPI, httpx, snapshot, Python 3.13, rate limiting, error taxonomy, MCP, testing, observability, versioning, failure injection)
- **Deployment**: Docker image, Kubernetes manifests, Helm chart, health probes
- **Troubleshooting**: Guide covering common issues and diagnostics

#### Observability (P11–P12)
- **OpenTelemetry**: Tracing integration with OTLP export; zero-config for development
- **Metrics**: Structured metrics (counters, histograms); Prometheus export; `asap_handler_errors_total` and transport client metrics
- **Dashboards**: Grafana dashboards (RED, detailed) for ASAP agents
- **Jaeger**: Integration test and trace export to Jaeger

#### MCP (P12)
- **MCP implementation**: Full MCP server/client; `serve_stdio`; tool call/result, resource fetch/data payloads
- **Validation**: Parse error handling, tool args validation, sanitized error responses
- **Interop**: Default `request_id_type=str` for interoperability

### Changed

- **MCP**: `request_id_type` defaults to `str` for better interoperability
- **CI**: Parallel jobs (lint, types, tests, security); path filters; coverage thresholds
- **Build**: Per-module mypy overrides; `jsonschema` dependency; pytest `pythonpath` for tests

### Fixed

- **Transport**: Narrow `JSONResponse | str` with cast for mypy in `handle_message`
- **MCP**: Parse errors, tool args validation, error sanitization; `serve_stdio` support
- **Observability**: Server import order, tracing type hints, debug logging, `reset_tracing`
- **Tests**: Jaeger handler trace detection among multiple traces; rate limiter isolation; flaky ULID sortable test
- **Handlers**: Use `get_running_loop` instead of deprecated `get_event_loop`
- **Utils**: `sanitize_url` exception fallback coverage

### Technical Details

- **Python**: 3.13+
- **Tests**: 1379+ passing; property, load, chaos, and contract test suites
- **Coverage**: ~95% (target met)
- **Linting**: Ruff (check + format), mypy strict
- **Security**: `pip-audit` clean; bandit (Low findings limited to examples and test helpers)

## [1.1.0] - 2026-02-10

Identity layer: OAuth2/OIDC, discovery, WebSocket, state storage, and webhooks. Backward compatible with v1.0.0.

### Added

#### Identity & Auth (S1, ADR-17)
- **OAuth2 server**: `OAuth2Config`, `OAuth2Middleware` — JWT validation via JWKS, optional scope, path prefix
- **OAuth2 client**: `OAuth2ClientCredentials` for client_credentials grant; `Token` model with expiry
- **OIDC discovery**: `OIDCDiscovery`, `OIDCConfig` — auto-config from `/.well-known/openid-configuration`
- **Custom Claims identity binding**: JWT custom claim (default: `https://github.com/adriannoes/asap-protocol/agent_id`; future: `https://asap-protocol.com/agent_id`) or `ASAP_AUTH_SUBJECT_MAP` allowlist; envelope sender must match authenticated agent
- **v1.1 Security Model**: `docs/security/v1.1-security-model.md` — trust limitations, Custom Claims, Auth0/Keycloak/Azure AD guides

#### Discovery (S2, SD-11, ADR-15)
- **Well-known**: `GET /.well-known/asap/manifest.json`; `ASAPClient.discover(base_url)`
- **Lite Registry**: `discover_from_registry()`, `LiteRegistry` — static JSON on GitHub Pages for agent discovery
- **Health/liveness**: `GET /.well-known/asap/health` with `ttl_seconds` in manifest (SD-10, ADR-14); `HealthStatus` model

#### State Storage (S2.5, SD-9, ADR-13)
- **MeteringStore Protocol**: Interface for usage metering (v1.3 foundation)
- **SQLiteSnapshotStore**: Persistent snapshot store via `aiosqlite`; `src/asap/state/stores/sqlite.py`
- **Storage configuration**: `ASAP_STORAGE_BACKEND` env (e.g. `memory`, `sqlite`); `create_snapshot_store()`
- **Best Practices**: `docs/best-practices/agent-failover-migration.md` — state handover, failover patterns

#### WebSocket (S3, SD-3, ADR-16)
- **WebSocket server**: ASAP messages over WebSocket; `websocket_asap` endpoint
- **WebSocket client**: `ASAPClient(transport_mode="websocket")`, `WebSocketTransport`
- **MessageAck**: Selective ack for state-changing messages; `requires_ack` on Envelope; `MessageAck` payload
- **AckAwareClient**: Pending ack tracking, timeout/retry, circuit breaker integration
- **WebSocket rate limiting**: Per-connection token bucket (default 10 msg/s)

#### Webhooks (S4)
- **WebhookDelivery**: POST callbacks to validated URLs; HMAC-SHA256 `X-ASAP-Signature`; SSRF checks (private IPs, localhost blocked; HTTPS in production)
- **WebhookRetryManager**: Retry queue, exponential backoff (1s–16s, max 5 retries), dead-letter handling, per-URL rate limit
- **`asap.transport.webhook`**: `WebhookDelivery`, `WebhookRetryManager`; `WebhookURLValidationError` in `asap.errors`

#### Transport & Infra
- **Custom rate limiter**: Migrated from slowapi to `ASAPRateLimiter` (using `limits` package); removes Python 3.12+ deprecation warnings
- **Example**: `secure_agent.py` — OAuth2Config server + OAuth2ClientCredentials client with env-based config

### Changed

- **Rate limiting**: Replaced slowapi with `ASAPRateLimiter`; `rate_limit.py`; backward-compatible `create_limiter()` / `create_test_limiter()`
- **Dependencies**: Removed `slowapi`; added `limits>=3.0`
- **InMemorySnapshotStore**: Moved to `src/asap/state/stores/memory.py`; re-exported for backward compatibility

### Technical Details

- **Python**: 3.13+
- **Tests**: 1800+ passing; property, integration, chaos, contract suites
- **Coverage**: ~94.5% (examples/dnssd omitted); 95% target in backlog
- **Docs**: v1.1 features table in `docs/index.md`; README/AGENTS.md updated; Security Model linked from README, AGENTS.md, docs

