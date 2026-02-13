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
from asap.crypto.models import SignatureBlock, SignedManifest

__all__ = [
    "keys",
    "signing",
    "SignatureBlock",
    "SignedManifest",
]
