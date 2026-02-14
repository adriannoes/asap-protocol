"""Unit tests for trust level model and detection."""

import json
from pathlib import Path

import pytest

from asap.crypto.keys import generate_keypair, load_private_key_from_pem, public_key_to_base64
from asap.crypto.models import SignatureBlock, SignedManifest
from asap.crypto.signing import sign_manifest
from asap.crypto.trust import TrustLevel, detect_trust_level, sign_with_ca, verify_ca_signature
from asap.errors import SignatureVerificationError
from asap.models.entities import Capability, Endpoint, Manifest, Skill

FIXTURES_DIR = Path(__file__).resolve().parent.parent / "fixtures"
ASAP_CA_DIR = FIXTURES_DIR / "asap_ca"


def _sample_manifest() -> Manifest:
    return Manifest(
        id="urn:asap:agent:test-trust",
        name="Test Agent",
        version="1.0.0",
        description="Agent for trust tests",
        capabilities=Capability(
            asap_version="0.1",
            skills=[Skill(id="echo", description="Echo skill")],
            state_persistence=False,
        ),
        endpoints=Endpoint(asap="https://example.com/asap"),
    )


def test_trust_level_enum_values() -> None:
    """TrustLevel enum has expected string values."""
    assert TrustLevel.SELF_SIGNED.value == "self-signed"
    assert TrustLevel.VERIFIED.value == "verified"
    assert TrustLevel.ENTERPRISE.value == "enterprise"


def test_trust_level_serializes_to_json() -> None:
    """TrustLevel values serialize correctly to JSON."""
    assert json.dumps(TrustLevel.SELF_SIGNED.value) == '"self-signed"'
    assert json.dumps(TrustLevel.VERIFIED.value) == '"verified"'
    assert json.dumps(TrustLevel.ENTERPRISE.value) == '"enterprise"'


def test_signature_block_includes_trust_level_default() -> None:
    """SignatureBlock defaults to SELF_SIGNED when trust_level omitted."""
    block = SignatureBlock(alg="ed25519", signature="a" * 88)  # 64 bytes base64
    assert block.trust_level == TrustLevel.SELF_SIGNED


def test_signature_block_accepts_explicit_trust_level() -> None:
    """SignatureBlock accepts explicit trust_level."""
    sig_b64 = "x" * 88
    for level in TrustLevel:
        block = SignatureBlock(alg="ed25519", signature=sig_b64, trust_level=level)
        assert block.trust_level == level


def test_signed_manifest_includes_trust_level() -> None:
    """SignedManifest from sign_manifest includes trust_level (default SELF_SIGNED)."""
    manifest = _sample_manifest()
    private_key, _ = generate_keypair()
    signed = sign_manifest(manifest, private_key)
    assert signed.signature.trust_level == TrustLevel.SELF_SIGNED


def test_detect_trust_level_self_signed() -> None:
    """detect_trust_level returns SELF_SIGNED for agent-signed manifest."""
    manifest = _sample_manifest()
    private_key, _ = generate_keypair()
    signed = sign_manifest(manifest, private_key)
    assert detect_trust_level(signed) == TrustLevel.SELF_SIGNED


def test_detect_trust_level_verified() -> None:
    """detect_trust_level returns VERIFIED when signature has trust_level=VERIFIED."""
    manifest = _sample_manifest()
    private_key, _ = generate_keypair()
    signed = sign_manifest(manifest, private_key)
    signed_dict = signed.model_dump()
    signed_dict["signature"]["trust_level"] = "verified"
    signed_verified = SignedManifest.model_validate(signed_dict)
    assert detect_trust_level(signed_verified) == TrustLevel.VERIFIED


def test_detect_trust_level_enterprise() -> None:
    """detect_trust_level returns ENTERPRISE when signature has trust_level=enterprise."""
    manifest = _sample_manifest()
    private_key, _ = generate_keypair()
    signed = sign_manifest(manifest, private_key)
    signed_dict = signed.model_dump()
    signed_dict["signature"]["trust_level"] = "enterprise"
    signed_enterprise = SignedManifest.model_validate(signed_dict)
    assert detect_trust_level(signed_enterprise) == TrustLevel.ENTERPRISE


def test_signed_manifest_model_dump_includes_trust_level() -> None:
    """SignedManifest model_dump includes trust_level in signature block."""
    manifest = _sample_manifest()
    private_key, _ = generate_keypair()
    signed = sign_manifest(manifest, private_key)
    dumped = signed.model_dump()
    assert "trust_level" in dumped["signature"]
    assert dumped["signature"]["trust_level"] == "self-signed"


def test_trust_level_backward_compat_omitted_field() -> None:
    """Manifests without trust_level (old format) default to SELF_SIGNED."""
    manifest = _sample_manifest()
    private_key, _ = generate_keypair()
    signed = sign_manifest(manifest, private_key)
    dumped = signed.model_dump()
    del dumped["signature"]["trust_level"]
    signed_legacy = SignedManifest.model_validate(
        {
            "manifest": dumped["manifest"],
            "signature": dumped["signature"],
            "public_key": dumped["public_key"],
        }
    )
    assert signed_legacy.signature.trust_level == TrustLevel.SELF_SIGNED
    assert detect_trust_level(signed_legacy) == TrustLevel.SELF_SIGNED


# --- Task 2.2: CA signing and verification ---


def test_sign_with_ca_returns_verified_trust_level() -> None:
    """sign_with_ca produces SignedManifest with trust_level=VERIFIED."""
    manifest = _sample_manifest()
    agent_key, _ = generate_keypair()
    ca_key, _ = generate_keypair()
    signed = sign_with_ca(manifest, agent_key, ca_key)
    assert signed.signature.trust_level == TrustLevel.VERIFIED
    assert signed.public_key == public_key_to_base64(ca_key.public_key())


def test_sign_with_ca_uses_jcs_canonicalization() -> None:
    """sign_with_ca uses JCS canonicalization (deterministic)."""
    manifest = _sample_manifest()
    agent_key, _ = generate_keypair()
    ca_key, _ = generate_keypair()
    a = sign_with_ca(manifest, agent_key, ca_key)
    b = sign_with_ca(manifest, agent_key, ca_key)
    assert a.signature.signature == b.signature.signature


def test_verify_ca_signature_accepts_known_ca() -> None:
    """verify_ca_signature returns True for manifest signed by known CA."""
    manifest = _sample_manifest()
    agent_key, _ = generate_keypair()
    ca_key, _ = generate_keypair()
    signed = sign_with_ca(manifest, agent_key, ca_key)
    known_cas = [public_key_to_base64(ca_key.public_key())]
    assert verify_ca_signature(signed, known_cas) is True


def test_verify_ca_signature_rejects_unknown_ca() -> None:
    """verify_ca_signature raises when CA not in known_cas."""
    manifest = _sample_manifest()
    agent_key, _ = generate_keypair()
    ca_key, _ = generate_keypair()
    signed = sign_with_ca(manifest, agent_key, ca_key)
    other_ca_key, _ = generate_keypair()
    known_cas = [public_key_to_base64(other_ca_key.public_key())]
    with pytest.raises(SignatureVerificationError) as exc_info:
        verify_ca_signature(signed, known_cas)
    assert "unknown CA" in exc_info.value.message


def test_verify_ca_signature_rejects_self_signed() -> None:
    """verify_ca_signature raises for trust_level != VERIFIED."""
    manifest = _sample_manifest()
    agent_key, _ = generate_keypair()
    signed = sign_manifest(manifest, agent_key)
    known_cas = [public_key_to_base64(agent_key.public_key())]
    with pytest.raises(SignatureVerificationError) as exc_info:
        verify_ca_signature(signed, known_cas)
    assert "trust_level" in exc_info.value.message


def test_fixtures_load_and_validate() -> None:
    """verified_manifest.json and self_signed_manifest.json load and validate."""
    for name in ("verified_manifest.json", "self_signed_manifest.json"):
        path = FIXTURES_DIR / name
        assert path.exists(), f"Fixture {name} not found"
        data = json.loads(path.read_text())
        signed = SignedManifest.model_validate(data)
        assert signed.manifest.id
        assert signed.signature.alg == "ed25519"


def test_verified_fixture_has_trust_level_verified() -> None:
    """verified_manifest.json has trust_level=verified."""
    data = json.loads((FIXTURES_DIR / "verified_manifest.json").read_text())
    signed = SignedManifest.model_validate(data)
    assert signed.signature.trust_level == TrustLevel.VERIFIED


def test_self_signed_fixture_has_trust_level_self_signed() -> None:
    """self_signed_manifest.json has trust_level=self-signed."""
    data = json.loads((FIXTURES_DIR / "self_signed_manifest.json").read_text())
    signed = SignedManifest.model_validate(data)
    assert signed.signature.trust_level == TrustLevel.SELF_SIGNED


def test_verify_ca_signature_with_asap_ca_fixture() -> None:
    """verify_ca_signature works with tests/fixtures/asap_ca CA."""
    ca_pem = (ASAP_CA_DIR / "ca_private.pem").read_bytes()
    ca_key = load_private_key_from_pem(ca_pem)
    ca_public_b64 = (ASAP_CA_DIR / "ca_public_b64.txt").read_text().strip()
    data = json.loads((FIXTURES_DIR / "verified_manifest.json").read_text())
    signed = SignedManifest.model_validate(data)
    assert verify_ca_signature(signed, [ca_public_b64]) is True
    assert verify_ca_signature(signed, [ca_key.public_key()]) is True
