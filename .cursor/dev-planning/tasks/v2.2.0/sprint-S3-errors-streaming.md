# Sprint S3: Error Taxonomy & Streaming/SSE

**PRD**: §4.6 Streaming/SSE (P1), §4.7 Error Taxonomy Evolution (P1)
**Branch**: `feat/errors-streaming`
**PR Scope**: RecoverableError/FatalError, recovery hints, error codes, SSE endpoint, TaskStream, client streaming
**Depends on**: Sprint S2 (Approval Flows) — can start in parallel if needed, no hard dependency

## Relevant Files

### New Files
- `tests/e2e/test_streaming.py` — End-to-end streaming test
- `src/asap/examples/streaming_agent.py` — Streaming echo agent example
- `docs/error-codes.md` — Public error code registry

### Modified Files
- `src/asap/errors.py` — RecoverableError, FatalError, recovery hints, error codes
- `src/asap/models/payloads.py` — TaskStream payload type
- `src/asap/transport/server.py` — `POST /asap/stream` SSE endpoint, streaming handler registration
- `src/asap/transport/http_client.py` — `ASAPClient.stream()`, auto-retry with recovery hints
- `src/asap/transport/jsonrpc.py` — Error code mapping in JSON-RPC responses
- `src/asap/transport/websocket.py` — WebSocket streaming support

---

## Tasks

### 1.0 Error Taxonomy Evolution

- [ ] 1.1 Add RecoverableError and FatalError base classes
  - **File**: `src/asap/errors.py` (modify)
  - **What**: Create `RecoverableError(ASAPError)` and `FatalError(ASAPError)`. Classify all existing errors. Add `retry_after_ms: int | None`, `alternative_agents: list[str] | None`, `fallback_action: str | None` to `ASAPError`.
  - **Verify**: `isinstance(ASAPConnectionError(...), RecoverableError)` is True

- [ ] 1.2 Define ASAP error code registry
  - **File**: `src/asap/errors.py` (modify), `docs/error-codes.md` (create)
  - **What**: Numeric codes in JSON-RPC range (-32000 to -32059) per PRD §4.7.
  - **Verify**: All error classes have `code` attribute in defined range

- [ ] 1.3 Update JSON-RPC error serialization
  - **File**: `src/asap/transport/jsonrpc.py` (modify), `src/asap/transport/server.py` (modify)
  - **What**: Server includes error codes and recovery hints in JSON-RPC error `data` field. Client reconstructs RecoverableError/FatalError from responses.
  - **Verify**: `uv run pytest tests/transport/test_jsonrpc.py tests/transport/test_server.py`

- [ ] 1.4 Update ASAPClient auto-retry with recovery hints
  - **File**: `src/asap/transport/http_client.py` (modify)
  - **What**: On `RecoverableError` with `retry_after_ms`, auto-wait and retry.
  - **Verify**: `uv run pytest tests/transport/test_http_client.py -k "retry"`

### 2.0 Streaming/SSE

- [ ] 2.1 Define TaskStream payload model
  - **File**: `src/asap/models/payloads.py` (modify)
  - **What**: `TaskStream` — `chunk: str`, `progress: float | None`, `final: bool`, `status: TaskStatus | None`. Register in `PayloadType` enum.
  - **Verify**: `Envelope[TaskStream]` serialization works

- [ ] 2.2 Implement SSE endpoint on server
  - **File**: `src/asap/transport/server.py` (modify)
  - **What**: `POST /asap/stream` — accepts JSON-RPC `TaskRequest`, returns `StreamingResponse` with `text/event-stream`. Each chunk is `Envelope[TaskStream]` as SSE `data:` line.
  - **Verify**: `uv run pytest tests/transport/test_streaming.py`

- [ ] 2.3 Add streaming handler registration
  - **File**: `src/asap/transport/server.py` (modify)
  - **What**: `HandlerRegistry.register_streaming_handler(method, handler: AsyncGenerator)`.
  - **Verify**: Handler registry dispatches streaming handlers

- [ ] 2.4 Implement `ASAPClient.stream()`
  - **File**: `src/asap/transport/http_client.py` (modify)
  - **What**: `async def stream(request) -> AsyncIterator[Envelope[TaskStream]]`. Uses `httpx.stream("POST", "/asap/stream")` with `Accept: text/event-stream`.
  - **Verify**: `uv run pytest tests/transport/test_http_client.py -k "stream"`

- [ ] 2.5 WebSocket streaming support
  - **File**: `src/asap/transport/websocket.py` (modify)
  - **What**: Multiple `Envelope[TaskStream]` messages with same `correlation_id`. JSON messages, not SSE format.
  - **Verify**: `uv run pytest tests/transport/test_websocket.py -k "stream"`

- [ ] 2.6 Streaming e2e test
  - **File**: `tests/e2e/test_streaming.py` (create)
  - **What**: Full pipeline: server with streaming handler → client calls stream() → receives chunks → final chunk has status.
  - **Verify**: `uv run pytest tests/e2e/test_streaming.py`

- [ ] 2.7 Streaming echo agent example
  - **File**: `src/asap/examples/streaming_agent.py` (create)
  - **What**: Example agent streaming response word-by-word with progress tracking.
  - **Verify**: `uv run python -m asap.examples.streaming_agent`

---

## Definition of Done

- [ ] RecoverableError/FatalError classification for all existing errors
- [ ] Recovery hints (retry_after_ms, alternative_agents) in error data
- [ ] Error code registry document published
- [ ] SSE endpoint functional with e2e test
- [ ] ASAPClient.stream() consuming SSE events
- [ ] WebSocket streaming with same payload type
- [ ] Streaming example agent working
- [ ] Test coverage >= 90% for new code
