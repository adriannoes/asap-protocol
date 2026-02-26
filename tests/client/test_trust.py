"""Unit tests for asap.client.trust module."""

import json
from pathlib import Path

import pytest

from asap.client.trust import ASAP_CA_PUBLIC_KEY_B64, verify_agent_trust
from asap.crypto.keys import generate_keypair
from asap.crypto.models import SignedManifest
from asap.crypto.signing import sign_manifest
from asap.crypto.trust import sign_with_ca
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


def test_asap_ca_public_key_constant_defined() -> None:
    """CA key constant is defined and matches fixture."""
    ca_b64 = (ASAP_CA_DIR / "ca_public_b64.txt").read_text().strip()
    assert ca_b64 == ASAP_CA_PUBLIC_KEY_B64
    assert len(ASAP_CA_PUBLIC_KEY_B64) > 40


def test_verify_agent_trust_valid_verified_manifest_passes() -> None:
    """Valid CA-signed manifest passes verification."""
    # verified_manifest.json is signed with ASAP CA (matches embedded key)
    data = json.loads((FIXTURES_DIR / "verified_manifest.json").read_text())
    signed_fixture = SignedManifest.model_validate(data)
    assert verify_agent_trust(signed_fixture) is True


def test_verify_agent_trust_self_signed_raises() -> None:
    """Self-signed manifest raises SignatureVerificationError."""
    manifest = _sample_manifest()
    private_key, _ = generate_keypair()
    signed = sign_manifest(manifest, private_key)
    with pytest.raises(SignatureVerificationError) as exc_info:
        verify_agent_trust(signed)
    assert "trust_level" in exc_info.value.message


def test_verify_agent_trust_unknown_ca_raises() -> None:
    """Manifest signed by unknown CA raises SignatureVerificationError."""
    manifest = _sample_manifest()
    agent_key, _ = generate_keypair()
    ca_key, _ = generate_keypair()
    signed = sign_with_ca(manifest, agent_key, ca_key)
    # signed is verified but signed with a different CA than our embedded one
    with pytest.raises(SignatureVerificationError) as exc_info:
        verify_agent_trust(signed)
    assert "unknown CA" in exc_info.value.message


def test_verify_agent_trust_missing_public_key_raises() -> None:
    """Manifest without public_key raises SignatureVerificationError."""
    manifest = _sample_manifest()
    private_key, _ = generate_keypair()
    signed = sign_manifest(manifest, private_key)
    signed_dict = signed.model_dump()
    signed_dict["signature"]["trust_level"] = "verified"
    signed_dict["public_key"] = None
    signed_no_pk = SignedManifest.model_validate(signed_dict)
    with pytest.raises(SignatureVerificationError) as exc_info:
        verify_agent_trust(signed_no_pk)
    assert "no public_key" in exc_info.value.message or "public_key" in exc_info.value.message


def test_verify_agent_trust_invalid_signature_raises() -> None:
    """Manifest with tampered signature raises SignatureVerificationError."""
    data = json.loads((FIXTURES_DIR / "verified_manifest.json").read_text())
    signed = SignedManifest.model_validate(data)
    # Tamper with signature
    signed_dict = signed.model_dump()
    signed_dict["signature"]["signature"] = "a" * 88  # Invalid base64 signature
    signed_tampered = SignedManifest.model_validate(signed_dict)
    with pytest.raises(SignatureVerificationError):
        verify_agent_trust(signed_tampered)
