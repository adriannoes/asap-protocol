# Sprint S4: Versioning & Async Protocol

**PRD**: §4.8 Unified Versioning (P1), §4.9 Async Protocol Resolution (P1)
**Branch**: `feat/versioning-async`
**PR Scope**: ASAP-Version header, content negotiation, AsyncSnapshotStore/MeteringStore protocols
**Depends on**: Sprint S3 (Errors & Streaming)

## Relevant Files

### New Files
- `tests/contract/test_version_negotiation.py` — Contract tests for version compat

### Modified Files
- `src/asap/models/constants.py` — `ASAP_VERSION_HEADER`, default + supported transport versions
- `src/asap/transport/jsonrpc.py` — `VERSION_INCOMPATIBLE` (-32000) for negotiation failures
- `src/asap/transport/middleware.py` — `ASAPVersionMiddleware` (negotiate + response header)
- `src/asap/transport/server.py` — ASAP-Version middleware
- `tests/transport/test_server.py` — `TestASAPVersionMiddleware` contract-style checks
- `src/asap/transport/client.py` — ``ASAPClient`` sends/parses ``ASAP-Version`` (HTTP JSON-RPC)
- `tests/transport/test_http_client.py` — Version header and ``last_response_asap_version`` tests
- `tests/state/test_storage_factory.py` — `create_async_snapshot_store` tests
- `src/asap/models/entities.py` — `supported_versions` in Manifest
- `tests/fixtures/verified_manifest.json`, `tests/fixtures/self_signed_manifest.json` — regenerated via `scripts/regenerate_signed_fixtures.py` after Manifest change
- `tests/crypto/test_signing.py` — canonicalize test includes all `model_dump` keys
- `tests/state/test_snapshot.py` — `TestAsyncInMemorySnapshotStore` (coverage + parity)
- `src/asap/state/snapshot.py` — AsyncSnapshotStore Protocol; `create_async_snapshot_store`
- `src/asap/state/stores/memory.py` — `AsyncInMemorySnapshotStore`
- `src/asap/state/metering.py` — AsyncMeteringStore Protocol
- `src/asap/state/stores/sqlite.py` — `_SQLiteSnapshotBackend`, `SQLiteAsyncSnapshotStore`, `SQLiteSnapshotStore`
- `src/asap/state/stores/__init__.py` — re-export async factory + `AsyncInMemorySnapshotStore`
- `src/asap/state/__init__.py` — export `create_async_snapshot_store`

---

## Tasks

### 1.0 Unified Versioning

- [x] 1.1 Add ASAP-Version header middleware to server
  - **File**: `src/asap/transport/server.py` (modify)
  - **What**: Middleware reads `ASAP-Version` header. Default to current version if absent. Return JSON-RPC error -32000 if incompatible. Set `ASAP-Version` on all responses.
  - **Verify**: Tests for no header (default), compatible header, incompatible header

- [x] 1.2 Add ASAP-Version header to client
  - **File**: `src/asap/transport/client.py` (modify; transport HTTP client)
  - **What**: `ASAPClient` sends `ASAP-Version` with supported versions. Parse response header.
  - **Verify**: `uv run pytest tests/transport/test_http_client.py -k "version"`

- [x] 1.3 Add `supported_versions` to Manifest
  - **File**: `src/asap/models/entities.py` (modify)
  - **What**: `supported_versions: list[str] = ["2.2"]` field. Update well-known endpoint.
  - **Verify**: `uv run pytest tests/models/test_entities.py tests/discovery/test_wellknown.py`

- [x] 1.4 Version negotiation contract tests
  - **File**: `tests/contract/test_version_negotiation.py` (create)
  - **What**: v2.1 client → v2.2 server, v2.2 client → v2.1 server, incompatible version.
  - **Verify**: `uv run pytest tests/contract/test_version_negotiation.py`

### 2.0 Async Protocol Resolution

- [x] 2.1 Define AsyncSnapshotStore Protocol
  - **File**: `src/asap/state/snapshot.py` (modify)
  - **What**: `@runtime_checkable class AsyncSnapshotStore(Protocol)` with async methods. Keep sync `SnapshotStore` with `@deprecated`.
  - **Verify**: `uv run pytest tests/state/test_snapshot.py`

- [x] 2.2 Define AsyncMeteringStore Protocol
  - **File**: `src/asap/state/metering.py` (modify)
  - **What**: Same pattern. Async methods, sync deprecated.
  - **Verify**: `uv run pytest tests/state/test_metering.py`

- [x] 2.3 Update SQLiteSnapshotStore to implement AsyncSnapshotStore
  - **File**: `src/asap/state/stores/sqlite.py` (modify)
  - **What**: Implement both protocols. `save_async`/`get_async` become canonical `save`/`get` in async protocol.
  - **Verify**: `isinstance(store, AsyncSnapshotStore)` is True

- [x] 2.4 Factory function for async stores
  - **File**: `src/asap/state/snapshot.py` (modify)
  - **What**: `create_async_snapshot_store(backend="sqlite", *, db_path=...) -> AsyncSnapshotStore`.
  - **Verify**: Factory returns correct implementation

---

## Definition of Done

- [x] ASAP-Version header in all HTTP requests/responses
- [x] Content negotiation v2.1 ↔ v2.2 working
- [x] Manifest has `supported_versions` field
- [x] Contract tests for version negotiation passing
- [x] AsyncSnapshotStore and AsyncMeteringStore Protocols defined
- [x] Sync protocols deprecated with warnings
- [x] SQLiteSnapshotStore implements AsyncSnapshotStore (via shared backend + `SQLiteAsyncSnapshotStore`)
- [x] Test coverage >= 90% for new code (full `pytest tests/ --cov=src`; regenerate signed fixtures after Manifest changes)
