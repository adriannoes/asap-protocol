# Code Review: PR #115

> **PR**: [feat: HTTP version negotiation, async state stores, and dependency security bumps](https://github.com/adriannoes/asap-protocol/pull/115)
> **Branch**: `feat/versioning-async`
> **Sprint**: S4 — Versioning & Async Protocol
> **Reviewer**: Staff Engineer (AI)
> **Date**: 2026-04-10
>
> **Remediation status**: Addressed (2026-04-10) — required items, optional improvements (§3 executor shutdown, §4 WAL/cache/typing/middleware/contract tests, §4.5 weak locks + LRU WAL metadata), and test gaps below are implemented in-tree.

---

## 1. Executive Summary

| Category | Status | Summary |
| :--- | :--- | :--- |
| **Tech Stack** | ✅ | No new deps; `cryptography` / `langchain-core` bumped for security; Pydantic v2, `aiosqlite` throughout |
| **Architecture** | ✅ | Clean layered design: constants → middleware → client/server; shared `_SQLiteSnapshotBackend` reduces duplication |
| **Security** | ✅ | Parameterized SQL, no hardcoded secrets, sanitized logging, WAL pragma lock prevents concurrent journal corruption |
| **Tests** | ✅ | Version negotiation + async stores covered; `TestSQLiteAsyncSnapshotStore` + `AsyncMeteringStore` `isinstance` in `test_metering.py` |

> **General Feedback:** High-quality PR that correctly implements both PRD §4.8 (Unified Versioning) and §4.9 (Async Protocol Resolution). Follow-up work landed: thread-safe pragma lock map, `WeakValueDictionary` for per-path locks, LRU-bounded WAL metadata, integration tests for `SQLiteAsyncSnapshotStore`, and stricter contract assertions on `result.envelope.payload_type`.

---

## 2. Required Fixes (Must Address Before Merge)

### 2.1 Race condition in `_pragma_setup_lock()` dictionary access

*   **Location:** `src/asap/state/stores/sqlite.py`
*   **Status:** ✅ **Fixed** — `_PRAGMA_DICT_GUARD` (`threading.Lock`) wraps dict/weak-map access; check-then-set is atomic under the guard.

### 2.2 Missing `SQLiteAsyncSnapshotStore` integration tests

*   **Location:** `tests/state/test_snapshot.py`
*   **Status:** ✅ **Fixed** — `TestSQLiteAsyncSnapshotStore` covers roundtrip, list/delete, and concurrent `asyncio.gather` saves.

### 2.3 Missing `AsyncMeteringStore` protocol conformance test

*   **Location:** `tests/state/test_metering.py`
*   **Status:** ✅ **Covered** — `TestAsyncMeteringStoreProtocol.test_in_memory_implements_async_metering_store` asserts `isinstance(store, AsyncMeteringStore)`.

---

## 3. Tech-Specific Bug Hunt (Deep Dive)

*   [x] **No sync I/O in async paths**: `src/asap/state/` has no `open()`, `time.sleep`, `requests`, or `sqlite3` usage. All DB access via `aiosqlite`. ✅
*   [x] **No Pydantic v1 syntax**: All models use `model_dump()`, `model_validate()`, `ConfigDict`, `Field(default_factory=...)`. ✅
*   [x] **No mutable default arguments**: `Manifest.supported_versions` uses `default_factory=lambda: [ASAP_DEFAULT_TRANSPORT_VERSION]`. ✅
*   [x] **No `python-jose`**: JWT operations use `joserfc` (verified in auth module). ✅
*   [x] **SQL injection prevention**: All SQL queries in `sqlite.py` use parameterized `?` placeholders. Table names (`SNAPSHOTS_TABLE`, `USAGE_EVENTS_TABLE`) are module-level constants, not user input. ✅
*   [x] **No swallowed exceptions**: `_run_sync` catches `RuntimeError` (expected from `get_running_loop()`). All `except Exception as e:` handlers in `client.py` log via `logger.exception()` or `logger.warning()` with full context. ✅
*   [x] **No `asyncio.create_task()` without reference**: No fire-and-forget task creation in new code. ✅
*   [x] **No `app.dependency_overrides` leak**: Tests use `monkeypatch` and `isolated_rate_limiter` fixtures instead of `dependency_overrides`. ✅
*   [x] **Error responses don't leak internals**: `_handle_internal_error` returns generic "Internal server error" in production, full traceback only when `ASAP_DEBUG=true`. ✅
*   [x] **`_SYNC_BRIDGE_EXECUTOR` shutdown**: `atexit.register` + `_shutdown_sync_bridge_executor()` (`shutdown(wait=False)`) on first lazy init. ✅

---

## 4. Improvements & Refactoring (Highly Recommended)

*   [x] **Optimization — WAL pragma on every connection**: `_apply_wal_pragmas` skips `PRAGMA journal_mode=WAL` when `db_key` is in LRU metadata (see `_WAL_INITIALIZED_LRU`); `busy_timeout` / `synchronous` still applied per connection.

*   [x] **Typing — `Manifest.supported_versions` default should reference a constant**: `default_factory=lambda: [ASAP_DEFAULT_TRANSPORT_VERSION]` in `entities.py`. ✅

*   [x] **Readability — `_first_supported_transport_version`**: Linear scan with `token in ASAP_SUPPORTED_TRANSPORT_VERSIONS` (redundant `if token and` removed). ✅

*   [x] **Test hygiene — Contract tests should validate response body structure**: `tests/contract/test_version_negotiation.py` asserts `result.envelope.payload_type == "task.response"` on success paths. ✅

*   [x] **Observability — `_PRAGMA_SETUP_LOCKS` cleanup**: `_PRAGMA_SETUP_LOCKS` is a `weakref.WeakValueDictionary` (entries drop when locks are collectable). WAL hint cache uses `OrderedDict` LRU (`_MAX_WAL_METADATA_KEYS = 512`) so path-key metadata does not grow without bound in long test processes; eviction only drops the in-memory skip hint (re-running `journal_mode=WAL` remains safe).

---

## 5. Verification Steps

> Run these commands to verify the fixes:

```bash
# 1. Full test suite (should already pass)
PYTHONPATH=src uv run pytest tests/ -v --cov=src --cov-report=term-missing

# 2. Specific: version negotiation contract tests
uv run pytest tests/contract/test_version_negotiation.py -v

# 3. Specific: ASAP-Version middleware tests
uv run pytest tests/transport/test_server.py -k "TestASAPVersionMiddleware" -v

# 4. Specific: client version header tests
uv run pytest tests/transport/test_http_client.py -k "version" -v

# 5. Specific: async store factory tests
uv run pytest tests/state/test_storage_factory.py -k "async" -v

# 6. Specific: async in-memory snapshot store tests
uv run pytest tests/state/test_snapshot.py -k "Async" -v

# 7. After adding SQLiteAsyncSnapshotStore tests:
uv run pytest tests/state/test_snapshot.py -k "SQLiteAsync" -v

# 8. Type checking
uv run mypy src/ scripts/ tests/

# 9. Linting + formatting
uv run ruff check . && uv run ruff format --check .

# 10. Security audit
uv sync --frozen --all-extras --dev --no-extra crewai --no-extra llamaindex && uv run pip-audit
```

---

## 6. Alignment with Tech Stack Decisions

| Decision | Compliance | Notes |
| :--- | :--- | :--- |
| §1.1 Python 3.13+ | ✅ | `warnings.deprecated` decorator (3.13+) |
| §1.2 Pydantic v2 | ✅ | `model_dump()`, `model_validate()`, `ConfigDict` |
| §1.3 JSON-RPC 2.0 | ✅ | `VERSION_INCOMPATIBLE = -32000` in reserved range |
| §1.4 FastAPI | ✅ | Starlette `BaseHTTPMiddleware` for version negotiation |
| §2.4 aiosqlite | ✅ | All SQLite access via `aiosqlite`; no sync `sqlite3` |
| §3.1 Ed25519 | ✅ | Signing tests updated with new `supported_versions` field |
| §5.2 No Lock-in | ✅ | `AsyncSnapshotStore` is a `Protocol` (structural typing) |
| §5.3 Async Protocol | ✅ | Dual protocol: `AsyncSnapshotStore` (new) + `SnapshotStore` (deprecated) |

---

## 7. PRD Requirement Coverage

| PRD Requirement | Status | Evidence |
| :--- | :--- | :--- |
| VER-001: ASAP-Version header in all HTTP responses | ✅ | `ASAPVersionMiddleware` sets header on all responses (line 632) |
| VER-002: Content negotiation (best match) | ✅ | `_first_supported_transport_version` picks first match |
| VER-003: Backward compat (accept v2.1) | ✅ | Contract test `test_v21_client_against_v22_capable_server` |
| VER-004: Manifest `supported_versions` | ✅ | `Manifest.supported_versions: list[str]` with min_length=1 |
| VER-005: Default when no header | ✅ | Middleware defaults to `ASAP_DEFAULT_TRANSPORT_VERSION` |
| VER-006: Contract tests | ✅ | `tests/contract/test_version_negotiation.py` (3 scenarios) |
| ASYNC-001: AsyncSnapshotStore Protocol | ✅ | `snapshot.py` line 24 |
| ASYNC-002: AsyncMeteringStore Protocol | ✅ | `metering.py` line 83 |
| ASYNC-004: Sync protocols remain (deprecated) | ✅ | `@warnings.deprecated` on `SnapshotStore` and `MeteringStore` |
| ASYNC-005: `create_async_snapshot_store()` | ✅ | `snapshot.py` line 147 |
