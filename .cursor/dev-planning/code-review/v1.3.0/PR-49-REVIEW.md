# Code Review: PR #49

> **PR**: [feat(economics): Sprint E2 — Delegation tokens (model, API, revocation, observability)](https://github.com/adriannoes/asap-protocol/pull/49)
> **Branch**: `feat/e2-delegation-tokens` → `main`
> **Sprint**: [E2 — Delegation Tokens](../../tasks/v1.3.0/sprint-E2-delegation-tokens.md)
> **Reviewed**: 2026-02-17

---

## 1. Executive Summary

| Category | Status | Summary |
| :--- | :--- | :--- |
| **Tech Stack** | ✅ | Correct use of `joserfc` (EdDSA), `aiosqlite`, Pydantic v2, `ASAPBaseModel`. No violations. |
| **Architecture** | ✅ | Clean layer separation: economics → transport → server wiring. Protocol pattern used for `DelegationStorage`. |
| **Security** | ⚠️ | Ed25519 correctly enforced. Two issues: `revoke_cascade` unbounded recursion, and `hasattr` dispatch for cascade is fragile. |
| **Tests** | ✅ | Excellent coverage across all three layers (566 + 203 + 636 lines). Tests cover happy/unhappy paths, access control, cascade, persistence. |

> **General Feedback:** Very solid sprint delivery. The JWT-based delegation design is well-aligned with the protocol stack and the code is clean. The main issues are a potential stack overflow in cascade revocation and several opportunities to reduce redundant DB connections in the SQLite storage layer.

---

## 2. Required Fixes (Must Address Before Merge)

### RF-1: `revoke_cascade` is vulnerable to unbounded recursion (stack overflow / DoS)

*   **Location:** `src/asap/economics/delegation_storage.py:93-103`
*   **Problem:** `revoke_cascade` recurses without any depth limit. A malicious or misconfigured delegation chain (A→B→C→…→Z→A, or simply a very deep chain) will cause a `RecursionError`. Since this is invoked by an authenticated API endpoint (`DELETE /asap/delegations/{id}`), it's a potential denial-of-service vector.
*   **Fix Suggestion:** Use an iterative BFS/DFS with a visited set and a configurable depth limit.

    ```python
    async def revoke_cascade(
        self,
        token_id: str,
        reason: str | None = None,
        *,
        _max_depth: int = 50,
    ) -> None:
        visited: set[str] = set()
        stack: list[tuple[str, int]] = [(token_id, 0)]
        while stack:
            tid, depth = stack.pop()
            if tid in visited or depth > _max_depth:
                continue
            visited.add(tid)
            delegate_urn = await self.get_delegate(tid)
            if delegate_urn:
                child_ids = await self.list_token_ids_issued_by(delegate_urn)
                for child_id in child_ids:
                    stack.append((child_id, depth + 1))
            await self.revoke(tid, reason)
    ```

### RF-2: `hasattr` dispatch for `revoke_cascade` in API layer is fragile

*   **Location:** `src/asap/transport/delegation_api.py:193-196`
*   **Problem:** The delete handler uses `hasattr(storage, "revoke_cascade")` to decide whether to cascade. This is a duck-typing check that bypasses the `DelegationStorage` Protocol entirely. Since both concrete implementations (`InMemoryDelegationStorage`, `SQLiteDelegationStorage`) inherit from `DelegationStorageBase` which defines `revoke_cascade`, and the `DelegationStorage` Protocol does **not** include `revoke_cascade`, the Protocol's contract is incomplete. A third-party implementation satisfying the Protocol would silently skip cascade.
*   **Fix Suggestion:** Either add `revoke_cascade` to the `DelegationStorage` Protocol, or (simpler) always call `revoke_cascade` since `DelegationStorageBase` guarantees it:

    ```python
    # Option A: Add to Protocol (preferred — makes cascade a first-class operation)
    @runtime_checkable
    class DelegationStorage(Protocol):
        ...
        async def revoke_cascade(
            self, token_id: str, reason: str | None = None,
        ) -> None: ...

    # Then in delegation_api.py:
    await storage.revoke_cascade(token_id)
    ```

### RF-3: Redundant `_ensure_tables` call on every SQLite operation

*   **Location:** `src/asap/economics/delegation_storage.py` — every async method (L222, L234, L252, L264, L276, L288, L308, L329, L341)
*   **Problem:** Every single method opens a new connection (`aiosqlite.connect`) and calls `_ensure_tables`. This means every `is_revoked`, `get_delegator`, etc. call runs `CREATE TABLE IF NOT EXISTS` + `CREATE INDEX IF NOT EXISTS` + `PRAGMA table_info` + potential `ALTER TABLE`. This is expensive and redundant after first use. In the `list_delegations` endpoint, `list_issued_summaries` + N × `is_revoked` calls will cause N+1 connection opens + N+1 schema checks.
*   **Fix Suggestion:** Use a one-time initialization flag (same pattern as `SQLiteMeteringStorage` from Sprint E1):

    ```python
    class SQLiteDelegationStorage(DelegationStorageBase):
        def __init__(self, db_path: str | Path = _DEFAULT_DB_PATH) -> None:
            self._db_path = Path(db_path)
            self._initialized = False

        async def _ensure_tables(self, conn: aiosqlite.Connection) -> None:
            if self._initialized:
                return
            # ... existing CREATE TABLE logic ...
            self._initialized = True
    ```

    > Additionally, consider reusing a single connection across operations within one request lifecycle, or pooling — but the flag alone addresses the critical performance concern.

---

## 3. Tech-Specific Bug Hunt (Deep Dive)

*   [x] **No mutable default arguments** — All `list` and `dict` parameters use `Field(default_factory=...)` or explicit `None`. Clean.
*   [x] **No `assert` for validation** — All validation uses Pydantic validators or explicit checks. Clean.
*   [x] **`asyncio.gather` usage (good!)** — `delegation_api.py:211` correctly uses `asyncio.gather` for batching `is_revoked` checks. Well done.
*   [ ] **`asyncio.run()` in CLI revoke command** — `cli.py:256` uses `asyncio.run()` inside a Typer command, which is correct for CLI (sync entrypoint). However, this creates a new event loop. Fine for CLI; just noting it is intentional.
*   [x] **No `create_task()` without reference** — No orphaned tasks found. Clean.
*   [x] **SQL uses bind variables** — All SQL in `delegation_storage.py` uses parameterized queries (`VALUES (?, ?, ?)`). No injection risk. Clean.
*   [x] **`app.dependency_overrides` cleanup** — No test overrides used; tests construct fresh apps. Clean.

---

## 4. Improvements & Refactoring (Highly Recommended)

### IMP-1: N+1 DB connections in `list_delegations` and `get_delegation` API endpoints

*   **Location:** `delegation_api.py:208-222` and `delegation_api.py:229-258`
*   **Suggestion:** The `list_delegations` handler calls `list_issued_summaries` (1 connection) then `asyncio.gather(is_revoked(s.id) for s in summaries)` — each `is_revoked` opens a **new** SQLite connection. For 50 delegations, that's 51 connections opened and closed. Same for `get_delegation` which calls `get_delegator` + `get_delegate` + `get_issued_at` + `is_revoked` + `get_revoked_at` = up to 5 separate connections.
*   **Fix:** Consider adding a batch method `are_revoked(token_ids: list[str]) -> dict[str, bool]` and a combined `get_token_details(token_id) -> TokenDetails | None` to reduce connection overhead. This is especially important since SQLite contention can cause locking issues under concurrent requests.

### IMP-2: `DelegationTokenSummary` and `DelegationTokenDetail` use `BaseModel` instead of `ASAPBaseModel`

*   **Location:** `delegation_api.py:45-63`
*   **Suggestion:** The rest of the codebase uses `ASAPBaseModel` (which sets `extra="forbid"` and other project-wide config). While these models do manually set `ConfigDict(extra="forbid")`, using `ASAPBaseModel` would be more consistent and future-proof (any project-wide config changes propagate automatically).

### IMP-3: `created_at` stored as `str` in response models instead of `datetime`

*   **Location:** `delegation_api.py:51, 61`
*   **Suggestion:** `DelegationTokenSummary.created_at` and `DelegationTokenDetail.created_at` are `str` fields. Using `datetime` with Pydantic's auto-serialization would be more type-safe and consistent with the rest of the codebase (e.g., `DelegationConstraints.expires_at` is `datetime`).

### IMP-4: `post_delegation` calls `require_scope` twice

*   **Location:** `delegation_api.py:119-128`
*   **Suggestion:** The route has `dependencies=[Depends(require_scope(SCOPE_EXECUTE))]` (line 122) **and** `claims: OAuth2Claims = Depends(require_scope(SCOPE_EXECUTE))` (line 127). The first runs but its result is discarded; the second runs again to extract claims. FastAPI might cache dependency results within a request for the same callable **instance**, but since `require_scope(SCOPE_EXECUTE)` creates a new closure each time, these are separate dependency evaluations. Use a single `Depends` on the parameter:

    ```python
    @router.post("", status_code=201)
    async def post_delegation(
        request: Request,
        body: CreateDelegationRequest,
        claims: OAuth2Claims = Depends(require_scope(SCOPE_EXECUTE)),
    ) -> JSONResponse:
    ```

    This applies to all four route handlers (`post`, `delete`, `get` list, `get` detail).

### IMP-5: Delegation `create` CLI command doesn't validate `key_file` is readable

*   **Location:** `cli.py:214-215`
*   **Suggestion:** The command only checks `key_file.exists()`. Consider also checking it's a file (not a directory) and has appropriate permissions (not world-readable) — similar to the existing `PRIVATE_KEY_FILE_MODE` constant defined at the top of the CLI module.

---

## 5. Verification Steps

Run the new delegation tests in isolation:

```bash
PYTHONPATH=src uv run pytest tests/economics/test_delegation.py tests/economics/test_delegation_storage.py tests/transport/test_delegation_api.py tests/test_cli.py::TestCliDelegationRevoke -v --tb=short
```

After fixing RF-1 (cascade recursion), add a test for circular chains:

```python
@pytest.mark.asyncio
async def test_revoke_cascade_circular_chain_terminates(memory_storage):
    """Circular delegate chains don't cause infinite recursion."""
    await memory_storage.register_issued("t1", "urn:A", delegate_urn="urn:B")
    await memory_storage.register_issued("t2", "urn:B", delegate_urn="urn:A")
    await memory_storage.revoke_cascade("t1")  # Should not hang or crash
    assert await memory_storage.is_revoked("t1") is True
    assert await memory_storage.is_revoked("t2") is True
```

Full CI check:

```bash
PYTHONPATH=src uv run pytest -n auto --tb=short
uv run ruff check . && ruff format --check . && mypy src/
```
