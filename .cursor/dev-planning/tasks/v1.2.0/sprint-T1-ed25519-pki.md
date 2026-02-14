# Sprint T1: Ed25519 PKI Foundation

> **Goal**: Cryptographic identity for agent authentication
> **Prerequisites**: v1.1.0 completed (OAuth2, Discovery)
> **Parent Roadmap**: [tasks-v1.2.0-roadmap.md](./tasks-v1.2.0-roadmap.md)

---

## Relevant Files

- `pyproject.toml` - Added cryptography and jcs dependencies (1.1.1)
- `src/asap/crypto/__init__.py` - Crypto module init (1.1.2)
- `src/asap/crypto/keys.py` - Key generation and management (1.1.2)
- `src/asap/crypto/signing.py` - Manifest signing
- `src/asap/crypto/models.py` - SignedManifest and SignatureBlock models
- `tests/crypto/__init__.py` - Crypto test package (1.1.7)
- `tests/crypto/test_keys.py` - Key unit tests (1.1.7)
- `src/asap/cli.py` - Added `asap keys generate --out`, `asap manifest sign` (1.1.8, 1.2.5)
- `src/asap/crypto/models.py` - SignedManifest, SignatureBlock (1.2.4)
- `src/asap/crypto/signing.py` - canonicalize, sign_manifest (1.2.1–1.2.3)
- `tests/crypto/test_signing.py` - Signing unit tests (1.2.6), verification tests (1.3.6)
- `src/asap/crypto/signing.py` - verify_manifest (1.3.1, 1.3.4)
- `src/asap/crypto/keys.py` - load_public_key_from_base64 (1.3)
- `src/asap/errors.py` - SignatureVerificationError (1.3.4)
- `src/asap/transport/client.py` - verify_signatures, signed manifest (1.3.2)
- `src/asap/discovery/validation.py` - validate_signed_manifest_response (1.3.3)
- `src/asap/cli.py` - asap manifest verify (1.3.5)

---

## Context

Cryptographic signatures enable agents to prove authenticity without centralized trust. Ed25519 provides fast, secure signing with 64-byte signatures. This is the foundation for the Trust Layer.

---

## Task 1.1: Key Management

**Goal**: Generate, store, and load Ed25519 keypairs for agent identity.

**Context**: Each agent needs a unique keypair. The private key signs manifests; the public key verifies them.

**Prerequisites**: None (first task of v1.2.0)

### Sub-tasks

- [x] 1.1.1 Add cryptography and JCS dependencies
  - **File**: `pyproject.toml` (modify)
  - **What**: Add `cryptography>=41.0` and `jcs>=0.2.0` (RFC 8785)
  - **Command**: `uv add "cryptography>=41.0" "jcs>=0.2.0"`
  - **Verify**: `uv run python -c "import jcs; from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey"`

- [x] 1.1.2 Create crypto module structure
  - **File**: `src/asap/crypto/__init__.py` (create new)
  - **File**: `src/asap/crypto/keys.py` (create new)
  - **Pattern**: Follow structure of `src/asap/auth/` module
  - **Verify**: `from asap.crypto import keys` imports without error

- [x] 1.1.3 Implement key generation
  - **File**: `src/asap/crypto/keys.py`
  - **What**: `generate_keypair() -> (Ed25519PrivateKey, Ed25519PublicKey)`
  - **Reference**: https://cryptography.io/en/latest/hazmat/primitives/asymmetric/ed25519/
  - **Verify**: Generated key can sign and verify a message

- [x] 1.1.4 Implement key serialization
  - **File**: `src/asap/crypto/keys.py`
  - **What**: `serialize_private_key(key) -> bytes` (PEM), `public_key_to_base64(key) -> str`
  - **Verify**: Roundtrip: serialize → deserialize → compare

- [x] 1.1.5 Implement key loading
  - **File**: `src/asap/crypto/keys.py`
  - **What**: `load_private_key_from_file(path)`, `load_private_key_from_pem(pem)`, `load_private_key_from_env(var_name)`
  - **Verify**: Load key from all three sources successfully

- [x] 1.1.6 Add key metadata and rotation warnings
  - **File**: `src/asap/crypto/keys.py`
  - **What**: `KeyMetadata` model tracking creation time, warn if key > 1 year old
  - **Verify**: Warning logged for key older than 365 days

- [x] 1.1.7 Write comprehensive unit tests
  - **File**: `tests/crypto/__init__.py` (create new)
  - **File**: `tests/crypto/test_keys.py` (create new)
  - **Verify**: `pytest tests/crypto/test_keys.py -v` all pass

- [x] 1.1.8 Add CLI command for key generation
  - **File**: `src/asap/cli.py` (modify/create)
  - **What**: `asap keys generate --out private.pem`
  - **Security**: Warn if file permissions are too open (enforce `0600` on creation).
  - **Note**: Native Keyring integration deferred to future release (ADR-18).
  - **Verify**: Command creates a valid key file with strict permissions

- [x] 1.1.9 Commit milestone
  - **Command**: `git commit -m "feat(crypto): add Ed25519 key management"`

**Acceptance Criteria**:
- [x] Keys can be generated, stored and loaded
- [x] Multiple loading sources supported
- [x] Test coverage >95%

---

## Task 1.2: Manifest Signing

**Goal**: Sign agent manifests with Ed25519 for authenticity verification.

**Prerequisites**: Task 1.1 completed

### Sub-tasks

- [x] 1.2.1 Create signing module
  - **File**: `src/asap/crypto/signing.py` (create new)
  - **Verify**: Module imports without error

- [x] 1.2.2 Implement JCS canonicalization (RFC 8785)
  - **File**: `src/asap/crypto/signing.py`
  - **Library**: `jcs`
  - **What**: `canonicalize(manifest: Manifest) -> bytes`
  - **Constraint**: Must use JCS, not custom JSON sorting.
  - **Verify**: Two calls with same manifest (different key order) produce identical bytes

- [x] 1.2.3 Implement signing function
  - **File**: `src/asap/crypto/signing.py`
  - **What**: `sign_manifest(manifest, private_key) -> SignedManifest`
  - **Verify**: Signature is exactly 64 bytes

- [x] 1.2.4 Define SignedManifest and SignatureBlock models
  - **File**: `src/asap/crypto/models.py` (create new)
  - **Fields**: `SignatureBlock` must include `alg: Literal["ed25519"]` (ADR-18).
  - **Verify**: Model validates correctly and rejects unknown algorithms

- [x] 1.2.5 Add CLI command for signing
  - **File**: `src/asap/cli.py` (modify)
  - **What**: `asap manifest sign --key private.pem manifest.json`
  - **Verify**: `asap manifest sign --help` shows usage

- [x] 1.2.6 Write tests
  - **File**: `tests/crypto/test_signing.py` (create new)
  - **Verify**: `pytest tests/crypto/test_signing.py -v` all pass

- [x] 1.2.7 Commit milestone
  - **Command**: `git commit -m "feat(crypto): add manifest signing with Ed25519"`

**Acceptance Criteria**:
- [x] Manifests can be signed
- [x] Signatures are deterministic
- [x] CLI available for signing

---

## Task 1.3: Signature Verification

**Goal**: Verify signed manifests to detect tampering.

**Prerequisites**: Task 1.2 completed

### Sub-tasks

- [x] 1.3.1 Implement verification function (Strict)
  - **File**: `src/asap/crypto/signing.py`
  - **What**: `verify_manifest(signed_manifest) -> bool`
  - **Security**: Enforce `alg: "ed25519"` check.
  - **Security**: Use RFC 8032 strict verification (reject malleable signatures).
  - **Verify**: Valid signatures return True, invalid return False

- [x] 1.3.2 Integrate verification with ASAPClient
  - **File**: `src/asap/transport/client.py`
  - **What**: `ASAPClient(verify_signatures=True)` option
  - **Verify**: Client rejects tampered manifest

- [x] 1.3.3 Add verification to registry discovery
  - **File**: `src/asap/discovery/validation.py`
  - **Verify**: Invalid registry manifest rejected

- [x] 1.3.4 Implement tampering detection with clear errors
  - **File**: `src/asap/crypto/signing.py`
  - **What**: Raise descriptive `SignatureVerificationError`
  - **Verify**: Error message identifies tampering

- [x] 1.3.5 Add CLI verification command
  - **File**: `src/asap/cli.py`
  - **What**: `asap manifest verify signed-manifest.json`

- [x] 1.3.6 Write tests
  - **File**: `tests/crypto/test_signing.py` (modify)
  - **Verify**: All verification scenarios covered

- [x] 1.3.7 Commit milestone
  - **Command**: `git commit -m "feat(crypto): add signature verification"`

**Acceptance Criteria**:
- [x] Verification detects tampering
- [x] Client integration works
- [x] Clear error messages

---

## Sprint T1 Definition of Done

- [x] Ed25519 key generation and management
- [x] Manifest signing with 64-byte signatures
- [x] Verification rejects tampering
- [x] CLI commands for sign/verify
- [x] Test coverage >95%

**Total Sub-tasks**: ~25

## Documentation Updates
- [x] **Update Roadmap**: Mark completed items in [v1.2.0 Roadmap](./tasks-v1.2.0-roadmap.md)
