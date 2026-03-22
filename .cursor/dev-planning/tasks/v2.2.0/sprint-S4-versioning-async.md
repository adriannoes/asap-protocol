# Sprint S4: Versioning & Async Protocol

**PRD**: §4.8 Unified Versioning (P1), §4.9 Async Protocol Resolution (P1)
**Branch**: `feat/versioning-async`
**PR Scope**: ASAP-Version header, content negotiation, AsyncSnapshotStore/MeteringStore protocols
**Depends on**: Sprint S3 (Errors & Streaming)

## Relevant Files

### New Files
- `tests/contract/test_version_negotiation.py` — Contract tests for version compat

### Modified Files
- `src/asap/transport/server.py` — ASAP-Version middleware
- `src/asap/transport/http_client.py` — ASAP-Version header on requests
- `src/asap/models/entities.py` — `supported_versions` in Manifest
- `src/asap/state/snapshot.py` — AsyncSnapshotStore Protocol
- `src/asap/state/metering.py` — AsyncMeteringStore Protocol
- `src/asap/state/stores/sqlite.py` — Implement AsyncSnapshotStore

---

## Tasks

### 1.0 Unified Versioning

- [ ] 1.1 Add ASAP-Version header middleware to server
  - **File**: `src/asap/transport/server.py` (modify)
  - **What**: Middleware reads `ASAP-Version` header. Default to current version if absent. Return JSON-RPC error -32000 if incompatible. Set `ASAP-Version` on all responses.
  - **Verify**: Tests for no header (default), compatible header, incompatible header

- [ ] 1.2 Add ASAP-Version header to client
  - **File**: `src/asap/transport/http_client.py` (modify)
  - **What**: `ASAPClient` sends `ASAP-Version` with supported versions. Parse response header.
  - **Verify**: `uv run pytest tests/transport/test_http_client.py -k "version"`

- [ ] 1.3 Add `supported_versions` to Manifest
  - **File**: `src/asap/models/entities.py` (modify)
  - **What**: `supported_versions: list[str] = ["2.2"]` field. Update well-known endpoint.
  - **Verify**: `uv run pytest tests/models/test_entities.py tests/discovery/test_wellknown.py`

- [ ] 1.4 Version negotiation contract tests
  - **File**: `tests/contract/test_version_negotiation.py` (create)
  - **What**: v2.1 client → v2.2 server, v2.2 client → v2.1 server, incompatible version.
  - **Verify**: `uv run pytest tests/contract/test_version_negotiation.py`

### 2.0 Async Protocol Resolution

- [ ] 2.1 Define AsyncSnapshotStore Protocol
  - **File**: `src/asap/state/snapshot.py` (modify)
  - **What**: `@runtime_checkable class AsyncSnapshotStore(Protocol)` with async methods. Keep sync `SnapshotStore` with `@deprecated`.
  - **Verify**: `uv run pytest tests/state/test_snapshot.py`

- [ ] 2.2 Define AsyncMeteringStore Protocol
  - **File**: `src/asap/state/metering.py` (modify)
  - **What**: Same pattern. Async methods, sync deprecated.
  - **Verify**: `uv run pytest tests/state/test_metering.py`

- [ ] 2.3 Update SQLiteSnapshotStore to implement AsyncSnapshotStore
  - **File**: `src/asap/state/stores/sqlite.py` (modify)
  - **What**: Implement both protocols. `save_async`/`get_async` become canonical `save`/`get` in async protocol.
  - **Verify**: `isinstance(store, AsyncSnapshotStore)` is True

- [ ] 2.4 Factory function for async stores
  - **File**: `src/asap/state/snapshot.py` (modify)
  - **What**: `create_async_snapshot_store(backend="sqlite", **kwargs) -> AsyncSnapshotStore`.
  - **Verify**: Factory returns correct implementation

---

## Definition of Done

- [ ] ASAP-Version header in all HTTP requests/responses
- [ ] Content negotiation v2.1 ↔ v2.2 working
- [ ] Manifest has `supported_versions` field
- [ ] Contract tests for version negotiation passing
- [ ] AsyncSnapshotStore and AsyncMeteringStore Protocols defined
- [ ] Sync protocols deprecated with warnings
- [ ] SQLiteSnapshotStore implements AsyncSnapshotStore
- [ ] Test coverage >= 90% for new code
