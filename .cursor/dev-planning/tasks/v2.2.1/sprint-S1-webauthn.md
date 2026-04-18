# Sprint S1: Real WebAuthn Verification

**PRD**: [v2.2.1 §4.1](../../../product-specs/prd/prd-v2.2.1-patch.md) — WAUTH-001..008 (P0)
**Branch**: `feat/webauthn-real`
**PR Scope**: Replace the `WebAuthnVerifier` placeholder with a concrete implementation backed by the `webauthn` (or `fido2`) library. Behind opt-in extra `asap-protocol[webauthn]` for backward compatibility.
**Depends on**: v2.2.0 (`auth/self_auth.py` with `WebAuthnVerifier` Protocol)

## Relevant Files

### New Files
- `src/asap/auth/webauthn.py` — `WebAuthnVerifierImpl`, `WebAuthnCredentialStore` Protocol, `InMemoryWebAuthnCredentialStore`, `SQLiteWebAuthnCredentialStore`
- `tests/auth/test_webauthn.py` — TDD unit tests (NONE + EC2 vectors); RED until `asap.auth.webauthn` exists
- `tests/auth/integration/test_webauthn_flow.py` — End-to-end registration + assertion flow

### Modified Files
- `pyproject.toml` — Optional extra `webauthn` → `webauthn>=2.6` (completed in 1.1)
- `src/asap/auth/self_auth.py` — Wire `WebAuthnVerifierImpl` as default when extra is installed; keep placeholder fallback otherwise
- `src/asap/auth/__init__.py` — Export new types behind `__all__`
- `docs/security/self-authorization-prevention.md` — Section "Real WebAuthn" documenting the threat model with concrete verification
- `docs/migration.md` — Note `[webauthn]` extra installation

## Tasks

### 1.0 Dependency & Scaffolding (TDD-first)

- [x] 1.1 Add `webauthn>=2.6` as optional extra
  - **File**: `pyproject.toml` (modify)
  - **What**: `[project.optional-dependencies] webauthn = ["webauthn>=2.6"]`
  - **Verify**: `uv sync --extra webauthn` succeeds; `uv run python -c "import webauthn"` works

- [x] 1.2 Write failing tests first (TDD)
  - **File**: `tests/auth/test_webauthn.py` (create)
  - **What**: Test cases for registration ceremony (`finish_webauthn_registration` validates attestation), assertion ceremony (`finish_webauthn_assertion` validates assertion), credential rebinding rejection, replay rejection
  - **Verify**: `uv run pytest tests/auth/test_webauthn.py` fails (red)

### 2.0 WebAuthn Verifier Implementation

- [ ] 2.1 `WebAuthnCredentialStore` Protocol
  - **File**: `src/asap/auth/webauthn.py` (create)
  - **What**: Protocol with `save_credential(host_id, credential_id, public_key, sign_count)`, `get_credential(host_id, credential_id)`, `update_sign_count(host_id, credential_id, new_count)`, `list_credentials(host_id)`
  - **Verify**: Protocol conformance test

- [ ] 2.2 `InMemoryWebAuthnCredentialStore` and `SQLiteWebAuthnCredentialStore`
  - **File**: `src/asap/auth/webauthn.py` (extend)
  - **What**: Two implementations following SnapshotStore pattern
  - **Verify**: Both pass the same fixture suite

- [ ] 2.3 `WebAuthnVerifierImpl` registration ceremony
  - **File**: `src/asap/auth/webauthn.py` (extend)
  - **What**: `start_webauthn_registration(host_id) -> challenge`, `finish_webauthn_registration(host_id, attestation) -> credential_id`. Use `webauthn.generate_registration_options` + `webauthn.verify_registration_response`. Persist via `WebAuthnCredentialStore`.
  - **Verify**: Test with `webauthn` test vectors

- [ ] 2.4 `WebAuthnVerifierImpl` assertion ceremony
  - **File**: `src/asap/auth/webauthn.py` (extend)
  - **What**: `start_webauthn_assertion(host_id) -> challenge`, `finish_webauthn_assertion(host_id, assertion) -> bool`. Use `webauthn.generate_authentication_options` + `webauthn.verify_authentication_response`. Update `sign_count` on success; reject if `sign_count` regresses.
  - **Verify**: Replay rejection + sign-count regression rejection tests

### 3.0 Integration with Self-Auth Prevention

- [ ] 3.1 Wire `WebAuthnVerifierImpl` as default when extra is installed
  - **File**: `src/asap/auth/self_auth.py` (modify)
  - **What**: Conditional import: `try: from asap.auth.webauthn import WebAuthnVerifierImpl as _DefaultVerifier; except ImportError: from asap.auth.self_auth import _PlaceholderVerifier as _DefaultVerifier`. Document the fallback behavior.
  - **Verify**: Two test runs: one with `[webauthn]` extra, one without — both pass

- [ ] 3.2 Enforce `userVerification: "required"` on capability approval
  - **File**: `src/asap/auth/self_auth.py` (modify)
  - **What**: When `agent_controls_browser=True` AND `WebAuthnVerifierImpl` available, require successful `finish_webauthn_assertion` before allowing capability grant. Return `403 webauthn_required` error otherwise.
  - **Verify**: Integration test simulating browser-controlling agent without WebAuthn assertion → 403

### 4.0 Documentation

- [ ] 4.1 Update self-authorization-prevention threat model
  - **File**: `docs/security/self-authorization-prevention.md` (modify)
  - **What**: New section "Real WebAuthn" with: threat model with concrete verification, flow diagram, configuration example, fallback behavior when extra not installed
  - **Verify**: Markdown lint clean; reviewed against original threat-model section

- [ ] 4.2 Migration note in docs/migration.md
  - **File**: `docs/migration.md` (modify)
  - **What**: Section "v2.2.0 → v2.2.1": opt-in extra installation, behavior unchanged when not installed, recommendation for production (install extra)
  - **Verify**: Cross-link from CHANGELOG entry

## Acceptance Criteria

- [ ] All tests pass (red → green via TDD)
- [ ] Coverage ≥90% on `src/asap/auth/webauthn.py`
- [ ] `uv run mypy src/asap/auth/webauthn.py` clean
- [ ] `uv run ruff check src/asap/auth/webauthn.py` clean
- [ ] Behavior unchanged when `[webauthn]` extra not installed (placeholder still resolves)
- [ ] Documented threat model + migration note merged

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| `webauthn` library API changes between releases | Pin `webauthn>=2.6,<3` and add CI matrix entry |
| Browser-side JS missing for full E2E | Document the JS counterpart in a follow-up; SDK demo can use `@simplewebauthn/browser` |
| Test vectors not covering edge cases | Use both library-provided vectors + custom corruption tests (tampered attestation, replayed assertion, regressed sign_count) |
