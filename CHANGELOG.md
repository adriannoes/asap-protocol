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

## [Unreleased]

### Added
- Future changes will be documented here

## [1.2025.01-draft] - 2025-01-15

- Initial draft specification
