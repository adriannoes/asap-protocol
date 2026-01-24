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

## [Unreleased]

### Specification
- Initial protocol specification (DRAFT v1.2025.01)
- Core concepts: Agent, Manifest, Conversation, Task, Message, Part, Artifact, StateSnapshot
- Message types: TaskRequest, TaskResponse, TaskUpdate, TaskCancel, StateQuery, StateRestore
- MCP integration payloads: McpToolCall, McpToolResult, McpResourceFetch, McpResourceData
- Task state machine with 8 states
- Deployment patterns: direct, orchestrated, mesh
- Error taxonomy with 6 categories and 18 error codes
- Security considerations with optional request signing
- Observability with correlation IDs and metrics exposure

### Decided (via Critical Analysis)
- State persistence: Mode-selectable (snapshot default, event-sourced opt-in)
- Transport binding: JSON-RPC prioritized for A2A/MCP alignment
- Topology: Replaced fixed P2P default with context-based deployment patterns
- Consistency model: Causal consistency for task state
- Versioning: Hybrid Major.YYYY.MM format for spec, SemVer for implementation
- MCP integration: Envelope approach with streaming for large results
- MVP security: Added optional HMAC request signing

## [1.2025.01-draft] - 2025-01-15

- Initial draft specification
