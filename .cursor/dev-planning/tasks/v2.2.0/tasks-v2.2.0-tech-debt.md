# Tasks: v2.2.0 Tech Debt & Security Hardening

**Status: ✅ Release completed.** v2.1.1 merged to `main`; tag and PyPI publish when ready.

Based on the [v2.1.0 Red-Team Code Review](../code-review/v2.1.0/review-notes.md), these tasks map the critical architectural, security, and concurrency findings into actionable implementation steps. They **must be completed before** starting the new v2.2.0 Scale & Registry features.

## Relevant Files
- `src/asap/auth/jwks.py` - JWKS validation, `_ALLOWED_JWT_ALGORITHMS` (SEC-01, CONC-01)
- `src/asap/auth/middleware.py` - JWT decoding with algorithms allowlist (SEC-01)
- `tests/auth/test_jwks.py` - Unit test for `none` algo rejection (SEC-01)
- `src/asap/auth/oidc.py` - asyncio.Lock for discovery cache (CONC-01)
- `src/asap/state/stores/sqlite.py` - save_async/get_async/list_versions_async/delete_async (ARCH-01), WAL mode
- `tests/state/test_sqlite_store.py` - test_sqlite_snapshot_store_concurrent_async_save_get
- `src/asap/transport/webhook.py` - Webhook retries (Dead letters)
- `src/asap/transport/handlers.py` - Task request validation (Pydantic)
- `src/asap/economics/delegation.py` - `aud` claim parsing (list coercion RFC 7519)
- `tests/economics/test_delegation.py` - test_aud_claim_array_extracts_first_element
- `src/asap/transport/cache.py` - Manifest cache cleanup
- `src/asap/transport/validators.py` - Nonce store cleanup
- `src/asap/integrations/vercel_ai.py` - SECURITY WARNING docstring, optional api_key_header (Depends)
- `tests/integrations/test_vercel_ai.py` - api_key_header 401/200 tests
- `src/asap/transport/middleware.py` - Rate limiter / comments
- `src/asap/discovery/registry.py` - Registry locks & coercion
- `src/asap/economics/storage.py` - SQLite table creation overhead
- `src/asap/transport/compression.py` - prefer_fast_compression option (F-02)
- `CHANGELOG.md` - [2.1.1] release notes
- `tests/*` - Unit tests for all affected modules

### Notes
- Ensure all tests continue to pass via `uv run pytest tests/` after modifications.
- Do not bypass `mypy` or `ruff` typing rules. 

---

## Tasks

- [x] 1.0 Security & Authentication Hardening
  **Trigger / entry point:** Any incoming authenticated HTTP request to the ASAP protocol.
  **Enables:** Secure JWT validation without Algorithm Confusion risks; properly coerced delegation claims.
  **Depends on:** Existing `joserfc` integration and `Pydantic` models.
  
  - [x] 1.1 Restrict JWT algorithms in JWKS decoding (SEC-01)
    - **File**: `src/asap/auth/jwks.py` and `src/asap/auth/middleware.py` (modify existing)
    - **What**: Define `_ALLOWED_JWT_ALGORITHMS = ["EdDSA", "RS256", "ES256"]` and pass it as the `algorithms=` to `jose_jwt.decode(token, key_set, algorithms=...)`.
    - **Why**: Prevents Algorithm Confusion attacks (e.g., an attacker signing tokens with symmetric algorithms using the target's public key).
    - **Pattern**: Follow RFC 8725 §3.2 and the strict JOSE rules from ADR-12.
    - **Verify**: `pytest tests/auth/test_jwks.py tests/auth/test_middleware.py` passes. (Add a unit test attempting to use a `none` algo token and verify it raises a `JoseError`).

  - [x] 1.2 Fix `aud` claim list coercion in Delegation
    - **File**: `src/asap/economics/delegation.py` (modify existing)
    - **What**: Update `aud` parsing to gracefully handle JSON arrays. If `isinstance(aud, list)`, use `aud[0]` instead of forcefully converting the entire list to a string replica (`"['urn:...']"`).
    - **Why**: RFC 7519 allows `aud` to be an array, which breaks existing strict URI string matching.
    - **Pattern**: Standard Python type checking `isinstance(aud, list)`.
    - **Verify**: Include a test with an array `aud` claim and verify proper extraction.

  - [x] 1.3 Add auth warning/middleware to Vercel AI router
    - **File**: `src/asap/integrations/vercel_ai.py` (modify existing)
    - **What**: Add a `SECURITY WARNING` to the docstring about missing auth middleware, and add an optional `api_key_header` parameter to the router creation.
    - **Why**: Currently exposes agent invocation endpoints without any native authentication.
    - **Pattern**: Follow standard FastAPI `Depends` injection for optional auth headers.
    - **Verify**: Ensure the module can still be imported normally without breaking existing usage.

- [x] 2.0 Concurrency & Architecture Fixes
  **Trigger / entry point:** High-velocity concurrent traffic to the app (e.g., 50+ simultaneous connections).
  **Enables:** True non-blocking event loop execution, eliminating threading deadlocks and stalling.
  **Depends on:** Existing `asyncio` and `aiosqlite` SQLite foundation.

  - [x] 2.1 Eliminate event-loop blocking in SQLite bridging (ARCH-01)
    - **File**: `src/asap/state/stores/sqlite.py` (modify existing)
    - **What**: Add `async def` versions of `save` and `get` (e.g., `save_async`, `get_async`) that call the native `aiosqlite` methods directly, bypassing `_run_sync` and `ThreadPoolExecutor`.
    - **Why**: `future.result()` inside a threadpool under an async context blocks the FastAPI worker completely, bringing concurrent capacity to zero.
    - **Pattern**: Expose native async methods alongside the legacy sync ones for Protocol compliance. Update FastAPI endpoint handlers to call the `_async` methods.
    - **Verify**: `pytest tests/state/test_sqlite_store.py -k "concurrent"` runs without hanging or deadlock.
    - **Integration**: State handler endpoints in the main app must switch to awaiting these new async methods.

  - [x] 2.2 Replace `threading.Lock` with `asyncio.Lock` in async caches (CONC-01)
    - **File**: `src/asap/auth/oidc.py` and `src/asap/auth/jwks.py` (modify existing)
    - **What**: Swap `from threading import Lock` to `from asyncio import Lock`. Use `async with self._lock:` instead of `with self._lock:`.
    - **Why**: A thread lock stalls all asyncio coroutines when multiple requests attempt to refresh OIDC/JWKS caches simultaneously.
    - **Pattern**: Maintain the double-checked locking idiom, but use the non-blocking `asyncio.Lock`.
    - **Verify**: Both `test_auth_oidc.py` and `test_auth_jwks.py` pass without regression.

  - [x] 2.3 Enable SQLite WAL mode
    - **File**: `src/asap/state/stores/sqlite.py`, `src/asap/economics/storage.py` (modify existing)
    - **What**: Execute `PRAGMA journal_mode=WAL` and `PRAGMA synchronous=NORMAL` when opening `aiosqlite` database connections.
    - **Why**: Prevents writes from acquiring exclusive database-level locks that block reads, heavily improving SQLite concurrency.
    - **Pattern**: Execute pragmas right after `aiosqlite.connect()`.
    - **Verify**: Inspect the local testing directory for SQLite `.wal` and `.shm` files during tests.

  - [x] 2.4 Fix GIL-atomic dictionary initialization for Registry locks
    - **File**: `src/asap/discovery/registry.py` (modify existing)
    - **What**: Replace the `with _registry_locks_guard:` block and `if not in` checks with `_registry_locks.setdefault(registry_url, asyncio.Lock())`.
    - **Why**: Removes a convoluted threading lock around an asyncio lock, leveraging Python's GIL to handle atomic dict insertions cleanly.
    - **Pattern**: Standard CPython atomic `.setdefault()`.
    - **Verify**: Function works correctly and passes typings.

- [x] 3.0 Reliability, Limits & Leaks
  **Trigger / entry point:** Long-running ASAP server processes with heavy webhook traffic or load.
  **Enables:** Stable memory footprint and predictable resource limits over weeks of uptime.

  - [x] 3.1 Cap Webhook dead letters list size
    - **File**: `src/asap/transport/webhook.py` (modify existing)
    - **What**: Add a capping mechanism (e.g., `MAX_DEAD_LETTERS = 1000`) in `_send_to_dead_letter()`. Use `pop(0)` or `collections.deque` with `maxlen`.
    - **Why**: Prevents unbounded memory growth when target endpoints are down for extended periods.
    - **Pattern**: Simple fixed-size queue eviction.
    - **Verify**: Run a mock test emitting 1001 dead letters, assert the storage length is exactly 1000.

  - [x] 3.2 Add background cleanup to ManifestCache
    - **File**: `src/asap/transport/cache.py` (modify existing)
    - **What**: Add documentation or provide a hook for a background `asyncio.create_task` loop that periodically calls `cleanup_expired()`. Fix it so expired caches actually get pruned automatically.
    - **Why**: Expired cache entries sit in memory indefinitely unless manually requested again.
    - **Verify**: Add a unit test verifying memory release over time.

  - [x] 3.3 Increase Nonce store cleanup probability
    - **File**: `src/asap/transport/validators.py` (modify existing)
    - **What**: Change `_CLEANUP_PROBABILITY` from `0.01` to `0.05`, or add a hard `_MAX_NONCE_STORE_SIZE` limit fallback.
    - **Why**: 1% execution rate is too sparse under high throughput (thousands of requests), risking memory drift.
    - **Verify**: Review `len(self._store)` behavior visually or via assertions.

  - [x] 3.4 Support distributed rate limiting (F-01)
    - **File**: `src/asap/transport/middleware.py` (modify existing)
    - **What**: Enhance the rate limiter to use `redis-py` (as an optional extra dependency) if `ASAP_RATE_LIMIT_BACKEND=redis://...` is configured, falling back to the current in-memory limit. Document this configuration.
    - **Why**: In-memory rate limiting is currently per-worker/process, meaning a 4-worker setup allows 4x the rate limit per IP.
    - **Pattern**: Simple Strategy pattern for the `RateLimiter` class (InMemory vs Redis).
    - **Verify**: Unit tests with and without Redis (or mock Redis) to verify limits are properly distributed.

- [x] 4.0 Code Quality & Minor Adjustments
  **Trigger / entry point:** Module loading / inbound unvalidated socket requests.
  **Enables:** Strict data sanitization and reduced redundant queries.
  
  - [x] 4.1 Enforce Pydantic validation on `echo_handler`
    - **File**: `src/asap/transport/handlers.py` (modify existing)
    - **What**: Change `TaskRequest(**envelope.payload_dict)` to `TaskRequest.model_validate(envelope.payload_dict)`.
    - **Why**: The `**dict` positional unpacking completely skips custom Pydantic v2 field coercions and model-level validators.
    - **Pattern**: Explicit `.model_validate()` calls for dynamic JSON inputs.
    - **Verify**: Valid input tests pass, invalid inputs raise ValidationError correctly.

  - [x] 4.2 Fix empty-string coercion in Agent Registry
    - **File**: `src/asap/discovery/registry.py` (modify existing)
    - **What**: Change `repository_url=repository_url or None` to explicitly strip and handle blank whitespace `repository_url=(repository_url.strip() or None) if repository_url else None`.
    - **Why**: Consistency with the rest of the codebase (preventing untrimmed spaces `" "` from bypassing empty checks).
    - **Verify**: Unit tests with whitespace URLs resolve to `None`.

  - [x] 4.3 Optimize SQLite `_ensure_table` execution
    - **File**: `src/asap/economics/storage.py` and related (modify existing)
    - **What**: Add an `_initialized` boolean instance flag so that `_ensure_table` is executed exactly once upon the first `.save()` or `.get()`, instead of repeating on every query.
    - **Why**: Removes redundant `CREATE TABLE IF NOT EXISTS` schema queries on every read/write.
    - **Pattern**: Lazy initialization block (`if not self._initialized: ...`).
    - **Verify**: Ensure the table is still correctly created on virgin databases.

  - [x] 4.4 Update stale version comments
    - **File**: `src/asap/transport/middleware.py` (modify existing)
    - **What**: Update line 13 from "(planned for v1.2.0)" to "(planned for v2.1.1; see backlog)".
    - **Why**: Housekeeping.
    - **Verify**: N/A.

  - [x] 4.5 Implement fast compression option (F-02)
    - **File**: `src/asap/transport/compression.py` (modify existing)
    - **What**: Resolve the TODO at line 143 by adding a `prefer_fast_compression` option to the compression middleware/utilities.
    - **Why**: Gives agents the ability to optimize for latency over bandwidth.
    - **Verify**: Unit test that verifies compression method selection changes when the flag is truthy.

- [x] 5.0 Release v2.1.1 (PyPI)
  **Trigger / entry point:** All previous Tech Debt tasks (1.0 to 4.0) are completed and tested.
  **Enables:** Distribution of ASAP Protocol `v2.1.1` to users fixing critical architecture and security bugs.
  **Depends on:** `tests/` passing, `ruff` passing, `mypy` passing.
  
  - [x] 5.1 Bump version to 2.1.1
    - **File**: `pyproject.toml` and `src/asap/__init__.py` (modify existing)
    - **What**: Change `version = "2.1.0"` to `version = "2.1.1"` in both `pyproject.toml` `[project]` section and the runtime `__version__` string.
    - **Why**: Semantic versioning for a patch release.
    - **Verify**: `uv run python -c "import asap; print(asap.__version__)"` outputs `2.1.1`.

  - [x] 5.2 Update CHANGELOG notes
    - **File**: `CHANGELOG.md` (modify existing)
    - **What**: Add a new `## [2.1.1]` section detailing the security fix (SEC-01 JWT Algorithm allowlist), the architecture fix (ARCH-01 SQLite async bridging), the SSRF DNS protection in frontend, and internal deadlocks fixed via `asyncio.Lock` and WAL mode.
    - **Why**: Maintain rigorous historical records for users relying on the SDK.
    - **Verify**: CHANGELOG renders correctly in markdown preview.

  - [x] 5.3 Git Tag and trigger Trusted Publishing
    - **File**: Terminal / Git (Action)
    - **What**: Commit the version bumps, then create and push an annotated git tag: `git tag -a v2.1.1 -m "Release v2.1.1" && git push origin v2.1.1`.
    - **Why**: Pushing a tag starting with `v*` will trigger `.github/workflows/release.yml`, which bundles the sdist/wheel and securely publishes to PyPI without manual tokens.
    - **Verify**: Observe GitHub Actions tab to confirm the workflow succeeds and `pip install asap-protocol==2.1.1` becomes available on PyPI.
