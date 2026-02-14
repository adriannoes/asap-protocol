"""Trust level model and detection for agent identity verification.

Implements 3-tier trust model (SD-5):
- SELF_SIGNED: Free, agent-signed manifests
- VERIFIED: ASAP CA verified ($49/mo)
- ENTERPRISE: Organization CA signed
"""

from __future__ import annotations

import base64
from collections.abc import Iterable

from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)

from asap.crypto.keys import load_public_key_from_base64, public_key_to_base64
from asap.crypto.models import SignatureBlock, SignedManifest
from asap.crypto.signing import canonicalize, verify_manifest
from asap.crypto.trust_levels import TrustLevel
from asap.errors import SignatureVerificationError
from asap.models.entities import Manifest


def detect_trust_level(signed_manifest: SignedManifest) -> TrustLevel:
    """Return trust_level from signature block (defaults to SELF_SIGNED for legacy manifests)."""
    return signed_manifest.signature.trust_level


def sign_with_ca(
    manifest: Manifest,
    agent_key: Ed25519PrivateKey,
    ca_key: Ed25519PrivateKey,
) -> SignedManifest:
    """Sign manifest with ASAP CA key (simulation; full service in v2.0). JCS canonicalized.

    Tech debt: Replace with real CA service integration. See issue #44.
    """
    _ = agent_key
    payload_bytes = canonicalize(manifest)
    raw_signature = ca_key.sign(payload_bytes)
    signature_b64 = base64.b64encode(raw_signature).decode("ascii")
    sig_block = SignatureBlock(
        alg="ed25519",
        signature=signature_b64,
        trust_level=TrustLevel.VERIFIED,
    )
    ca_public_b64 = public_key_to_base64(ca_key.public_key())
    return SignedManifest(manifest=manifest, signature=sig_block, public_key=ca_public_b64)


def verify_ca_signature(
    signed_manifest: SignedManifest,
    known_cas: Iterable[str] | Iterable[Ed25519PublicKey],
) -> bool:
    """Verify manifest was signed by a known CA. Raises SignatureVerificationError if invalid or unknown CA."""
    if signed_manifest.signature.trust_level != TrustLevel.VERIFIED:
        raise SignatureVerificationError(
            f"Expected trust_level=verified for CA verification, got {signed_manifest.signature.trust_level.value}.",
            details={"trust_level": signed_manifest.signature.trust_level.value},
        )
    if not signed_manifest.public_key:
        raise SignatureVerificationError(
            "Cannot verify CA: signed manifest has no public_key.",
            details={},
        )
    public_key = load_public_key_from_base64(signed_manifest.public_key)
    known_ca_b64 = {
        public_key_to_base64(ca) if isinstance(ca, Ed25519PublicKey) else ca for ca in known_cas
    }
    if public_key_to_base64(public_key) not in known_ca_b64:
        raise SignatureVerificationError(
            "CA not in known_cas: signature from unknown CA.",
            details={"public_key_preview": signed_manifest.public_key[:16] + "..."},
        )
    verify_manifest(signed_manifest, public_key=public_key)
    return True
