# Tasks: v2.2.0 Protocol Hardening

**Status: PLANNING** — Pending ADR approvals (ADR-018 Streaming, ADR-019 Versioning)

Based on the [Strategic Review v2.2](../../product-specs/strategy/roadmap-to-marketplace.md) and [PRD v2.2 Protocol Hardening](../../product-specs/prd/prd-v2.2-protocol-hardening.md), these tasks implement protocol-level improvements to close competitive gaps and resolve open technical debt.

## Prerequisites
- [x] v2.1.1 Tech Debt & Security Cleared
- [x] A2H Integration ~90% complete
- [ ] ADR-018 (Streaming Transport) accepted
- [ ] ADR-019 (Unified Versioning) accepted

## Sprint Organization

| Sprint | Focus | Estimated Effort | Priority |
|--------|-------|-----------------|----------|
| S1 | A2H Completion + Error Taxonomy Evolution | 3-4 days | P1 |
| S2 | Streaming/SSE | 5-7 days | P1 |
| S3 | Unified Versioning + Async Protocol | 4-5 days | P1 |
| S4 | Batch Operations + Audit Logging | 4-5 days | P2 |
| S5 | Compliance Harness v2 + Release | 3-4 days | P2 |

---

## Tasks

### Sprint S1: A2H Completion + Error Taxonomy Evolution

- [ ] 1.0 A2H Integration Completion
  **Trigger / entry point:** Pending commits from tasks-a2h-integration.md.
  **Enables:** Complete HITL (Human-in-the-Loop) support for ASAP agents.
  **Depends on:** Existing A2H models, client, and provider (90% done).

  - [ ] 1.1 Complete pending A2H commits (1.4, 2.5, 3.7, 4.4, 5.7) - check before making/redoing commits
    - **Files**: See `tasks-a2h-integration.md` for specific files
    - **What**: Finalize all pending commits from the A2H integration task list.
    - **Why**: A2H is 90% complete; finishing it is low-effort, high-value.
    - **Verify**: `uv run pytest tests/integrations/test_a2h*.py tests/handlers/` passes. All A2H exports accessible from `asap.handlers` and `asap.integrations.a2h`.

  - [ ] 1.2 A2H documentation and example
    - **Files**: `src/asap/examples/a2h_approval.py`, `docs/guides/`
    - **What**: Ensure the `a2h_approval` example is functional and documented.
    - **Why**: Users need a working reference for HITL integration.
    - **Verify**: Example runs successfully. Documentation covers setup, usage, and integration patterns.

- [ ] 2.0 Error Taxonomy Evolution
  **Trigger / entry point:** Any error response from an ASAP agent or client.
  **Enables:** Structured error recovery, auto-retry, and self-healing orchestration loops.
  **Depends on:** Existing ADR-012 error hierarchy in `src/asap/errors.py`.

  - [ ] 2.1 Add RecoverableError and FatalError base classes
    - **File**: `src/asap/errors.py` (modify existing)
    - **What**: Create `RecoverableError(ASAPError)` and `FatalError(ASAPError)` subclasses. Classify all existing errors: `ASAPConnectionError` -> Recoverable, `InvalidTransitionError` -> Fatal, `CircuitOpenError` -> Recoverable, `ASAPTimeoutError` -> Recoverable, `ASAPRemoteError` -> depends on code.
    - **Why**: Clients need machine-readable classification for retry decisions (ADR-012 evolution).
    - **Pattern**: Each subclass inherits from ASAPError + RecoverableError or FatalError.
    - **Verify**: `uv run pytest tests/test_errors.py` passes. `isinstance(ASAPConnectionError(...), RecoverableError)` is True.

  - [ ] 2.2 Add recovery hints to error data
    - **File**: `src/asap/errors.py` (modify existing)
    - **What**: Add optional fields to `ASAPError`: `retry_after_ms: int | None`, `alternative_agents: list[str] | None`, `fallback_action: str | None`. Include these in JSON-RPC error `data` field.
    - **Why**: Enables auto-recovery in orchestration loops without manual intervention.
    - **Verify**: Error serialization includes recovery hints when provided. Test round-trip: create error with hints -> serialize to JSON-RPC -> deserialize -> hints preserved.

  - [ ] 2.3 Define ASAP error code registry
    - **File**: `src/asap/errors.py` (modify), `docs/error-codes.md` (create)
    - **What**: Define numeric error codes in JSON-RPC range (-32000 to -32099) mapped to ASAP categories. Create public documentation of all codes.
    - **Why**: Machine-readable codes enable automated error handling across different SDK implementations.
    - **Pattern**: -32000 to -32009 (protocol), -32010 to -32019 (routing), -32020 to -32029 (capability), -32030 to -32039 (execution), -32040 to -32049 (resource), -32050 to -32059 (security).
    - **Verify**: All error classes have a `code` attribute in the defined range. `docs/error-codes.md` exists and is complete.

  - [ ] 2.4 Update ASAPClient auto-retry with recovery hints
    - **File**: `src/asap/transport/http_client.py` (modify existing)
    - **What**: When `ASAPClient` receives a `RecoverableError` with `retry_after_ms`, automatically wait and retry. When `alternative_agents` is provided, log the suggestion.
    - **Why**: Client-side self-healing reduces manual error handling.
    - **Verify**: `uv run pytest tests/transport/test_http_client.py -k "retry"` includes test for recovery hint-driven retry.

  - [ ] 2.5 Update JSON-RPC error handling in transport
    - **File**: `src/asap/transport/jsonrpc.py` (modify existing), `src/asap/transport/server.py` (modify existing)
    - **What**: Server-side error responses include the new error codes and recovery hints. Client-side parsing reconstructs `RecoverableError`/`FatalError` from JSON-RPC error responses.
    - **Why**: End-to-end error semantics require both server and client to understand the new taxonomy.
    - **Verify**: `uv run pytest tests/transport/test_jsonrpc.py tests/transport/test_server.py` passes.

---

### Sprint S2: Streaming/SSE

- [ ] 3.0 Streaming Transport
  **Trigger / entry point:** Client sends `POST /asap/stream` with `Accept: text/event-stream`.
  **Enables:** Incremental task responses for AI agents (LLM token streaming, progress updates).
  **Depends on:** ADR-018 (Streaming Transport) accepted. Existing FastAPI server and httpx client.

  - [ ] 3.1 Define TaskStream payload model
    - **File**: `src/asap/models/payloads.py` (modify existing)
    - **What**: Add `TaskStream` payload type with fields: `chunk: str`, `progress: float | None`, `final: bool`, `status: TaskStatus | None` (only on final=True). Register in `PayloadType` enum and `PAYLOAD_TYPE_MAP`.
    - **Why**: Protocol needs a dedicated payload for streaming chunks.
    - **Verify**: `uv run pytest tests/models/test_payloads.py` includes TaskStream validation tests. Envelope[TaskStream] serialization works.

  - [ ] 3.2 Implement SSE endpoint on server
    - **File**: `src/asap/transport/server.py` (modify existing)
    - **What**: Add `POST /asap/stream` endpoint that accepts a JSON-RPC `TaskRequest`, invokes the handler, and returns a `StreamingResponse` with `media_type="text/event-stream"`. Each yielded chunk is an `Envelope[TaskStream]` serialized as an SSE `data:` line. The handler must be an async generator.
    - **Why**: This is the core streaming capability (PRD STR-001).
    - **Pattern**: Use `starlette.responses.StreamingResponse` with async generator.
    - **Verify**: `uv run pytest tests/transport/test_streaming.py` with a mock streaming handler. Response is valid SSE format.

  - [ ] 3.3 Add streaming handler registration
    - **File**: `src/asap/transport/server.py` (modify existing)
    - **What**: Extend `HandlerRegistry` to support registering async generator handlers for streaming. `register_streaming_handler(method: str, handler: AsyncGenerator)`.
    - **Why**: Handlers need to yield chunks instead of returning a single response.
    - **Verify**: Handler registry accepts and dispatches streaming handlers correctly.

  - [ ] 3.4 Implement ASAPClient.stream()
    - **File**: `src/asap/transport/http_client.py` (modify existing)
    - **What**: Add `async def stream(self, request: Envelope) -> AsyncIterator[Envelope[TaskStream]]` method. Uses `httpx.stream("POST", "/asap/stream")` with `Accept: text/event-stream` header. Parses SSE events and yields deserialized envelopes.
    - **Why**: Client-side streaming consumption (PRD STR-003).
    - **Verify**: `uv run pytest tests/transport/test_http_client.py -k "stream"` with mock SSE server.

  - [ ] 3.5 WebSocket streaming support
    - **File**: `src/asap/transport/websocket.py` (modify existing)
    - **What**: Support streaming via WebSocket by sending multiple `Envelope[TaskStream]` messages with the same `correlation_id`. WebSocket streaming does not use SSE format — it sends JSON messages.
    - **Why**: WebSocket is the bidirectional alternative (STR-006). Same payload type, different transport.
    - **Verify**: `uv run pytest tests/transport/test_websocket.py -k "stream"` passes.

  - [ ] 3.6 Streaming e2e test
    - **File**: `tests/e2e/test_streaming.py` (create)
    - **What**: Full end-to-end test: start server with streaming handler -> client calls stream() -> receives incremental chunks -> final chunk has status.
    - **Why**: Validates the entire streaming pipeline works together.
    - **Verify**: `uv run pytest tests/e2e/test_streaming.py` passes.

  - [ ] 3.7 Integration example: streaming echo agent
    - **File**: `src/asap/examples/streaming_agent.py` (create)
    - **What**: Example agent that streams a response word-by-word with progress tracking.
    - **Why**: Developer reference for implementing streaming agents.
    - **Verify**: Example runs successfully with `uv run python -m asap.examples.streaming_agent`.

---

### Sprint S3: Unified Versioning + Async Protocol

- [ ] 4.0 Unified Versioning
  **Trigger / entry point:** Any HTTP request/response between ASAP agents.
  **Enables:** Backward-compatible protocol evolution and multi-version agent ecosystems.
  **Depends on:** ADR-019 (Unified Versioning) accepted.

  - [ ] 4.1 Add ASAP-Version header to server
    - **File**: `src/asap/transport/server.py` (modify existing)
    - **What**: Add middleware that reads `ASAP-Version` header from requests and sets it on responses. Default to current version if no header present. Return JSON-RPC error -32000 if incompatible version requested.
    - **Why**: Content negotiation per ADR-019.
    - **Verify**: `uv run pytest tests/transport/test_server.py -k "version"` with tests for: no header (default), compatible header, incompatible header.

  - [ ] 4.2 Add ASAP-Version header to client
    - **File**: `src/asap/transport/http_client.py` (modify existing)
    - **What**: `ASAPClient` sends `ASAP-Version` header with supported versions on all requests. Parse response header to confirm negotiated version.
    - **Why**: Client-side version negotiation.
    - **Verify**: `uv run pytest tests/transport/test_http_client.py -k "version"`.

  - [ ] 4.3 Add supported_versions to Manifest
    - **File**: `src/asap/models/entities.py` (modify existing)
    - **What**: Add `supported_versions: list[str] = ["2.2"]` field to the `Manifest` model. Update well-known endpoint to serve this.
    - **Why**: Agents advertise which protocol versions they support (VER-004).
    - **Verify**: `uv run pytest tests/models/test_entities.py tests/discovery/test_wellknown.py`.

  - [ ] 4.4 Version negotiation contract tests
    - **File**: `tests/contract/test_version_negotiation.py` (create)
    - **What**: Contract tests covering: v2.1 client -> v2.2 server (backward compat), v2.2 client -> v2.1 server (graceful degradation), incompatible version (error).
    - **Why**: ADR-016 requires contract tests for compatibility.
    - **Verify**: `uv run pytest tests/contract/test_version_negotiation.py` passes.

- [ ] 5.0 Async Protocol Resolution
  **Trigger / entry point:** Any storage operation in an async context.
  **Enables:** Non-blocking persistence without ThreadPoolExecutor bridging.
  **Depends on:** Existing SnapshotStore, MeteringStore, SLAStorage Protocols. tech-stack-decisions.md §5.3.

  - [ ] 5.1 Define AsyncSnapshotStore Protocol
    - **File**: `src/asap/state/snapshot.py` (modify existing)
    - **What**: Add `@runtime_checkable class AsyncSnapshotStore(Protocol)` with `async def save(...)`, `async def get(...)`, `async def list_versions(...)`, `async def delete(...)`. Keep existing sync `SnapshotStore` with `@deprecated` decorator.
    - **Why**: Resolves the CP-1 open decision (Dual Protocol approach).
    - **Verify**: `uv run pytest tests/state/test_snapshot.py`.

  - [ ] 5.2 Define AsyncMeteringStore Protocol
    - **File**: `src/asap/state/metering.py` (modify existing)
    - **What**: Add `@runtime_checkable class AsyncMeteringStore(Protocol)` with async methods. Deprecate sync version.
    - **Why**: Consistency with AsyncSnapshotStore.
    - **Verify**: `uv run pytest tests/state/test_metering.py`.

  - [ ] 5.3 Update SQLiteSnapshotStore to implement AsyncSnapshotStore
    - **File**: `src/asap/state/stores/sqlite.py` (modify existing)
    - **What**: Ensure `SQLiteSnapshotStore` implements both `SnapshotStore` (sync, deprecated) and `AsyncSnapshotStore` (async, primary). The `save_async`/`get_async` methods from v2.1.1 become the canonical `save`/`get` in the async protocol.
    - **Why**: Reference implementation must demonstrate the new protocol.
    - **Verify**: `isinstance(store, AsyncSnapshotStore)` is True. All async tests pass.

  - [ ] 5.4 Factory function for async stores
    - **File**: `src/asap/state/snapshot.py` (modify existing)
    - **What**: Add `create_async_snapshot_store(backend: str = "sqlite", **kwargs) -> AsyncSnapshotStore` factory.
    - **Why**: Consistent creation pattern (mirrors existing `create_snapshot_store`).
    - **Verify**: Factory returns correct implementation for "memory" and "sqlite" backends.

---

### Sprint S4: Batch Operations + Audit Logging

- [ ] 6.0 Batch Operations
  **Trigger / entry point:** Client sends JSON array to `POST /asap`.
  **Enables:** Reduced network overhead for orchestration loops sending multiple tasks.
  **Depends on:** ADR-003 (JSON-RPC 2.0 batch is native to the spec).

  - [ ] 6.1 Server-side batch request handling
    - **File**: `src/asap/transport/server.py` (modify existing), `src/asap/transport/jsonrpc.py` (modify existing)
    - **What**: Detect when request body is a JSON array (vs object). Process each request individually, collecting responses. Return JSON array of responses. Apply rate limiting as N individual requests.
    - **Why**: JSON-RPC 2.0 spec defines batch as array of Request objects (BATCH-001).
    - **Verify**: `uv run pytest tests/transport/test_server.py -k "batch"` with tests for: valid batch, mixed success/error, empty batch (error), oversized batch (error).

  - [ ] 6.2 Batch size limit configuration
    - **File**: `src/asap/transport/server.py` (modify existing)
    - **What**: Add `max_batch_size: int = 50` configuration. Return JSON-RPC error if batch exceeds limit.
    - **Why**: Prevents resource exhaustion from very large batches (BATCH-005).
    - **Verify**: Test with batch of 51 requests returns appropriate error.

  - [ ] 6.3 Client-side batch method
    - **File**: `src/asap/transport/http_client.py` (modify existing)
    - **What**: Add `async def batch(self, requests: list[Envelope]) -> list[Envelope]` method. Serializes as JSON array, sends single POST, deserializes response array.
    - **Why**: SDK convenience for batch operations (BATCH-004).
    - **Verify**: `uv run pytest tests/transport/test_http_client.py -k "batch"`.

- [ ] 7.0 Audit Logging
  **Trigger / entry point:** Any write operation in the ASAP protocol (task creation, state transition, delegation).
  **Enables:** Tamper-evident compliance trail for enterprise customers.
  **Depends on:** Existing SnapshotStore pattern for storage interfaces.

  - [ ] 7.1 Define AuditStore Protocol and models
    - **File**: `src/asap/economics/audit.py` (create)
    - **What**: Define `AuditEntry` model (id, timestamp, operation, agent_urn, details, prev_hash, hash), `AuditStore` Protocol with `append(entry)`, `query(urn, start, end)`, hash chain validation.
    - **Why**: Tamper-evident logging requires hash chain (AUD-001).
    - **Verify**: `uv run pytest tests/economics/test_audit.py`.

  - [ ] 7.2 In-memory and SQLite AuditStore implementations
    - **File**: `src/asap/economics/audit.py` (extend)
    - **What**: `InMemoryAuditStore` and `SQLiteAuditStore` implementing the AuditStore Protocol. Hash chain: each entry hashes (prev_hash + timestamp + operation + details).
    - **Why**: Reference implementations following the SnapshotStore pattern.
    - **Verify**: Hash chain integrity test: tamper with an entry -> validation fails.

  - [ ] 7.3 Audit logging hooks in transport
    - **File**: `src/asap/transport/server.py` (modify existing)
    - **What**: Add optional `audit_store` parameter to server. Log all write operations (task creation, state changes) to audit store via middleware.
    - **Why**: Protocol-level audit trail (AUD-002).
    - **Verify**: Server with audit_store logs task creation, state transitions.

  - [ ] 7.4 Audit query API
    - **File**: `src/asap/transport/server.py` (modify existing)
    - **What**: Add `GET /audit` endpoint with query params: `urn`, `start`, `end`. Returns paginated audit entries.
    - **Why**: Queryable audit trail for compliance (AUD-004).
    - **Verify**: `uv run pytest tests/transport/test_server.py -k "audit"`.

---

### Sprint S5: Compliance Harness v2 + Release

- [ ] 8.0 Compliance Harness v2
  **Trigger / entry point:** Agent developer runs `asap compliance-check`.
  **Enables:** Comprehensive protocol certification covering v2.2 features.
  **Depends on:** All S1-S4 features implemented.

  - [ ] 8.1 Streaming compliance checks
    - **File**: `src/asap/testing/compliance.py` (modify/create)
    - **What**: Add compliance checks: SSE endpoint responds correctly, event format valid, stream terminates with final event.
    - **Verify**: Checks pass against streaming test agent.

  - [ ] 8.2 Error handling compliance checks
    - **File**: `src/asap/testing/compliance.py` (modify/create)
    - **What**: Add checks: errors include RecoverableError/FatalError classification, recovery hints present, error codes in defined range.
    - **Verify**: Checks pass against test agent with proper error taxonomy.

  - [ ] 8.3 Version negotiation compliance checks
    - **File**: `src/asap/testing/compliance.py` (modify/create)
    - **What**: Add checks: ASAP-Version header present in responses, version negotiation works, backward compat maintained.
    - **Verify**: Checks pass against test agent with versioning support.

  - [ ] 8.4 Batch compliance checks
    - **File**: `src/asap/testing/compliance.py` (modify/create)
    - **What**: Add checks: batch request accepted, array response returned, size limit enforced.
    - **Verify**: Checks pass against test agent with batch support.

  - [ ] 8.5 Compliance report export
    - **File**: `src/asap/testing/compliance.py` (modify/create)
    - **What**: Generate JSON compliance report with score, check results, and summary.
    - **Verify**: Report JSON is valid and parseable.

- [ ] 9.0 Release v2.2.0
  **Trigger / entry point:** All S1-S5 tasks complete and CI passing.
  **Enables:** v2.2.0 available on PyPI.
  **Depends on:** All previous tasks.

  - [ ] 9.1 Update version and changelog
    - **Files**: `pyproject.toml`, `CHANGELOG.md`, `src/asap/__init__.py`
    - **What**: Bump version to 2.2.0. Document all changes in CHANGELOG.
    - **Verify**: `uv run python -c "import asap; print(asap.__version__)"` shows 2.2.0.

  - [ ] 9.2 Full CI verification
    - **What**: Run complete CI suite: `uv run ruff check . && uv run ruff format --check . && uv run mypy src/ scripts/ tests/ && PYTHONPATH=src uv run pytest --cov=src --cov-report=xml && uv run pip-audit`
    - **Verify**: All checks pass with zero errors.

  - [ ] 9.3 Update AGENTS.md and documentation
    - **Files**: `AGENTS.md`, `docs/`
    - **What**: Update project context with v2.2 features. Update migration guide for v2.1 -> v2.2.
    - **Verify**: AGENTS.md reflects current state.

  - [ ] 9.4 Tag and publish
    - **What**: `git tag v2.2.0 && git push --tags`. Publish to PyPI via CI.
    - **Verify**: Package available on PyPI.

---

## Definition of Done

- [ ] All P1 features (Streaming, Error Taxonomy, Versioning, Async Protocol, A2H) implemented and tested
- [ ] All P2 features (Batch, Compliance Harness v2, Audit Logging) implemented and tested
- [ ] Test coverage >= 90% for new code
- [ ] `uv run mypy src/` passes with zero errors
- [ ] `uv run ruff check .` passes
- [ ] Contract tests for version negotiation passing
- [ ] E2E streaming test passing
- [ ] CHANGELOG.md updated
- [ ] v2.2.0 published to PyPI
