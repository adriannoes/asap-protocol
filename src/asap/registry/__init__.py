"""Registry automation (Lite Registry bot flows)."""

from __future__ import annotations

from asap.registry.anti_spam import (
    DEFAULT_AUTO_REGISTER_VERIFICATION,
    TRUST_LEVEL_SELF_SIGNED,
    auto_register_verification,
)
from asap.registry.bot_pr import BotPRResult, BotPRSettings, merge_lite_registry

__all__ = [
    "DEFAULT_AUTO_REGISTER_VERIFICATION",
    "TRUST_LEVEL_SELF_SIGNED",
    "BotPRResult",
    "BotPRSettings",
    "auto_register_verification",
    "merge_lite_registry",
]
