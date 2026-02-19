"""Pydantic models for signed manifests and signature blocks (ADR-18)."""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field

from asap.crypto.trust_levels import TrustLevel
from asap.models.entities import Manifest

# Base64 (standard alphabet) pattern for public_key and signature fields.
BASE64_PATTERN = r"^[A-Za-z0-9+/=]+$"


class SignatureBlock(BaseModel):
    """Ed25519 only (ADR-18); alg Literal["ed25519"], signature base64."""

    model_config = ConfigDict(extra="forbid")

    alg: Literal["ed25519"] = Field(
        ...,
        description="Signature algorithm (Ed25519 only per ADR-18).",
    )
    signature: Annotated[
        str,
        Field(..., description="Base64-encoded 64-byte Ed25519 signature.", pattern=BASE64_PATTERN),
    ]
    trust_level: TrustLevel = Field(
        default=TrustLevel.SELF_SIGNED,
        description="Trust tier: self-signed, verified (ASAP CA), or enterprise (org CA).",
    )


class SignedManifest(BaseModel):
    """Manifest + signature block; optional public_key (base64) for verification."""

    model_config = ConfigDict(extra="forbid")

    manifest: Manifest = Field(..., description="The signed manifest payload.")
    signature: SignatureBlock = Field(
        ...,
        description="Signature block (alg and signature bytes as base64).",
    )
    public_key: str | None = Field(
        default=None,
        description="Optional base64-encoded Ed25519 public key for verification.",
        pattern=BASE64_PATTERN,
    )
