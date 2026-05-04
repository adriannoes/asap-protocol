# Code Review: PR #134

> `feat(registry): auto-registration, registry-bot, and CI auto-merge`
> Branch: `feat/auto-registration` → `main`
> Sprint: S3 (AUTO-001..007)

## 1. Executive Summary

| Category | Status | Summary |
| :--- | :--- | :--- |
| **Tech Stack** | ✅ | Pydantic v2, FastAPI, httpx, asyncio — all aligned. No banned dependencies. |
| **Architecture** | ✅ | Clean DI via `AutoRegistrationConfig` (now a `@dataclass`). Bot PR adds label. Receipt cache bounded. |
| **Security** | ✅ | SSRF guards, HTTPS enforcement, opaque 502 errors, TTL-bounded cache. |
| **Tests** | ✅ | 55 tests, all passing. Label assertion, rate limit with unique URLs, TTL cache unit tests. |

---

## 2. Required Fixes — Verification

### 2.1 ✅ Bot PR Now Adds the `auto-registration` Label

**Status:** Resolved

**Implementation:**
- New constant `AUTO_REGISTRATION_PR_LABEL = "auto-registration"` at module level (L31).
- New function `_github_add_auto_registration_label()` (L253-273) handles the POST to `/repos/{owner}/{repo}/issues/{number}/labels`.
- `_github_create_pull_request()` now extracts `number` from the PR creation response (L312-314) and calls the label function (L315-319).
- **Test coverage:** `test_github_create_pull_request_success` (L122-148) uses `MockTransport` to verify both the PR creation and the label endpoint are called. The handler asserts the label payload contains `"auto-registration"` and the test asserts `/issues/42/labels` appeared in the request log.
- **Edge case:** `test_github_create_pull_response_without_number_raises` (L203-218) verifies that a missing `number` in the API response raises `RuntimeError`.

**Quality:** ✅ Excellent. Proper separation of concerns, explicit assertion on the label payload, and edge-case coverage for malformed GitHub API responses.

---

### 2.2 ✅ Shared Mutable `VerificationStatus` Instance Fixed

**Status:** Resolved

**Implementation:** `anti_spam.py:20` now returns `DEFAULT_AUTO_REGISTER_VERIFICATION.model_copy()` — each call produces a fresh instance.

**Minor note:** The line currently reads `.model_copy().model_copy()` (double call). This is functionally correct (Pydantic v2 `model_copy()` is a shallow copy, and `VerificationStatus` has no nested mutable fields), so this is safe but redundant. A single `.model_copy()` would be sufficient. **Not a blocker — cosmetic only.**

---

### 2.3 ✅ Error Message No Longer Leaks Internal Details

**Status:** Resolved

**Implementation:** `auto_registration.py:260-265`:
```python
except Exception:
    logger.exception("registry.bot_pr_failed")
    raise HTTPException(
        status_code=502,
        detail="Pull request flow failed. Check server logs for details.",
    ) from None
```
- The `from None` suppresses exception chaining in the HTTP response.
- **Test coverage:** `test_register_agent_pr_unexpected_error_502` (L586-621) explicitly asserts:
  - `detail == "Pull request flow failed. Check server logs for details."`
  - `"github unavailable" not in detail` — confirming internal error strings are not leaked.

**Quality:** ✅ Exact match on the review suggestion.

---

## 3. Improvements — Verification

### 4.1 ✅ Bounded TTL Receipt Cache

**Status:** Resolved — **went beyond the suggestion**.

**Implementation:** New module `asap.registry.receipt_cache` with `RegistrationReceiptTTLCache`:
- Implements `MutableMapping[str, V]` (so it's a drop-in replacement for `dict`).
- LRU eviction with configurable `maxsize` (default: 10,000).
- TTL-based expiry with `time.monotonic()` (monotonic clock — correct for cache timing).
- Lazy front-of-queue expiry on reads and writes.
- Factory `create_registration_receipt_cache()` used in `server.py:1892-1895`.
- **4 dedicated unit tests** in `test_receipt_cache.py`: basic set/get, expiry, eviction, factory.

**Quality:** ✅ Production-grade. Custom implementation avoids adding `cachetools` as a dependency, consistent with the project's "lean dependency" policy. `__slots__` for memory efficiency. Type-parameterized (`V`).

---

### 4.2 ✅ `AutoRegistrationConfig` Converted to `@dataclass`

**Status:** Resolved

**Implementation:** `auto_registration.py:34` now uses `@dataclass` instead of a plain class with manual `__init__`. All fields have type annotations and default values.

**Quality:** ✅ Clean and consistent with `BotPRSettings` and other config objects in the codebase.

---

### 4.3 ✅ `sys.path` Hack Removed from Merge Eligibility Script

**Status:** Resolved

**Implementation:** `check_auto_registration_merge_eligible.py` no longer has `sys.path.insert`. It imports `asap.*` directly, relying on `uv run` (which the CI workflow uses). The docstring at L15 documents this: `"Run from the repo root with uv run python scripts/..."`.

**Quality:** ✅ Clean.

---

### 4.4 ✅ `subprocess.run` Timeout Guards Added

**Status:** Resolved

**Implementation:** Module-level constant `_GIT_SUBPROCESS_TIMEOUT_SEC = 120` (L33). All 5 `subprocess.run` calls in `bot_pr.py` now include `timeout=_GIT_SUBPROCESS_TIMEOUT_SEC`:
- `git clone` (L175)
- `git checkout -b` (L182)
- `git add` (L121)
- `git commit` (L135)
- `git push` (L153)

**Quality:** ✅ Centralized constant, no magic numbers.

---

### 4.5 ✅ Tighter Typing for `oauth_claims_dependency`

**Status:** Resolved

**Implementation:** `auto_registration.py:39-41`:
```python
oauth_claims_dependency: (
    Callable[..., OAuth2Claims | Awaitable[OAuth2Claims]] | None
) = None
```

**Quality:** ✅ Same pattern applied to `run_compliance` (L42) and `open_pull_request` (L43-44).

---

### 4.6 ✅ Rate Limit Test Uses Unique Manifest URLs

**Status:** Resolved

**Implementation:** `test_registration_rate_limit_sixth_request_429` (L222-231):
```python
for i in range(5):
    body = {"manifest_url": f"https://example.org/rate-m{i}.json"}
    r = client.post("/registry/agents", json=body, headers=headers)
    assert r.status_code == 200, f"iteration {i}"
r6 = client.post(
    "/registry/agents",
    json={"manifest_url": "https://example.org/rate-m5.json"},
    headers=headers,
)
assert r6.status_code == 429
```

**Quality:** ✅ Each iteration uses a unique URL, ensuring all 5 pass through the rate limiter (no idempotency cache bypass).

---

## 4. Verification Results

```
tests/registry/  55 passed in 0.46s  ✅
mypy:            0 issues (5 files)  ✅
ruff:            All checks passed   ✅
```

## 5. Final Verdict

**All 3 Required Fixes and all 6 Recommended Improvements have been addressed.** The implementation quality is consistently high — each fix follows the review suggestion closely or improves upon it (the custom TTL cache is a notably thorough solution to the unbounded cache issue).

One cosmetic observation: `anti_spam.py:20` calls `.model_copy().model_copy()` (double copy). A single `.model_copy()` is sufficient. Not a blocker.

**Status: ✅ Approved for merge.**
