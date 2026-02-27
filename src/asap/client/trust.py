"""Trust validation for SDK consumers.

Validates Ed25519-signed manifests using the ASAP CA public key.
SEC-003: SDK embeds CA key locally (no network call).
Fail Closed: ASAP_CA_PUBLIC_KEY env var is required; no default in production.
"""

from __future__ import annotations

import os

from asap.crypto.models import SignedManifest
from asap.crypto.trust import verify_ca_signature


def _get_ca_key_b64() -> str:
    key = os.environ.get("ASAP_CA_PUBLIC_KEY")
    if not key:
        raise RuntimeError(
            "ASAP_CA_PUBLIC_KEY environment variable is required. "
            "Set it to the base64-encoded ASAP CA public key (fail closed)."
        )
    return key


def __getattr__(name: str) -> str:
    if name == "ASAP_CA_PUBLIC_KEY_B64":
        return _get_ca_key_b64()
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def verify_agent_trust(signed_manifest: SignedManifest) -> bool:
    return verify_ca_signature(signed_manifest, known_cas=[_get_ca_key_b64()])
