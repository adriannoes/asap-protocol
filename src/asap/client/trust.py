"""Trust validation for SDK consumers.

Validates Ed25519-signed manifests using the embedded ASAP CA public key.
SEC-003: SDK embeds CA key locally (no network call).
"""

from __future__ import annotations

import os

from asap.crypto.models import SignedManifest
from asap.crypto.trust import verify_ca_signature

# Default ASAP CA public key (base64). Matches tests/fixtures/asap_ca/ca_public_b64.txt.
# Override via ASAP_CA_PUBLIC_KEY env var for custom CA.
_DEFAULT_ASAP_CA_B64 = "QRVEqzwjzUfPhzznmftAZzpf83euZuoWzbynkuqj4E4="

ASAP_CA_PUBLIC_KEY_B64: str = os.environ.get("ASAP_CA_PUBLIC_KEY", _DEFAULT_ASAP_CA_B64)


def verify_agent_trust(signed_manifest: SignedManifest) -> bool:
    """Validate manifest Ed25519 signature using embedded ASAP CA key. Raises SignatureVerificationError on invalid."""
    return verify_ca_signature(signed_manifest, known_cas=[ASAP_CA_PUBLIC_KEY_B64])
