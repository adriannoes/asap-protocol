"""Map OpenAPI operations to ASAP approval strength (OA-008, v2.2.1 self-auth)."""

from __future__ import annotations

import logging
from collections.abc import Mapping, Sequence
from typing import Literal, cast

from asap.adapters.openapi.capability_mapper import OpenAPICapability

logger = logging.getLogger(__name__)

ApprovalStrength = Literal["session", "webauthn"]

_HTTP_VERBS_FROZEN: frozenset[str] = frozenset(
    ("GET", "PUT", "POST", "DELETE", "OPTIONS", "HEAD", "PATCH", "TRACE"),
)
_VALID_STRENGTH: frozenset[str] = frozenset(("session", "webauthn"))


def normalize_approval_strength_map(
    mapping: Mapping[str, str],
) -> dict[str, ApprovalStrength]:
    """Normalize user map keys (HTTP verbs uppercased) and validate strength values.

    Args:
        mapping: Keys are HTTP methods (any case) or OpenAPI ``operationId`` strings
            (case-sensitive). Values must be ``\"session\"`` or ``\"webauthn\"``.

    Returns:
        A normalized dict suitable for :func:`resolve_approval_strength`.

    Raises:
        ValueError: If any strength value is invalid.
    """
    out: dict[str, ApprovalStrength] = {}
    for raw_key, raw_val in mapping.items():
        if not isinstance(raw_key, str) or not raw_key.strip():
            continue
        key = raw_key.strip()
        norm_key = key.upper() if key.strip().upper() in _HTTP_VERBS_FROZEN else key.strip()
        if not isinstance(raw_val, str) or not raw_val.strip():
            msg = f"approval_strength value for {raw_key!r} must be a non-empty string"
            raise ValueError(msg)
        val = raw_val.strip().lower()
        if val not in _VALID_STRENGTH:
            msg = (
                f"Invalid approval_strength {raw_val!r} for key {raw_key!r}; "
                "expected 'session' or 'webauthn'"
            )
            raise ValueError(msg)
        out[norm_key] = cast("ApprovalStrength", val)
    return out


def resolve_approval_strength(
    *,
    http_method: str,
    operation_id: str | None,
    mapping: Mapping[str, ApprovalStrength],
) -> ApprovalStrength | None:
    """Resolve strength for one operation.

    Precedence:
        1. Exact ``operationId`` key in *mapping* when *operation_id* is set.
        2. HTTP method (case-insensitive, compared as uppercase).
    """
    if operation_id is not None and operation_id in mapping:
        return mapping[operation_id]
    verb = http_method.strip().upper()
    return mapping.get(verb)


def collect_webauthn_required_capability_names(
    capabilities: Sequence[OpenAPICapability],
    approval_strength: Mapping[str, str],
) -> list[str]:
    """Capability names that must appear in ``FreshSessionConfig.require_webauthn_for``.

    Args:
        capabilities: Mapped OpenAPI operations from :func:`~.capability_mapper.map_openapi_to_capabilities`.
        approval_strength: Raw mapping (normalized by :func:`normalize_approval_strength_map`).
    """
    normalized = normalize_approval_strength_map(approval_strength)
    ordered: list[str] = []
    seen: set[str] = set()
    for cap in capabilities:
        strength = resolve_approval_strength(
            http_method=cap.http_method,
            operation_id=cap.operation_id,
            mapping=normalized,
        )
        if strength == "webauthn":
            name = cap.skill.id
            if name not in seen:
                seen.add(name)
                ordered.append(name)
    logger.debug("collect_webauthn_required_capability_names: %s name(s)", len(ordered))
    return ordered


__all__ = [
    "ApprovalStrength",
    "collect_webauthn_required_capability_names",
    "normalize_approval_strength_map",
    "resolve_approval_strength",
]
