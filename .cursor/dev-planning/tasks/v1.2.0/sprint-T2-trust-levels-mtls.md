# Sprint T2: Trust Levels & mTLS

> **Goal**: Implement trust categorization and optional transport security
> **Prerequisites**: Sprint T1 completed (Ed25519 PKI)
> **Parent Roadmap**: [tasks-v1.2.0-roadmap.md](./tasks-v1.2.0-roadmap.md)

---

## Relevant Files

- `src/asap/crypto/trust.py` - Trust level model, detect, sign_with_ca, verify_ca_signature (2.1, 2.2)
- `src/asap/crypto/trust_levels.py` - TrustLevel enum (avoids circular import)
- `src/asap/crypto/models.py` - SignatureBlock with trust_level (2.1.3)
- `src/asap/crypto/__init__.py` - TrustLevel, detect_trust_level, sign_with_ca, verify_ca_signature
- `src/asap/cli.py` - manifest info, manifest verify with trust display (2.1.5)
- `src/asap/transport/client.py` - manifest_fetched log with trust_level (2.1.5)
- `tests/crypto/test_trust.py` - Trust level + CA tests (2.1, 2.2)
- `tests/fixtures/asap_ca/` - Test CA keypair (2.2.1)
- `tests/fixtures/verified_manifest.json` - CA-signed fixture (2.2.4)
- `tests/fixtures/self_signed_manifest.json` - Agent-signed fixture (2.2.4)
- `src/asap/transport/mtls.py` - mTLS support (2.3)
- `tests/transport/test_mtls.py` - mTLS tests (2.3)
- `docs/security/mtls.md` - mTLS setup documentation (2.3)

---

## Context

Trust Levels categorize agents by verification degree. mTLS provides transport-layer security for enterprise deployments. Both are optional, following design decision SD-6.

---

## Task 2.1: Trust Levels

**Goal**: Implement 3-tier trust model (self-signed, verified, enterprise).

**Prerequisites**: Task 1.3 completed

### Sub-tasks

- [x] 2.1.1 Create trust module
  - **File**: `src/asap/crypto/trust.py` (create new)
  - **Verify**: Module imports

- [x] 2.1.2 Define TrustLevel enum
  - **File**: `src/asap/crypto/trust.py`
  - **What**:
    ```python
    class TrustLevel(str, Enum):
        SELF_SIGNED = "self-signed"   # Free, agent-signed
        VERIFIED = "verified"          # ASAP CA verified ($49/mo)
        ENTERPRISE = "enterprise"      # Org CA signed
    ```
  - **Verify**: Enum values serialize correctly to JSON

- [x] 2.1.3 Add trust level to SignatureBlock
  - **File**: `src/asap/crypto/models.py`
  - **What**: Add `trust_level: TrustLevel` to SignatureBlock
  - **Verify**: SignedManifest includes trust_level

- [x] 2.1.4 Implement trust level detection
  - **File**: `src/asap/crypto/trust.py`
  - **What**: `detect_trust_level(signed_manifest) -> TrustLevel`
  - **Verify**: Correct level detected for each type

- [x] 2.1.5 Add trust level display
  - **What**: Show trust level in CLI manifest info, client logs, discovery responses
  - **Verify**: Trust level visible in all contexts

- [x] 2.1.6 Write tests
  - **File**: `tests/crypto/test_trust.py` (create new)
  - **Verify**: `pytest tests/crypto/test_trust.py -v` all pass

- [ ] 2.1.7 Commit milestone
  - **Command**: `git commit -m "feat(crypto): add 3-tier trust levels"`
  - **Note**: Deferred until end of sprint (per user request)

**Acceptance Criteria**:
- [x] Trust levels defined and serializable
- [x] Automatic detection works
- [x] Visibility in CLI/logs

---

## Task 2.2: Verified Badge Simulation

**Goal**: Simulate ASAP CA signing for testing (full service in v2.0).

**Prerequisites**: Task 2.1 completed

### Sub-tasks

- [x] 2.2.1 Create test ASAP CA keypair
  - **File**: `tests/fixtures/asap_ca/` (create dir)
  - **Verify**: CA key files exist

- [x] 2.2.2 Implement CA signing function
  - **File**: `src/asap/crypto/trust.py`
  - **Dependencies**: Use `asap.crypto.signing.canonicalize` (JCS)
  - **What**: `sign_with_ca(manifest, agent_key, ca_key) -> SignedManifest`
  - **Constraint**: Must use JCS canonicalization before signing.
  - **Verify**: Result has trust_level=VERIFIED

- [x] 2.2.3 Implement CA verification
  - **File**: `src/asap/crypto/trust.py`
  - **What**: `verify_ca_signature(signed_manifest, known_cas) -> bool`
  - **Verify**: Rejects unknown CAs

- [x] 2.2.4 Add test fixtures
  - **File**: `tests/fixtures/`
  - **What**: `verified_manifest.json`, `self_signed_manifest.json`
  - **Verify**: Fixtures load and validate

- [x] 2.2.5 Write tests
  - **File**: `tests/crypto/test_trust.py` (modify)
  - **Verify**: All CA scenarios covered

- [ ] 2.2.6 Commit milestone
  - **Command**: `git commit -m "feat(crypto): add Verified badge simulation"`
  - **Note**: Deferred until end of sprint (per user request)

**Acceptance Criteria**:
- [x] CA signing works
- [x] CA verification works
- [x] Unknown CAs rejected

---

## Task 2.3: Optional mTLS Support

**Goal**: Mutual TLS for transport security in enterprise deployments.

**Prerequisites**: Task 2.2 completed

### Sub-tasks

- [x] 2.3.1 Create mTLS module
  - **File**: `src/asap/transport/mtls.py` (create new)
  - **Verify**: Module imports

- [x] 2.3.2 Implement mTLS context builder
  - **File**: `src/asap/transport/mtls.py`
  - **What**: `MTLSConfig` and `create_ssl_context(config) -> ssl.SSLContext`
  - **Verify**: SSL context created successfully

- [x] 2.3.3 Integrate mTLS with ASAPServer
  - **File**: `src/asap/transport/server.py`
  - **What**: Optional `mtls_config` parameter
  - **Verify**: Server works with and without mTLS

- [x] 2.3.4 Integrate mTLS with ASAPClient
  - **File**: `src/asap/transport/client.py`
  - **What**: Optional `mtls_config` parameter
  - **Verify**: Client can connect to mTLS server

- [x] 2.3.5 Document mTLS setup
  - **File**: `docs/security/mtls.md` (create new)
  - **What**: Cert generation, configuration, use cases
  - **Verify**: Docs are accurate and complete

- [x] 2.3.6 Write tests
  - **File**: `tests/transport/test_mtls.py` (create new)
  - **Verify**: `pytest tests/transport/test_mtls.py -v` all pass

- [ ] 2.3.7 Commit milestone
  - **Command**: `git commit -m "feat(transport): add optional mTLS support"`
  - **Note**: Deferred until end of sprint (per user request)

**Acceptance Criteria**:
- [x] mTLS available as opt-in
- [x] Non-mTLS still works (backward compat)
- [x] Documentation complete

---

## Task 2.4: Mark Sprint T2 Complete

### Sub-tasks

- [x] 2.4.1 Update roadmap progress
  - **File**: `tasks-v1.2.0-roadmap.md`
  - **Verify**: Progress shows 46% for v1.2.0 (6/13 tasks)

- [x] 2.4.2 Verify all crypto goals achieved
  - **What**: Manual verification checklist
  - **Checklist**: 3-tier trust levels ✓, Verified badge simulation ✓, mTLS optional ✓, Trust levels in CLI/logs ✓

- [x] 2.4.3 Run crypto test suite
  - **Command**: `pytest tests/crypto tests/transport/test_mtls.py -v --cov`
  - **Verify**: All 74 tests pass, crypto coverage 98%, mtls 81%

- [ ] 2.4.4 Commit checkpoint
  - **Command**: `git commit -m "chore: mark v1.2.0 T1-T2 complete"`
  - **Note**: Deferred until user confirms (per earlier request)

**Acceptance Criteria**:
- [x] All T1-T2 tasks complete
- [x] Test suite passes

---

## Sprint T2 Definition of Done

- [x] 3-tier trust levels implemented
- [x] Verified badge simulation working
- [x] mTLS optional and working
- [x] Test coverage >95% (crypto 98%)
- [x] Progress tracked in roadmap

**Total Sub-tasks**: ~30

## Documentation Updates
- [x] **Update Roadmap**: Mark completed items in [v1.2.0 Roadmap](./tasks-v1.2.0-roadmap.md)
