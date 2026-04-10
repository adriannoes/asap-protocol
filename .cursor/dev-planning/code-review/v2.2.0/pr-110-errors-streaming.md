# Code Review: PR #110

**Branch:** `feat/errors-streaming`
**Sprint:** S3 — Error Taxonomy & Streaming/SSE
**Reviewer:** AI Staff Engineer
**Date:** 2026-04-04
**Commits:** 8 (1172dfa → ad558d0)
**Files changed:** 23 (+1748 / −384)

---

## 1. Executive Summary

| Category | Status | Summary |
| :--- | :--- | :--- |
| **Tech Stack** | ✅ | No new dependencies; uses existing FastAPI/httpx/Pydantic v2. `aiohttp`/`fastmcp` bumps are security-driven. |
| **Architecture** | ✅ | Follows Envelope pattern, JSON-RPC 2.0 transport, handler registry. SSE additive, WebSocket coexists. |
| **Security** | ⚠️ | `time.sleep` in sync background thread is acceptable. SSE `sse_events()` generator swallows unhandled handler exceptions silently — see RF-1. |
| **Tests** | ⚠️ | Good coverage for happy paths. Missing edge-case tests for SSE error mid-stream and `stream()` client disconnect. See RF-3. |

> **General Feedback:** This is a solid, well-structured sprint delivery. The error taxonomy (`RecoverableError`/`FatalError`, `rpc_code`, recovery hints) is clean and consistent. The streaming implementation (SSE + WebSocket + `ASAPClient.stream()`) is additive and follows existing patterns. Two issues require attention before merge: (1) unhandled exceptions inside the SSE async generator silently abort the stream without notifying the client, and (2) code duplication between `handle_message` and `_prepare_streaming_request` should be extracted. A minor type-safety issue in `streaming_agent.py` rounds out the findings.

---

## 2. Required Fixes (Must Address Before Merge)

### RF-1: SSE Generator Swallows Handler Exceptions Silently

*   **Location:** `src/asap/transport/server.py:1306-1339` (the `sse_events()` inner function)
*   **Problem:** If the streaming handler (`dispatch_stream_async`) raises an exception *after* the first chunk has been yielded, the generator terminates silently. The client receives a truncated SSE stream with no error event, no final `TaskStream(final=True, status="failed")`, and no way to distinguish "stream completed successfully" from "stream died mid-flight".
*   **Rationale (Expert View):** SSE is a unidirectional protocol — once headers are sent with `200 OK`, HTTP status codes cannot convey errors. The industry standard (used by OpenAI, Anthropic, etc.) is to emit a final error event before closing the stream. Without this, SDK consumers cannot implement robust retry/recovery loops, directly contradicting PRD §4.7 (error recoverability) and user story "SDK Consumer (Error Recovery)".
*   **Fix Suggestion:**

    ```python
    async def sse_events() -> AsyncIterator[bytes]:
        try:
            async for response_envelope in self.registry_holder.registry.dispatch_stream_async(
                envelope, self.manifest
            ):
                injected = inject_envelope_trace_context(response_envelope)
                line = f"data: {json.dumps(injected.model_dump(mode='json'))}\n\n"
                yield line.encode("utf-8")
            # ... success metrics (existing code) ...
        except Exception as exc:
            logger.exception(
                "asap.request.stream_error",
                envelope_id=envelope.id,
                error=str(exc),
                error_type=type(exc).__name__,
            )
            error_event = {
                "error": True,
                "code": getattr(exc, "rpc_code", -32603),
                "message": str(exc),
            }
            yield f"event: error\ndata: {json.dumps(error_event)}\n\n".encode("utf-8")
        finally:
            if trace_token is not None:
                context.detach(trace_token)
    ```

    And correspondingly, `ASAPClient.stream()` should handle `event: error` lines.

---

### RF-2: `_prepare_streaming_request` Duplicates Validation Logic from `handle_message`

*   **Location:** `src/asap/transport/server.py:1158-1289` vs `src/asap/transport/server.py:992-1156`
*   **Problem:** The `_prepare_streaming_request` method duplicates ~130 lines of request parsing, authentication, envelope validation, timestamp/nonce validation, and error response building that are already in `handle_message`. This violates DRY and creates a maintenance burden — any bug fix or new validation step must be applied in two places.
*   **Rationale (Expert View):** This is a "blast radius" risk. When the versioning header (`ASAP-Version`) is added in Sprint S4, or when batch operations land, each new validation must be copied. The refactoring opportunity is clear: extract a shared `_validate_and_prepare(request) -> (ctx, envelope, trace_token) | Response` method and have both `handle_message` and `handle_stream` call it.
*   **Fix Suggestion:** Refactor into a shared private method. The current `_prepare_streaming_request` is already 90% of the way there — make `handle_message` also use it (removing duplicate code from `handle_message`). The only difference is that `handle_message` proceeds to `_dispatch_to_handler` while `handle_stream` checks for streaming handler existence.

    ```python
    async def handle_message(self, request: Request) -> Response:
        start_time = time.perf_counter()
        try:
            prepared = await self._prepare_streaming_request(request, start_time)
            if isinstance(prepared, Response):
                return prepared
            ctx, envelope, trace_token = prepared
            # ... dispatch to handler (existing code) ...
        except Exception as e:
            # ... error handling (existing code) ...
    ```

    The streaming-handler existence check can be moved to `handle_stream` as a post-prepare step.

---

### RF-3: Missing Test — SSE Error Mid-Stream

*   **Location:** `tests/transport/test_streaming.py` and `tests/e2e/test_streaming.py`
*   **Problem:** All streaming tests use a well-behaved handler that yields cleanly. No test covers the scenario where the streaming handler raises an exception *after* emitting some chunks. This is the most dangerous streaming failure mode.
*   **Rationale (Expert View):** This directly exercises RF-1. Without this test, we cannot verify that the error event is emitted and the client receives actionable feedback.
*   **Fix Suggestion:**

    ```python
    async def _failing_stream_handler(envelope: Envelope, manifest: Any) -> AsyncIterator[Envelope]:
        """Yield one chunk then raise to simulate mid-stream failure."""
        yield Envelope(...)  # first chunk
        raise RuntimeError("Simulated mid-stream failure")

    @pytest.mark.anyio
    async def test_sse_error_mid_stream_sends_error_event(...):
        registry = HandlerRegistry()
        registry.register_streaming_handler("task.request", _failing_stream_handler)
        app = create_app(sample_manifest, registry, rate_limit="999999/minute")
        # ... stream and assert error event is received ...
    ```

---

## 3. Tech-Specific Bug Hunt (Deep Dive)

*   [x] **No Sync I/O in Async Path**: The `time.sleep` at `server.py:232` is inside a dedicated `daemon=True` background thread (`_run_handler_watcher`), not in an async coroutine — this is correct.
*   [x] **No Mutable Default Arguments**: No instances of `def func(data: list = [])` found. All list/dict defaults use `Field(default_factory=...)` or explicit `None`.
*   [x] **Pydantic v2 Only**: `TaskStream` uses `ASAPBaseModel` (Pydantic v2 `BaseModel` subclass), `model_dump()`, `model_validate()`, `ConfigDict`. No v1 patterns detected.
*   [x] **No `python-jose`**: Auth uses `Authlib` + `joserfc` as mandated. No `jose` imports in changed files.
*   [x] **No Swallowed Exceptions**: All `except Exception` blocks include `logger.exception` or `logger.warning` with full error context. The `_handle_internal_error` method logs the full traceback server-side and returns a sanitized error to the client in production.
*   [x] **No Hardcoded Secrets**: No API keys, tokens, or credential patterns (`sk-`, `ghp_`, `eyJ`) in any changed file.
*   [x] **`asyncio.create_task` References Saved**: In `websocket.py`, `_recv_task` and `_ack_check_task` are assigned to instance attributes, preventing garbage collection. The heartbeat task in `handle_websocket_connection` is also saved to `heartbeat_task` variable.
*   [ ] **`Any` Type Escape Hatch**: `streaming_agent.py:32` — `manifest: Any` bypasses type safety. Should be `manifest: Manifest`. See IMP-2.
*   [ ] **`iter_websocket_stream` Error Handling**: `server.py:1365-1414` — If `dispatch_stream_async` raises during the WebSocket streaming path, the exception propagates as a Python exception through the generator. The caller in `handle_websocket_connection` (`websocket.py:1019`) catches it with a generic `except Exception` and sends a JSON-RPC `-32603` error frame — this is acceptable but could leak internal details via `str(e)`. It already does in debug mode, but in production the error message should be generic.

---

## 4. Improvements & Refactoring (Highly Recommended)

*   [ ] **IMP-1: Extract Metrics Recording for Streaming Success**
    *   `server.py:1316-1336` and `server.py:1391-1411` contain identical metrics recording blocks (6 lines each) for SSE and WebSocket streaming success. Extract a `_record_streaming_success_metrics(ctx, payload_type, start_time)` helper.

*   [ ] **IMP-2: Type `manifest` Parameter in `streaming_agent.py`**
    *   **Location:** `src/asap/examples/streaming_agent.py:32`
    *   **Problem:** `async def streaming_echo_handler(envelope: Envelope, manifest: Any)` uses `Any` for `manifest`, bypassing `mypy` checks on `manifest.id`.
    *   **Fix:** Change to `manifest: Manifest` and add the import (already imported at line 19).

*   [ ] **IMP-3: `TaskStream` Not in `PAYLOAD_TYPE_REGISTRY` with Correct Casing**
    *   **Location:** `src/asap/models/payloads.py:349`
    *   The registry has `"taskstream": TaskStream` (lowercased). However, the streaming handlers yield envelopes with `payload_type="TaskStream"` (PascalCase). This works because `Envelope` normalizes `payload_type` to lowercase for lookup, but the inconsistency in examples (`streaming_agent.py:51`, test fixtures) using `"TaskStream"` might confuse integrators. Consider documenting the canonical casing or adding a note in `docs/error-codes.md`.

*   [ ] **IMP-4: SSE Event Type Field Missing**
    *   **Location:** `server.py:1314`
    *   The PRD §4.6 SSE format specifies `event: task_stream` before the `data:` line. Current implementation only emits `data:` lines without an `event:` field. While SSE defaults to `message` event type, adding `event: task_stream` would match the PRD specification and allow clients to filter events by type.
    *   **Fix:**
        ```python
        line = f"event: task_stream\ndata: {json.dumps(injected.model_dump(mode='json'))}\n\n"
        ```
        And update `ASAPClient.stream()` to handle the `event:` prefix line.

*   [ ] **IMP-5: `RemoteFatalRPCError` and `RemoteRecoverableRPCError` Share Identical Structure**
    *   **Location:** `src/asap/errors.py:458-567`
    *   Both classes have identical `__init__`, `__str__`, `data` property, and `from_jsonrpc` classmethod. Only the base class differs. Consider a mixin or shared base to reduce the 110 lines of duplication to ~30.

*   [ ] **IMP-6: `_pop_remote_meta` Return Type is Complex**
    *   **Location:** `src/asap/errors.py:438-455`
    *   Returns a 5-tuple. A `NamedTuple` or `dataclass` would be more readable and less error-prone at call sites.

---

## 5. Verification Steps

After applying fixes, verify with:

```bash
# 1. Full test suite (includes new streaming tests)
PYTHONPATH=src uv run pytest -n auto -v

# 2. Specific streaming tests
PYTHONPATH=src uv run pytest tests/transport/test_streaming.py tests/e2e/test_streaming.py tests/transport/test_websocket.py::TestWebSocketStreamingIntegration -v

# 3. Client retry on recoverable JSON-RPC error
PYTHONPATH=src uv run pytest tests/transport/test_client.py -k "recoverable_json_rpc" -v

# 4. Error taxonomy tests
PYTHONPATH=src uv run pytest tests/test_errors.py -v

# 5. Type checking
uv run mypy src/ scripts/ tests/

# 6. Linting & formatting
uv run ruff check . && uv run ruff format --check .

# 7. Security audit
uv sync --frozen --all-extras --dev --no-extra crewai --no-extra llamaindex && uv run pip-audit

# 8. Streaming example agent (manual smoke test)
uv run python -m asap.examples.streaming_agent
# Then in another terminal:
# curl -X POST http://127.0.0.1:8002/asap/stream -H "Content-Type: application/json" \
#   -d '{"jsonrpc":"2.0","method":"asap.send","params":{"envelope":{...}},"id":"1"}'
```

---

## 6. Architecture Compliance Matrix

| Check | Status | Notes |
| :--- | :--- | :--- |
| JSON-RPC 2.0 for A2A | ✅ | All new endpoints use JSON-RPC wrapping |
| `POST /asap/stream` path | ✅ | PRD §4.6 STR-001 |
| `Envelope[TaskStream]` model | ✅ | PRD §4.6 STR-002/STR-004 |
| `ASAPClient.stream()` async gen | ✅ | PRD §4.6 STR-003 |
| WebSocket streaming coexists | ✅ | PRD §4.6 STR-006 |
| No MessageAck for streaming | ✅ | PRD §4.6 STR-007 |
| Error codes in -32000..-32059 | ✅ | PRD §4.7 ERR-003 |
| RecoverableError / FatalError | ✅ | PRD §4.7 ERR-001/ERR-004 |
| Recovery hints in error.data | ✅ | PRD §4.7 ERR-002 |
| Client auto-retry on recoverable | ✅ | PRD §4.7 ERR-006 |
| Error code registry doc | ✅ | PRD §4.7 ERR-005 (`docs/error-codes.md`) |
| No new external deps | ✅ | PRD §6.3 |
| Ed25519 only (no RSA/ECDSA) | ✅ | No crypto changes in this PR |
| Well-known URI paths | ✅ | No discovery path changes |
| Pydantic v2 exclusively | ✅ | `ASAPBaseModel`, `model_dump()`, `model_validate()` |

---

## 7. Verdict

**Conditional Approve** — Address RF-1 (SSE error event on mid-stream failure) and RF-3 (test for it). RF-2 (DRY refactor) is strongly recommended but can be a follow-up commit. IMP-4 (SSE `event:` field per PRD) should be addressed to match the spec.
