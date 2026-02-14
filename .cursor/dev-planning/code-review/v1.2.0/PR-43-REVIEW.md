# PR #43 Code Review: Trust Levels & mTLS

## Executive Summary
This PR introduces a 3-tier trust model (`SELF_SIGNED`, `VERIFIED`, `ENTERPRISE`) and mutual TLS (mTLS) support. The implementation is solid, with a clean separation of concerns and backward compatibility. The mTLS logic is correctly integrated into both HTTP and WebSocket transports.

**Verdict**: **Approved with Comments** (Requires Test Fixes)

---

## Addressed (Post-Review)

- [x] **manifest info tests**: Added `TestCliManifestInfo` in `tests/test_cli.py` (verified, self-signed, missing file, invalid JSON)
- [x] **WebSocketTransport lock**: Added `_connect_lock` to guard `connect()` for standalone use
- [x] **Tech debt**: Created issue #44 for sign_with_ca → real CA service; added docstring reference

## 1. Logic & Security Analysis
### Trust Levels & CA Simulation
- **Implementation**: The `TrustLevel` enum and detection logic in `src/asap/crypto/trust.py` are correct.
- **Security**:
    - `verify_ca_signature` correctly enforces `TrustLevel.VERIFIED`.
    - **Note**: The `sign_with_ca` function is explicitly marked as a simulation. This is acceptable for v1.2.0 but must be tracked as technical debt for v2.0.0 (Full CA Service).
- **Backward Compatibility**: Handling of manifests without `trust_level` defaults correctly to `SELF_SIGNED`.

### mTLS & Transport Security
- **Configuration**: `MTLSConfig` provides a type-safe way to handle certificates and keys.
- **Context Creation**: `create_ssl_context` correctly sets `CERT_REQUIRED` for clients and respects the optional nature of mTLS for servers.
- **Integration**:
    - `ASAPClient` correctly applies mTLS settings to both `httpx` and `websockets`.
    - **Concurrency**: `WebSocketTransport` connection logic relies on `ASAPClient`'s `connection_lock`, which is safe. However, adding an explicit lock within `WebSocketTransport` could prevent future regression if used standalone.

## 2. Structural & Test Hygiene Audit
### Test Coverage
- **Passed**: `tests/crypto/test_trust.py` covers trust logic and CA signing/verification extensively.
- **Passed**: `tests/transport/test_mtls.py` covers mTLS configuration and context creation, including error cases.
- **FAILED**: `src/asap/cli.py` adds a new command `manifest info` which **lacks test coverage**.
    - **Action Required**: Add a test case in `tests/test_cli.py` that invokes `manifest info <path/to/manifest>`.
    - Verify that the output contains the correct `Trust Level`.

### Architecture & linting
- **Pydantic v2**: Usage is consistent with the codebase.
- **Async/Await**: Correctly used in transport layers.

## 3. Recommendations
### Critical (Must Fix)
1.  **Add Tests for `manifest info`**:
    - Create a test in `tests/test_cli.py` that uses `CliRunner` to call `manifest info <path/to/manifest>`.
    - Verify that the output contains the correct `Trust Level`.

### Suggestions (Nice to Have)
1.  **Explicit Locking in WebSocketTransport**: Consider adding `self._connect_lock = asyncio.Lock()` in `WebSocketTransport` to guard `_do_connect` independently of `ASAPClient`.
2.  **Tech Debt Tracking**: Create a ticket/issue to replace `sign_with_ca` (simulation) with a real CA service integration for v2.0.0.

## 4. Verification
- **Files Analyzed**: `src/asap/crypto/trust.py`, `src/asap/transport/mtls.py`, `src/asap/cli.py`, `src/asap/transport/client.py`.
- **Tests Reviewed**: `tests/crypto/test_trust.py`, `tests/transport/test_mtls.py`, `tests/test_cli.py`.
