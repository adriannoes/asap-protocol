"""ASAP Protocol Cryptographic Layer.

This module provides Ed25519 key management and manifest signing for agent identity:
- Key generation, serialization, and loading (PEM, file, env)
- Manifest signing with JCS canonicalization (RFC 8785)
- Signature verification (RFC 8032 strict)

Public exports:
    keys: Key generation and management submodule
    signing: Manifest canonicalize and sign_manifest
    models: SignedManifest, SignatureBlock
"""

from asap.crypto import keys
from asap.crypto import signing
from asap.crypto import trust
from asap.crypto.models import SignatureBlock, SignedManifest
from asap.crypto.trust import detect_trust_level, sign_with_ca, verify_ca_signature
from asap.crypto.trust_levels import TrustLevel

__all__ = [
    "keys",
    "signing",
    "trust",
    "SignatureBlock",
    "SignedManifest",
    "TrustLevel",
    "detect_trust_level",
    "sign_with_ca",
    "verify_ca_signature",
]
