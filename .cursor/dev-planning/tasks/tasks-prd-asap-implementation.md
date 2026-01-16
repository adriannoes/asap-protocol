# Tasks: ASAP Protocol Python Implementation

> Task list generated from [prd-asap-implementation.md](../prd/prd-asap-implementation.md)
> 
> **Approach**: TDD (Test-Driven Development) - Tests are written first to guide implementation.

---

## Relevant Files

### Core Models (Sprint 1)
- `src/__init__.py` - Package initialization with version
- `src/models/__init__.py` - Public model exports
- `src/models/base.py` - Base model configuration
- `src/models/ids.py` - ULID generation utilities
- `src/models/entities.py` - Core entities: Agent, Task, Conversation, etc.
- `src/models/parts.py` - Part types: TextPart, DataPart, etc.
- `src/models/payloads.py` - Payload types: TaskRequest, TaskResponse, etc.
- `src/models/envelope.py` - Message envelope wrapper
- `tests/models/test_entities.py` - Tests for entity models
- `tests/models/test_parts.py` - Tests for part models
- `tests/models/test_payloads.py` - Tests for payload models
- `tests/models/test_envelope.py` - Tests for envelope
- `schemas/` - Auto-generated JSON Schema files

### State Management (Sprint 2)
- `src/state/__init__.py` - State module exports
- `src/state/machine.py` - Task state machine implementation
- `src/state/snapshot.py` - Snapshot storage interfaces
- `src/errors.py` - Error taxonomy and exceptions
- `tests/state/test_machine.py` - State transition tests
- `tests/state/test_snapshot.py` - Snapshot store tests

### HTTP Transport (Sprint 3)
- `src/transport/__init__.py` - Transport module exports
- `src/transport/server.py` - FastAPI server implementation
- `src/transport/client.py` - Async HTTP client
- `src/transport/handlers.py` - Payload handlers
- `tests/transport/test_server.py` - Server integration tests
- `tests/transport/test_client.py` - Client unit tests

### Examples & CLI (Sprint 4-5)
- `examples/echo_agent.py` - Simple echo agent example
- `examples/coordinator.py` - Coordinator agent example
- `examples/run_demo.py` - Demo runner script
- `src/cli.py` - CLI entry point

### Configuration
- `pyproject.toml` - Project configuration and dependencies
- `.github/workflows/ci.yml` - CI/CD pipeline
- `README.md` - Project documentation

### Notes

- **Test runner**: Use `uv run pytest` for faster execution (uv manages deps + runs pytest)
- **Specific tests**: `uv run pytest tests/models/` to run module tests
- **Coverage**: `uv run pytest --cov=src tests/`
- **Schema export**: `uv run python -m src.models --export-schemas`

> **Why uv + pytest?** `uv` is 10-100x faster than pip for dependency management. `pytest` is the de-facto Python testing framework. Combined: `uv run pytest` gives us both speed and power.

---

## Sprint 0: Project Setup

### Technology Stack (January 2026)

| Technology | Version | Rationale |
|------------|---------|-----------|
| **Python** | 3.13.x | Latest stable. Enhanced typing, better errors, experimental JIT |
| **uv** | latest | Rust-based, 10-100x faster than pip |
| **Pydantic** | ≥2.12 | Rust core, native JSON Schema |
| **FastAPI** | ≥0.124 | Full Pydantic v2 integration |
| **httpx** | ≥0.28 | Stable async HTTP client |
| **uvicorn** | ≥0.34 | ASGI server with HTTP/2 |
| **python-ulid** | ≥3.0 | ULID generation |
| **mypy** | ≥1.14 | Static type checker (strict mode) |
| **ruff** | ≥0.14 | Linter + formatter |
| **mkdocs-material** | ≥9.5 | Modern documentation |
| **pytest** | ≥8.0 | Test framework |

### Open Source Requirements

| File | Purpose |
|------|---------|
| `LICENSE` | Apache 2.0 license |
| `CONTRIBUTING.md` | Contribution guidelines |
| `CODE_OF_CONDUCT.md` | Community standards |
| `SECURITY.md` | Security policy |
| `.github/ISSUE_TEMPLATE/bug_report.yml` | Bug report template |
| `.github/ISSUE_TEMPLATE/feature_request.yml` | Feature request template |
| `.github/PULL_REQUEST_TEMPLATE.md` | PR template |

### Tasks

- [x] 1.0 Project Foundation
  - [x] 1.1 Create `pyproject.toml` with:
    - `requires-python = ">=3.13"`
    - Deps: `pydantic>=2.12`, `fastapi>=0.124`, `httpx>=0.28`, `uvicorn>=0.34`, `python-ulid>=3.0`
    - Dev: `pytest>=8.0`, `pytest-asyncio>=0.24`, `pytest-cov>=6.0`, `mypy>=1.14`, `ruff>=0.14`
    - Docs: `mkdocs-material>=9.5`, `mkdocstrings[python]>=0.27`
  - [x] 1.2 Create directory structure: `src/`, `tests/`, `schemas/`, `examples/`, `docs/`
  - [x] 1.3 Create `src/__init__.py` with `__version__ = "0.1.0"`

- [ ] 1.1 Open Source Files
  - [x] 1.4 Create `LICENSE` (Apache 2.0)
  - [x] 1.5 Create `CONTRIBUTING.md` with dev setup, commit conventions, PR process
  - [x] 1.6 Create `CODE_OF_CONDUCT.md` (Contributor Covenant)
  - [x] 1.7 Create `SECURITY.md` with vulnerability reporting process

- [x] 1.2 GitHub Templates
  - [x] 1.8 Create `.github/ISSUE_TEMPLATE/bug_report.yml`
  - [x] 1.9 Create `.github/ISSUE_TEMPLATE/feature_request.yml`
  - [x] 1.10 Create `.github/PULL_REQUEST_TEMPLATE.md`

- [x] 1.3 CI/CD Pipeline
  - [x] 1.11 Create `.github/workflows/ci.yml` with jobs:
    - **lint**: `uv run ruff check . && uv run ruff format --check .`
    - **type-check**: `uv run mypy src/`
    - **test**: `uv run pytest --cov=src --cov-report=xml`
    - **security**: `uv run pip-audit`
  - [x] 1.12 Configure Codecov for coverage reports
  - [x] 1.13 Create `.github/workflows/release.yml` for PyPI publish on tag

- [x] 1.4 Code Quality Config
  - [x] 1.14 Configure ruff in `pyproject.toml` (target-version="py313", rules, format)
  - [x] 1.15 Configure mypy in `pyproject.toml` (strict=true, plugins)
  - [x] 1.16 Create `tests/conftest.py` with pytest-asyncio config

- [x] 1.5 Documentation Setup
  - [x] 1.17 Create `mkdocs.yml` with material theme config
  - [x] 1.18 Create `docs/index.md` with project overview
  - [x] 1.19 Add docs deploy workflow (GitHub Pages)

- [x] 1.6 Final Verification
  - [x] 1.20 Create `README.md` with badges (CI, coverage, PyPI, license)
  - [x] 1.21 Verify all commands pass: `uv run pytest`, `uv run ruff check .`, `uv run mypy src/`
  - [x] 1.22 First commit: `feat: initial project setup with Python 3.13, Apache 2.0`

**Definition of Done**: 
- ✅ All CI jobs pass (lint, type-check, test, security)
- ✅ Open source files present (LICENSE, CONTRIBUTING, CODE_OF_CONDUCT)
- ✅ GitHub templates working
- ✅ `uv run mkdocs serve` shows docs locally

---

## Sprint 1: Core Models (TDD)

- [ ] 2.0 Core Models Implementation
  - [ ] 2.1 **TEST FIRST**: Create `tests/models/test_ids.py` with tests for ULID generation
  - [ ] 2.2 Implement `src/models/ids.py` with `generate_id()` function using python-ulid
  - [ ] 2.3 Create `src/models/base.py` with `ASAPBaseModel(BaseModel)` (common config)
  - [ ] 2.4 **TEST FIRST**: Create `tests/models/test_entities.py` with tests for all 7 entities (Agent, Manifest, Conversation, Task, Message, Artifact, StateSnapshot)
  - [ ] 2.5 Implement `src/models/entities.py` with all entity models
  - [ ] 2.6 **TEST FIRST**: Create `tests/models/test_parts.py` with tests for 5 Part types + discriminated union
  - [ ] 2.7 Implement `src/models/parts.py` with TextPart, DataPart, FilePart, ResourcePart, TemplatePart
  - [ ] 2.8 **TEST FIRST**: Create `tests/models/test_payloads.py` with tests for all 12 payload types
  - [ ] 2.9 Implement `src/models/payloads.py` with all payload models + discriminated union
  - [ ] 2.10 **TEST FIRST**: Create `tests/models/test_envelope.py` with tests for Envelope (auto-gen id, timestamp)
  - [ ] 2.11 Implement `src/models/envelope.py` with Envelope model
  - [ ] 2.12 Create `src/models/__init__.py` with all public exports
  - [ ] 2.13 Create script to export JSON Schemas to `schemas/` directory
  - [ ] 2.14 Commit: `feat(models): add all core entities, parts, payloads and envelope`

**Definition of Done**: All models have passing tests, JSON Schemas exported, `from src.models import Envelope, TaskRequest` works.

---

## Sprint 2: State Machine (TDD)

- [ ] 3.0 State Machine & Persistence
  - [ ] 3.1 **TEST FIRST**: Create `tests/state/test_machine.py` with tests for all 8 states and valid/invalid transitions
  - [ ] 3.2 Implement `src/state/machine.py` with TaskStatus enum, VALID_TRANSITIONS dict, can_transition(), transition() functions
  - [ ] 3.3 Implement `src/errors.py` with InvalidTransitionError and error taxonomy from spec
  - [ ] 3.4 **TEST FIRST**: Create `tests/state/test_snapshot.py` with tests for SnapshotStore interface
  - [ ] 3.5 Implement `src/state/snapshot.py` with SnapshotStore protocol and InMemorySnapshotStore
  - [ ] 3.6 Create `src/state/__init__.py` with public exports
  - [ ] 3.7 Commit: `feat(state): add task state machine and snapshot persistence`

**Definition of Done**: All state transitions tested (valid + invalid), snapshots can be saved/restored, 100% coverage on state module.

---

## Sprint 3: HTTP Transport (TDD)

- [ ] 4.0 HTTP Transport Layer
  - [ ] 4.1 **TEST FIRST**: Create `tests/transport/test_server.py` with tests for POST `/asap` endpoint and GET `/.well-known/asap/manifest.json`
  - [ ] 4.2 Implement `src/transport/server.py` with FastAPI app factory, JSON-RPC endpoint, manifest endpoint
  - [ ] 4.3 Implement `src/transport/handlers.py` with handler registry pattern and base TaskRequestHandler
  - [ ] 4.4 **TEST FIRST**: Create `tests/transport/test_client.py` with tests for ASAPClient (async context manager, send method)
  - [ ] 4.5 Implement `src/transport/client.py` with async ASAPClient class
  - [ ] 4.6 Create `src/transport/__init__.py` with public exports
  - [ ] 4.7 **TEST FIRST**: Create `tests/transport/test_integration.py` with server + client integration test
  - [ ] 4.8 Verify integration: client sends TaskRequest, server responds with TaskResponse
  - [ ] 4.9 Commit: `feat(transport): add FastAPI server and async client`

**Definition of Done**: Server runs with `uvicorn`, client can send/receive, manifest accessible via curl.

---

## Sprint 4: End-to-End Integration

- [ ] 5.0 End-to-End Integration
  - [ ] 5.1 Create `examples/echo_agent.py` - Agent that echoes input as output
  - [ ] 5.2 Create `examples/coordinator.py` - Agent that sends tasks to echo_agent
  - [ ] 5.3 Create `examples/run_demo.py` - Script that starts both agents and runs demo flow
  - [ ] 5.4 **TEST**: Create `tests/e2e/test_two_agents.py` with automated E2E test
  - [ ] 5.5 Verify trace_id and correlation_id flow through full request cycle
  - [ ] 5.6 Add logging to show message flow in terminal
  - [ ] 5.7 Commit: `feat(examples): add echo agent demo with E2E test`

**Definition of Done**: `uv run python examples/run_demo.py` shows complete TaskRequest → TaskResponse flow with correlated logs.

---

## Sprint 5: Documentation & Packaging

- [ ] 6.0 Documentation & Packaging
  - [ ] 6.1 Add docstrings to all public classes and functions
  - [ ] 6.2 Update README.md with: installation, quick start, API overview, links to spec
  - [ ] 6.3 Create `src/cli.py` with basic CLI (`asap --version`)
  - [ ] 6.4 Add CLI entry point to `pyproject.toml`
  - [ ] 6.5 Update CHANGELOG.md with all changes
  - [ ] 6.6 Verify `pyproject.toml` has complete metadata (description, authors, license, classifiers)
  - [ ] 6.7 Test publish to TestPyPI: `uv publish --repository testpypi`
  - [ ] 6.8 Verify installation from TestPyPI works
  - [ ] 6.9 Commit: `chore: prepare v0.1.0 release`

**Definition of Done**: Package installable from TestPyPI, README allows getting started in <5 min, `asap --version` works.

---

## Summary

| Sprint | Tasks | Focus | TDD Tests First |
|--------|-------|-------|-----------------|
| 0 | 1.0 (8 sub-tasks) | Setup | N/A |
| 1 | 2.0 (14 sub-tasks) | Models | ✅ 2.1, 2.4, 2.6, 2.8, 2.10 |
| 2 | 3.0 (7 sub-tasks) | State | ✅ 3.1, 3.4 |
| 3 | 4.0 (9 sub-tasks) | Transport | ✅ 4.1, 4.4, 4.7 |
| 4 | 5.0 (7 sub-tasks) | E2E | ✅ 5.4 |
| 5 | 6.0 (9 sub-tasks) | Polish | N/A |

**Total**: 54 sub-tasks across 6 sprints

---

*Generated: 2026-01-16 | Based on PRD v1.1*
