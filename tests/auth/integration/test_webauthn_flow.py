"""Integration smoke: registration + assertion ceremonies (Sprint S1 Relevant Files).

The published py_webauthn NONE registration and EC2 assertion fixtures use different
credential keys. This module still runs both ceremonies against one
:class:`~asap.auth.webauthn.WebAuthnVerifierImpl` and store to validate the full server-side
lifecycle wiring (pending challenges, persistence, sign-count update).
"""

from __future__ import annotations

import importlib.util

import pytest
from webauthn.helpers import base64url_to_bytes

pytestmark = pytest.mark.skipif(
    importlib.util.find_spec("webauthn") is None,
    reason="webauthn extra not installed",
)


@pytest.mark.asyncio
async def test_webauthn_verifier_registration_then_assertion_smoke() -> None:
    """Register one host (NONE attestation), then assert another (EC2 vector + pre-seeded key)."""
    from asap.auth.webauthn import InMemoryWebAuthnCredentialStore

    from tests.auth.test_webauthn import (
        _ASSERTION_CREDENTIAL_PUBLIC_KEY_B64,
        _ASSERTION_EC2,
        _ASSERTION_SIGN_COUNT_BEFORE,
        _AUTH_CHALLENGE_B64,
        _EC2_CREDENTIAL_ID_B64,
        _EXPECTED_CREDENTIAL_ID_B64,
        _NONE_ATTESTATION,
        _REG_CHALLENGE_B64,
        _verifier_for_vectors,
    )

    store = InMemoryWebAuthnCredentialStore()
    impl = _verifier_for_vectors(store)

    reg_challenge = await impl.start_webauthn_registration("host-reg")
    assert reg_challenge == _REG_CHALLENGE_B64
    cred_id_b64 = await impl.finish_webauthn_registration("host-reg", _NONE_ATTESTATION)
    assert cred_id_b64 == _EXPECTED_CREDENTIAL_ID_B64

    cid = base64url_to_bytes(_EC2_CREDENTIAL_ID_B64)
    pk = base64url_to_bytes(_ASSERTION_CREDENTIAL_PUBLIC_KEY_B64)
    await store.save_credential("host-as", cid, pk, _ASSERTION_SIGN_COUNT_BEFORE)

    auth_challenge = await impl.start_webauthn_assertion("host-as")
    assert auth_challenge == _AUTH_CHALLENGE_B64
    assert await impl.finish_webauthn_assertion("host-as", _ASSERTION_EC2) is True

    row = await store.get_credential("host-as", cid)
    assert row is not None
    assert row.sign_count == 78


@pytest.mark.asyncio
async def test_webauthn_self_auth_verifier_matches_impl_assertion_path() -> None:
    """``WebAuthnSelfAuthVerifier`` delegates to the same finish path as the impl."""
    from asap.auth.webauthn import InMemoryWebAuthnCredentialStore, WebAuthnSelfAuthVerifier

    from tests.auth.test_webauthn import (
        _ASSERTION_CREDENTIAL_PUBLIC_KEY_B64,
        _ASSERTION_EC2,
        _ASSERTION_SIGN_COUNT_BEFORE,
        _AUTH_CHALLENGE_B64,
        _EC2_CREDENTIAL_ID_B64,
        _verifier_for_vectors,
    )

    store = InMemoryWebAuthnCredentialStore()
    impl = _verifier_for_vectors(store)
    verifier = WebAuthnSelfAuthVerifier(impl)

    cid = base64url_to_bytes(_EC2_CREDENTIAL_ID_B64)
    pk = base64url_to_bytes(_ASSERTION_CREDENTIAL_PUBLIC_KEY_B64)
    await store.save_credential("host-as", cid, pk, _ASSERTION_SIGN_COUNT_BEFORE)
    await impl.start_webauthn_assertion("host-as")

    assert await verifier.verify(_AUTH_CHALLENGE_B64, _ASSERTION_EC2, host_id="host-as") is True
