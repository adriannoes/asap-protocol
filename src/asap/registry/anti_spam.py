"""Anti-spam defaults for auto-registration (AUTO-005).

New listings use marketplace verification ``pending`` (self-signed trust path).
Promotion to ``verified`` stays manual (IssueOps).
"""

from __future__ import annotations

from asap.models.entities import VerificationStatus
from asap.models.enums import VerificationState

# Human-readable trust label used in receipts and tags (manifest crypto trust is separate).
TRUST_LEVEL_SELF_SIGNED = "self-signed"

DEFAULT_AUTO_REGISTER_VERIFICATION = VerificationStatus(status=VerificationState.PENDING)


def auto_register_verification() -> VerificationStatus:
    """Return verification block for a new auto-registered Lite Registry entry."""
    return DEFAULT_AUTO_REGISTER_VERIFICATION.model_copy()
