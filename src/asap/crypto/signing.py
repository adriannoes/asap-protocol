"""Ed25519 manifest signing with JCS canonicalization (RFC 8785)."""

import base64
import binascii
from typing import cast

import jcs
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)
from cryptography.exceptions import InvalidSignature

from asap.crypto.keys import load_public_key_from_base64, public_key_to_base64
from asap.crypto.models import SignatureBlock, SignedManifest
from asap.errors import SignatureVerificationError
from asap.models.entities import Manifest


def canonicalize(manifest: Manifest) -> bytes:
    payload = manifest.model_dump(exclude={"signature"})
    return cast(bytes, jcs.canonicalize(payload))


def sign_manifest(
    manifest: Manifest,
    private_key: Ed25519PrivateKey,
) -> SignedManifest:
    payload_bytes = canonicalize(manifest)
    raw_signature = private_key.sign(payload_bytes)
    assert len(raw_signature) == 64, "Ed25519 signature must be 64 bytes"
    signature_b64 = base64.b64encode(raw_signature).decode("ascii")
    block = SignatureBlock(alg="ed25519", signature=signature_b64)
    public_key_b64 = public_key_to_base64(private_key.public_key())
    return SignedManifest(manifest=manifest, signature=block, public_key=public_key_b64)


def verify_manifest(
    signed_manifest: SignedManifest,
    public_key: Ed25519PublicKey | None = None,
) -> bool:
    if signed_manifest.signature.alg != "ed25519":
        raise SignatureVerificationError(
            f"Unsupported signature algorithm: {signed_manifest.signature.alg}. "
            "Only ed25519 is supported.",
            details={"alg": signed_manifest.signature.alg},
        )
    pk = public_key
    if pk is None:
        if not signed_manifest.public_key:
            raise SignatureVerificationError(
                "Cannot verify: no public key provided and signed manifest has no public_key.",
                details={},
            )
        try:
            pk = load_public_key_from_base64(signed_manifest.public_key)
        except ValueError as e:
            raise SignatureVerificationError(
                f"Invalid public_key in signed manifest: {e}.",
                details={},
            ) from e
    try:
        raw_sig = base64.b64decode(signed_manifest.signature.signature)
    except binascii.Error as e:
        raise SignatureVerificationError(
            f"Invalid signature encoding (base64): {e}.",
            details={},
        ) from e
    if len(raw_sig) != 64:
        raise SignatureVerificationError(
            f"Ed25519 signature must be 64 bytes, got {len(raw_sig)}. Possible tampering.",
            details={"signature_length": len(raw_sig)},
        )
    payload_bytes = canonicalize(signed_manifest.manifest)
    try:
        pk.verify(raw_sig, payload_bytes)
    except InvalidSignature as e:
        raise SignatureVerificationError(
            "Signature verification failed: manifest may have been tampered with or signature is invalid.",
            details={"cause": str(e)},
        ) from e
    return True
