#!/usr/bin/env python3
"""Evaluate whether an auto-registration PR may enable squash auto-merge.

Policy:
- ``registry.json`` must already validate as :class:`~asap.discovery.registry.LiteRegistry`
  (run ``scripts/validate_registry.py`` first in CI).
- **Self-signed path** (registry terms): no new or escalated **verified** marketplace badge.
  New agents must not ship with ``verification.status == "verified"``.
  Existing agents must not gain ``verified`` unless they were already verified in the base
  revision (human review handles promotions).

Exit code ``0`` = eligible for auto-merge; ``1`` = requires human review. Reason printed to
stdout (and stderr on failure).

Run from the repo root with ``uv run python scripts/check_auto_registration_merge_eligible.py``
so the editable ``asap`` package is on ``sys.path``.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import cast

from pydantic import ValidationError

from asap.discovery.registry import LiteRegistry, RegistryEntry
from asap.models.enums import VerificationState


def _is_verified(entry: RegistryEntry) -> bool:
    v = entry.verification
    return v is not None and v.status == VerificationState.VERIFIED


def _load(path: Path) -> LiteRegistry:
    raw = json.loads(path.read_text())
    if isinstance(raw, list):
        agents = [RegistryEntry.model_validate(cast(dict[str, object], item)) for item in raw]
        return LiteRegistry(
            version="1.0",
            updated_at=datetime.fromtimestamp(0, tz=UTC),
            agents=agents,
        )
    return LiteRegistry.model_validate(cast(dict[str, object], raw))


def evaluate(base_path: Path, head_path: Path) -> tuple[bool, str]:
    try:
        base = _load(base_path)
        head = _load(head_path)
    except (json.JSONDecodeError, ValidationError, OSError) as e:
        return False, f"Failed to parse registry JSON: {e}"

    base_by_id: dict[str, RegistryEntry] = {str(a.id): a for a in base.agents}

    for agent in head.agents:
        aid = str(agent.id)
        prev = base_by_id.get(aid)
        if prev is None:
            if _is_verified(agent):
                return (
                    False,
                    f"New agent {aid} must not use verification.status=verified "
                    "(self-signed / auto-registration path only).",
                )
        elif _is_verified(agent) and not _is_verified(prev):
            return (
                False,
                f"Agent {aid} cannot be promoted to verified via auto-registration; "
                "use the manual verification flow.",
            )
    return True, "Auto-merge eligible: registry verification policy satisfied."


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--base-file",
        type=Path,
        required=True,
        help="Path to base revision registry.json",
    )
    parser.add_argument(
        "--head-file",
        type=Path,
        required=True,
        help="Path to PR head registry.json",
    )
    args = parser.parse_args()
    ok, message = evaluate(args.base_file, args.head_file)
    print(message)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
