"""Pydantic models for signed manifests and signature blocks (ADR-18)."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from asap.models.entities import Manifest


class SignatureBlock(BaseModel):
    """Ed25519 only (ADR-18); alg Literal["ed25519"], signature base64."""

    model_config = ConfigDict(extra="forbid")

    alg: Literal["ed25519"] = Field(
        ...,
        description="Signature algorithm (Ed25519 only per ADR-18).",
    )
    signature: str = Field(
        ...,
        description="Base64-encoded 64-byte Ed25519 signature.",
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
    )
