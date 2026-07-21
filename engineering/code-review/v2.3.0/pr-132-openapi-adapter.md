# Code Review: PR #132 — `feat(openapi): OpenAPI 3.x adapter`

> **Reviewer**: Maintainer review
> **PR**: [#132](https://github.com/adriannoes/asap-protocol/pull/132)
> **Branch**: `feat/openapi-adapter-python` → `main`
> **Sprint**: [S1 — OpenAPI Adapter](../../../engineering/tasks/v2.3.0/sprint-S1-openapi-adapter.md)
> **Date**: 2026-05-01
> **Re-review**: 2026-05-01 (post-fixes)

---

## ✅ Review Status: APPROVED

All Required Fixes (RF-1 through RF-3) and Improvements (IMP-1 through IMP-6) have been verified locally. **82/82 tests passing** in 0.36s.

---

## 1. Executive Summary

| Category | Status | Summary |
| :--- | :--- | :--- |
| **Tech Stack** | ✅ | Correct dependencies, Pydantic v2, optional extras — all per tech-stack-decisions.md |
| **Architecture** | ✅ | Clean adapter module boundary, handler registry pattern, no monolith expansion |
| **Security** | ✅ | Async I/O fixed; `resolve_headers` validated; upstream error body leakage mitigated |
| **Tests** | ✅ | 82 tests across 5 test files; comprehensive unit + integration + E2E coverage |
| **Observability** | ✅ | Structured logging across all 4 adapter modules |

---

## 2. Required Fixes — Re-verification

### RF-1: Synchronous File I/O in Async Path ✅ FIXED

**File:** [spec_loader.py](file:///Users/adrianno/GitHub/asap-protocol/src/asap/adapters/openapi/spec_loader.py#L61-L83)

**Implementation:** `_load_json_from_path()` is now `async def` and delegates all filesystem operations (`is_file()`, `read_text()`, `json.loads()`) to a nested `_sync_load()` function called via `asyncio.to_thread()`. This was the zero-dependency approach recommended in the review.

```python
async def _load_json_from_path(path: Path) -> dict[str, Any]:
    """Read a local spec without blocking the event loop (filesystem + decode in worker thread)."""
    def _sync_load() -> dict[str, Any]:
        ...
    try:
        return await asyncio.to_thread(_sync_load)
    except OpenAPISpecError as exc:
        logger.error("OpenAPI spec load from path failed path=%s: %s", path, exc)
        raise
```

**Verdict:** Clean implementation. Error handling preserves the original `OpenAPISpecError` chain while adding a log point.

---

### RF-2: Missing Structured Logging ✅ FIXED

**Files:** All 4 adapter modules now have `logger = logging.getLogger(__name__)`:

| Module | Logger | Key log points |
| :--- | :--- | :--- |
| [spec_loader.py](file:///Users/adrianno/GitHub/asap-protocol/src/asap/adapters/openapi/spec_loader.py#L22) | ✅ L22 | HTTP fetch errors (ERROR), version/parse errors (ERROR), load start (DEBUG), load complete (INFO) |
| [handler.py](file:///Users/adrianno/GitHub/asap-protocol/src/asap/adapters/openapi/handler.py#L28) | ✅ L28 | Upstream connection errors (WARNING), 5xx (WARNING), 4xx (ERROR) |
| [factory.py](file:///Users/adrianno/GitHub/asap-protocol/src/asap/adapters/openapi/factory.py#L30) | ✅ L30 | Capabilities mapped count (INFO) |
| [capability_mapper.py](file:///Users/adrianno/GitHub/asap-protocol/src/asap/adapters/openapi/capability_mapper.py#L14) | ✅ L14 | `$ref` depth limit hit (DEBUG), capabilities produced count (DEBUG) |

**Verdict:** Appropriate log levels — operators will see WARNINGs for transient upstream issues and ERRORs for client errors, without DEBUG noise in production.

---

### RF-3: Missing `create_from_openapi` Re-export ✅ FIXED

**File:** [src/asap/\_\_init\_\_.py](file:///Users/adrianno/GitHub/asap-protocol/src/asap/__init__.py)

```python
def __getattr__(name: str) -> Any:
    if name == "create_from_openapi":
        from asap.adapters.openapi import create_from_openapi as exported
        return exported
    msg = f"module {__name__!r} has no attribute {name!r}"
    raise AttributeError(msg)
```

**Test:** [test_factory.py::test_asap_package_lazy_exports_create_from_openapi](file:///Users/adrianno/GitHub/asap-protocol/tests/adapters/openapi/test_factory.py#L210-L214) — verifies `asap.create_from_openapi is create_from_openapi`.

**Verdict:** Lazy `__getattr__` avoids importing `openapi-pydantic` for users without the `[openapi]` extra. Exactly as recommended.

---

## 3. Improvements — Re-verification

### IMP-1: Silent `**kwargs` Swallowing ✅ FIXED

**File:** [factory.py](file:///Users/adrianno/GitHub/asap-protocol/src/asap/adapters/openapi/factory.py#L169-L178)

Now filters kwargs against `_KNOWN_CREATE_FROM_OPENAPI_KEYS` frozenset and emits `UserWarning` for unrecognized keys:

```python
remainder = dict(kwargs)
for _key in _KNOWN_CREATE_FROM_OPENAPI_KEYS:
    remainder.pop(_key, None)
if remainder:
    warnings.warn(
        "create_from_openapi ignored unexpected keyword arguments: "
        + ", ".join(sorted(remainder)),
        UserWarning,
        stacklevel=2,
    )
```

**Test:** [test_factory.py::test_kwargs_unknown_keys_emit_warning](file:///Users/adrianno/GitHub/asap-protocol/tests/adapters/openapi/test_factory.py#L188-L207) — uses `pytest.warns(UserWarning, ...)`.

---

### IMP-2: Test Fixture Cleanup Pattern ✅ FIXED

**File:** [conftest.py](file:///Users/adrianno/GitHub/asap-protocol/tests/adapters/openapi/conftest.py)

Introduced shared `tmp_openapi_spec()` context manager using `pytest`'s `tmp_path` fixture. All test files (`test_handler.py`, `test_capability_mapper.py`) refactored to use `with tmp_openapi_spec(tmp_path, raw, name) as path:` instead of manual `_write_tmp` + `try/finally/unlink`.

**Verdict:** Clean DRY pattern. Old `_FIXTURES` directory no longer gets polluted with temp files.

---

### IMP-3: Excessive `cast()` Usage Comment ✅ FIXED

**File:** [capability_mapper.py](file:///Users/adrianno/GitHub/asap-protocol/src/asap/adapters/openapi/capability_mapper.py#L16-L18)

Added explanatory comment at module level:

```python
# ``cast(...)`` usages below compensate for incomplete / structural typing from
# openapi-pydantic stubs: paths, responses, headers, and parameters are modeled
# as generic objects at compile time though runtime layout matches OpenAPI 3.x.
```

**Verdict:** Documents the technical debt clearly for future contributors.

---

### IMP-4: `$ref` Recursion Depth Guard ✅ FIXED

**File:** [capability_mapper.py](file:///Users/adrianno/GitHub/asap-protocol/src/asap/adapters/openapi/capability_mapper.py#L128-L149)

`expand_refs()` now takes a `depth: int = 0` parameter with a limit of 50:

```python
def expand_refs(self, node: Any, seen: frozenset[str], depth: int = 0) -> Any:
    if depth > 50:
        logger.debug("OpenAPI schema $ref expansion stopped at depth %s ...", depth)
        return node
    next_depth = depth + 1
    ...
```

**Test:** `test_expand_refs_depth_returns_early_without_error_on_deep_trees` — PASSED ✅

**Verdict:** Graceful degradation for deeply nested schemas (e.g., Stripe's API spec) without crashing with `RecursionError`.

---

### IMP-5: `session=None` in Task Handler ✅ DOCUMENTED

**File:** [handler.py](file:///Users/adrianno/GitHub/asap-protocol/src/asap/adapters/openapi/handler.py#L472-L478)

Documented as a known limitation with a clear future-work pointer:

```python
def create_openapi_task_handler(upstream: OpenAPIUpstreamHandler) -> AsyncHandler:
    """Build an async ``task.request`` handler that proxies to *upstream*.

    The nested ``openapi_task_request_handler`` always passes ``session=None`` into
    :meth:`OpenAPIUpstreamHandler.execute` today. OA-009 header resolution from Host-held
    context likely needs envelope- or TaskRequest-level session wiring in a future change.
    """
```

**Verdict:** Acceptable — documenting the limitation is the right call for v2.3.0; wiring session extraction from envelope context can be a v2.3.x follow-up.

---

### IMP-6: Path Parameter Value Validation ✅ FIXED

**File:** [handler.py](file:///Users/adrianno/GitHub/asap-protocol/src/asap/adapters/openapi/handler.py#L281-L299)

`_fill_path_template()` now validates path parameter values after checking for missing ones:

```python
invalid_names = [
    n for n in names_order
    if path_params[n] is None
    or (isinstance(path_params[n], str) and cast(str, path_params[n]).strip() == "")
]
if invalid_names:
    raise OpenAPIPathParameterError(path_template=path_template, invalid=invalid_names)
```

`OpenAPIPathParameterError` was also extended to support both `missing=` and `invalid=` modes with mutually exclusive constructor validation.

**Tests (3 new):**
- `test_execute_empty_path_parameter_string_raises` — ✅
- `test_execute_whitespace_only_path_parameter_raises` — ✅
- `test_execute_none_path_parameter_raises` — ✅

---

## 4. Security Fix — Re-verification

### §5.3: Upstream Error Body Leakage ✅ FIXED

**File:** [handler.py](file:///Users/adrianno/GitHub/asap-protocol/src/asap/adapters/openapi/handler.py#L407-L446)

| HTTP Status | Before | After |
| :--- | :--- | :--- |
| **5xx** | `body_snippet` = first 500 chars exposed to caller | `body_snippet` **removed** from details dict; logged server-side only |
| **4xx** | `body_snippet` = first 500 chars | Truncated to **200 chars** (`_UPSTREAM_CLIENT_ERROR_BODY_MAX_LEN`) |

Constants and inline comments explain the rationale:

```python
# Bound upstream HTTP error payloads copied into FatalError/RecoverableError details to
# reduce accidental leakage of large or sensitive bodies (prefer server logs for triage).
_UPSTREAM_CLIENT_ERROR_BODY_MAX_LEN = 200
```

**Tests:**
- `test_execute_upstream_502_is_recoverable` — now asserts `"body_snippet" not in exc_info.value.details` ✅
- `test_execute_upstream_404_is_fatal` — now asserts `len(snippet) <= 200` ✅

---

## 5. Test Run Results

```
tests/adapters/openapi/ — 82 passed in 0.36s
```

| Test File | Count | Status |
| :--- | :--- | :--- |
| `test_approval.py` | 4 | ✅ All passed |
| `test_capability_mapper.py` | 22 | ✅ All passed |
| `test_factory.py` | 10 | ✅ All passed |
| `test_handler.py` | 26 | ✅ All passed |
| `test_spec_loader.py` | 20 | ✅ All passed |

---

## 6. Final Verdict

**✅ APPROVED — Ready to merge.**

All 3 Required Fixes, 6 Improvements, and the security mitigation have been verified in the local codebase with passing tests. The code is clean, well-documented, and architecturally sound. Push the local changes to the branch and merge when CI is green.
