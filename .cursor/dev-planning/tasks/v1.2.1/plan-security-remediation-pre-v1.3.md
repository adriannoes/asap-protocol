# Plan: Security Remediation Pre-v1.3.0

> **Purpose**: Execute all findings from v1.2.0 Security Review before starting v1.3.0 development
> **Source**: [v1.2.0-security-review.md](v1.2.0-security-review.md)
> **Prerequisite**: v1.2.0 released
> **Target**: Patch release v1.2.1 (critical fix) + hardening items
> **Estimated Duration**: 5–8 days

---

## Overview

| Phase | Focus | Priority | Est. Days |
|-------|-------|----------|-----------|
| **P0** | JWT Expiration Bypass (HIGH) | Critical | 1 |
| **P1** | Architecture & Error Handling | High | 2 |
| **P2** | Low-severity Vulns & Config | Medium | 1–2 |
| **P3** | Test Coverage Gaps | Medium | 1–2 |
| **P4** | CI & Nitpicks | Low | 0.5 |

---

## Phase P0: JWT Expiration Bypass (Critical)

**Severity**: HIGH — Authentication Bypass  
**Recommendation**: Patch release v1.2.1 immediately after completion.

### Task P0.1: Enforce JWT `exp` Validation

**Goal**: Reject expired tokens in `validate_jwt` so stolen/expired tokens cannot be used indefinitely.

**Context**: The `validate_jwt` function in `src/asap/auth/jwks.py` does not validate `exp`. The middleware assumes valid tokens; there is no downstream check. An attacker with an expired token can bypass rotation and short-lived token security.

#### Sub-tasks

- [x] P0.1.1 Update `validate_jwt` to enforce `exp`
  - **File**: `src/asap/auth/jwks.py`
  - **What**: Use `jose_jwt.decode(..., claims={"exp": Require})` or manually check `claims["exp"] > time.time()` after decode. Prefer joserfc's built-in validation if available.
  - **Reference**: [joserfc jwt docs](https://github.com/thsant/joserfc) — `validate_claims` or `claims` parameter
  - **Verify**: Expired token raises `JoseError` or `ExpiredTokenError`

- [x] P0.1.2 Add regression test for expired token rejection
  - **File**: `tests/auth/test_jwks.py`
  - **What**: Create token with `exp` in the past; assert `validate_jwt` raises `JoseError` (or equivalent)
  - **Verify**: `uv run pytest tests/auth/test_jwks.py -v -k "expired"`

- [x] P0.1.3 Update docstring
  - **File**: `src/asap/auth/jwks.py`
  - **What**: Remove "Does not check exp" and document that `exp` is now validated

- [x] P0.1.4 Commit
  - **Command**: `git commit -m "fix(auth): enforce JWT exp validation to prevent expired token reuse"`
  - **Scope**: `src/asap/auth/jwks.py`, `tests/auth/test_jwks.py`

**Acceptance Criteria**:
- [x] Expired tokens raise `JoseError` (or equivalent)
- [x] Valid tokens with future `exp` still work
- [x] Test explicitly asserts expired token rejection

---

## Phase P1: Architecture & Error Handling

### Task P1.1: SQLite Sync/Async Bridge Optimization

**Goal**: Eliminate per-operation `ThreadPoolExecutor` creation in `_run_sync`.

**Context**: `_run_sync` creates a new `ThreadPoolExecutor` and `EventLoop` for every DB operation when called from async context. This is a performance bottleneck for high-throughput agents.

#### Sub-tasks

- [x] P1.1.1 Replace per-call executor with shared executor or `asyncio.to_thread`
  - **File**: `src/asap/state/stores/sqlite.py`
  - **What**: Use `asyncio.to_thread()` when running in async context (Python 3.9+), or a module-level `ThreadPoolExecutor` reused across calls. Avoid `asyncio.run()` inside a new executor per call.
  - **Reference**: [tech-stack-decisions.md](../../architecture/tech-stack-decisions.md) — consider evolving SnapshotStore to async if feasible
  - **Verify**: Existing tests pass; no new executor per operation

- [x] P1.1.2 Add benchmark or integration test (optional)
  - **File**: `tests/state/test_sqlite_store.py`
  - **What**: Assert that multiple sequential operations do not spawn excessive threads
  - **Status**: Done

- [x] P1.1.3 Commit
  - **Command**: `git commit -m "perf(state): use shared executor in SQLite sync bridge"`

**Acceptance Criteria**:
- [x] No new `ThreadPoolExecutor` per DB operation
- [x] All existing tests pass

---

### Task P1.2: WebSocket Error Handling

**Goal**: Reraise critical exceptions or set explicit `needs_restart` flag instead of swallowing them.

**Context**: `_recv_loop` in `src/asap/transport/websocket.py:427` catches generic `Exception`, logs, and exits. `_run_loop` doesn't know *why* it failed. `SystemExit` or keyboard interrupt could be swallowed.

#### Sub-tasks

- [x] P1.2.1 Reraise critical exceptions
  - **File**: `src/asap/transport/websocket.py`
  - **What**: In `_recv_loop`, re-raise `SystemExit`, `KeyboardInterrupt`, `BaseException` (or equivalent). Only catch and log recoverable exceptions.
  - **Verify**: Keyboard interrupt propagates correctly

- [x] P1.2.2 Add test for handler exception → JSON-RPC error frame
  - **File**: `tests/transport/test_websocket*.py`
  - **What**: Mock `ASAPRequestHandler.handle_message` to raise `Exception("Boom")`; assert client receives JSON-RPC error frame (-32603) and connection behavior is correct (per review: "does NOT close the connection" or document intended behavior)
  - **Reference**: Security review lines 890–919, 127–129

- [x] P1.2.3 Commit
  - **Command**: `git commit -m "fix(transport): reraise critical exceptions in WebSocket recv loop"`

**Acceptance Criteria**:
- [x] Critical exceptions propagate
- [x] Handler exception scenario covered by test

---

### Task P1.3: Auth Custom Claim Default Mismatch

**Goal**: Align `DEFAULT_CUSTOM_CLAIM` with documentation.

**Context**: Code uses `https://github.com/adriannoes/...` but `tech-stack-decisions.md` recommends `https://asap.ai/agent_id`. Implementers expect docs to work out-of-the-box.

#### Sub-tasks

- [x] P1.3.1 Update default to match docs
  - **File**: `src/asap/auth/middleware.py`
  - **What**: Keep `DEFAULT_CUSTOM_CLAIM` as `https://github.com/adriannoes/asap-protocol/agent_id` (per project decision; aligns with existing docs)
  - **Reference**: tech-stack-decisions.md line 119

- [x] P1.3.2 Update tests that assert the old default
  - **File**: `tests/auth/test_middleware.py` (or equivalent)
  - **What**: Adjust any assertions that expect the old URL

- [x] P1.3.3 Commit
  - **Command**: `git commit -m "fix(auth): align default custom claim with tech-stack-decisions"`

**Acceptance Criteria**:
- [x] `DEFAULT_CUSTOM_CLAIM == "https://github.com/adriannoes/asap-protocol/agent_id"` (per project decision)
- [x] All auth tests pass

---

## Phase P2: Low-Severity Vulnerabilities & Config

### Task P2.1: MCP Command Injection Mitigation

**Severity**: LOW (configuration-dependent)

**Goal**: Document and optionally validate `server_command` to reduce risk.

#### Sub-tasks

- [x] P2.1.1 Document trusted-source requirement
  - **File**: `src/asap/mcp/client.py` (docstring) and `docs/` or README
  - **What**: Add clear docstring: "server_command must come from a trusted source (e.g. config file). Do not derive from user input."
  - **Verify**: Docstring visible in IDE

- [x] P2.1.2 (Optional) Add allowlist validation
  - **File**: `src/asap/mcp/client.py`
  - **What**: If feasible, validate first element of `server_command` against allowlist (e.g. known binaries). Document as opt-in.
  - **Note**: Implemented as `allowed_binaries: frozenset[str] | None = None` (opt-in)

- [x] P2.1.3 Commit
  - **Command**: `git commit -m "docs(mcp): document trusted-source requirement for server_command"`

**Acceptance Criteria**:
- [x] Documentation clearly states `server_command` must be trusted
- [x] No breaking change to existing configs

---

### Task P2.2: OIDC SSRF Mitigation

**Severity**: LOW (configuration-dependent)

**Goal**: Block private/internal `issuer_url` unless explicitly allowed.

#### Sub-tasks

- [x] P2.2.1 Add `issuer_url` validator
  - **File**: `src/asap/auth/oidc.py`
  - **What**: Validate `issuer_url` host: block 127.0.0.1, 0.0.0.0, 10.x, 172.16–31.x, 192.168.x, link-local, etc. Add config flag `allow_private_issuers: bool = False` to override for dev/test.
  - **Reference**: Security review lines 86–95

- [x] P2.2.2 Add tests for blocked and allowed URLs
  - **File**: `tests/auth/test_oidc.py`
  - **What**: Assert `http://127.0.0.1/...` raises; assert `https://auth.example.com` passes; assert `allow_private_issuers=True` allows localhost

- [x] P2.2.3 Commit
  - **Command**: `git commit -m "fix(auth): validate OIDC issuer_url to mitigate SSRF"`

**Acceptance Criteria**:
- [x] Private IP ranges blocked by default
- [x] Override available for local development
- [x] Tests cover blocked and allowed cases

---

## Phase P3: Test Coverage Gaps

### Task P3.1: WebSocket Error Handling Tests

**Goal**: Cover lines 890–919 (error handling in message loop) and 249–253 (race during close).

#### Sub-tasks

- [x] P3.1.1 Test handler exception → JSON-RPC error
  - **File**: `tests/transport/test_websocket*.py`
  - **What**: Handler mock raises `Exception("Boom")`; assert client receives -32603 error frame
  - **Reference**: Security review "Missing Scenarios" #1

- [x] P3.1.2 Test race condition during close (if feasible)
  - **File**: `tests/transport/test_websocket*.py`
  - **What**: Cover lines 249–253; may require timing-sensitive test or documented limitation
  - **Status**: Done (mock-based test for close-during-connect race)

- [x] P3.1.3 Commit
  - **Command**: `git commit -m "test(transport): add WebSocket error handling coverage"`

---

### Task P3.2: Introspection Cache Eviction Test

**Goal**: Cover lines 151–154 (LRU eviction when cache exceeds `max_cache_size`).

#### Sub-tasks

- [x] P3.2.1 Add cache eviction test
  - **File**: `tests/auth/test_introspection.py`
  - **What**: `TokenIntrospector(max_cache_size=2)`, introspect 3 different tokens, verify cache size remains 2 and oldest evicted
  - **Reference**: Security review "Missing Scenarios" #2

- [x] P3.2.2 Commit
  - **Command**: `git commit -m "test(auth): add introspection cache eviction coverage"`

---

### Task P3.3: SSL/TLS WebSocket Connection Test

**Goal**: Cover line 243 (connect with `ssl_context`).

#### Sub-tasks

- [x] P3.3.1 Add SSL context test
  - **File**: `tests/transport/test_websocket*.py`
  - **What**: Test WebSocket client/server with `ssl_context` (may use self-signed cert in test)
  - **Reference**: Security review "Missing Scenarios" #3

- [x] P3.3.2 Commit
  - **Command**: `git commit -m "test(transport): add WebSocket SSL context coverage"`

---

## Phase P4: CI & Nitpicks

### Task P4.1: Enforce Minimum Coverage in CI

**Goal**: Prevent coverage regression.

#### Sub-tasks

- [x] P4.1.1 Add coverage threshold to pytest
  - **File**: `pyproject.toml` or `pytest.ini`
  - **What**: CI already uses `--cov-fail-under=85`; threshold in place (90 deferred until coverage allows)
  - **Verify**: `uv run pytest --cov=src --cov-report=xml --cov-fail-under=85` fails if coverage drops

- [x] P4.1.2 Add to CI workflow
  - **File**: `.github/workflows/*.yml` (or equivalent)
  - **What**: Ensure coverage check runs and fails the job on regression

- [x] P4.1.3 Commit
  - **Command**: `git commit -m "ci: enforce minimum test coverage threshold"`

---

### Task P4.2: Loose Typing (Optional / Deferred)

**Goal**: Consider `TypedDict` or `pydantic.Json` for `dict[str, Any]` in models.

**Context**: Security review suggests tightening validation. This is a refactor; can be deferred to v1.3 or later.

- [x] P4.2.1 Audit `src/asap/models/*.py` for `dict[str, Any]`
- [x] P4.2.2 Create follow-up task in v1.3 backlog if valuable

**Status**: Audit done; follow-up task at [task-P4.2-loose-typing-follow-up.md](../v1.3.0/task-P4.2-loose-typing-follow-up.md).

---

## Execution Order

| Order | Task | Phase | Dependency |
|-------|------|-------|------------|
| 1 | P0.1 JWT exp validation | P0 | None |
| 2 | P1.1 SQLite sync bridge | P1 | None |
| 3 | P1.2 WebSocket error handling | P1 | None |
| 4 | P1.3 Auth custom claim default | P1 | None |
| 5 | P2.1 MCP documentation | P2 | None |
| 6 | P2.2 OIDC SSRF validation | P2 | None |
| 7 | P3.1 WebSocket error tests | P3 | P1.2 |
| 8 | P3.2 Introspection cache test | P3 | None |
| 9 | P3.3 WebSocket SSL test | P3 | None |
| 10 | P4.1 CI coverage threshold | P4 | None |

---

## Release Strategy

1. **v1.2.1** (patch): Include P0.1 only. Release as soon as P0 is done.
2. **v1.2.2** (optional): Include P1–P4 if not ready for v1.3.0.
3. **v1.3.0**: Start only after P0–P2 complete; P3–P4 can be done in parallel with v1.3.0 planning.

---

## Definition of Done (Pre-v1.3.0)

- [x] P0.1 complete — JWT exp enforced, test added
- [ ] v1.2.1 released to PyPI with JWT fix
- [x] P1.1, P1.2, P1.3 complete
- [x] P2.1, P2.2 complete (or explicitly deferred with documented rationale)
- [x] P3.1, P3.2, P3.3 complete (or coverage gaps documented)
- [x] P4.1 complete — CI enforces coverage
- [x] All tests pass: `uv run pytest`
- [x] Type check clean: `uv run mypy src/`
- [x] Lint clean: `uv run ruff check src/ tests/`

---

## Relevant Files (Created or Modified)

| File | Purpose |
|------|---------|
| `src/asap/transport/websocket.py` | Reraise SystemExit/KeyboardInterrupt in _heartbeat_loop |
| `src/asap/mcp/client.py` | Module docstring: server_command trusted-source requirement |
| `tests/auth/test_introspection.py` | Cache eviction test (max_cache_size LRU) |
| `tests/transport/test_websocket.py` | SSL context passthrough test |
| `src/asap/mcp/client.py` | allowed_binaries opt-in validation |
| `tests/state/test_sqlite_store.py` | Sequential ops thread count test |
| `tests/mcp/test_client.py` | allowed_binaries tests |
| `.cursor/dev-planning/tasks/v1.3.0/task-P4.2-loose-typing-follow-up.md` | P4.2 follow-up task |
| `plan-security-remediation-pre-v1.3.md` | Task status updates |

---

## Related Documents

- [v1.2.0-security-review.md](v1.2.0-security-review.md)
- [tasks-v1.3.0-roadmap.md](../v1.3.0/tasks-v1.3.0-roadmap.md)
- [tech-stack-decisions.md](../../architecture/tech-stack-decisions.md)
- [task-template.md](../../templates/task-template.md)
