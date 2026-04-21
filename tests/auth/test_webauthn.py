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


def test_webauthn_credential_store_protocol_conformance() -> None:
    """A minimal implementation must satisfy :class:`WebAuthnCredentialStore`."""
    from asap.auth.webauthn import WebAuthnCredentialRecord, WebAuthnCredentialStore

    class _MinimalStore:
        async def save_credential(
            self,
            host_id: str,
            credential_id: bytes,
            public_key: bytes,
            sign_count: int,
        ) -> None:
            _ = (host_id, credential_id, public_key, sign_count)

        async def get_credential(
            self,
            host_id: str,
            credential_id: bytes,
        ) -> WebAuthnCredentialRecord | None:
            _ = (host_id, credential_id)
            return None

        async def update_sign_count(
            self,
            host_id: str,
            credential_id: bytes,
            new_count: int,
        ) -> None:
            _ = (host_id, credential_id, new_count)

        async def list_credentials(self, host_id: str) -> list[bytes]:
            _ = host_id
            return []

    assert isinstance(_MinimalStore(), WebAuthnCredentialStore)


def test_builtin_webauthn_stores_satisfy_protocol(tmp_path: object) -> None:
    from pathlib import Path

    from asap.auth.webauthn import (
        InMemoryWebAuthnCredentialStore,
        SQLiteWebAuthnCredentialStore,
        WebAuthnCredentialStore,
    )

    assert isinstance(InMemoryWebAuthnCredentialStore(), WebAuthnCredentialStore)
    p = Path(tmp_path) / "webauthn_proto.db"
    assert isinstance(SQLiteWebAuthnCredentialStore(p), WebAuthnCredentialStore)


@pytest.fixture(params=["memory", "sqlite"])
def webauthn_store(request: pytest.FixtureRequest, tmp_path: object) -> object:
    from pathlib import Path

    from asap.auth.webauthn import InMemoryWebAuthnCredentialStore, SQLiteWebAuthnCredentialStore

    if request.param == "memory":
        return InMemoryWebAuthnCredentialStore()
    return SQLiteWebAuthnCredentialStore(Path(tmp_path) / "webauthn.db")


@pytest.mark.asyncio
async def test_store_save_get_update_list(webauthn_store: object) -> None:
    """In-memory and SQLite stores share the same observable behavior."""
    cid_a = b"id-a"
    cid_b = b"id-b"
    pk = b"pub-key-bytes"
    await webauthn_store.save_credential("host-1", cid_a, pk, 1)
    await webauthn_store.save_credential("host-1", cid_b, pk, 2)

    row = await webauthn_store.get_credential("host-1", cid_a)
    assert row is not None
    assert row.credential_id == cid_a
    assert row.public_key == pk
    assert row.sign_count == 1

    assert set(await webauthn_store.list_credentials("host-1")) == {cid_a, cid_b}
    assert await webauthn_store.list_credentials("host-other") == []

    await webauthn_store.update_sign_count("host-1", cid_a, 5)
    updated = await webauthn_store.get_credential("host-1", cid_a)
    assert updated is not None
    assert updated.sign_count == 5


@pytest.mark.asyncio
async def test_store_update_missing_raises(webauthn_store: object) -> None:
    with pytest.raises(KeyError):
        await webauthn_store.update_sign_count("host-x", b"missing", 0)


def _verifier_for_vectors(store: object) -> object:
    """Build a verifier aligned with the baked-in attestation/assertion test vectors."""
    from asap.auth.webauthn import WebAuthnVerifierImpl

    return WebAuthnVerifierImpl(
        store,
        rp_id=_RP_ID,
        origin=_ORIGIN,
        registration_challenge=base64url_to_bytes(_REG_CHALLENGE_B64),
        authentication_challenge=base64url_to_bytes(_AUTH_CHALLENGE_B64),
    )


@pytest.mark.asyncio
async def test_finish_registration_validates_none_attestation() -> None:
    """Registration ceremony must verify attestation and persist credential id."""
    from asap.auth.webauthn import InMemoryWebAuthnCredentialStore

    store = InMemoryWebAuthnCredentialStore()
    impl = _verifier_for_vectors(store)
    challenge = await impl.start_webauthn_registration("host-a")
    assert challenge == _REG_CHALLENGE_B64

    cred_id = await impl.finish_webauthn_registration("host-a", _NONE_ATTESTATION)
    assert cred_id == _EXPECTED_CREDENTIAL_ID_B64


@pytest.mark.asyncio
async def test_finish_assertion_validates_ec2_response() -> None:
    """Assertion ceremony must verify signature and advance sign count."""
    from asap.auth.webauthn import InMemoryWebAuthnCredentialStore

    store = InMemoryWebAuthnCredentialStore()
    impl = _verifier_for_vectors(store)

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
    from asap.auth.webauthn import InMemoryWebAuthnCredentialStore, WebAuthnCeremonyError

    store = InMemoryWebAuthnCredentialStore()
    impl = _verifier_for_vectors(store)
    await impl.start_webauthn_registration("host-a")

    with pytest.raises(WebAuthnCeremonyError):
        await impl.finish_webauthn_registration("host-b", _NONE_ATTESTATION)


@pytest.mark.asyncio
async def test_assertion_rejects_replay() -> None:
    """The same assertion payload must not succeed twice (replay / counter)."""
    from asap.auth.webauthn import InMemoryWebAuthnCredentialStore

    store = InMemoryWebAuthnCredentialStore()
    impl = _verifier_for_vectors(store)

    cid = base64url_to_bytes(_EC2_CREDENTIAL_ID_B64)
    pk = base64url_to_bytes(_ASSERTION_CREDENTIAL_PUBLIC_KEY_B64)
    await store.save_credential("host-a", cid, pk, _ASSERTION_SIGN_COUNT_BEFORE)

    await impl.start_webauthn_assertion("host-a")
    assert await impl.finish_webauthn_assertion("host-a", _ASSERTION_EC2) is True

    await impl.start_webauthn_assertion("host-a")
    assert await impl.finish_webauthn_assertion("host-a", _ASSERTION_EC2) is False


@pytest.mark.asyncio
async def test_finish_assertion_fails_when_user_verification_required_but_not_present() -> None:
    """EC2 test vector authenticates without UV; ``require_user_verification=True`` must reject."""
    from asap.auth.webauthn import InMemoryWebAuthnCredentialStore

    store = InMemoryWebAuthnCredentialStore()
    impl = _verifier_for_vectors(store)

    cid = base64url_to_bytes(_EC2_CREDENTIAL_ID_B64)
    pk = base64url_to_bytes(_ASSERTION_CREDENTIAL_PUBLIC_KEY_B64)
    await store.save_credential("host-a", cid, pk, _ASSERTION_SIGN_COUNT_BEFORE)

    await impl.start_webauthn_assertion("host-a")
    ok = await impl.finish_webauthn_assertion(
        "host-a",
        _ASSERTION_EC2,
        require_user_verification=True,
    )
    assert ok is False


@pytest.mark.asyncio
async def test_sqlite_store_get_missing_returns_none(tmp_path: object) -> None:
    from pathlib import Path

    from asap.auth.webauthn import SQLiteWebAuthnCredentialStore

    store = SQLiteWebAuthnCredentialStore(Path(tmp_path) / "w.db")
    assert await store.get_credential("host-x", b"missing") is None


def test_ensure_webauthn_installed_raises_without_distribution(monkeypatch: pytest.MonkeyPatch) -> None:
    import builtins

    real_import = builtins.__import__

    def guarded_import(
        name: str,
        globals: dict[str, object] | None = None,
        locals: dict[str, object] | None = None,
        fromlist: tuple[str, ...] = (),
        level: int = 0,
    ) -> object:
        if name == "webauthn" or name.startswith("webauthn."):
            raise ImportError("simulated missing webauthn")
        return real_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr(builtins, "__import__", guarded_import)
    from asap.auth.webauthn import InMemoryWebAuthnCredentialStore, WebAuthnVerifierImpl

    impl = WebAuthnVerifierImpl(
        InMemoryWebAuthnCredentialStore(),
        rp_id=_RP_ID,
        origin=_ORIGIN,
    )
    with pytest.raises(ImportError, match="optional extra"):
        impl._ensure_webauthn_installed()


@pytest.mark.asyncio
async def test_finish_registration_invalid_attestation_raises() -> None:
    from asap.auth.webauthn import InMemoryWebAuthnCredentialStore, WebAuthnCeremonyError, WebAuthnVerifierImpl

    store = InMemoryWebAuthnCredentialStore()
    impl = WebAuthnVerifierImpl(
        store,
        rp_id=_RP_ID,
        origin="http://wrong-origin:5000",
        registration_challenge=base64url_to_bytes(_REG_CHALLENGE_B64),
    )
    await impl.start_webauthn_registration("host-a")
    with pytest.raises(WebAuthnCeremonyError):
        await impl.finish_webauthn_registration("host-a", _NONE_ATTESTATION)


@pytest.mark.asyncio
async def test_start_assertion_with_user_verification_required() -> None:
    from asap.auth.webauthn import InMemoryWebAuthnCredentialStore, WebAuthnVerifierImpl

    store = InMemoryWebAuthnCredentialStore()
    impl = WebAuthnVerifierImpl(
        store,
        rp_id=_RP_ID,
        origin=_ORIGIN,
        authentication_challenge=base64url_to_bytes(_AUTH_CHALLENGE_B64),
    )
    await store.save_credential("host-a", b"cid", b"pk", 1)
    ch = await impl.start_webauthn_assertion("host-a", user_verification_required=True)
    assert ch == _AUTH_CHALLENGE_B64


@pytest.mark.asyncio
async def test_finish_assertion_no_pending_returns_false() -> None:
    from asap.auth.webauthn import InMemoryWebAuthnCredentialStore

    store = InMemoryWebAuthnCredentialStore()
    impl = _verifier_for_vectors(store)
    assert await impl.finish_webauthn_assertion("host-a", _ASSERTION_EC2) is False


@pytest.mark.asyncio
async def test_finish_assertion_claimed_challenge_decode_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    from asap.auth.webauthn import InMemoryWebAuthnCredentialStore

    def _boom(_s: str) -> bytes:
        raise ValueError("bad decode")

    monkeypatch.setattr("webauthn.helpers.base64url_to_bytes", _boom)

    store = InMemoryWebAuthnCredentialStore()
    impl = _verifier_for_vectors(store)
    cid = base64url_to_bytes(_EC2_CREDENTIAL_ID_B64)
    pk = base64url_to_bytes(_ASSERTION_CREDENTIAL_PUBLIC_KEY_B64)
    await store.save_credential("host-a", cid, pk, _ASSERTION_SIGN_COUNT_BEFORE)
    await impl.start_webauthn_assertion("host-a")
    assert (
        await impl.finish_webauthn_assertion(
            "host-a",
            _ASSERTION_EC2,
            claimed_challenge_b64url="any",
        )
        is False
    )


@pytest.mark.asyncio
async def test_finish_assertion_invalid_claimed_challenge_b64url() -> None:
    from asap.auth.webauthn import InMemoryWebAuthnCredentialStore

    store = InMemoryWebAuthnCredentialStore()
    impl = _verifier_for_vectors(store)
    cid = base64url_to_bytes(_EC2_CREDENTIAL_ID_B64)
    pk = base64url_to_bytes(_ASSERTION_CREDENTIAL_PUBLIC_KEY_B64)
    await store.save_credential("host-a", cid, pk, _ASSERTION_SIGN_COUNT_BEFORE)
    await impl.start_webauthn_assertion("host-a")
    assert (
        await impl.finish_webauthn_assertion(
            "host-a",
            _ASSERTION_EC2,
            claimed_challenge_b64url="not-valid-base64url!!!",
        )
        is False
    )


@pytest.mark.asyncio
async def test_finish_assertion_claimed_challenge_mismatch() -> None:
    from asap.auth.webauthn import InMemoryWebAuthnCredentialStore

    store = InMemoryWebAuthnCredentialStore()
    impl = _verifier_for_vectors(store)
    cid = base64url_to_bytes(_EC2_CREDENTIAL_ID_B64)
    pk = base64url_to_bytes(_ASSERTION_CREDENTIAL_PUBLIC_KEY_B64)
    await store.save_credential("host-a", cid, pk, _ASSERTION_SIGN_COUNT_BEFORE)
    await impl.start_webauthn_assertion("host-a")
    assert (
        await impl.finish_webauthn_assertion(
            "host-a",
            _ASSERTION_EC2,
            claimed_challenge_b64url=_REG_CHALLENGE_B64,
        )
        is False
    )


@pytest.mark.asyncio
async def test_finish_assertion_rejects_non_string_raw_id() -> None:
    from asap.auth.webauthn import InMemoryWebAuthnCredentialStore

    store = InMemoryWebAuthnCredentialStore()
    impl = _verifier_for_vectors(store)
    cid = base64url_to_bytes(_EC2_CREDENTIAL_ID_B64)
    pk = base64url_to_bytes(_ASSERTION_CREDENTIAL_PUBLIC_KEY_B64)
    await store.save_credential("host-a", cid, pk, _ASSERTION_SIGN_COUNT_BEFORE)
    await impl.start_webauthn_assertion("host-a")
    bad = {**_ASSERTION_EC2, "rawId": None, "id": None}
    assert await impl.finish_webauthn_assertion("host-a", bad) is False


@pytest.mark.asyncio
async def test_finish_assertion_unknown_credential_id() -> None:
    from asap.auth.webauthn import InMemoryWebAuthnCredentialStore

    store = InMemoryWebAuthnCredentialStore()
    impl = _verifier_for_vectors(store)
    await impl.start_webauthn_assertion("host-a")
    unknown = {**_ASSERTION_EC2, "rawId": _EXPECTED_CREDENTIAL_ID_B64, "id": _EXPECTED_CREDENTIAL_ID_B64}
    assert await impl.finish_webauthn_assertion("host-a", unknown) is False


@pytest.mark.asyncio
async def test_self_auth_verifier_rejects_missing_host_id() -> None:
    from asap.auth.webauthn import InMemoryWebAuthnCredentialStore, WebAuthnSelfAuthVerifier, WebAuthnVerifierImpl

    impl = WebAuthnVerifierImpl(InMemoryWebAuthnCredentialStore(), rp_id=_RP_ID, origin=_ORIGIN)
    v = WebAuthnSelfAuthVerifier(impl)
    assert await v.verify("x", {}, host_id=None) is False


@pytest.mark.asyncio
async def test_self_auth_verifier_rejects_non_dict_response() -> None:
    from asap.auth.webauthn import InMemoryWebAuthnCredentialStore, WebAuthnSelfAuthVerifier, WebAuthnVerifierImpl

    impl = WebAuthnVerifierImpl(InMemoryWebAuthnCredentialStore(), rp_id=_RP_ID, origin=_ORIGIN)
    v = WebAuthnSelfAuthVerifier(impl)
    assert await v.verify("x", "not-a-dict", host_id="host-a") is False


@pytest.mark.asyncio
async def test_self_auth_verifier_verify_success() -> None:
    from asap.auth.webauthn import InMemoryWebAuthnCredentialStore, WebAuthnSelfAuthVerifier

    store = InMemoryWebAuthnCredentialStore()
    impl = _verifier_for_vectors(store)
    v = WebAuthnSelfAuthVerifier(impl)
    cid = base64url_to_bytes(_EC2_CREDENTIAL_ID_B64)
    pk = base64url_to_bytes(_ASSERTION_CREDENTIAL_PUBLIC_KEY_B64)
    await store.save_credential("host-a", cid, pk, _ASSERTION_SIGN_COUNT_BEFORE)
    await impl.start_webauthn_assertion("host-a")
    assert await v.verify(_AUTH_CHALLENGE_B64, _ASSERTION_EC2, host_id="host-a") is True
