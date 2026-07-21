# Formal Code Review: v2.4.0 + v2.5.0 Diff (`v2.3.0..HEAD`)

**Review Date:** 2026-06-25
**Reviewer:** Maintainer review
**Diff Range:** `v2.3.0` (commit `96201c6`, 2026-05-06) → `HEAD` (commit `4c367e0`, 2026-06-24)
**Commit Count in Range:** 275 commits (`git log --oneline v2.3.0..HEAD | wc -l`)
**Releases Covered:** v2.4.0 (Edge AI Discovery, tag `v2.4.0` → `d7958d8`, 2026-05-24) and v2.5.0 (MCP Auth Bridge, tag `v2.5.0` → `1c5027c`, 2026-06-24; follow-up `v2.5.0.1` → `0ecb39f`, 2026-06-24)
**Scope of Source Changes:** 29 source files changed, +1040 / −176 (src tree only); 377 files changed overall including tests/docs (+38,325 / −9,197)
**Reference Structure:** `engineering/code-review/v1.3.0/PR-48-REVIEW.md`
**Sprint Cross-Reference:** `engineering/tasks/private/v2.5.1/sprint-S0-p0-correctness-security.md`

---

## Executive Summary

Two production releases — **v2.4.0 (Edge AI Discovery)** and **v2.5.0 (MCP Auth Bridge)** — shipped on `main` without a recorded formal code review (the last review in `engineering/code-review/` is `v2.3.0/`). This review retrospectively covers the `v2.3.0..HEAD` diff and records the resolution status of the correctness/security defects uncovered by the v2.5.1 code-quality patch bug-hunt (Sprint S0, bugs B1–B6).

The diff is broadly well-structured: the v2.4.0 edge/hardware manifest extension is additive and backward-compatible (all new manifest fields are optional), and the v2.5.0 MCP Auth Bridge is a clean opt-in adapter layer (`protect_server`) that reuses the canonical `verify_agent_jwt`/`verify_host_jwt` verifiers and the existing `CapabilityRegistry` grant machinery. JWT claim validation was correctly centralized into `asap/auth/claims.py` and threaded into both `OAuth2Middleware` and `validate_jwt` (iss/aud enforcement that was previously missing).

However, the review confirms **six P0 defects** (B1–B6) that span the v2.4.0/v2.5.0 range — three of them security-relevant (B3 revoked-host bypass, B4 WebSocket OAuth2 bypass, B1 non-atomic cascade revocation). All six are identified and scheduled for remediation in Sprint S0 with a failing-test-first policy. Two additional findings (M-1, M-2) are recorded below that are not in the S0 list but surfaced during this read.

| Severity | Count | Notes |
|----------|-------|-------|
| 🔴 CRITICAL | 3 | B3 (revoked-host bypass), B4 (WS OAuth2 bypass), B1 (non-atomic cascade + missing InMemory lock) |
| 🟠 HIGH | 2 | B6 (client correlation_id not bound), B2 (divergent usage_events DDL) |
| 🟡 MEDIUM | 3 | B5 (OpenAPI handler dead path / pre-v2.3.0 carry-over), M-1 (MCP env-JWT fallback posture), M-2 (hide_unauthorized_tools silent no-op) |
| 🔵 LOW / NITPICK | 2 | L-1 (wellknown alias change is behaviorally correct but unflagged for cache impact), L-2 (from_server shallow tool-dict copy) |

> **Verdict:** REQUEST CHANGES — the three Critical findings (B1/B3/B4) are security-relevant and are being remediated in Sprint S0. This review exists to *record* that those defects were present in the shipped v2.4.0/v2.5.0 range and to track their remediation; it does not block any already-shipped release.

---

## 🔴 CRITICAL Findings

### C-1 (S0 B3 / BUG #1): Divergent Host-JWT verifiers — revoked-host bypass on capability routes

**Severity:** CRITICAL (security)
**Location:** `src/asap/transport/capability_routes.py:60-83` vs `src/asap/transport/agent_routes.py:239-282`
**Status:** Identified; **Remediated in S0** (Task 3.0 — unify verifier into `_auth_helpers.py`)

Two independent Host-JWT verifiers exist in the transport package, with divergent strictness:

- `agent_routes._verify_host_bearer_identity` (the strict one) inspects `result.host.status` and rejects with **403** when the host is revoked (`agent_routes.py:278-280`).
- `capability_routes._verify_host_bearer` (the weak one) **omits the host-status check entirely** — it only checks `result.ok` and returns the result (`capability_routes.py:81-83`).

**Evidence** (`capability_routes.py:60-83`):

```60:83:src/asap/transport/capability_routes.py
async def _verify_host_bearer(
    request: Request,
    *,
    jti_replay_cache: JtiReplayCache | None = None,
) -> tuple[JwtVerifyResult | None, JSONResponse | None]:
    """Verify a Host JWT Bearer token."""
    token = bearer_token_from_request(request)
    if not token:
        return None, JSONResponse(
            status_code=401,
            content={"detail": "Authentication required"},
            headers={"WWW-Authenticate": "Bearer"},
        )
    host_store: HostStore = request.app.state.identity_host_store
    audience = request.app.state.identity_jwt_audience
    result = await verify_host_jwt(
        token,
        host_store,
        expected_audience=audience,
        jti_replay_cache=jti_replay_cache,
    )
    if not result.ok:
        return None, JSONResponse(status_code=401, content={"detail": result.error})
    return result, None
```

Contrast with the strict verifier in `agent_routes.py`:

```278:282:src/asap/transport/agent_routes.py
    host = result.host
    if host is not None and host.status == "revoked":
        return None, JSONResponse(status_code=403, content={"detail": "host revoked"})

    return result, None
```

**Impact:** A revoked **host** can still authenticate against capability routes (e.g. `POST /asap/agent/reactivate` routed through `capability_routes`). The existing test `test_reactivate_revoked_agent_returns_403` revokes the **agent**, not the host, so it exercises the agent-status check inside `reactivate_agent` and does **not** cover this gap.

**S0 Remediation (Task 3.0):** Promote a single canonical `verify_host_bearer(request, *, jti_replay_cache, require_active_host=True)` into `src/asap/transport/_auth_helpers.py` (currently only holds `bearer_token_from_request`). Delete both local copies; both route modules import and call the canonical one. A new failing test revokes the **host** and asserts 403 on `/reactivate`. *Status: in progress on `feat/v2.5.1-s0-p0-fixes`.*

---

### C-2 (S0 B4 / BUG #4): WebSocket path bypasses `OAuth2Middleware`

**Severity:** CRITICAL (security — authentication evasion in OAuth2-only deployments)
**Location:** `src/asap/transport/websocket.py:761-786` (`_make_fake_request`), invoked at `websocket.py:1017` and `1024`; `src/asap/transport/server.py:2141-2152` (`websocket_asap`); `src/asap/auth/middleware.py:135` (`OAuth2Middleware`)
**Status:** Identified; **Remediated in S0** (Task 4.0 — enforce auth on the WS path)

`OAuth2Middleware` is a `BaseHTTPMiddleware` (`auth/middleware.py:135`) that only executes on the Starlette HTTP middleware stack via its `dispatch` method. The WebSocket handler does **not** run through that stack. Instead, `handle_websocket_connection` synthesizes an HTTP `Request` from the WS frame and calls the request handler directly:

```761:786:src/asap/transport/websocket.py
async def _make_fake_request(body: str, websocket: WebSocket) -> Request:
    body_bytes = body.encode("utf-8")
    headers = list(websocket.scope.get("headers", []))
    headers.append((b"content-length", str(len(body_bytes)).encode()))
    scope = {
        "type": "http",
        "method": "POST",
        "headers": headers,
        "path": websocket.scope.get("path", "/asap"),
        "root_path": "",
        "query_string": b"",
        "server": websocket.scope.get("server", ("localhost", 8000)),
    }
    first_receive = True

    async def receive() -> dict[str, Any]:
        nonlocal first_receive
        if first_receive:
            first_receive = False
            return {"type": "http.request", "body": body_bytes, "more_body": False}
        return {"type": "http.disconnect"}

    async def send(_: MutableMapping[str, Any]) -> None:
        pass

    return Request(scope, receive, send)
```

Invocation sites:

```1017:1024:src/asap/transport/websocket.py
                request = await _make_fake_request(raw, websocket)
                ...
                    response = await request_handler.handle_message(request)
```

The `websocket_asap` route (`server.py:2141-2152`) calls `handle_websocket_connection` with no auth gate.

**Impact:** In an OAuth2-only deployment (`oauth2_config` set, `manifest.auth`/`token_validator` absent), `POST /asap` is JWT-protected but `WS /asap/ws` is **unauthenticated** — a client can connect and dispatch `task.request` envelopes without a valid Bearer token.

**S0 Remediation (Task 4.0):** Enforce OAuth2/identity auth explicitly at WS connection acceptance (read `Authorization` from `websocket.scope["headers"]`, validate with the same logic `OAuth2Middleware` uses, reject the connection with a close code on failure), coordinated with S2 Task 3.2 which deletes `_make_fake_request`. A new E2E test (`tests/e2e/test_websocket_oauth2.py`) connects without a token and asserts the message is denied, not dispatched. *Status: in progress on `feat/v2.5.1-s0-p0-fixes`.*

---

### C-3 (S0 B1 + BUG #3): Non-atomic `revoke_cascade` and missing `InMemoryDelegationStorage` lock

**Severity:** CRITICAL (security invariant — revocation atomicity)
**Location:** `src/asap/economics/delegation_storage.py:128-150` (`DelegationStorageBase.revoke_cascade`), `:153-220` (`InMemoryDelegationStorage`), `:277-292` (`SQLiteDelegationStorage.revoke`)
**Status:** Identified; **Remediated in S0** (Task 1.0 — atomic cascade + InMemory lock)

The cascade revocation lives on the **base class** and calls `self.revoke(tid)` per token id in an iterative BFS loop:

```128:150:src/asap/economics/delegation_storage.py
    async def revoke_cascade(
        self,
        token_id: str,
        reason: str | None = None,
    ) -> None:
        """Revoke a token and all child delegations (iterative BFS).

        Uses a visited set to handle circular delegation chains and a
        depth limit (_MAX_CASCADE_DEPTH) to prevent DoS.
        """
        visited: set[str] = set()
        stack: list[tuple[str, int]] = [(token_id, 0)]
        while stack:
            tid, depth = stack.pop()
            if tid in visited or depth > _MAX_CASCADE_DEPTH:
                continue
            visited.add(tid)
            delegate_urn = await self.get_delegate(tid)
            if delegate_urn:
                child_ids = await self.list_token_ids_issued_by(delegate_urn)
                for child_id in child_ids:
                    stack.append((child_id, depth + 1))
            await self.revoke(tid, reason)
```

Two defects combine:

1. **Non-atomic SQLite cascade (B1):** `SQLiteDelegationStorage.revoke` (`:277-292`) opens its **own** `aiosqlite.connect` and commits independently per id. A mid-cascade crash leaves a partial revocation state — the parent revoked but some children still alive — violating the "revoke parent ⟹ revoke all children, atomically" invariant.

2. **Missing InMemory lock (BUG #3):** `InMemoryDelegationStorage.__init__` (`:156-158`) holds only `self._revoked` and `self._issued` dicts — **no `asyncio.Lock`** (contrast with `InMemorySLAStorage`/`InMemoryMeteringStorage`, which use `asyncio.Lock`). Concurrent `register_issued` interleaved between `list_token_ids_issued_by` and `revoke` in the cascade can lose newly-issued children.

**Evidence (InMemory init, no lock):**

```156:158:src/asap/economics/delegation_storage.py
    def __init__(self) -> None:
        self._revoked: dict[str, tuple[datetime, str | None]] = {}
        self._issued: dict[str, tuple[str, str | None, datetime]] = {}
```

**S0 Remediation (Task 1.0):** Refactor `revoke_cascade` to delegate to a per-subclass `_revoke_cascade_atomic(token_id, reason)` hook. SQLite opens **one** connection, `BEGIN`, walks the tree, `COMMIT` (rollback on exception). InMemory adds an `asyncio.Lock` held across the whole cascade. Failing regression test simulates a 2nd-child failure and asserts no partial state. *Status: in progress on `feat/v2.5.1-s0-p0-fixes`.*

---

## 🟠 HIGH Findings

### H-1 (S0 B6 / BUG #6): Client-side `correlation_id` not bound to request id

**Severity:** HIGH (protocol integrity — request/response mixup under concurrency)
**Location:** `src/asap/models/envelope.py:138-147` (`validate_response_correlation`), `src/asap/transport/client.py:1032` (HTTP response construction), `src/asap/transport/websocket.py:413` (WS recv loop)
**Status:** Identified; **Remediated in S0** (Task 6.0 — bind `correlation_id == request.id` at the client pairing site)

The envelope validator only checks that `correlation_id` is **non-empty** for response payload types — it does not bind the value to the originating request id:

```138:147:src/asap/models/envelope.py
    @model_validator(mode="after")
    def validate_response_correlation(self) -> "Envelope":
        response_type_keys = {"taskresponse", "mcptoolresult", "mcpresourcedata"}

        if (
            _normalize_payload_type(self.payload_type) in response_type_keys
            and not self.correlation_id
        ):
            raise ValueError(f"{self.payload_type} must have correlation_id for request tracking")
        return self
```

The HTTP client constructs the response envelope without asserting the correlation matches the request id:

```1032:1032:src/asap/transport/client.py
                response_envelope = Envelope(**envelope_data)
```

The WS recv loop (`websocket.py:413`) has the same gap: `envelope = Envelope.model_validate(result["envelope"])` is paired to `request_id` by futures at `:414-417` but the envelope's `correlation_id` is never asserted to equal `request_id`.

**Impact:** A buggy or malicious server can return any non-empty `correlation_id` and the client accepts it as the response to a different request. Under concurrent in-flight requests this enables request/response mixup.

**S0 Remediation (Task 6.0):** When awaiting a response for a known `request_id`, assert `response.correlation_id == request_id` and raise a typed `ProtocolCorrelationError` on mismatch. Keep `validate_response_correlation` as the structural non-empty check; add the binding check at the client pairing site. Document and skip the streaming/unmatched callback paths where correlation is intentionally loose. *Status: in progress on `feat/v2.5.1-s0-p0-fixes`.*

---

### H-2 (S0 B2): Divergent `usage_events` DDL — consumer index missing in one owner

**Severity:** HIGH (correctness — non-deterministic query plans)
**Location:** `src/asap/state/stores/sqlite.py:397-416` (state-layer DDL, missing index) vs `src/asap/economics/storage.py:486-511` (economics DDL, both indexes)
**Status:** Identified; **Remediated in S0** (Task 2.0 — single canonical DDL owner)

Two stores create the same physical `usage_events` table on a shared DB file (`asap_state.db`) with different index sets. Whichever store initializes first wins the index set; `CREATE INDEX IF NOT EXISTS` never adds the missing one later.

State-layer DDL (missing the consumer index):

```397:416:src/asap/state/stores/sqlite.py
    async def _ensure_usage_table(self, conn: aiosqlite.Connection) -> None:
        await conn.execute(
            """
            CREATE TABLE IF NOT EXISTS usage_events (
                id TEXT PRIMARY KEY,
                task_id TEXT NOT NULL,
                agent_id TEXT NOT NULL,
                consumer_id TEXT NOT NULL,
                metrics TEXT NOT NULL,
                timestamp TEXT NOT NULL
            )
            """
        )
        await conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_usage_agent_timestamp
            ON usage_events (agent_id, timestamp)
            """
        )
        await conn.commit()
```

Economics DDL (creates both indexes):

```505:510:src/asap/economics/storage.py
        await conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_usage_consumer_timestamp
            ON usage_events (consumer_id, timestamp)
            """
        )
```

**Impact:** When the state-layer store initializes first, `idx_usage_consumer_timestamp` is never created. Consumer-keyed usage queries fall back to full table scans — non-deterministic performance depending on init order, and a behavioral divergence between deployments that "should" be identical.

**S0 Remediation (Task 2.0):** Extract a shared `_USAGE_EVENTS_DDL` constant + `_ensure_usage_events_schema(conn)` helper and call it from both stores. Full `AsyncSqliteRepository` consolidation is deferred to S1. Failing test asserts the consumer index exists under both init orders. *Status: in progress on `feat/v2.5.1-s0-p0-fixes`.*

---

## 🟡 MEDIUM Findings

### M-1 (S0 B5): OpenAPI handler dead `resolve_headers` path + pre-v2.3.0 carry-over

**Severity:** MEDIUM (maintainability / dead code)
**Location:** `src/asap/adapters/openapi/handler.py:366-401` (`execute`), `:493-517` (module-level `execute` wiring `session=None`)
**Status:** Identified; **Remediated in S0** (Task 5.0)

> **Note on diff scope:** `src/asap/adapters/openapi/handler.py` is **byte-identical** between `v2.3.0` and `HEAD` (`git rev-parse` of both blobs returns `ac09b5d3c697d489bb6d074d4fcca87a4f1dd6ba`; no commits in `v2.3.0..HEAD` touch this file). The concerns below are therefore **pre-existing carry-over from v2.3.0 and earlier**, not regressions introduced by v2.4.0/v2.5.0. They are recorded here because Sprint S0 Task 5.0 cleans them up as part of the same patch series, and a retrospective review of the shipped range should note their presence.

The handler exposes a `resolve_headers` callback plumbed through a `session` argument, but the default wiring hardcodes `session=None`, making the callback dead in the actual task-request path:

```493:500:src/asap/adapters/openapi/handler.py
async def execute(
    ...,
    session: object | None = None,
) -> ...:
    ...
    return await handler.execute(capability_name, args, session=session)
```

```512:517:src/asap/adapters/openapi/handler.py
        """Translate ``task.request`` envelopes through *upstream* (``session`` is always ``None``)."""
        ...
            session=None,
```

The inline-import and raising-constructor concerns originally listed under B5 are **not present** at HEAD: the `OpenAPIPathParameterError.__init__` (`:81-115`) is already pure (side-effect-free; the docstring at `:76-78` states "Construction is pure... use `for_missing`/`for_invalid` to enforce the invariant at the raise-site"), and the only imports in the file are top-level (`import logging`, `import re`, `import httpx`, and `asap.*` imports — no function-body inline imports). The remaining live concern is the dead `resolve_headers`/`session=None` branch.

**S0 Remediation (Task 5.0):** Either wire `session` properly or delete `resolve_headers` and the dead branch. The "hoist inline import" and "fix raising constructor" sub-tasks are effectively already satisfied in the current tree; S0 confirms this and removes the dead path. *Status: in progress on `feat/v2.5.1-s0-p0-fixes`.*

---

### M-2 (additional): MCP Auth Bridge `allow_env_jwt_fallback` — process-wide token inheritance risk

**Severity:** MEDIUM (security posture / defense-in-depth)
**Location:** `src/asap/adapters/mcp/jwt_extractor.py:13-52`, `src/asap/adapters/mcp/config.py:47` (`allow_env_jwt_fallback: bool = False`)
**Status:** New finding (not in the S0 bug list). No remediation required for v2.5.0; documented for awareness.

The MCP Auth Bridge JWT extractor can fall back to reading the Agent JWT from the `ASAP_AGENT_JWT` environment variable when `allow_env_jwt_fallback=True`:

```45:51:src/asap/adapters/mcp/jwt_extractor.py
    if not allow_env_fallback:
        return None

    env_token = os.environ.get(_ENV_JWT_KEY)
    if isinstance(env_token, str) and env_token.strip():
        return env_token.strip()

    return None
```

**Assessment:** The default is `False` and the docstring (`:18-27`) explicitly states this is "single-agent local testing only" and that the default "ensures production cannot inherit a process-wide token." This is a reasonable dev affordance. The residual risk is operator misconfiguration: if `allow_env_jwt_fallback=True` is set in a multi-tenant deployment, every `tools/call` from any caller would authenticate as the same agent identity (the one whose JWT is in the env). This is not a defect — it is a documented foot-gun. **Recommendation:** Consider a startup log warning when `allow_env_jwt_fallback=True` is set (mirroring the `hide_unauthorized_tools_noop` warning pattern in `protected_server.py:36-37`), and a hard error if it is enabled together with `enforce_grants=True` and more than one registered tool. No S0 action required.

---

### M-3 (additional): `ProtectedMCPServer` — `hide_unauthorized_tools` is a silent no-op

**Severity:** MEDIUM (operator expectations / fail-open appearance)
**Location:** `src/asap/adapters/mcp/protected_server.py:36-37`, `:28-29` (docstring)
**Status:** New finding (not in the S0 bug list). Documented as deferred (MCP-MAP-004); no remediation required for v2.5.0.

When `config.hide_unauthorized_tools=True`, the constructor only logs a warning and does nothing — `tools/list` still returns the full tool set:

```36:37:src/asap/adapters/mcp/protected_server.py
        if config.hide_unauthorized_tools:
            logger.warning("mcp.auth.hide_unauthorized_tools_noop")
```

The class docstring (`:28-29`) and `MCPAuthConfig` docstring (`config.py:27-28`) both state MCP-MAP-004 is "deferred per design-lock §6 — no stdio JWT carriage on `tools/list`." This is a deliberate, documented scope deferral, not a bug. The risk is purely one of operator expectation: an operator setting `hide_unauthorized_tools=True` may believe unauthorized tools are hidden from discovery when in fact they are only gated at `tools/call`. **Recommendation:** The warning is the right mechanism; consider making the log message explicitly state "tools/list still returns all tools; only tools/call is gated" so operators do not infer a fail-closed discovery behavior. No S0 action required.

---

## 🔵 LOW / NITPICK

### L-1: `wellknown.get_manifest_json` switched to `by_alias=True` — correct but changes ETag input

**Severity:** LOW
**Location:** `src/asap/discovery/wellknown.py:43` (diff: `manifest.model_dump()` → `manifest.model_dump(mode="json", by_alias=True)`)

The change is **correct and an improvement**: `by_alias=True` ensures fields like `HardwareCapability.class_` (declared with `alias="class"`, `entities.py:101`) serialize as `"class"` rather than `"class_"`, matching the public manifest schema. `mode="json"` makes the output JSON-native (datetime → ISO string). The only thing to note is that this changes the byte output of `get_manifest_json`, which feeds `compute_manifest_etag` — any cached ETags computed against the old serialization will mismatch after this release. This is the expected behavior of a manifest format fix and does not require action; flagged only so release notes can mention that manifest ETags will recompute on upgrade.

---

### L-2: `ProtectedMCPServer.from_server` shallow-copies the tool dict

**Severity:** LOW (nitpick)
**Location:** `src/asap/adapters/mcp/protected_server.py:42-50`

`from_server` does `protected._tools = dict(server._tools)`. This is a **shallow** copy: the outer dict is new, but each value tuple `(func, input_schema, description, title, capability)` is shared by reference with the original server. Because tuples are immutable and the contained `func`/`schema`/`capability` objects are treated as read-only after registration, this is safe in practice and avoids an unnecessary deep copy. No action required; noted only because a future change that mutates a tool's `input_schema` in place on one server would also affect the other. If that ever becomes a concern, switch to copying the per-tool tuples.

---

## Scope & Methodology Notes

### Diff range determination

The exact requested tags all exist: `v2.3.0`, `v2.4.0`, `v2.5.0`, plus `v2.5.0.1` (a follow-up `asap-compliance` tag). `v2.3.0` is a confirmed ancestor of `HEAD` (`git merge-base --is-ancestor v2.3.0 HEAD` → true). The review therefore uses the exact range `v2.3.0..HEAD` (275 commits) as specified. The v2.5.0 release commit is `1c5027c` (2026-06-24); `HEAD` (`4c367e0`, 2026-06-24) is 5 commits ahead of `v2.5.0` on the same lineage and includes the `v2.5.0.1` compliance bump. No tag substitution was necessary.

### Areas surveyed (real code read, not inferred)

- **Edge AI Discovery (v2.4.0):** `src/asap/models/entities.py` (`HardwareCapability`, `InferenceCapability`, `LocalModelInfo` — all additive, all fields optional); `src/asap/models/enums.py` (`HardwareClass`, `HardwareIoType`, `InferenceMode`); `src/asap/discovery/registry.py` (`hardware_class`/`inference_modes`/`hardware_io` fields on `RegistryEntry`, `find_by_hardware_class`/`find_by_inference_mode`/`find_by_io`, `derive_registry_hardware_fields`); `src/asap/discovery/wellknown.py` (alias-correct serialization — L-1).
- **MCP Auth Bridge (v2.5.0):** `src/asap/adapters/mcp/` (`protected_server.py`, `config.py`, `capability_map.py`, `auth_middleware.py`, `jwt_extractor.py`, `errors.py`, `__init__.py`); `src/asap/mcp/{server,client,protocol}.py` (tool `capability` metadata, `subprocess_env`, `_meta` carriage); `src/asap/auth/{claims,jwks,agent_jwt,middleware}.py` (iss/aud centralization).
- **Transport / auth (cross-cutting):** `src/asap/transport/{server,client,websocket,capability_routes,agent_routes,_auth_helpers}.py`; `src/asap/economics/{delegation_storage,storage}.py`; `src/asap/state/stores/sqlite.py`; `src/asap/adapters/openapi/handler.py`.

### What this review is NOT

This is a **retrospective** review of already-shipped releases, produced to close the process gap noted in S0 Task 7.2 ("No code review exists past `engineering/code-review/v2.3.0/`"). It does not gate any past release and does not propose new code changes beyond what Sprint S0 already tracks. The Critical/High findings (B1–B6) are recorded with their S0 remediation status; the two additional Medium findings (M-2, M-3) are awareness items that do not require S0 action.

### Placement decision (public vs private)

This document is placed in the public `engineering/code-review/v2.5.1/` directory. The findings describe **classes of defects and their locations** but do **not** contain exploit-ready proof-of-concept code, weaponized request payloads, or step-by-step reproduction instructions for end-users. The security-relevant findings (B3/B4/B1) are already publicly tracked in the Sprint S0 task file (`engineering/tasks/private/v2.5.1/sprint-S0-p0-correctness-security.md`) and the AGENTS.md architecture notes; recording their existence in a review doc does not elevate exposure beyond what the sprint file already states. If a future revision adds exploit-ready detail (e.g., a working unauthenticated WS `task.request` payload), it should be moved to `engineering/code-review/private/v2.5.1/`.

---

## Resolution Status — S0 Bugs (B1–B6)

| Bug | Title | Severity | Location | S0 Status |
|-----|-------|----------|----------|-----------|
| **B1** (+BUG #3) | Non-atomic `revoke_cascade` + missing InMemory lock | 🔴 Critical | `economics/delegation_storage.py:128-150, 156-158, 277-292` | Remediated in S0 (Task 1.0) — in progress |
| **B2** | Divergent `usage_events` DDL (missing consumer index) | 🟠 High | `state/stores/sqlite.py:397-416` vs `economics/storage.py:486-511` | Remediated in S0 (Task 2.0) — in progress |
| **B3** (BUG #1) | Divergent Host-JWT verifiers — revoked-host bypass | 🔴 Critical | `transport/capability_routes.py:60-83` vs `agent_routes.py:239-282` | Remediated in S0 (Task 3.0) — in progress |
| **B4** (BUG #4) | WebSocket bypasses `OAuth2Middleware` | 🔴 Critical | `transport/websocket.py:761-786, 1017, 1024`; `server.py:2141-2152`; `auth/middleware.py:135` | Remediated in S0 (Task 4.0) — in progress |
| **B5** | OpenAPI handler dead `resolve_headers` path (inline-import / raising-ctor sub-items already satisfied) | 🟡 Medium | `adapters/openapi/handler.py:366-401, 493-517` (byte-identical to v2.3.0 — pre-existing carry-over) | Remediated in S0 (Task 5.0) — in progress |
| **B6** (BUG #6) | Client-side `correlation_id` not bound to request id | 🟠 High | `models/envelope.py:138-147`; `transport/client.py:1032`; `transport/websocket.py:413` | Remediated in S0 (Task 6.0) — in progress |

> All six bugs are confirmed present in the shipped `v2.3.0..HEAD` range by direct code inspection above, and all six are tracked for remediation in Sprint S0 with a failing-test-first policy. The "in progress" status reflects that the fixes are being implemented on branch `feat/v2.5.1-s0-p0-fixes` at the time of this review; commits are held by the user and have not been pushed.

---

## Verdict

> **REQUEST CHANGES (retrospective)** — 3 Critical (B1/B3/B4), 2 High (B2/B6), 3 Medium (B5/M-2/M-3), 2 Low.

The v2.4.0 and v2.5.0 releases shipped three security-relevant P0 defects (revoked-host bypass, WebSocket OAuth2 bypass, non-atomic revocation cascade) plus three correctness/maintainability defects. All are identified and under remediation in Sprint S0. The MCP Auth Bridge (v2.5.0) is architecturally sound — clean opt-in adapter, canonical verifier reuse, centralized iss/aud claim validation — and the Edge AI Discovery (v2.4.0) manifest extension is a safe, additive, backward-compatible change. The two additional Medium findings (M-2 env-JWT fallback posture, M-3 `hide_unauthorized_tools` no-op) are documented foot-guns/deferrals, not defects, and require no S0 action.
