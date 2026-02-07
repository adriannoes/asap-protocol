# Tasks: ASAP v1.2.0 PKI & Signing (T1-T2) - Detailed

> **Sprints**: T1-T2 - Ed25519 signing and Trust Levels
> **Goal**: Cryptographic identity and verification infrastructure
> **Prerequisites**: v1.1.0 completed (OAuth2, Discovery)
> **Estimated Duration**: 2 weeks

---

## Relevant Files

### Sprint T1: Ed25519 PKI
- `src/asap/crypto/__init__.py` - Crypto module init
- `src/asap/crypto/keys.py` - Key generation and management
- `src/asap/crypto/signing.py` - Manifest signing
- `tests/crypto/test_keys.py` - Key tests
- `tests/crypto/test_signing.py` - Signing tests

### Sprint T2: Trust Levels & mTLS
- `src/asap/crypto/trust.py` - Trust level model
- `src/asap/transport/mtls.py` - mTLS support
- `tests/crypto/test_trust.py` - Trust level tests
- `tests/transport/test_mtls.py` - mTLS tests

---

## Sprint T1: Ed25519 PKI Foundation

**Context**: Cryptographic signatures enable agents to prove authenticity without centralized trust. Ed25519 provides fast, secure signing with 64-byte signatures. This is the foundation for the Trust Layer.

### Task 1.1: Key Management

**Goal**: Generate, store, and load Ed25519 keypairs for agent identity.

**Context**: Each agent needs a unique keypair. The private key signs manifests; the public key verifies them. Keys must be storable in files, environment variables, or config.

**Prerequisites**: None (first task of v1.2.0)

#### Sub-tasks

- [ ] 1.1.1 Add cryptography dependency
  - **File**: `pyproject.toml` (modify)
  - **What**: Add `cryptography>=41.0` to dependencies
  - **Why**: cryptography has native Ed25519 support, well-audited
  - **Command**: `uv add "cryptography>=41.0"`
  - **Verify**: `uv run python -c "from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey"`

- [ ] 1.1.2 Create crypto module structure
  - **File**: `src/asap/crypto/__init__.py` (create new)
  - **File**: `src/asap/crypto/keys.py` (create new)
  - **What**: Create crypto module with key management skeleton
  - **Why**: Separates cryptographic concerns from transport layer
  - **Pattern**: Follow structure of `src/asap/auth/` module
  - **Verify**: `from asap.crypto import keys` imports without error

- [ ] 1.1.3 Implement key generation
  - **File**: `src/asap/crypto/keys.py` (modify)
  - **What**: Create functions:
    - `generate_keypair() -> (Ed25519PrivateKey, Ed25519PublicKey)`
    - Uses cryptography library's Ed25519 implementation
  - **Why**: Core capability - every agent needs a keypair
  - **Reference**: https://cryptography.io/en/latest/hazmat/primitives/asymmetric/ed25519/
  - **Verify**: Generated key can sign and verify a message

- [ ] 1.1.4 Implement key serialization
  - **File**: `src/asap/crypto/keys.py` (modify)
  - **What**: Add functions:
    - `serialize_private_key(key) -> bytes` (PEM format)
    - `serialize_public_key(key) -> bytes` (PEM format)
    - `public_key_to_base64(key) -> str` (for manifest embedding)
  - **Why**: PEM for file storage, Base64 for JSON embedding
  - **Pattern**: Use cryptography's serialization module
  - **Verify**: Roundtrip: serialize → deserialize → compare

- [ ] 1.1.5 Implement key loading
  - **File**: `src/asap/crypto/keys.py` (modify)
  - **What**: Add functions:
    - `load_private_key_from_file(path: Path) -> Ed25519PrivateKey`
    - `load_private_key_from_pem(pem: bytes) -> Ed25519PrivateKey`
    - `load_private_key_from_env(var_name: str) -> Ed25519PrivateKey`
  - **Why**: Flexible loading for different deployment scenarios
  - **Verify**: Load key from all three sources successfully

- [ ] 1.1.6 Add key metadata and rotation warnings
  - **File**: `src/asap/crypto/keys.py` (modify)
  - **What**: Add `KeyMetadata` model tracking creation time, warn if key > 1 year old
  - **Why**: Old keys are security risk, rotation should be encouraged
  - **Verify**: Warning logged for key older than 365 days

- [ ] 1.1.7 Write comprehensive unit tests
  - **File**: `tests/crypto/__init__.py` (create new)
  - **File**: `tests/crypto/test_keys.py` (create new)
  - **What**: Test scenarios:
    - Key generation produces valid keys
    - Serialization roundtrip preserves key
    - Loading from file/PEM/env works
    - Rotation warning fires correctly
  - **Pattern**: Follow test patterns in `tests/auth/`
  - **Verify**: `pytest tests/crypto/test_keys.py -v` all pass

- [ ] 1.1.8 Commit milestone
  - **Command**: `git add src/asap/crypto/ tests/crypto/ pyproject.toml && git commit -m "feat(crypto): add Ed25519 key management"`
  - **Verify**: `git log -1` shows correct message

**Acceptance Criteria**:
- [ ] Keys can be generated, stored, and loaded
- [ ] Multiple loading sources supported
- [ ] Rotation warnings implemented
- [ ] Test coverage >95%

---

### Task 1.2: Manifest Signing

**Goal**: Sign agent manifests with Ed25519 for authenticity verification.

**Context**: A signed manifest proves the manifest was created by the holder of the private key. This prevents tampering and impersonation.

**Prerequisites**: Task 1.1 completed

#### Sub-tasks

- [ ] 1.2.1 Create signing module
  - **File**: `src/asap/crypto/signing.py` (create new)
  - **What**: Create module skeleton with imports
  - **Why**: Separates signing logic from key management
  - **Verify**: Module imports without error

- [ ] 1.2.2 Implement canonical JSON serialization
  - **File**: `src/asap/crypto/signing.py` (modify)
  - **What**: Create `canonicalize(manifest: Manifest) -> bytes`:
    - Deterministic JSON (sorted keys, no whitespace)
    - Required for reproducible signatures
  - **Why**: Same manifest must always produce same bytes for signing
  - **Pattern**: Use `json.dumps(sort_keys=True, separators=(',', ':'))`
  - **Verify**: Two calls with same manifest produce identical bytes

- [ ] 1.2.3 Implement signing function
  - **File**: `src/asap/crypto/signing.py` (modify)
  - **What**: Create `sign_manifest(manifest: Manifest, private_key) -> SignedManifest`:
    - Canonicalize manifest
    - Sign with Ed25519 (produces 64 bytes)
    - Return SignedManifest with embedded signature
  - **Why**: Core signing functionality
  - **Verify**: Signature is exactly 64 bytes

- [ ] 1.2.4 Define SignedManifest and SignatureBlock models
  - **File**: `src/asap/crypto/models.py` (create new)
  - **What**: Create Pydantic models:
    ```python
    class SignatureBlock(BaseModel):
        algorithm: Literal["Ed25519"]
        public_key: str  # Base64 encoded
        value: str  # Base64, 64 bytes
        signed_at: datetime
    
    class SignedManifest(BaseModel):
        manifest: Manifest
        signature: SignatureBlock
    ```
  - **Why**: Structured format for signed manifests
  - **Verify**: Model validates correctly

- [ ] 1.2.5 Add CLI command for signing
  - **File**: `src/asap/cli.py` (modify existing)
  - **What**: Add command:
    - `asap manifest sign --key private.pem manifest.json`
    - Outputs signed-manifest.json
  - **Why**: Developer ergonomics for signing manifests
  - **Pattern**: Follow existing CLI patterns
  - **Verify**: `asap manifest sign --help` shows usage

- [ ] 1.2.6 Write tests
  - **File**: `tests/crypto/test_signing.py` (create new)
  - **What**: Test scenarios:
    - Signing produces valid signature
    - Different manifests = different signatures
    - Same manifest = same signature (deterministic)
    - CLI command works end-to-end
  - **Verify**: `pytest tests/crypto/test_signing.py -v` all pass

- [ ] 1.2.7 Commit milestone
  - **Command**: `git commit -m "feat(crypto): add manifest signing with Ed25519"`
  - **Verify**: Clean commit

**Acceptance Criteria**:
- [ ] Manifests can be signed
- [ ] Signatures are deterministic
- [ ] CLI available for signing

---

### Task 1.3: Signature Verification

**Goal**: Verify signed manifests to detect tampering.

**Context**: The counterpart to signing - receivers verify signatures to ensure manifests are authentic and unmodified.

**Prerequisites**: Task 1.2 completed

#### Sub-tasks

- [ ] 1.3.1 Implement verification function
  - **File**: `src/asap/crypto/signing.py` (modify)
  - **What**: Create `verify_manifest(signed_manifest: SignedManifest) -> bool`:
    - Extract public key from signature block
    - Canonicalize manifest
    - Verify Ed25519 signature
  - **Why**: Core verification functionality
  - **Verify**: Valid signatures return True, invalid return False

- [ ] 1.3.2 Integrate verification with ASAPClient
  - **File**: `src/asap/transport/client.py` (modify)
  - **What**: Add option `ASAPClient(verify_signatures=True)`:
    - When enabled, verify manifests on discovery
    - Reject manifests with invalid signatures
  - **Why**: Opt-in security for clients
  - **Pattern**: Similar to OAuth2 opt-in pattern
  - **Verify**: Client rejects tampered manifest

- [ ] 1.3.3 Add verification to registry discovery
  - **File**: `src/asap/discovery/validation.py` (modify)
  - **What**: Verify signatures when fetching from registry
  - **Why**: Registry manifests should be verified
  - **Verify**: Invalid registry manifest rejected

- [ ] 1.3.4 Implement tampering detection with clear errors
  - **File**: `src/asap/crypto/signing.py` (modify)
  - **What**: Raise descriptive `SignatureVerificationError` with:
    - What was expected vs found
    - Which field appears modified
  - **Why**: Clear errors help debugging
  - **Verify**: Error message identifies tampering

- [ ] 1.3.5 Add CLI verification command
  - **File**: `src/asap/cli.py` (modify)
  - **What**: Add command: `asap manifest verify signed-manifest.json`
  - **Why**: Developer tool for verification
  - **Verify**: `asap manifest verify --help` works

- [ ] 1.3.6 Write tests
  - **File**: `tests/crypto/test_signing.py` (modify)
  - **What**: Test scenarios:
    - Valid signature passes
    - Tampered manifest fails
    - Wrong key fails
    - Clear error messages
  - **Verify**: All verification scenarios covered

- [ ] 1.3.7 Commit milestone
  - **Command**: `git commit -m "feat(crypto): add signature verification"`
  - **Verify**: Clean commit

**Acceptance Criteria**:
- [ ] Verification detects tampering
- [ ] Client integration works
- [ ] Clear error messages

---

## Sprint T2: Trust Levels & mTLS

**Context**: Trust Levels categorize agents by verification degree. mTLS provides transport-layer security for enterprise deployments.

### Task 2.1: Trust Levels

**Goal**: Implement 3-tier trust model (self-signed, verified, enterprise).

**Context**: Different deployment scenarios need different trust levels. Self-signed is free, verified involves ASAP CA review, enterprise uses organization's CA.

**Prerequisites**: Task 1.3 completed

#### Sub-tasks

- [ ] 2.1.1 Create trust module
  - **File**: `src/asap/crypto/trust.py` (create new)
  - **What**: Create module for trust level handling
  - **Verify**: Module imports

- [ ] 2.1.2 Define TrustLevel enum
  - **File**: `src/asap/crypto/trust.py` (modify)
  - **What**: Create enum:
    ```python
    class TrustLevel(str, Enum):
        SELF_SIGNED = "self-signed"   # Free, agent-signed
        VERIFIED = "verified"          # ASAP CA verified ($49/mo)
        ENTERPRISE = "enterprise"      # Org CA signed
    ```
  - **Why**: Standardized trust categorization
  - **Verify**: Enum values serialize correctly to JSON

- [ ] 2.1.3 Add trust level to SignatureBlock
  - **File**: `src/asap/crypto/models.py` (modify)
  - **What**: Add `trust_level: TrustLevel` to SignatureBlock
  - **Why**: Trust level travels with signature
  - **Verify**: SignedManifest includes trust_level

- [ ] 2.1.4 Implement trust level detection
  - **File**: `src/asap/crypto/trust.py` (modify)
  - **What**: Create `detect_trust_level(signed_manifest) -> TrustLevel`:
    - ENTERPRISE if signed by known org CA
    - VERIFIED if signed by ASAP CA
    - SELF_SIGNED otherwise
  - **Why**: Automatic trust level detection
  - **Verify**: Correct level detected for each type

- [ ] 2.1.5 Add trust level display
  - **File**: Various (CLI, client logs)
  - **What**: Show trust level in:
    - CLI manifest info command
    - Client connection logs
    - Discovery responses
  - **Why**: Visibility for operators
  - **Verify**: Trust level visible in all contexts

- [ ] 2.1.6 Write tests
  - **File**: `tests/crypto/test_trust.py` (create new)
  - **What**: Test all trust levels and detection
  - **Verify**: `pytest tests/crypto/test_trust.py -v` all pass

- [ ] 2.1.7 Commit milestone
  - **Command**: `git commit -m "feat(crypto): add 3-tier trust levels"`
  - **Verify**: Clean commit

**Acceptance Criteria**:
- [ ] Trust levels defined and serializable
- [ ] Automatic detection works
- [ ] Visibility in CLI/logs

---

### Task 2.2: Verified Badge Simulation

**Goal**: Simulate ASAP CA signing for testing (full service in v2.0).

**Context**: The Verified badge requires ASAP CA signature. For v1.2.0, we simulate this for testing the verification flow.

**Prerequisites**: Task 2.1 completed

#### Sub-tasks

- [ ] 2.2.1 Create test ASAP CA keypair
  - **File**: `tests/fixtures/asap_ca/` (create dir)
  - **What**: Generate and store test CA keypair
  - **Why**: Needed for testing verified badge flow
  - **Verify**: CA key files exist

- [ ] 2.2.2 Implement CA signing function
  - **File**: `src/asap/crypto/trust.py` (modify)
  - **What**: Create `sign_with_ca(manifest, agent_key, ca_key) -> SignedManifest`:
    - Signs manifest with agent key
    - Adds CA counter-signature
  - **Why**: Simulates ASAP verification service
  - **Verify**: Result has trust_level=VERIFIED

- [ ] 2.2.3 Implement CA verification
  - **File**: `src/asap/crypto/trust.py` (modify)
  - **What**: Create `verify_ca_signature(signed_manifest, known_cas) -> bool`
  - **Why**: Verify CA chain before trusting VERIFIED status
  - **Verify**: Rejects unknown CAs

- [ ] 2.2.4 Add test fixtures
  - **File**: `tests/fixtures/` (add files)
  - **What**: Create:
    - `verified_manifest.json` - ASAP CA signed
    - `self_signed_manifest.json` - agent-only signed
  - **Why**: Test data for verification scenarios
  - **Verify**: Fixtures load and validate

- [ ] 2.2.5 Write tests
  - **File**: `tests/crypto/test_trust.py` (modify)
  - **What**: Test CA signing and verification
  - **Verify**: All CA scenarios covered

- [ ] 2.2.6 Commit milestone
  - **Command**: `git commit -m "feat(crypto): add Verified badge simulation"`
  - **Verify**: Clean commit

**Acceptance Criteria**:
- [ ] CA signing works
- [ ] CA verification works
- [ ] Unknown CAs rejected

---

### Task 2.3: Optional mTLS Support

**Goal**: Mutual TLS for transport security in enterprise deployments.

**Context**: mTLS provides additional transport-layer security. It's optional (never required) per design decision SD-6.

**Prerequisites**: Task 2.2 completed

#### Sub-tasks

- [ ] 2.3.1 Create mTLS module
  - **File**: `src/asap/transport/mtls.py` (create new)
  - **What**: Create module for mTLS configuration
  - **Verify**: Module imports

- [ ] 2.3.2 Implement mTLS context builder
  - **File**: `src/asap/transport/mtls.py` (modify)
  - **What**: Create `MTLSConfig` and `create_ssl_context(config) -> ssl.SSLContext`:
    - Load cert and key files
    - Configure client authentication
  - **Why**: Encapsulates SSL complexity
  - **Reference**: Python ssl module docs
  - **Verify**: SSL context created successfully

- [ ] 2.3.3 Integrate mTLS with ASAPServer
  - **File**: `src/asap/transport/server.py` (modify)
  - **What**: Add optional `mtls_config` parameter:
    - If provided, require client certs
    - If not provided, allow unauthenticated (default)
  - **Why**: Opt-in mTLS for those who need it
  - **Verify**: Server works with and without mTLS

- [ ] 2.3.4 Integrate mTLS with ASAPClient
  - **File**: `src/asap/transport/client.py` (modify)
  - **What**: Add optional `mtls_config` parameter:
    - Provides client cert/key for mutual auth
  - **Why**: Client side of mTLS handshake
  - **Verify**: Client can connect to mTLS server

- [ ] 2.3.5 Document mTLS setup
  - **File**: `docs/security/mtls.md` (create new)
  - **What**: Document:
    - How to generate certs (openssl commands)
    - How to configure server/client
    - When to use mTLS (enterprise use cases)
  - **Why**: mTLS is complex, needs documentation
  - **Verify**: Docs are accurate and complete

- [ ] 2.3.6 Write tests
  - **File**: `tests/transport/test_mtls.py` (create new)
  - **What**: Test scenarios:
    - mTLS connection succeeds
    - Non-mTLS still works (backward compat)
    - Invalid cert rejected
  - **Note**: May need test certs generated in fixtures
  - **Verify**: `pytest tests/transport/test_mtls.py -v` all pass

- [ ] 2.3.7 Commit milestone
  - **Command**: `git commit -m "feat(transport): add optional mTLS support"`
  - **Verify**: Clean commit

**Acceptance Criteria**:
- [ ] mTLS available as opt-in
- [ ] Non-mTLS still works
- [ ] Documentation complete

---

### Task 2.4: Mark Sprints T1-T2 Complete

**Goal**: Finalize PKI sprints and update tracking.

**Prerequisites**: Tasks 1.1-2.3 completed

#### Sub-tasks

- [ ] 2.4.1 Update roadmap progress
  - **File**: `tasks-v1.2.0-roadmap.md` (modify)
  - **What**: Mark T1-T2 tasks complete, update percentage
  - **Verify**: Progress shows 50% for v1.2.0

- [ ] 2.4.2 Verify all crypto goals achieved
  - **What**: Manual verification checklist:
    - Ed25519 key generation ✓
    - Manifest signing ✓
    - Signature verification ✓
    - Trust levels ✓
    - mTLS ✓
  - **Verify**: All items checked

- [ ] 2.4.3 Run crypto test suite
  - **Command**: `pytest tests/crypto tests/transport/test_mtls.py -v --cov`
  - **Verify**: All tests pass, coverage >95%

- [ ] 2.4.4 Commit checkpoint
  - **Command**: `git commit -m "chore: mark v1.2.0 T1-T2 complete"`
  - **Verify**: Clean commit

**Acceptance Criteria**:
- [ ] All T1-T2 tasks complete
- [ ] Test suite passes
- [ ] Progress tracked

---

**T1-T2 Definition of Done**:
- [ ] Ed25519 key generation and management
- [ ] Manifest signing with 64-byte signatures
- [ ] Verification rejects tampering
- [ ] 3-tier trust levels implemented
- [ ] mTLS optional and working
- [ ] Test coverage >95%

**Total Sub-tasks**: ~55

