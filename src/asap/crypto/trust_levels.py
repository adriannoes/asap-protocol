"""Trust level enum (SD-5); separate module to avoid circular imports."""

from enum import Enum


class TrustLevel(str, Enum):
    """Trust categorization for agent manifests (SD-5)."""

    SELF_SIGNED = "self-signed"
    """Free tier: agent signs its own manifest."""

    VERIFIED = "verified"
    """ASAP CA verified tier ($49/mo): manifest signed by ASAP CA."""

    ENTERPRISE = "enterprise"
    """Enterprise tier: manifest signed by organization CA."""
