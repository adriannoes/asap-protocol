# ASAP Protocol v2.1.0 — Red-Team Code Review

**Review Date:** 2026-03-01  
**Reviewer:** Claude Opus 4.6 + Gemini 3.1 Pro
**Methodology:** Static analysis, anti-pattern scanning, architecture drift review, concurrency/security deep-dive  
**Quality Gates Passed:** `ruff check` ✅ `ruff format --check` ✅ `mypy src/` ✅ `pytest tests/ — 2532 passed, 5 skipped` ✅

---

## 1. Executive Summary

| Category | Status | Summary |
| :--- | :--- | :--- |
| **Tech Stack** | ✅ | `joserfc`, `Pydantic v2`, `aiosqlite`, `httpx`, `cryptography` — all correct, no deprecated libraries found |
| **Architecture** | ⚠️ | `SnapshotStore` Protocol uses sync interface but bridges to async via `_run_sync` — creates new event loops in threads when called from FastAPI handlers |
| **Security** | ⚠️ | `jose_jwt.decode()` in `auth/jwks.py` and `auth/middleware.py` called **without an `algorithms=` allowlist** — opens algorithm confusion attack vector |
| **Concurrency** | ⚠️ | `threading.Lock` used in `async` methods across `auth/oidc.py` and `auth/jwks.py` — blocks event loop thread under contention |
| **Frontend/UI** | ✅ | Next.js visual and E2E review passed. Fixed minor layout issue on Usage Snippets tabs. No unhandled console errors. |
| **Tests** | ✅ | 2532 tests, fast (< 120s), good fixture hygiene; `dependency_overrides` cleared correctly |
| **Observability** | ✅ | All `except` blocks use `logger.exception()` or `logger.warning()` with `exc_info=True`; no bare swallows found |

> **General Feedback:** The codebase is well-structured, strictly typed, and passes all automated quality gates. The most impactful issues are in the **authentication** layer (algorithm confusion risk) and the **state storage** bridge (`_run_sync` threading model), which could surface as subtle, hard-to-reproduce bugs in production multi-worker deployments. The review found zero hardcoded secrets, no use of deprecated JWT libraries, and no SQL injection risks. These findings are addressable in v2.1.1 without breaking the wire protocol.

---

## 2. Required Fixes (Must Address Before v2.1.1)

### [SEC-01] `jose_jwt.decode()` Without Algorithm Allowlist — Algorithm Confusion Attack

- **Location:** `src/asap/auth/jwks.py:90` and `src/asap/auth/middleware.py:256,272`

- **Problem:** Both call sites use:
  ```python
  token_obj = jose_jwt.decode(token, key_set)
  ```
  The `joserfc` library requires the caller to restrict which algorithms are accepted. Without an explicit `algorithms=` parameter, the library may accept tokens signed with algorithms the server did not intend to trust (e.g., `none`, `HS256` with the public key as the symmetric secret, or `RS256` vs `EdDSA`). This is the **JWT Algorithm Confusion Attack** (CVE class, documented in [RFC 8725 §3.2](https://datatracker.ietf.org/doc/html/rfc8725#section-3.2)).

- **Expert View:** Per the tech-stack-decisions ADR-12, the project uses `joserfc` precisely because it provides rigorous JOSE security. Not passing an algorithm allowlist undermines this guarantee. Since ASAP mandates Ed25519 for agent signing (§3.1), the JWKS validation should explicitly restrict to `EdDSA`. For OAuth2 IdP-issued tokens (RS256/ES256), the allowlist should cover only those specific algorithms — never `none` or `HS*`.

- **Fix Suggestion:**
  ```python
  # In auth/jwks.py and auth/middleware.py
  # Define once as module constant
  _ALLOWED_JWT_ALGORITHMS = ["EdDSA", "RS256", "ES256"]

  # Replace:
  token_obj = jose_jwt.decode(token, key_set)
  # With:
  token_obj = jose_jwt.decode(token, key_set, algorithms=_ALLOWED_JWT_ALGORITHMS)
  ```
  If the JWKS endpoint only issues RS256 tokens (Auth0, Keycloak default), restrict further: `algorithms=["RS256"]`. For ASAP self-signed delegation tokens, use `algorithms=["EdDSA", "Ed25519"]`.

- **Verification:**
  ```bash
  uv run pytest tests/test_auth_jwks.py tests/test_auth_middleware.py -v
  # Add a test: attempt to decode a `none` or `HS256` token → expect JoseError
  ```

---

### [ARCH-01] `_run_sync` Bridges Async-to-Sync via `asyncio.run()` in ThreadPoolExecutor

- **Location:** `src/asap/state/stores/sqlite.py:39-47`

- **Problem:** When `SQLiteSnapshotStore.save()` / `.get()` / etc. are called from within an **async context** (e.g., a FastAPI handler), `_run_sync` calls `executor.submit(asyncio.run, coro)`. This creates a **new event loop in a worker thread**, which opens several risks:
  1. `aiosqlite` operations run on the new loop but the SQLite WAL might conflict with the main event loop's `aiosqlite` connections — creating **deadlocks** under concurrent writes.
  2. If the `ThreadPoolExecutor` is saturated (all 4 workers busy), `.result()` **blocks the calling async task** — blocking the entire FastAPI event loop worker.
  3. The caller's `asyncio` context (traces, contextvars, structured logging) is **lost** in the worker thread.
  
  ```python
  # Current — dangerous:
  def _run_sync(coro: Any) -> Any:
      try:
          asyncio.get_running_loop()
      except RuntimeError:
          return asyncio.run(coro)
      executor = _get_sync_bridge_executor()
      future = executor.submit(asyncio.run, coro)
      return future.result()  # ← blocks event loop thread!
  ```

- **Expert View:** The tech-stack-decisions document explicitly acknowledges this "Open Decision" (§5.3): the `SnapshotStore` Protocol uses sync methods because it was "inherited from v1.0 InMemorySnapshotStore". The document notes this is "not ideal" and commits to resolving at CP-1 checkpoint. This technical debt has grown to the point where it represents a correctness and performance hazard in v2.1.x. The `_run_sync` bridge should never block an async thread.

- **Fix Suggestion (short-term — v2.1.1):**  
  Replace `future.result()` with `asyncio.run_coroutine_threadsafe()` using the running loop, or better, use `loop.run_in_executor()` from the caller side:
  ```python
  # In async handlers, call the async impl directly instead of the sync wrapper:
  # Replace:
  store.save(snapshot)  # blocks!
  # With:
  await store._save_impl(snapshot)  # calls aiosqlite natively
  ```
  The cleanest fix is to add `async` versions of the public methods to `SQLiteSnapshotStore` and have FastAPI handlers use them:
  ```python
  class SQLiteSnapshotStore:
      async def save_async(self, snapshot: StateSnapshot) -> None:
          await self._save_impl(snapshot)

      async def get_async(self, task_id: TaskID, version: int | None = None) -> StateSnapshot | None:
          return await self._get_impl(task_id, version)
  ```
  Keep the sync wrappers for the `SnapshotStore` Protocol compliance (backward compat), but route all async call sites through the async methods.

- **Verification:**
  ```bash
  # Test that concurrent saves don't deadlock:
  uv run pytest tests/test_state_sqlite.py -v -k "concurrent"
  # Add stress test: 50 concurrent async handler calls each writing a snapshot
  ```

---

### [CONC-01] `threading.Lock` in `async` Methods — Event Loop Blocking

- **Location:** `src/asap/auth/oidc.py:138,148` and `src/asap/auth/jwks.py:132,147,158,163`

- **Problem:** `OIDCDiscovery.discover()` and `JWKSValidator.fetch_keys()` are `async` methods but use `threading.Lock` (via `with self._lock:`) for cache guards:
  ```python
  # oidc.py — sync lock inside async method:
  async def discover(self) -> OIDCConfig:
      with self._lock:  # blocks event loop!
          if self._cache_entry is not None and not self._cache_entry.is_expired():
              return self._cache_entry.config
      ...
  ```
  While the `with` block is held **very briefly** (in-memory dict lookup), under a thundering herd (burst of 100+ agent connections simultaneously), the event loop thread is blocked waiting on the mutex. In Python's asyncio model, this means **all other coroutines stall** for the duration. The double-check pattern is also missing the lock during the final cache write on `oidc.py:148`.

- **Expert View:** This is a classic async-sync lock mixing error. The correct pattern for async code is `asyncio.Lock` + `async with`. Since `asyncio.Lock` is already used throughout the middleware (e.g. `oauth2.py` uses `asyncio.Lock` correctly), this is an inconsistency that has likely survived because the critical path (JWT validation) was not stressed under concurrent load in tests.

- **Fix Suggestion:**
  ```python
  # oidc.py: replace threading.Lock with asyncio.Lock
  from asyncio import Lock  # instead of from threading import Lock

  class OIDCDiscovery:
      def __init__(self, ...):
          self._lock: Lock = Lock()  # asyncio.Lock

      async def discover(self) -> OIDCConfig:
          async with self._lock:  # non-blocking async mutex
              if self._cache_entry is not None and not self._cache_entry.is_expired():
                  return self._cache_entry.config
          config = await self._fetch_discovery()
          async with self._lock:
              self._cache_entry = _DiscoveryCacheEntry(config, DISCOVERY_CACHE_TTL_SECONDS)
          return config
  ```
  Apply the same fix to `auth/jwks.py`.

- **Verification:**
  ```bash
  uv run pytest tests/test_auth_oidc.py tests/test_auth_jwks.py -v
  # Add concurrency test: 50 concurrent discover() calls → all resolve, no deadlock
  ```

---

## 3. Tech-Specific Bug Hunt (Deep Dive)

### FastAPI & Pydantic v2

- [x] **Mutable Default in `MeteringQuery`**: `offset: int = Field(default=0, ge=0)` — correctly uses `Field`, no mutable defaults found anywhere in Pydantic models. ✅

- [x] **`assert` for Validation**: No `assert` statements found in business logic. All validation uses Pydantic validators or explicit `raise` statements. ✅

- [x] **`dependency_overrides` Leak**: Searched test files — `dependency_overrides` are properly cleared via `app.dependency_overrides.clear()` in fixture teardowns. ✅

- [ ] **`WebhookRetryManager._dead_letters` Grows Unbounded**: `_dead_letters: list[DeadLetterEntry]` in `transport/webhook.py:400` has no size cap. Under a thundering herd of failing webhooks, this list grows indefinitely and is never pruned.
  ```python
  # Fix: add max_dead_letters cap
  MAX_DEAD_LETTERS = 1000

  async def _send_to_dead_letter(self, ...):
      if len(self._dead_letters) >= MAX_DEAD_LETTERS:
          self._dead_letters.pop(0)  # evict oldest
      self._dead_letters.append(entry)
  ```

- [ ] **`echo_handler` Uses Positional `TaskRequest(**kwargs)` Instead of `.model_validate()`**: `transport/handlers.py:422`:
  ```python
  task_request = TaskRequest(**envelope.payload_dict)  # bypasses validators
  ```
  Pydantic v2's `model_validate()` runs full field validators and coercions. `TaskRequest(**dict)` bypasses `model_validator` functions. Should be:
  ```python
  task_request = TaskRequest.model_validate(envelope.payload_dict)
  ```

### Asyncio & aiosqlite

- [ ] **`asyncio.run()` in ThreadPoolExecutor** (see [ARCH-01] above — repeated for visibility).

- [x] **`asyncio.create_task()` Without Stored Reference Risk**: Checked all 5 `create_task()` call sites in `websocket.py`. All results are assigned to instance attributes (`self._recv_task`, `self._ack_check_task`, `self._run_task`) — no GC risk. ✅

- [ ] **SQLite WAL Contention — No `journal_mode=WAL`**: Both `SQLiteSnapshotStore` and `SQLiteMeteringStorage` open connections without setting `PRAGMA journal_mode=WAL`. Default journal mode is `DELETE`, which uses **exclusive locks on writes** — reads block during writes. Under concurrent FastAPI requests (common), this causes unnecessary latency. Fix:
  ```python
  async with aiosqlite.connect(self._db_path) as conn:
      await conn.execute("PRAGMA journal_mode=WAL")
      await conn.execute("PRAGMA synchronous=NORMAL")
      await self._ensure_table(conn)
      ...
  ```

- [x] **`aiosqlite` Nested Transactions**: No nested transaction patterns found. All `commit()` calls are at top-level per connection context. ✅

### Security

- [ ] **`delegation.py` — `aud` Claim Coerces `list` to `str`** (previously noted as F-11):
  ```python
  aud = claims.get("aud")
  delegate = str(aud) if aud is not None else None
  # If aud is ["urn:asap:agent:x"] → delegate = "['urn:asap:agent:x']"
  ```
  RFC 7519 allows `aud` to be a JSON array. Fix:
  ```python
  aud = claims.get("aud")
  if isinstance(aud, list):
      delegate = aud[0] if aud else None
  else:
      delegate = str(aud) if aud is not None else None
  ```

- [x] **Internal Stack Trace Leak**: `server.py:655` shows `traceback.format_exc()` in the JSON-RPC error response — but this is **gated** by `is_debug_mode()` (line 651). In production (`ASAP_DEBUG=false`), only `"Internal server error"` is returned. ✅

- [x] **Hardcoded Secrets Hunt**: No hardcoded API keys, tokens, or passwords found. All secrets referenced as `os.environ.get(...)` or via Pydantic `SecretStr`. Docstring examples use placeholder values like `"secret"` (not real credentials). ✅

- [x] **SSRF Protection**: `webhook.py` `validate_callback_url()` blocks private/loopback/link-local IPs both from literals and from DNS resolution (anti DNS-rebinding). ✅

- [x] **SQL Injection**: All SQL queries use parameterized `?` placeholders. Table names are module-level constants (`_USAGE_EVENTS_TABLE`, `SNAPSHOTS_TABLE`) with `# nosec B608` comments. No user input reaches bare f-string SQL. ✅

- [x] **Ed25519 Enforced for Manifest Signing**: `crypto/signing.py` strictly uses `Ed25519PrivateKey` / `Ed25519PublicKey`. No RSA or ECDSA paths exist. ✅

---

## 4. Improvements & Refactoring (Low Priority)

- [ ] **`ManifestCache` — No Background Expiry Cleanup (F-04)**: `cleanup_expired()` exists but is never driven by a background task. Register it in FastAPI `lifespan`:
  ```python
  @asynccontextmanager
  async def lifespan(app: FastAPI):
      task = asyncio.create_task(_periodic_cache_cleanup(manifest_cache))
      yield
      task.cancel()
  ```

- [ ] **`InMemoryNonceStore` — Cleanup Probability Too Low Under High Load (F-05)**: `_CLEANUP_PROBABILITY = 0.01` in `validators.py`. Increase to `0.05` or add a max-size guard:
  ```python
  if len(self._store) > _MAX_NONCE_STORE_SIZE or random.random() < _CLEANUP_PROBABILITY:
      self._cleanup()
  ```

- [ ] **`vercel_ai.py` — No Auth Middleware on Router (F-07)**: `create_asap_tools_router()` exposes agent invocation endpoints without auth. Add docstring warning and optional `api_key_header` param. Until then, add a `SECURITY WARNING` to the module docstring.

- [ ] **`generate_registry_entry` — Inconsistent Empty-String Coercion (F-08)**:
  ```python
  # Current (inconsistent):
  repository_url=repository_url or None,
  # Correct (explicit):
  repository_url=(repository_url.strip() or None) if repository_url else None,
  ```

- [ ] **`middleware.py` — Stale Version Reference in Comment (F-06)**: Line 13 references `"(planned for v1.2.0)"`. Update to `"(planned for v2.1.1; see backlog)"`.

- [ ] **`cli.py` — `manifest verify --public-key` Flag Name Misleading (F-12)**: The flag requires a **private key PEM** (public key is derived). Already fixed in help text; long-term, consider renaming to `--key-file` or supporting native public-key PEM.

- [ ] **`discovery/registry.py` — `asyncio.Lock` Created in `threading.Lock` Guard (F-03)**: Use `dict.setdefault()` pattern instead (GIL-atomic for CPython):
  ```python
  # Replace:
  with _registry_locks_guard:
      if registry_url not in _registry_locks:
          _registry_locks[registry_url] = asyncio.Lock()
  # With:
  _registry_locks.setdefault(registry_url, asyncio.Lock())
  ```

- [ ] **`SQLiteMeteringStorage` / `SQLiteDelegationStorage` / `SQLiteSLAStorage` — `_ensure_table()` per Operation (F-13)**: Consider an `initialized` flag or expose an `initialize()` async method to be called once during `lifespan`:
  ```python
  async def initialize(self) -> None:
      async with aiosqlite.connect(self._db_path) as conn:
          await self._ensure_table(conn)
      self._initialized = True
  ```

- [ ] **Rate Limiter Not Shared Across Workers (F-01)**: In-memory rate limit is per-process. Document `ASAP_RATE_LIMIT_BACKEND=redis://...` as the recommended production config. Implement in v2.1.1 with `redis-py` as an optional backend.

---

## 5. Web Platform & Frontend Verification

- [x] **UI Rendering & Console Errors:** Verified the landing page, Agent Registry `/browse`, Demos, and Developer Experience pages. No unhandled exceptions or console errors were found during general navigation.
- [x] **Agent Details Layout Fix:** Fixed a layout bug on `/agents/[id]` where the "Usage Snippets" `TabsList` used a hardcoded CSS grid, causing the tabs (Node.js, LangChain, LlamaIndex, etc.) to overlap or cramp on certain viewport sizes. Replaced with responsive `flex-wrap`.
- [x] **Playwright E2E:** Executed the Next.js Playwright suite. The standard `browse.spec.ts` passes successfully, validating the search and tag filtering capabilities. (Note: `load-test` requires explicit backend fixtures).
- [ ] **Auth Protected Routes Verification:** `Dashboard` and `/register` correctly redirect to GitHub OAuth. Next.js Server Actions CSRF protections are actively utilized.

---

## 6. Frontend Security Investigation (Next.js)

**Scope of Review:** `next.config.ts`, Server Actions, URL/SSRF Validators, and Auth configuration (`next-auth` v5).

### 🟢 Security Strengths Identified
1. **Content Security Policy (CSP):** Excellent configuration in `next.config.ts`. Blocks `unsafe-eval` in production, correctly enforces `strict-origin-when-cross-origin`, and uses `X-Frame-Options: DENY` (anti-clickjacking).
2. **Server Actions vs. API Routes:** The `/dashboard/register` form uses React Server Actions (`actions.ts`). Next.js 14+ automatically protects Server Actions against Cross-Site Request Forgery (CSRF) by enforcing `Origin` headers and POST methods. No manual CSUR/CSRF tokens are required.
3. **Session Management:** `next-auth` (v5 beta) is correctly configured to encrypt session JWTs (A256GCM) and never exposes the `accessToken` to the client browser cookie, keeping it server-side.

### 🔴 Critical Vulnerability Found & Fixed

**[SEC-02] Server-Side Request Forgery (SSRF) via DNS Rebinding in Agent Registration**

- **Location:** `src/lib/url-validator.ts`
- **Problem:** During agent registration, the server makes a `HEAD` request to the provided `manifest_url` to verify it is reachable (`fetch(manifest_url, { method: 'HEAD' })`). The URL was validated using `isAllowedExternalUrl(url)` which successfully blocked strings like `localhost` or `127.0.0.1`. However, an attacker could provide a domain like `malicious.example.com` which resolves passing the text-based check, but points its DNS A/AAAA record to an internal IP (e.g. `10.0.0.1` or an AWS metadata IP `169.254.169.254`). 
- **The Fix:** We completely rewrote `isAllowedExternalUrl` into an `async` function that utilizes Node's `dns.resolve()`. It now resolves the domain to its actual underlying IPs before making the check, stopping DNS-rebinding attacks cold.
- **Related Updates:** 
  - Updated `/api/health-check/route.ts` and `/dashboard/register/actions.ts` to `await isAllowedExternalUrl(...)`.
  - Introduced a synchronous `isAllowedProxyUrl` strictly for UI `href` rendering (preventing `javascript:` protocol injections) without causing async render waterfalls.
  - Test suites updated and passing.

---

## 7. Verification Steps

### After fixing [SEC-01] — Algorithm Allowlist:
```bash
uv run pytest tests/test_auth_jwks.py tests/test_auth_middleware.py -v
# Manual: forge a `none` algorithm JWT and send to /asap → should return 401
```

### After fixing [ARCH-01] — _run_sync:
```bash
uv run pytest tests/test_state_sqlite.py -v
# Stress test: send 50 concurrent task.request envelopes to the echo agent
python -c "
import asyncio, httpx
async def test():
    async with httpx.AsyncClient() as c:
        tasks = [c.post('http://localhost:8001/asap', json={...}) for _ in range(50)]
        results = await asyncio.gather(*tasks)
        print([r.status_code for r in results])
asyncio.run(test())
"
```

### After fixing [CONC-01] — asyncio.Lock:
```bash
uv run pytest tests/test_auth_oidc.py tests/test_auth_jwks.py -v
# Concurrent test: 100 asyncio tasks calling discover() simultaneously
```

### Full regression:
```bash
uv run mypy src/ scripts/ tests/
uv run ruff check src/
uv run pytest tests/ -x -q
```

---

## 6. Legacy Findings Reference (v2.1.0 Review Pass 1)

> These findings were documented in the initial review session. Still pending for v2.1.1.

| ID | File | Severity | Summary |
|----|------|----------|---------|
| F-01 | `transport/middleware.py` | Medium | Rate limiter in-memory limit not shared across workers |
| F-02 | `transport/compression.py:143` | Low | TODO: No `prefer_fast_compression` option |
| F-03 | `discovery/registry.py:169` | Low | `asyncio.Lock` created inside `threading.Lock` guard |
| F-04 | `transport/cache.py` | Low | No background task driving `ManifestCache.cleanup_expired()` |
| F-05 | `transport/validators.py:158` | Very Low | `InMemoryNonceStore` cleanup probability (1%) too low under high load |
| F-06 | `transport/middleware.py:13` | Cosmetic | Stale comment references `v1.2.0` |
| F-07 | `integrations/vercel_ai.py` | Medium | Router endpoints expose agent invocation without auth middleware |
| F-08 | `discovery/registry.py:268` | Cosmetic | Redundant `or None` pattern, inconsistent empty-string coercion |
| F-09 | `auth/oidc.py` | Low → ⬆️ **CONC-01** | `threading.Lock` in async method — promoted to required fix |
| F-10 | `auth/jwks.py` | Low → ⬆️ **CONC-01** | Same as F-09 — promoted to required fix |
| F-11 | `economics/delegation.py:196` | Low | `aud` claim coerces `list[str]` to garbled Python `repr` |
| F-12 | `cli.py:168` | Cosmetic | `--public-key` flag name misleading — **already fixed** in review |
| F-13 | `economics/storage.py` | Very Low | `_ensure_table()` called on every SQLite operation |

---

## 7. Things Done Well (Strengths)

- **Strict typing**: MyPy passes with zero errors across the entire codebase.
- **No deprecated JWT library**: `joserfc` used throughout — no `python-jose` or `PyJWT`.
- **Correct JWT library choice**: `Authlib` + `joserfc` as mandated by ADR-12.
- **Ed25519 only**: No RSA or ECDSA signing paths in the codebase — fully aligned with §3.1.
- **No hardcoded secrets**: 100% env-var driven, `SecretStr` used where appropriate.
- **SQL injection safe**: All queries parameterized, constant table names with `nosec` annotations.
- **SSRF protection**: Webhook URL validation blocks private/loopback/link-local IPs + DNS rebinding.
- **Thread-safe circuit breaker**: Correct `RLock` + HALF_OPEN single-permit logic.
- **`asyncio.create_task()` references stored**: No fire-and-forget GC risks in WebSocket transport.
- **Lazy imports**: Integration modules (LangChain, CrewAI, SmolAgents) use `__getattr__` lazy loading.
- **Comprehensive test coverage**: 2532 tests, < 120s total, clean fixture hygiene.
- **Observability-first**: All exception handlers log via `logger.exception()` or `logger.warning(exc_info=True)`.
- **Rate limiting + size limits**: Both enforced at middleware level before reaching handlers.
