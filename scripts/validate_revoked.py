#!/usr/bin/env python3
"""Validate revoked_agents.json against the RevokedAgentsList Pydantic schema.

Used by CI to ensure manual edits to revoked_agents.json do not break
the SDK revocation check or IssueOps revoke flow.

Exit code: 0 if valid, 1 if invalid (errors to stderr).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Ensure src is on path when run from repo root (e.g. in CI)
_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT / "src"))

from pydantic import ValidationError  # noqa: E402

from asap.client.revocation import RevokedAgentsList  # noqa: E402


def validate_revoked(path: Path) -> list[str]:
    """Return list of error strings; empty if valid."""
    if not path.exists():
        return [f"File not found: {path}"]

    try:
        raw = json.loads(path.read_text())
    except json.JSONDecodeError as e:
        return [f"Invalid JSON: {e}"]

    if not isinstance(raw, dict):
        return ["Root must be a JSON object with 'revoked' and 'version'."]

    try:
        RevokedAgentsList.model_validate(raw)
        return []
    except ValidationError as e:
        return [f"{'.'.join(str(x) for x in err['loc'])}: {err['msg']}" for err in e.errors()]


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate revoked_agents.json against the RevokedAgentsList schema."
    )
    parser.add_argument(
        "file",
        nargs="?",
        default="revoked_agents.json",
        type=Path,
        help="Path to revoked agents JSON file (default: revoked_agents.json)",
    )
    args = parser.parse_args()

    errors = validate_revoked(args.file)
    if not errors:
        return 0
    for msg in errors:
        print(msg, file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
