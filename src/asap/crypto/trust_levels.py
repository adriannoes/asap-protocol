"""Trust level enum (SD-5); separate module to avoid circular imports."""

from enum import Enum


class TrustLevel(str, Enum):
    """Trust categorization for agent manifests (SD-5)."""

    SELF_SIGNED = "self-signed"
    VERIFIED = "verified"
    ENTERPRISE = "enterprise"
