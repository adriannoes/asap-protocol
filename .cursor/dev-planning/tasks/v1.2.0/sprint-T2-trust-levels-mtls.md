# Sprint T2: Trust Levels & mTLS

> **Goal**: Implement trust categorization and optional transport security
> **Prerequisites**: Sprint T1 completed (Ed25519 PKI)
> **Parent Roadmap**: [tasks-v1.2.0-roadmap.md](./tasks-v1.2.0-roadmap.md)

---

## Relevant Files

- `src/asap/crypto/trust.py` - Trust level model and detection
- `src/asap/crypto/models.py` - SignatureBlock with trust_level
- `src/asap/transport/mtls.py` - mTLS support
- `tests/crypto/test_trust.py` - Trust level tests
- `tests/transport/test_mtls.py` - mTLS tests
- `tests/fixtures/asap_ca/` - Test CA keypair
- `docs/security/mtls.md` - mTLS setup documentation

---

## Context

Trust Levels categorize agents by verification degree. mTLS provides transport-layer security for enterprise deployments. Both are optional, following design decision SD-6.

---

## Task 2.1: Trust Levels

**Goal**: Implement 3-tier trust model (self-signed, verified, enterprise).

**Prerequisites**: Task 1.3 completed

### Sub-tasks

- [ ] 2.1.1 Create trust module
  - **File**: `src/asap/crypto/trust.py` (create new)
  - **Verify**: Module imports

- [ ] 2.1.2 Define TrustLevel enum
  - **File**: `src/asap/crypto/trust.py`
  - **What**:
    ```python
    class TrustLevel(str, Enum):
        SELF_SIGNED = "self-signed"   # Free, agent-signed
        VERIFIED = "verified"          # ASAP CA verified ($49/mo)
        ENTERPRISE = "enterprise"      # Org CA signed
    ```
  - **Verify**: Enum values serialize correctly to JSON

- [ ] 2.1.3 Add trust level to SignatureBlock
  - **File**: `src/asap/crypto/models.py`
  - **What**: Add `trust_level: TrustLevel` to SignatureBlock
  - **Verify**: SignedManifest includes trust_level

- [ ] 2.1.4 Implement trust level detection
  - **File**: `src/asap/crypto/trust.py`
  - **What**: `detect_trust_level(signed_manifest) -> TrustLevel`
  - **Verify**: Correct level detected for each type

- [ ] 2.1.5 Add trust level display
  - **What**: Show trust level in CLI manifest info, client logs, discovery responses
  - **Verify**: Trust level visible in all contexts

- [ ] 2.1.6 Write tests
  - **File**: `tests/crypto/test_trust.py` (create new)
  - **Verify**: `pytest tests/crypto/test_trust.py -v` all pass

- [ ] 2.1.7 Commit milestone
  - **Command**: `git commit -m "feat(crypto): add 3-tier trust levels"`

**Acceptance Criteria**:
- [ ] Trust levels defined and serializable
- [ ] Automatic detection works
- [ ] Visibility in CLI/logs

---

## Task 2.2: Verified Badge Simulation

**Goal**: Simulate ASAP CA signing for testing (full service in v2.0).

**Prerequisites**: Task 2.1 completed

### Sub-tasks

- [ ] 2.2.1 Create test ASAP CA keypair
  - **File**: `tests/fixtures/asap_ca/` (create dir)
  - **Verify**: CA key files exist

- [ ] 2.2.2 Implement CA signing function
  - **File**: `src/asap/crypto/trust.py`
  - **Dependencies**: Use `asap.crypto.signing.canonicalize` (JCS)
  - **What**: `sign_with_ca(manifest, agent_key, ca_key) -> SignedManifest`
  - **Constraint**: Must use JCS canonicalization before signing.
  - **Verify**: Result has trust_level=VERIFIED

- [ ] 2.2.3 Implement CA verification
  - **File**: `src/asap/crypto/trust.py`
  - **What**: `verify_ca_signature(signed_manifest, known_cas) -> bool`
  - **Verify**: Rejects unknown CAs

- [ ] 2.2.4 Add test fixtures
  - **File**: `tests/fixtures/`
  - **What**: `verified_manifest.json`, `self_signed_manifest.json`
  - **Verify**: Fixtures load and validate

- [ ] 2.2.5 Write tests
  - **File**: `tests/crypto/test_trust.py` (modify)
  - **Verify**: All CA scenarios covered

- [ ] 2.2.6 Commit milestone
  - **Command**: `git commit -m "feat(crypto): add Verified badge simulation"`

**Acceptance Criteria**:
- [ ] CA signing works
- [ ] CA verification works
- [ ] Unknown CAs rejected

---

## Task 2.3: Optional mTLS Support

**Goal**: Mutual TLS for transport security in enterprise deployments.

**Prerequisites**: Task 2.2 completed

### Sub-tasks

- [ ] 2.3.1 Create mTLS module
  - **File**: `src/asap/transport/mtls.py` (create new)
  - **Verify**: Module imports

- [ ] 2.3.2 Implement mTLS context builder
  - **File**: `src/asap/transport/mtls.py`
  - **What**: `MTLSConfig` and `create_ssl_context(config) -> ssl.SSLContext`
  - **Verify**: SSL context created successfully

- [ ] 2.3.3 Integrate mTLS with ASAPServer
  - **File**: `src/asap/transport/server.py`
  - **What**: Optional `mtls_config` parameter
  - **Verify**: Server works with and without mTLS

- [ ] 2.3.4 Integrate mTLS with ASAPClient
  - **File**: `src/asap/transport/client.py`
  - **What**: Optional `mtls_config` parameter
  - **Verify**: Client can connect to mTLS server

- [ ] 2.3.5 Document mTLS setup
  - **File**: `docs/security/mtls.md` (create new)
  - **What**: Cert generation, configuration, use cases
  - **Verify**: Docs are accurate and complete

- [ ] 2.3.6 Write tests
  - **File**: `tests/transport/test_mtls.py` (create new)
  - **Verify**: `pytest tests/transport/test_mtls.py -v` all pass

- [ ] 2.3.7 Commit milestone
  - **Command**: `git commit -m "feat(transport): add optional mTLS support"`

**Acceptance Criteria**:
- [ ] mTLS available as opt-in
- [ ] Non-mTLS still works (backward compat)
- [ ] Documentation complete

---

## Task 2.4: Mark Sprint T2 Complete

### Sub-tasks

- [ ] 2.4.1 Update roadmap progress
  - **File**: `tasks-v1.2.0-roadmap.md`
  - **Verify**: Progress shows 33% for v1.2.0

- [ ] 2.4.2 Verify all crypto goals achieved
  - **What**: Manual verification checklist

- [ ] 2.4.3 Run crypto test suite
  - **Command**: `pytest tests/crypto tests/transport/test_mtls.py -v --cov`
  - **Verify**: All tests pass, coverage >95%

- [ ] 2.4.4 Commit checkpoint
  - **Command**: `git commit -m "chore: mark v1.2.0 T1-T2 complete"`

**Acceptance Criteria**:
- [ ] All T1-T2 tasks complete
- [ ] Test suite passes

---

## Sprint T2 Definition of Done

- [ ] 3-tier trust levels implemented
- [ ] Verified badge simulation working
- [ ] mTLS optional and working
- [ ] Test coverage >95%
- [ ] Progress tracked in roadmap

**Total Sub-tasks**: ~30
