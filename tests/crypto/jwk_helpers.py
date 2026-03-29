"""Shared Ed25519 public JWK helpers for tests."""

from __future__ import annotations

import base64

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey


def make_ed25519_jwk() -> dict[str, str]:
    """Return a valid Ed25519 public JWK (OKP) from a freshly generated key pair."""
    sk = Ed25519PrivateKey.generate()
    return ed25519_public_jwk(sk)


def ed25519_public_jwk(private_key: Ed25519PrivateKey) -> dict[str, str]:
    """Derive a public JWK (OKP / Ed25519) from an Ed25519 private key."""
    raw = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
    x = base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")
    return {"kty": "OKP", "crv": "Ed25519", "x": x}
