# Upstream: slowapi Deprecation Warning

## Context

ASAP protocol uses **slowapi** for rate limiting (IP-based, `ASAP_RATE_LIMIT` env, `create_limiter`, `RateLimitExceeded`). On Python 3.14+, slowapi triggers:

```text
DeprecationWarning: 'asyncio.iscoroutinefunction' is deprecated and slated for removal in Python 3.16; use inspect.iscoroutinefunction() instead
```

**Location:** `slowapi/extension.py` (around line 717).

**Fix:** Replace `asyncio.iscoroutinefunction(func)` with `inspect.iscoroutinefunction(func)` and add `import inspect`.

---

## Need for ASAP Protocol

- **Dependency:** `slowapi>=0.1.9` (pyproject.toml).
- **Usage:** `src/asap/transport/middleware.py` (Limiter, create_limiter, rate_limit_handler); `src/asap/transport/server.py` (limiter on POST /asap).
- **Impact:** Test runs show the deprecation warning when hitting the /asap endpoint (e.g. `TestDebugLogMode`). We added a pytest filter to ignore this warning until slowapi releases a fix.

---

## Decision (ASAP protocol)

- **Keep slowapi:** Continue using slowapi for rate limiting; no switch to another library.
- **Workaround:** Pytest filter in `pyproject.toml` ignores `DeprecationWarning` from `slowapi.extension` so test output stays clean.
- **Upstream:** No new issue opened in the slowapi repo — the fix is already proposed in open PR #246; we track that PR and will bump the dependency when a release includes the fix.

---

## Upstream Status (checked 2025-01-31)

**No new issue was opened** — the problem is already reported and has open/closed PRs:

| Type | Number | Title | State | Link |
|------|--------|--------|--------|------|
| PR | **246** | Switch from asyncio to inspect for iscoroutinefunction to fix deprecation warning | **Open** | https://github.com/laurentS/slowapi/pull/246 |
| PR | 248 | Fix: Replace deprecated asyncio.iscoroutinefunction with inspect.iscoroutinefunction | Closed (not merged) | https://github.com/laurentS/slowapi/pull/248 |

**Recommendation:** Track **PR #246** (open, 5 +1 reactions). When it is merged and a new slowapi version is released, bump the dependency (e.g. `slowapi>=0.1.10` or whatever version includes the fix) and remove the pytest filter in `pyproject.toml`:

```toml
filterwarnings = [
    "ignore::DeprecationWarning:slowapi.extension",
]
```

---

## References

- Python deprecation: [Pending removal in Python 3.16](https://docs.python.org/3/library/deprecation.html) — use `inspect.iscoroutinefunction()` instead of `asyncio.iscoroutinefunction()`.
- slowapi repo: https://github.com/laurentS/slowapi
