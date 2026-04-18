"""TDD tests for real WebAuthn verification (Sprint S1, task 1.2).

Vectors match duo-labs/py_webauthn test fixtures (NONE registration + EC2 assertion).
"""

from __future__ import annotations

from typing import Any

import pytest
from webauthn.helpers import base64url_to_bytes

# RP settings aligned with the vectors (localhost dev).
_RP_ID = "localhost"
_ORIGIN = "http://localhost:5000"

# NONE attestation (registration) — py_webauthn test_verifies_none_attestation_response
_NONE_ATTESTATION: dict[str, Any] = {
    "id": "9y1xA8Tmg1FEmT-c7_fvWZ_uoTuoih3OvR45_oAK-cwHWhAbXrl2q62iLVTjiyEZ7O7n-CROOY494k7Q3xrs_w",
    "rawId": "9y1xA8Tmg1FEmT-c7_fvWZ_uoTuoih3OvR45_oAK-cwHWhAbXrl2q62iLVTjiyEZ7O7n-CROOY494k7Q3xrs_w",
    "response": {
        "attestationObject": (
            "o2NmbXRkbm9uZWdhdHRTdG10oGhhdXRoRGF0YVjESZYN5YgOjGh0NBcPZHZgW4_krrmihjLHmVzzuoMdl2NFAAAAFwAAAAAAAAAAAAAAAAAAAAAAQPctcQPE5oNRRJk_nO_371mf7qE7qIodzr0eOf6ACvnMB1oQG165dqutoi1U44shGezu5_gkTjmOPeJO0N8a7P-lAQIDJiABIVggSFbUJF-42Ug3pdM8rDRFu_N5oiVEysPDB6n66r_7dZAiWCDUVnB39FlGypL-qAoIO9xWHtJygo2jfDmHl-_eKFRLDA"
        ),
        "clientDataJSON": (
            "eyJ0eXBlIjoid2ViYXV0aG4uY3JlYXRlIiwiY2hhbGxlbmdlIjoiVHdON240V1R5R0tMYzRaWS1xR3NGcUtuSE00bmdscXN5VjBJQ0psTjJUTzlYaVJ5RnRya2FEd1V2c3FsLWdrTEpYUDZmbkYxTWxyWjUzTW00UjdDdnciLCJvcmlnaW4iOiJodHRwOi8vbG9jYWxob3N0OjUwMDAiLCJjcm9zc09yaWdpbiI6ZmFsc2V9"
        ),
    },
    "type": "public-key",
    "clientExtensionResults": {},
    "transports": ["nfc", "usb"],
}

_REG_CHALLENGE_B64 = (
    "TwN7n4WTyGKLc4ZY-qGsFqKnHM4nglqsyV0ICJlN2TO9XiRyFtrkaDwUvsql-gkLJXP6fnF1MlrZ53Mm4R7Cvw"
)
_EXPECTED_CREDENTIAL_ID_B64 = (
    "9y1xA8Tmg1FEmT-c7_fvWZ_uoTuoih3OvR45_oAK-cwHWhAbXrl2q62iLVTjiyEZ7O7n-CROOY494k7Q3xrs_w"
)

# EC2 assertion — py_webauthn test_verify_authentication_response_with_EC2_public_key
_ASSERTION_EC2: dict[str, Any] = {
    "id": "EDx9FfAbp4obx6oll2oC4-CZuDidRVV4gZhxC529ytlnqHyqCStDUwfNdm1SNHAe3X5KvueWQdAX3x9R1a2b9Q",
    "rawId": "EDx9FfAbp4obx6oll2oC4-CZuDidRVV4gZhxC529ytlnqHyqCStDUwfNdm1SNHAe3X5KvueWQdAX3x9R1a2b9Q",
    "response": {
        "authenticatorData": "SZYN5YgOjGh0NBcPZHZgW4_krrmihjLHmVzzuoMdl2MBAAAATg",
        "clientDataJSON": (
            "eyJjaGFsbGVuZ2UiOiJ4aTMwR1BHQUZZUnhWRHBZMXNNMTBEYUx6VlFHNjZudi1fN1JVYXpIMHZJMll2RzhMWWdERW52TjVmWlpOVnV2RUR1TWk5dGUzVkxxYjQyTjBma0xHQSIsImNsaWVudEV4dGVuc2lvbnMiOnt9LCJoYXNoQWxnb3JpdGhtIjoiU0hBLTI1NiIsIm9yaWdpbiI6Imh0dHA6Ly9sb2NhbGhvc3Q6NTAwMCIsInR5cGUiOiJ3ZWJhdXRobi5nZXQifQ"
        ),
        "signature": (
            "MEUCIGisVZOBapCWbnJJvjelIzwpixxIwkjCCb5aCHafQu68AiEA88v-2pJNNApPFwAKFiNuf82-2hBxYW5kGwVweeoxCwo"
        ),
    },
    "type": "public-key",
    "clientExtensionResults": {},
}

_AUTH_CHALLENGE_B64 = (
    "xi30GPGAFYRxVDpY1sM10DaLzVQG66nv-_7RUazH0vI2YvG8LYgDEnvN5fZZNVuvEDuMi9te3VLqb42N0fkLGA"
)
_ASSERTION_CREDENTIAL_PUBLIC_KEY_B64 = (
    "pQECAyYgASFYIIeDTe-gN8A-zQclHoRnGFWN8ehM1b7yAsa8I8KIvmplIlgg4nFGT5px8o6gpPZZhO01wdy9crDSA_Ngtkx0vGpvPHI"
)
_ASSERTION_SIGN_COUNT_BEFORE = 77
_EC2_CREDENTIAL_ID_B64 = (
    "EDx9FfAbp4obx6oll2oC4-CZuDidRVV4gZhxC529ytlnqHyqCStDUwfNdm1SNHAe3X5KvueWQdAX3x9R1a2b9Q"
)


@pytest.mark.asyncio
async def test_finish_registration_validates_none_attestation() -> None:
    """Registration ceremony must verify attestation and persist credential id."""
    from asap.auth.webauthn import InMemoryWebAuthnCredentialStore, WebAuthnVerifierImpl

    store = InMemoryWebAuthnCredentialStore()
    impl = WebAuthnVerifierImpl(store, rp_id=_RP_ID, origin=_ORIGIN)
    challenge = await impl.start_webauthn_registration("host-a")
    assert challenge == _REG_CHALLENGE_B64

    cred_id = await impl.finish_webauthn_registration("host-a", _NONE_ATTESTATION)
    assert cred_id == _EXPECTED_CREDENTIAL_ID_B64


@pytest.mark.asyncio
async def test_finish_assertion_validates_ec2_response() -> None:
    """Assertion ceremony must verify signature and advance sign count."""
    from asap.auth.webauthn import InMemoryWebAuthnCredentialStore, WebAuthnVerifierImpl

    store = InMemoryWebAuthnCredentialStore()
    impl = WebAuthnVerifierImpl(store, rp_id=_RP_ID, origin=_ORIGIN)

    cid = base64url_to_bytes(_EC2_CREDENTIAL_ID_B64)
    pk = base64url_to_bytes(_ASSERTION_CREDENTIAL_PUBLIC_KEY_B64)
    await store.save_credential("host-a", cid, pk, _ASSERTION_SIGN_COUNT_BEFORE)

    challenge = await impl.start_webauthn_assertion("host-a")
    assert challenge == _AUTH_CHALLENGE_B64

    ok = await impl.finish_webauthn_assertion("host-a", _ASSERTION_EC2)
    assert ok is True
    row = await store.get_credential("host-a", cid)
    assert row is not None
    assert row.sign_count == 78


@pytest.mark.asyncio
async def test_registration_rejects_credential_rebinding_to_wrong_host() -> None:
    """Finish registration for host B must not accept a ceremony started for host A."""
    from asap.auth.webauthn import InMemoryWebAuthnCredentialStore, WebAuthnVerifierImpl
    from asap.auth.webauthn import WebAuthnCeremonyError

    store = InMemoryWebAuthnCredentialStore()
    impl = WebAuthnVerifierImpl(store, rp_id=_RP_ID, origin=_ORIGIN)
    await impl.start_webauthn_registration("host-a")

    with pytest.raises(WebAuthnCeremonyError):
        await impl.finish_webauthn_registration("host-b", _NONE_ATTESTATION)


@pytest.mark.asyncio
async def test_assertion_rejects_replay() -> None:
    """The same assertion payload must not succeed twice (replay / counter)."""
    from asap.auth.webauthn import InMemoryWebAuthnCredentialStore, WebAuthnVerifierImpl

    store = InMemoryWebAuthnCredentialStore()
    impl = WebAuthnVerifierImpl(store, rp_id=_RP_ID, origin=_ORIGIN)

    cid = base64url_to_bytes(_EC2_CREDENTIAL_ID_B64)
    pk = base64url_to_bytes(_ASSERTION_CREDENTIAL_PUBLIC_KEY_B64)
    await store.save_credential("host-a", cid, pk, _ASSERTION_SIGN_COUNT_BEFORE)

    await impl.start_webauthn_assertion("host-a")
    assert await impl.finish_webauthn_assertion("host-a", _ASSERTION_EC2) is True

    await impl.start_webauthn_assertion("host-a")
    assert await impl.finish_webauthn_assertion("host-a", _ASSERTION_EC2) is False
