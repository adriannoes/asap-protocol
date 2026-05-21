from __future__ import annotations

from asap.models.enums import VerificationState
from asap.registry.anti_spam import (
    TRUST_LEVEL_SELF_SIGNED,
    auto_register_verification,
)


def test_auto_register_verification_returns_pending() -> None:
    status = auto_register_verification()
    assert status.status == VerificationState.PENDING


def test_auto_register_verification_independent_instances() -> None:
    a = auto_register_verification()
    b = auto_register_verification()
    assert a is not b
    assert a.model_dump() == b.model_dump()
    assert a.status == VerificationState.PENDING


def test_trust_level_self_signed_constant() -> None:
    assert TRUST_LEVEL_SELF_SIGNED == "self-signed"
