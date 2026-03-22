# Code Review: PR #102

**PR**: [feat(auth,transport): per-runtime agent identity, Host/Agent JWT, and /asap/agent endpoints (S0)](https://github.com/adriannoes/asap-protocol/pull/102)
**Branch**: `feat/agent-identity` → `main`
**Sprint**: S0 — Per-Runtime-Agent Identity (v2.2 Protocol Hardening)
**Reviewer**: Senior Staff Engineer (AI-Assisted)
**Date**: 2026-03-22

---

## 1. Executive Summary

| Category | Status | Summary |
| :--- | :--- | :--- |
| **Tech Stack** | ✅ | Ed25519 via `cryptography`, `joserfc` for JOSE, Pydantic v2 (`ASAPBaseModel`), FastAPI — all aligned with `tech-stack-decisions.md` |
| **Architecture** | ⚠️ | Layered correctly (models → JWT → transport), async stores follow `Protocol` pattern. RFC 7638 thumbprint deviates from spec (see Fix #1). `server.py` gaining weight |
| **Security** | ⚠️ | Solid JWT verification chain. `aud` claim not validated (Fix #2), unbounded memory risk in `JtiReplayCache` (Fix #3), `assert` in production path (Fix #4) |
| **Tests** | ✅ | Excellent coverage (~1,500 LoC tests). Covers happy paths, edge cases, replay detection, cross-host rejection, key rotation, and OAuth2 coexistence |

> **General Feedback:** This is a high-quality PR that lays a strong foundation for the v2.2 identity hierarchy. The code is well-structured, the test matrix is thorough, and the design correctly isolates the new identity system from existing OAuth2 flows. The main concerns are (1) a non-trivial RFC 7638 compliance issue in the thumbprint function, (2) missing `aud` validation which opens a token reuse vector, and (3) unbounded `JtiReplayCache` growth under sustained load. All are fixable before merge.

---

## 2. Required Fixes (Must Address Before Merge)

### Fix #1: RFC 7638 Thumbprint Uses All Keys Instead of Required Members Only

*   **Location:** `src/asap/auth/identity.py:93-96` (`jwk_thumbprint_sha256`)
*   **Problem:** RFC 7638 §3.2 mandates that the thumbprint input uses **only the required members** for the key type, in **lexicographic order**. For OKP keys: `{"crv":"...","kty":"OKP","x":"..."}`. The current implementation passes the **entire** `public_key` dict (which may include optional fields like `kid`, `use`, `key_ops`, or `alg`) to `json.dumps(… sort_keys=True)`. This means two JWKs with the same cryptographic material but different metadata would produce different thumbprints — breaking identity resolution.
*   **Rationale (Expert View):** Thumbprint consistency is the **root of trust** for the entire Host→Agent identity chain. `iss` in Host JWT equals the host's thumbprint. If two representations of the same key produce different thumbprints, host lookup by `iss` silently fails, agents become orphaned, and replay detection partitions fragment. This is a silent data correctness bug, not a crash.
*   **Fix Suggestion:**
    ```python
    def jwk_thumbprint_sha256(public_key: dict[str, Any]) -> str:
        """RFC 7638 JWK thumbprint using SHA-256 (base64url, no padding).

        Uses only the required members for the key type in lexicographic order.
        """
        kty = public_key.get("kty")
        if kty == "OKP":
            required = {"crv": public_key["crv"], "kty": kty, "x": public_key["x"]}
        elif kty == "EC":
            required = {"crv": public_key["crv"], "kty": kty, "x": public_key["x"], "y": public_key["y"]}
        elif kty == "RSA":
            required = {"e": public_key["e"], "kty": kty, "n": public_key["n"]}
        elif kty == "oct":
            required = {"k": public_key["k"], "kty": kty}
        else:
            msg = f"unsupported kty for thumbprint: {kty}"
            raise ValueError(msg)
        canonical = json.dumps(required, sort_keys=True, separators=(",", ":"))
        digest = hashlib.sha256(canonical.encode("utf-8")).digest()
        return base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")
    ```

---

### Fix #2: `aud` Claim Is Never Validated During JWT Verification

*   **Location:** `src/asap/auth/agent_jwt.py:154-197` (`verify_host_jwt`) and `src/asap/auth/agent_jwt.py:200-260` (`verify_agent_jwt`)
*   **Problem:** Both `create_host_jwt` and `create_agent_jwt` accept an `aud` parameter and embed it in the token, but neither `verify_host_jwt` nor `verify_agent_jwt` check the `aud` claim against an expected audience. This means a Host JWT minted for `aud: "payment-service"` would be accepted by the identity registration service, enabling cross-service token reuse attacks.
*   **Rationale (Expert View):** Audience validation is a fundamental JWT security control (RFC 7519 §4.1.3). Without it, any valid Host JWT from any service can be replayed against `/asap/agent/*` endpoints. In a multi-service ASAP deployment, this is a privilege escalation vector.
*   **Fix Suggestion:** Add an `expected_audience` parameter to both verify functions:
    ```python
    async def verify_host_jwt(
        token: str,
        host_store: HostStore,
        *,
        expected_audience: str | list[str] | None = None,
        jti_replay_cache: JtiReplayCache | None = None,
    ) -> JwtVerifyResult:
        # ... after claims extraction ...
        if expected_audience is not None:
            aud = claims.get("aud")
            expected = [expected_audience] if isinstance(expected_audience, str) else expected_audience
            token_auds = [aud] if isinstance(aud, str) else (aud if isinstance(aud, list) else [])
            if not any(a in expected for a in token_auds):
                return JwtVerifyResult(ok=False, error="audience mismatch")
    ```
    Then pass the expected audience from the transport endpoints (e.g., the server's manifest ID or a configured audience string).

---

### Fix #3: `JtiReplayCache` Has No Size Bound — Unbounded Memory Growth

*   **Location:** `src/asap/auth/agent_jwt.py:60-87` (`JtiReplayCache`)
*   **Problem:** The cache uses a plain `dict` with TTL-based expiry via `_prune_expired()`, but pruning only occurs on `check_and_record` calls. Under sustained high-throughput (e.g., bursty agent registration), the dict grows unboundedly between prune cycles. A malicious actor could exhaust server memory by sending thousands of unique JWTs.
*   **Rationale (Expert View):** In-memory caches without hard size caps are a classic DoS vector. The 90s TTL window helps, but pruning is lazy (only on reads). A sustained burst of 100k unique tokens over 30 seconds allocates memory that isn't freed until the next `check_and_record` call — which may come late if traffic spikes then drops.
*   **Fix Suggestion:** Add a `max_size` cap with LRU eviction:
    ```python
    class JtiReplayCache:
        def __init__(self, ttl_seconds: float = 90.0, max_size: int = 10_000) -> None:
            self._ttl = ttl_seconds
            self._max_size = max_size
            self._expiry_by_key: dict[tuple[str, str], float] = {}

        def _prune_expired(self, now: float) -> None:
            dead = [k for k, exp in self._expiry_by_key.items() if exp <= now]
            for k in dead:
                del self._expiry_by_key[k]
            # Evict oldest entries if still over limit
            if len(self._expiry_by_key) > self._max_size:
                by_expiry = sorted(self._expiry_by_key, key=self._expiry_by_key.get)  # type: ignore[arg-type]
                for k in by_expiry[: len(self._expiry_by_key) - self._max_size]:
                    del self._expiry_by_key[k]
    ```

---

### Fix #4: `assert` in Production Path

*   **Location:** `src/asap/transport/server.py:236` (inside `_handle_agent_register`)
*   **Problem:**
    ```python
    assert claims is not None
    ```
    Python's `assert` statements are removed when running with `-O` (optimized bytecode). This means in production with `PYTHONOPTIMIZE=1`, the assertion disappears and `claims` could be `None`, leading to an unhandled `AttributeError` on the next line.
*   **Rationale (Expert View):** Per the project's own review checklist, `assert` should never be used for data validation in production code. Use explicit checks.
*   **Fix Suggestion:**
    ```python
    if claims is None:
        return JSONResponse(status_code=401, content={"detail": "Invalid host token"})
    ```

---

## 3. Tech-Specific Bug Hunt (Deep Dive)

- [x] **No Sync I/O in Async Paths**: ✅ — No `open()`, `requests`, `time.sleep`, or raw `sqlite3`. All stores use `async def`. `time.time()` calls are for timestamp generation only (non-blocking).
- [x] **Pydantic v2 Compliance**: ✅ — `ASAPBaseModel` with `ConfigDict(frozen=True, extra="forbid")`. `model_copy(update=...)` used correctly instead of v1's `copy()`.
- [x] **No `python-jose`**: ✅ — Uses `joserfc` exclusively (correct per `tech-stack-decisions.md` §2.2).
- [x] **Ed25519 Only**: ✅ — `Ed25519PrivateKey` from `cryptography`, `OKPKey` from `joserfc`. No RSA/ECDSA.
- [x] **No Mutable Defaults**: ✅ — `default_capabilities` uses `Field(default_factory=list)`. No `def route(data: List = [])` pattern.
- [x] **No Swallowed Exceptions**: ✅ — All `except` blocks return structured `JwtVerifyResult(ok=False, error=...)`. No bare `except Exception: pass`.
- [x] **No Hardcoded Secrets**: ✅ — Keys are generated at runtime; no API keys, tokens, or salts in source.

### Potential Issues (Low/Medium Severity)

- [ ] **`asyncio.run()` in Sync Test Code**: Several transport tests (`test_server.py`) call `asyncio.run(agent_store.get(...))` inside synchronous test methods. This works with `TestClient` (which runs its own event loop), but `asyncio.run()` creates a new loop each time. If the test runner (pytest-asyncio) is configured with a shared loop, this could cause event loop conflicts.
  **Recommendation:** Convert these tests to `async def` with `@pytest.mark.asyncio`, or use a fixture that provides the running loop's `run_coroutine_threadsafe`.

- [ ] **`_unverified_header_and_payload` Re-implements JWT Parsing**: `agent_jwt.py` manually splits and decodes JWT segments before verification. While correct, it duplicates logic that `joserfc` already handles internally. If `joserfc` changes its serialization format or adds compact JWE support, this parser silently diverges.
  **Recommendation:** Check if `joserfc` exposes a `decode_header` or similar utility that can be used instead.

---

## 4. Improvements & Refactoring (Highly Recommended)

### Architecture & Design

- [ ] **`server.py` is growing too large (~1,900 lines):** The agent identity handlers add ~300 lines to an already-large file. Consider extracting agent identity endpoints into a dedicated `FastAPI.APIRouter` in a new file `src/asap/transport/agent_routes.py`, similar to how `create_usage_router()` works in the existing codebase. This improves maintainability without changing behavior.

- [ ] **`_effective_identity_host_id` could silently construct URNs:** The function synthesizes `urn:asap:host:{iss}` for first-seen hosts, which is a fallback for unregistered hosts. This same URN is created in `_handle_agent_register`. If the urn-construction logic diverges between the two, `_handle_agent_status` silently fails to match the host. Extract the URN construction into a single `host_urn_from_thumbprint(thumbprint: str) -> str` function in `identity.py`.

### Security Hardening

- [ ] **Rate-limit agent registration independently:** `_handle_agent_register` uses the global `app.state.limiter.check(request)`, which shares rate budget with all other ASAP endpoints. A malicious actor could burn through the rate limit via `/asap/agent/register` calls, starving legitimate `/asap` JSON-RPC traffic. Consider a separate rate limiter for identity endpoints.

- [ ] **Log security-relevant events:** Agent registration, revocation, and key rotation are security-critical lifecycle events. Currently, none of them emit structured log entries. Add `logger.info(...)` with `agent_id`, `host_id`, and `action` context to enable audit trail and anomaly detection.

### Typing

- [ ] **`public_key: dict[str, Any]` on models:** Both `HostIdentity.public_key` and `AgentSession.public_key` use `dict[str, Any]`, which provides no validation of the JWK structure. Consider adding a custom Pydantic validator that checks the required OKP fields (`kty`, `crv`, `x`) at model construction time. This would catch invalid JWKs before they're stored, rather than at JWT verification time.

- [ ] **`cast` usage in `agent_jwt.py`:** Lines like `cast("dict[str, str | list[str]]", dict(public_key))` suppress type checker errors but don't validate at runtime. Since these are security-critical paths, consider using a runtime type guard or Pydantic model parse instead.

### Test Quality

- [ ] **Missing edge case: Host JWT with `aud` as a list:** `create_host_jwt` accepts `aud: str | list[str]`, but test coverage only exercises the `str` path. Add a test with `aud=["aud1", "aud2"]` to verify list audience round-trips correctly.

- [ ] **Missing edge case: Concurrent registration of the same agent key from different requests:** The idempotency test uses sequential calls. Under concurrent requests, the `list_by_host` + `save` pattern in `_handle_agent_register` has a TOCTOU race (two requests could both miss the existing session and create duplicates). This is acceptable for in-memory stores (single-threaded async), but document this as a known limitation for production store implementations.

---

## 5. Verification Steps

After applying fixes, verify with:

```bash
# Unit tests for identity models
uv run pytest tests/auth/test_identity.py -v

# Unit tests for JWT create/verify
uv run pytest tests/auth/test_agent_jwt.py -v

# Transport endpoint tests
uv run pytest tests/transport/test_server.py -k "Agent" -v

# OAuth2 coexistence
uv run pytest tests/auth/test_server_oauth2_integration.py -v

# Type checking
uv run mypy src/asap/auth/identity.py src/asap/auth/agent_jwt.py src/asap/transport/server.py

# Linting
uv run ruff check src/asap/auth/ src/asap/transport/server.py

# Full CI suite
uv run pytest -n auto && uv run mypy src/ scripts/ tests/ && uv run ruff check src/
```

### Specific Verification for Fix #1 (Thumbprint):
```python
# After fix, this must produce identical thumbprints:
jwk_minimal = {"kty": "OKP", "crv": "Ed25519", "x": "dGVzdA"}
jwk_with_extras = {"kty": "OKP", "crv": "Ed25519", "x": "dGVzdA", "kid": "key-1", "use": "sig"}
assert jwk_thumbprint_sha256(jwk_minimal) == jwk_thumbprint_sha256(jwk_with_extras)
```
