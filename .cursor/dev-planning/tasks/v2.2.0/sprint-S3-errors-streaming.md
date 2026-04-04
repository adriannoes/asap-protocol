# Sprint S3: Error Taxonomy & Streaming/SSE

**PRD**: §4.6 Streaming/SSE (P1), §4.7 Error Taxonomy Evolution (P1)
**Branch**: `feat/errors-streaming`
**PR Scope**: RecoverableError/FatalError, recovery hints, error codes, SSE endpoint, TaskStream, client streaming
**Depends on**: Sprint S2 (Approval Flows) — can start in parallel if needed, no hard dependency

## Relevant Files

### New Files
- `tests/e2e/test_streaming.py` — End-to-end streaming test (`ASAPClient.stream` + SSE)
- `tests/transport/test_streaming.py` — TaskStream model and `/asap/stream` tests
- `src/asap/examples/streaming_agent.py` — Streaming echo agent example (SSE)
- `docs/error-codes.md` — Public JSON-RPC ASAP error code registry (§4.7 ranges)

### Modified Files
- `src/asap/errors.py` — RecoverableError, FatalError, rpc_code band -32000..-32059, recovery hints, remote RPC errors, ASAPConnectionError/ASAPTimeoutError
- `src/asap/models/payloads.py` — TaskStream payload type
- `src/asap/transport/server.py` — ASAP JSON-RPC errors with rpc_code + data hints; 503 thread-pool body extended (Sprint 2.0 adds SSE)
- `src/asap/transport/client.py` — ASAPClient `send()` maps JSON-RPC errors to Recoverable/Fatal remote types; retry on recoverable `retry_after_ms`
- `src/asap/transport/handlers.py` — HandlerNotFoundError as FatalError + RPC_HANDLER_NOT_FOUND
- `src/asap/transport/jsonrpc.py` — (unchanged in 1.0; standard codes remain for non-ASAP errors)
- `src/asap/transport/websocket.py` — WebSocket streaming (multiple `result.envelope` with same JSON-RPC id)

---

## Tasks

### 1.0 Error Taxonomy Evolution — completed

- [x] 1.1 Add RecoverableError and FatalError base classes
  - **File**: `src/asap/errors.py` (modify)
  - **What**: Create `RecoverableError(ASAPError)` and `FatalError(ASAPError)`. Classify all existing errors. Add `retry_after_ms: int | None`, `alternative_agents: list[str] | None`, `fallback_action: str | None` to `ASAPError`.
  - **Verify**: `isinstance(ASAPConnectionError(...), RecoverableError)` is True

- [x] 1.2 Define ASAP error code registry
  - **File**: `src/asap/errors.py` (modify), `docs/error-codes.md` (create)
  - **What**: Numeric codes in JSON-RPC range (-32000 to -32059) per PRD §4.7.
  - **Verify**: All error classes have `rpc_code` in defined range (`code` remains taxonomy URI)

- [x] 1.3 Update JSON-RPC error serialization
  - **File**: `src/asap/transport/server.py` (modify), `src/asap/transport/handlers.py` (modify)
  - **What**: Server includes `rpc_code` top-level and recovery hints in JSON-RPC error `data`. Client reconstructs remote errors via `remote_rpc_error_from_json`.
  - **Verify**: `uv run pytest tests/transport/test_jsonrpc.py tests/transport/test_server.py`

- [x] 1.4 Update ASAPClient auto-retry with recovery hints
  - **File**: `src/asap/transport/client.py` (modify; path updated from legacy `http_client.py`)
  - **What**: On JSON-RPC `RecoverableError` with `retry_after_ms` in `error.data`, auto-wait and retry.
  - **Verify**: `uv run pytest tests/transport/test_client.py -k "recoverable_json_rpc"`

### 2.0 Streaming/SSE — completed

- [x] 2.1 Define TaskStream payload model
  - **File**: `src/asap/models/payloads.py` (modify)
  - **What**: `TaskStream` — `chunk: str`, `progress: float | None`, `final: bool`, `status: TaskStatus | None`. Register in `PayloadType` enum.
  - **Verify**: `Envelope[TaskStream]` serialization works

- [x] 2.2 Implement SSE endpoint on server
  - **File**: `src/asap/transport/server.py` (modify)
  - **What**: `POST /asap/stream` — accepts JSON-RPC `TaskRequest`, returns `StreamingResponse` with `text/event-stream`. Each chunk is `Envelope[TaskStream]` as SSE `data:` line.
  - **Verify**: `uv run pytest tests/transport/test_streaming.py`

- [x] 2.3 Add streaming handler registration
  - **File**: `src/asap/transport/handlers.py` (modify)
  - **What**: `HandlerRegistry.register_streaming_handler(payload_type, handler: async generator)`.
  - **Verify**: Handler registry dispatches streaming handlers

- [x] 2.4 Implement `ASAPClient.stream()`
  - **File**: `src/asap/transport/client.py` (modify; path is `client.py`, not legacy `http_client.py`)
  - **What**: `async def stream(request) -> AsyncIterator[Envelope[TaskStream]]`. Uses `httpx.stream("POST", "/asap/stream")` with `Accept: text/event-stream`.
  - **Verify**: `uv run pytest tests/transport/test_client.py::TestASAPClientStreaming`

- [x] 2.5 WebSocket streaming support
  - **File**: `src/asap/transport/websocket.py` (modify)
  - **What**: Multiple `Envelope[TaskStream]` messages with same `correlation_id`. JSON messages, not SSE format.
  - **Verify**: `uv run pytest tests/transport/test_websocket.py -k "streaming_yields"`

- [x] 2.6 Streaming e2e test
  - **File**: `tests/e2e/test_streaming.py` (create)
  - **What**: Full pipeline: server with streaming handler → client calls stream() → receives chunks → final chunk has status.
  - **Verify**: `uv run pytest tests/e2e/test_streaming.py`

- [x] 2.7 Streaming echo agent example
  - **File**: `src/asap/examples/streaming_agent.py` (create)
  - **What**: Example agent streaming response word-by-word with progress tracking.
  - **Verify**: `uv run python -m asap.examples.streaming_agent`

---

## Definition of Done

- [x] RecoverableError/FatalError classification for all existing errors (`asap.errors`: taxonomias concretas sob `RecoverableError` ou `FatalError`)
- [x] Recovery hints (`retry_after_ms`, `alternative_agents`, `fallback_action`) serializados em `error.data` (via `to_dict` / `jsonrpc_error_data_for_asap_exception`)
- [x] Error code registry document published (`docs/error-codes.md`)
- [x] SSE endpoint functional with e2e test
- [x] ASAPClient.stream() consuming SSE events
- [x] WebSocket streaming with same payload type
- [x] Streaming example agent working
- [x] Tests for new sprint paths (errors + streaming + client + WS); **≥90% em linhas novas** — conferir relatório/diff-coverage no CI
