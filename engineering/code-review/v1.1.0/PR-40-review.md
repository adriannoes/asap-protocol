# Code Review: Release v1.1.0 — Webhooks, ASAPRateLimiter, Security Model, secure_agent

**PR**: [#40](https://github.com/adriannoes/asap-protocol/pull/40)
**Branch**: `release/v1.1.0` → `main`
**Reviewer**: Staff Engineer (Red Team)
**Date**: 2026-02-10

---

## 1. Executive Summary

| Metric | Assessment |
| :--- | :--- |
| **Architecture** | ✅ Aligned — slowapi → `ASAPRateLimiter` migration is clean; webhook module follows existing patterns |
| **Test Coverage** | ✅ Solid — 60 webhook tests, chaos tests for WebSocket, rate limiter isolation via `create_test_limiter` |
| **Security (SSRF)** | ✅ Strong — DNS rebinding checks, private IP blocking, HMAC-SHA256 signatures |
| **Blocking Issues** | **2** Critical Bugs/Risks |

### Files Reviewed (src/ only, excluding docs/planning)

| File | LOC Δ | Verdict |
|:-----|:------|:--------|
| `src/asap/transport/webhook.py` | +510 (new) | ⚠️ 2 findings |
| `src/asap/transport/rate_limit.py` | +268/−4 | ⚠️ 1 finding |
| `src/asap/transport/middleware.py` | +16/−92 | ✅ Clean migration |
| `src/asap/transport/server.py` | +18/−14 | ✅ |
| `src/asap/transport/handlers.py` | +2 | ✅ Good fix for leaked coroutine |
| `src/asap/transport/__init__.py` | +31 | ✅ |
| `src/asap/errors.py` | +31 | ✅ |
| `src/asap/examples/secure_agent.py` | +212 (new) | ⚠️ 1 finding |
| `src/asap/examples/rate_limiting.py` | +1/−4 | ✅ |
| `tests/transport/unit/test_webhook.py` | +670 (new) | ✅ Solid |
| `tests/chaos/test_websocket_stability.py` | +708 (new) | ✅ |
| `pyproject.toml` | +8/−6 | ✅ |

---

## 2. Architecture & Stack Violations (Critical)

> Strict enforcement of tech-stack standards: Python 3.13+, Pydantic v2, FastAPI, `aiosqlite`, `Authlib`. Forbidden: sync I/O (`open`, `requests`), `python-jose`, global mutable state.

### 2.1 🔴 Blocking Sync I/O in Async Path — `socket.getaddrinfo`

* **File:** `src/asap/transport/webhook.py:60`
* **Rule Broken:** Sync blocking I/O in async code path. `_resolve_hostname()` calls `socket.getaddrinfo()` which blocks the event loop during DNS resolution. This is called from `WebhookDelivery.deliver()` → `validate_url()` → `validate_callback_url()` → `_resolve_hostname()`.
* **Impact:** Under load, every webhook delivery blocks the event loop for the duration of DNS resolution (up to system DNS timeout, often 5-30s on failure). With concurrent webhook deliveries, this serializes all DNS lookups, starving other coroutines.
* **Required Fix:**

```diff
- import socket
+ import asyncio
+ import socket

- def _resolve_hostname(hostname: str) -> list[str]:
-     """Resolve hostname to deduplicated IP list via getaddrinfo."""
-     try:
-         results = socket.getaddrinfo(hostname, None, socket.AF_UNSPEC, socket.SOCK_STREAM)
-     except socket.gaierror as exc:
+ async def _resolve_hostname(hostname: str) -> list[str]:
+     """Resolve hostname to deduplicated IP list via async getaddrinfo."""
+     loop = asyncio.get_running_loop()
+     try:
+         results = await loop.getaddrinfo(hostname, None, family=socket.AF_UNSPEC, type=socket.SOCK_STREAM)
+     except socket.gaierror as exc:
```

This requires making `validate_callback_url` async as well, and updating callers accordingly. The `validate_url` method and tests already operate in async context, so the migration is straightforward.

### 2.2 ✅ No `python-jose` — Confirmed Clean

Verified: no `python-jose` in `pyproject.toml` or imports. Auth uses `Authlib` + `joserfc`.

### 2.3 ✅ No `requests` — Confirmed Clean

Verified: only `httpx.AsyncClient` is used for HTTP calls. No `import requests` in `src/`.

### 2.4 ✅ No Global Mutable State Introduced

The module-level `limiter` in `middleware.py` is replaced per-app via `create_limiter()` and overridden in tests — same pattern as before. `_url_buckets` in `WebhookRetryManager` is instance-scoped, not global.

---

## 3. Red Team Findings (Bugs & Logic)

### 3.1 🔴 `ASAPRateLimiter.check()` — Hit Consumed Even When Rate Limit Exceeded

* **Location:** `src/asap/transport/rate_limit.py:130-147`
* **Attack Vector:** The `check()` method iterates all configured limits and calls `self._strategy.hit()` for each one. `hit()` both tests AND increments the counter. If the first limit (e.g., `10/second`) passes but the second limit (e.g., `100/minute`) is exceeded, the first limit's counter has already been incremented — consuming a hit that should not have been consumed. This causes **double-counting drift** over time.

    Concrete scenario with `10/second;100/minute`:
    1. Client sends request #101 in a minute (should be rejected).
    2. `hit(10/second, key)` → passes, counter +1.
    3. `hit(100/minute, key)` → fails, `RateLimitExceeded` raised.
    4. But the `10/second` window now has a phantom hit.

    Over sustained traffic, this inflates the per-second counter, causing legitimate requests to get 429'd prematurely.

* **Fix Suggestion:**

```diff
  def check(self, request: Request) -> None:
      key = self._key_func(request)
+     # Two-phase check: test all limits first, then hit all if allowed.
+     for rate_limit in self._rate_limits:
+         if not self._strategy.test(rate_limit, key):
+             window_stats = self._strategy.get_window_stats(rate_limit, key)
+             retry_seconds = max(1, int(window_stats[0] - time.time()))
+             raise RateLimitExceeded(
+                 detail=f"Rate limit exceeded: {rate_limit}",
+                 retry_after=retry_seconds,
+                 limit=str(rate_limit),
+             )
+     # All limits pass — now increment all counters atomically.
+     for rate_limit in self._rate_limits:
+         self._strategy.hit(rate_limit, key)
-     max_retry_after = 0
-     exceeded_limit: RateLimitItem | None = None
-     for rate_limit in self._rate_limits:
-         if not self._strategy.hit(rate_limit, key):
-             ...
```

### 3.2 ⚠️ `WebhookDelivery.deliver()` — httpx Client Created Per Call

* **Location:** `src/asap/transport/webhook.py:206-213`
* **Attack Vector:** Each `deliver()` call creates a new `httpx.AsyncClient`, establishes a new connection pool, and tears it down. Under high-frequency webhook delivery (e.g., retry loop sending to the same URL), this wastes TCP connections and adds latency for TLS handshakes.
* **Impact:** Performance degradation under load; not a correctness bug. In the retry path, 6 deliveries (1 + 5 retries) create 6 separate TCP connections.
* **Fix Suggestion:** Accept an optional `httpx.AsyncClient` parameter or hold one at the `WebhookDelivery` instance level.

```diff
  class WebhookDelivery:
      def __init__(self, *, secret=None, timeout_seconds=DEFAULT_WEBHOOK_TIMEOUT,
-                  require_https=True) -> None:
+                  require_https=True, client: httpx.AsyncClient | None = None) -> None:
          self._secret = secret
          self._timeout_seconds = timeout_seconds
          self._require_https = require_https
+         self._client = client  # reuse if provided
```

### 3.3 ⚠️ `WebhookRetryManager._url_buckets` — Unbounded Memory Growth

* **Location:** `src/asap/transport/webhook.py:428-432`
* **Attack Vector:** `_url_buckets` is a `dict[str, _URLTokenBucket]` that grows by one entry per unique URL. If an attacker can register arbitrary callback URLs, this dict grows without bound. In a long-lived process with many unique webhook URLs, this is a slow memory leak.
* **Impact:** Low severity for typical use cases (webhooks usually go to a small set of URLs), but worth capping.
* **Fix Suggestion:** Use `functools.lru_cache` or cap the dict size (e.g., evict LRU after 10,000 entries).

### 3.4 ⚠️ `secure_agent.py` — `asyncio.run()` Inside Sync Function Nested in Event Loop

* **Location:** `src/asap/examples/secure_agent.py:73`
* **Attack Vector:** `_get_jwks_uri()` calls `asyncio.run(discover())` to resolve the JWKS URI from OIDC discovery. If this function is ever called from within an already-running event loop (e.g., in a Jupyter notebook, or from an async framework setup), `asyncio.run()` raises `RuntimeError: This event loop is already running`. Since this is in the server startup path before `uvicorn.run()`, it currently works for the CLI use case but is fragile.
* **Impact:** Example code — low blast radius. But users may copy-paste it into async entrypoints.
* **Fix Suggestion:** Document the limitation or use `asyncio.get_event_loop().run_until_complete()` with a check:

```python
try:
    loop = asyncio.get_running_loop()
    # Already in an event loop — use nest_asyncio or restructure
except RuntimeError:
    return asyncio.run(discover())
```

### 3.5 ✅ Coroutine Leak Fix in `handlers.py` — Good

* **Location:** `src/asap/transport/handlers.py:303-304`
* The addition of `result.close()` before raising `TypeError` for unawaited coroutines in `dispatch()` is the correct fix for the `RuntimeWarning: coroutine was never awaited`. This prevents resource leaks.

### 3.6 ✅ `time.sleep()` Scan — Clean in New Code

Verified: `time.sleep()` only appears in `examples/` (acceptable for demo scripts), `testing/mocks.py` (sync delay mock), `discovery/dnssd.py` (P3, deferred), and `server.py:202` (hot-reload retry, sync context). No `time.sleep` in new webhook or rate limiter code. All async paths correctly use `asyncio.sleep()`.

---

## 4. QA & Test Health

### 4.1 Coverage Gaps

| Source File | Test File | Status |
|:------------|:----------|:-------|
| `src/asap/transport/webhook.py` | `tests/transport/unit/test_webhook.py` (670 LOC, 60 tests) | ✅ Covered |
| `src/asap/transport/rate_limit.py` | `tests/transport/test_middleware.py` + `tests/transport/integration/test_rate_limiting.py` | ✅ Covered |
| `src/asap/transport/middleware.py` | `tests/transport/test_middleware.py` | ✅ Covered |
| `src/asap/transport/server.py` | `tests/transport/test_server.py` | ✅ Covered |
| `src/asap/transport/handlers.py` | `tests/transport/test_handlers.py` | ✅ Covered |
| `src/asap/examples/secure_agent.py` | `tests/examples/` | ⚠️ Example — omitted from coverage |
| `src/asap/errors.py` (`WebhookURLValidationError`) | `tests/transport/unit/test_webhook.py` | ✅ Implicitly covered |

**Gap**: The `ASAPRateLimiter.check()` double-counting bug (§3.1) does not have a test that exercises multi-limit scenarios with boundary conditions. Existing rate limiting integration tests use single limits.

### 4.2 Fixture & Async Hygiene

| Check | Result |
|:------|:-------|
| `isolated_limiter_factory` usage | ✅ All transport tests use it correctly (via `tests/transport/conftest.py`) |
| `create_test_limiter` adoption | ✅ Migrated from slowapi `Limiter` to `ASAPRateLimiter` in conftest, benchmarks, contract tests |
| Rate limiter isolation | ✅ Unique `memory://` URI per test instance via `uuid.uuid4().hex` |
| `asyncio_mode = "auto"` | ✅ Consistent |
| Websocket deprecation warnings | ✅ Suppressed in `pyproject.toml` filterwarnings (acceptable for v1.1) |

### 4.3 Architecture Compliance

| Interface | Implementation | Compliant |
|:----------|:---------------|:----------|
| Rate limiter (replaces slowapi) | `ASAPRateLimiter` with `limits` package | ✅ |
| `RateLimitExceeded` exception | Drop-in replacement with same attributes | ✅ |
| `create_limiter()` / `create_test_limiter()` | Factory functions preserved | ✅ |
| Webhook security model | SSRF validation + HMAC-SHA256 | ✅ |
| `SnapshotStore` protocol | Not touched in this PR | N/A |

### Verification Command

```bash
uv run pytest tests/transport/unit/test_webhook.py tests/transport/integration/test_rate_limiting.py tests/transport/test_middleware.py tests/transport/test_server.py tests/chaos/test_websocket_stability.py -v
```

---

## 5. Refactoring & Nitpicks

### 5.1 `typing.Optional` → Union Syntax

`webhook.py` inconsistently uses `Optional[str]` (old-style) and `dict[str, str] | None` (PEP 604). Since `from __future__ import annotations` is present and the target is Python 3.13+, prefer `| None` everywhere.

* **Files:** `webhook.py:29` (`Optional`), lines 172, 182, 206

### 5.2 `WebhookResult` — Consider Pydantic `BaseModel`

`WebhookResult` and `RetryPolicy` are plain `dataclass` instances. Given the project standardizes on Pydantic v2, consider using `BaseModel` for consistency and automatic serialization if these will ever be exposed via API endpoints. However, the `frozen=True, slots=True` dataclass pattern is performant and acceptable for internal-only types. **Non-blocking.**

### 5.3 `DeadLetterEntry.created_at` Uses `time.monotonic()` — Not Serializable

* **Location:** `webhook.py:320`
* `time.monotonic()` returns an arbitrary float relative to process start. If `DeadLetterEntry` is logged or inspected for debugging, `created_at` is meaningless across restarts. Consider `time.time()` or `datetime.now(UTC)` for human-readable timestamps.

### 5.4 Coverage Omit Broadened

`pyproject.toml` changed coverage omit from two specific files to `src/asap/examples/*`. This is intentional for v1.1 (examples are tested via `tests/examples/`), but drops coverage visibility for all example code. **Acceptable, just noting.**

### 5.5 Module-Level `limiter` in `middleware.py`

The module-level `limiter = create_limiter(key_func=_get_sender_from_envelope)` (line ~119) is still instantiated at import time and emits a `logger.warning` for memory storage. Since `create_app()` overrides it immediately, this import-time instantiation is wasted work and produces a spurious warning. Consider making it lazy or removing the module-level instance entirely.

---

## 6. Summary Verdict

| Finding | Severity | Status |
|:--------|:---------|:-------|
| §2.1 Blocking `socket.getaddrinfo` in async path | 🔴 Critical | ✅ **Resolved** — migrated to `loop.getaddrinfo` |
| §3.1 `ASAPRateLimiter.check()` double-counting | 🔴 Critical | ✅ **Resolved** — two-phase test-then-hit |
| §3.2 httpx client per delivery call | ⚠️ Medium | ✅ **Resolved** — optional `client` param |
| §3.3 `_url_buckets` unbounded growth | ⚠️ Low | ✅ **Resolved** — capped at 10k with FIFO eviction |
| §3.4 `asyncio.run()` in example | ⚠️ Low | ✅ **Resolved** — active-loop detection |
| §5.1 `Optional[X]` → `X \| None` | Nitpick | ✅ **Resolved** |
| §5.3 `DeadLetterEntry.created_at` monotonic | ⚠️ Low | ✅ **Resolved** — `time.time()` |
| §5.5 Module-level limiter instantiation | ⚠️ Low | ✅ **Resolved** — lazy `_get_default_limiter()` |

**All blocking and non-blocking findings have been resolved.** ✅ Ready to merge.

---

## 7. Resolution Log

| § | File | Fix Applied |
|:--|:-----|:------------|
| 2.1 | `webhook.py` | `_resolve_hostname()` → `async` via `loop.getaddrinfo`; `validate_callback_url()` and `WebhookDelivery.validate_url()` made async; all 60+ tests updated |
| 3.1 | `rate_limit.py` | `check()` refactored to two-phase: `test()` all limits first, `hit()` all only if all pass |
| 3.2 | `webhook.py` | `WebhookDelivery.__init__` accepts optional `client: httpx.AsyncClient`; reuses if provided, falls back to per-call client |
| 3.3 | `webhook.py` | `_url_buckets` capped at `self._max_buckets = 10_000`; oldest entry evicted with logged warning |
| 3.4 | `secure_agent.py` | `_get_jwks_uri()` detects active event loop; uses `ThreadPoolExecutor` + `asyncio.run` as fallback |
| 5.1 | `webhook.py` | All `Optional[X]` → `X \| None`; removed `from typing import Optional` |
| 5.3 | `webhook.py` | `DeadLetterEntry.created_at` default changed from `time.monotonic` to `time.time` |
| 5.5 | `middleware.py` | Module-level `limiter` → `None`; lazy init via `_get_default_limiter()` to avoid import-time side effects |

### Verification

```
uv run pytest tests/ -q --ignore=tests/chaos --ignore=tests/deepeval
1718 passed, 6 skipped, 4 warnings in 72s
```

All 6 skips are intentional conditional skips:
- `test_dnssd.py` — `zeroconf` optional extra not installed (`uv sync --extra dns-sd`)
- `test_jaeger_tracing.py` — Docker not available (CI/integration only)
- `test_compression.py` ×3 + `test_compression_server.py` ×1 — "brotli unavailable" error paths skipped because brotli IS installed
