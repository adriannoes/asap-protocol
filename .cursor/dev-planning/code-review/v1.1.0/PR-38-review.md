# Code Review: PR #38 Refactoring: State Storage & Observability

## 1. Executive Summary
* **Impact Analysis:** Medium Risk. The PR introduces persistent state storage, which is a critical feature. The implementation is robust but introduces a specific architectural pattern (sync-over-async) that carries performance implications.
* **Architecture Check:** **Partial**.
    *   **Aligned**: Defines clear interfaces (`MeteringStore`, `SnapshotStore`) and uses the Factory pattern for configuration. Follows SOLID principles (Interface Segregation).
    *   **Concern**: The `SQLiteSnapshotStore` implementation uses an asynchronous driver (`aiosqlite`) to implement a synchronous protocol (`SnapshotStore`), necessitating a heavy `_run_sync` bridge that spins up new event loops and threads. This contradicts the efficient, async-first nature of the ASAP protocol, although it maintains backward compatibility.
* **Blockers:** 1 Critical Issue (Architecture/Performance).

## 2. Critical Issues (Must Fix)
*Issues that cause bugs, security risks, or strictly violate architecture/linting rules.*

### [Architecture] Sync-over-Async Pattern in SQLite Store
* **File:** `src/asap/state/stores/sqlite.py`
* **Location:** Lines 23-34 (`_run_sync`), Lines 210-228 (Sync Wrappers)
* **Problem:** 
    The `SnapshotStore` protocol is synchronous. The implementation uses `aiosqlite` (async) and bridges it using `_run_sync`.
    This abstraction:
    1.  Checks for a running loop.
    2.  If found (e.g., when called from an `AsyncHandler` in `server.py`), it spawns a `ThreadPoolExecutor`.
    3.  Inside the thread, it calls `asyncio.run()`, which creates a *new* event loop.
    4.  It then runs the DB operation.
    
    **Impact**: 
    - **Performance**: High overhead. Creating a thread and a fresh event loop for *every* database operation (save/get) is expensive.
    - **Complexity**: Debugging issues across thread/loop boundaries is difficult.
    - **Resource Usage**: Under load, this could exhaust system resources if many handlers trigger DB ops simultaneously.

* **Recommendation:**
    Since the `SnapshotStore` protocol is synchronous, the correct technical choice is to use the standard library `sqlite3` module, which is synchronous, robust, and zero-dependency. It avoids the async-sync bridge entirely.

    If async support is desired for the future, the Protocol itself should be updated to be async (breaking change), or `aiosqlite` should only be used if we expose an `AsyncSnapshotStore` interface.

```diff
# src/asap/state/stores/sqlite.py

- import aiosqlite
+ import sqlite3
+ import json

class SQLiteSnapshotStore:
    def __init__(self, db_path: str | Path = DEFAULT_DB_PATH) -> None:
        self._db_path = Path(db_path)
    
-   async def _save_impl(self, snapshot: StateSnapshot) -> None:
-       async with aiosqlite.connect(self._db_path) as conn:
-           # ...
-
-   def save(self, snapshot: StateSnapshot) -> None:
-       _run_sync(self._save_impl(snapshot))

+   def save(self, snapshot: StateSnapshot) -> None:
+       with sqlite3.connect(self._db_path) as conn:
+           self._ensure_snapshots_table(conn)
+           row = _snapshot_to_row(snapshot)
+           conn.execute(
+               f"""
+               INSERT OR REPLACE INTO {SNAPSHOTS_TABLE}
+               (task_id, id, version, data, checkpoint, created_at)
+               VALUES (?, ?, ?, ?, ?, ?)
+               """,
+               row,
+           )
+           conn.commit()
```

## 3. Improvements & Refactoring (Strongly Recommended)

### [Testing] Missing Async Context Test
* **File:** `tests/state/test_sqlite_store.py`
* **Location:** Whole File
* **Context:** The current tests run synchronously. They do not exercise the `_run_sync` "running loop" path (Line 31 in `sqlite.py`). This path is exactly what will be hit if an `AsyncHandler` uses the store, making it a critical untested path.
* **Suggestion:**
    If you keep the `aiosqlite` implementation, verify the bridge works from an async context.

    ```python
    @pytest.mark.asyncio
    async def test_save_from_async_context(sqlite_snapshot_store, sample_snapshot):
        # This forces the _run_sync -> ThreadPoolExecutor -> asyncio.run path
        sqlite_snapshot_store.save(sample_snapshot)
        assert sqlite_snapshot_store.get(sample_snapshot.task_id) is not None
    ```

### [Security] Subprocess Call in Example
* **File:** `src/asap/examples/agent_failover.py`
* **Location:** Line 202
* **Context:** `subprocess.Popen` is used. While marked `# nosec`, ensure inputs are strictly controlled. The `port` and `db_path` come from args/env, which is generally safe for an example script, but good to double-check.
* **Suggestion:** No change code-wise, but ensure `db_path` is sanitized if this pattern moves to production code.

## 4. Nitpicks & Questions

* **[src/asap/transport/server.py] (Line 1345):**
    `logger.info("asap.server.nonce_validation_enabled", ...)`
    Logging constraint: verify if `manifest_id` is always safe to log (it should be, but check PII rules if agent names are user-generated).

* **[docs/best-practices/agent-failover-migration.md]:**
    Excellent documentation. One minor addition: Is `StateSnapshot.data` guaranteed to be JSON compliant? `SnapshotStore` assumes it, but `StateSnapshot` (Pydantic) defines it as `dict[str, Any]`.
    *Ref*: `src/asap/state/stores/sqlite.py` line 38 `json.dumps(snapshot.data)` will fail if data contains non-serializable objects (e.g. datetimes, sets).
    *Suggestion*: Add a validator or serializer to `SQLiteSnapshotStore` to handle common non-JSON types (like `datetime` -> ISO string) to prevent runtime 500 errors during save.

## 5. Verification Checklist (Passed)
*   [x] **Resilience**: Retry logic handled in client examples; Store handles DB locking (via SQLite timeout defaults).
*   [x] **Data Integrity**: Schema looks correct. JSON serialization used for flexible data.
*   [x] **Concurrency**: `InMemorySnapshotStore` uses `RLock`. `SQLite` handles it via DB engine.
*   [x] **Observability**: New `MeteringStore` lays good foundation for v1.3.

## 6. QA Audit (Structural Analysis)

### 1. Coverage Gap
*   **Critical Missing Test Path (`sqlite.py`):** The `SQLiteSnapshotStore` relies on `_run_sync` to bridge async `aiosqlite` to sync `SnapshotStore`. The current tests (`test_sqlite_store.py`) are synchronous, meaning they likely execute the "no running loop" branch of `_run_sync`.
    *   **Gap:** We are NOT testing the "running loop" branch (Thread + `asyncio.run`), which is exactly how the store will be used in production (inside `async def` FastAPI handlers).
    *   **Risk:** Potential `RuntimeError` if nested event loops are mishandled or if thread context propagation fails.
*   **Server Decompression Logic:** `src/asap/transport/server.py` added support for gzip/brotli (lines 897-948). `tests/transport/test_server.py` mocks `request.stream()` with raw bytes but does not appear to have a test case sending actual compressed data with `Content-Encoding` headers to verify the decompression implementation.

### 2. Fixture & Async Analysis
*   **Rate Limiting Isolation:** **Pass**. Structure is excellent.
    *   `tests/transport/conftest.py` defines `isolated_limiter_factory` and `replace_global_limiter`.
    *   `tests/conftest.py` applies `_isolate_rate_limiter` globally (autouse), preventing cross-test pollution.
*   **Async/Await Hygiene:**
    *   `pytest-asyncio` configuration (`loop_scope = "function"`) in `pyproject.toml` is correct for v0.24+.
    *   New state tests are synchronous, which avoids async color pollution but necessitates the `_run_sync` bridge (see Critical Issues).

### 3. Refactoring Opportunities
*   **`test_server.py` Boilerplate:** The `RequestContext`, `JsonRpcRequest`, and `Envelope` setup in `TestASAPRequestHandlerHelpers` (lines 208-600) is repetitive.
    *   *Suggestion:* Move `rpc_request` and `context` creation into `tests/transport/conftest.py` as reusable fixtures to clean up the test file.

### 4. Verification Command
To run only the relevant tests for this PR:
```bash
uv run pytest tests/state/ tests/transport/test_server.py
```

## 7. Verification Findings (Active Testing)

### Active Test Summary
| Component | Test Scenarios | Result | Notes |
| :--- | :--- | :--- | :--- |
| **SQLite Store** | `repro_sqlite_async_context.py` | **VERIFIED (With Caveats)** | The `_run_sync` bridge successfully manages the nested loop/thread creation without crashing. However, the architectural concern regarding performance remains critical (1 thread + 1 loop per DB call). |
| **Decompression** | `repro_server_decompression.py` | **VERIFIED** | Server correctly decompresses `gzip` bodies and rejects invalid compressed data with 400 Bad Request. |

### Details
1.  **SQLite Async Context Stress Test**:
    *   **Method**: Used `_run_sync` inside an `async def` loop 50 times.
    *   **Outcome**: No crashes, data persisting correctly.
    *   **Insight**: `ThreadPoolExecutor` + `asyncio.run` isolate the new loop effectively, preventing "running loop" errors. **However**, this confirms the "heavy" nature of the operation.

2.  **Server Decompression Verification**:
    *   **Method**: Sent real `gzip` compressed payloads via `TestClient`.
    *   **Outcome**: Server transparently decompressed and processed the JSON.
    *   **Gap Confirmed**: Existing tests mocked the stream but didn't actually test the decompression library integration. A new test file `tests/transport/test_compression.py` should be added with these cases.

---
**Final Recommendation**:
1.  **Merge Blocking**: The architecture of `SQLiteSnapshotStore` must be addressed. It is functionally safe (as verified) but performance-prohibitive for a "fast" protocol.
2.  **Test Debt**: Add the decompression tests to the suite before merge.
