#!/usr/bin/env python3
"""Process agent revocation from a GitHub Issue Form body (IssueOps).

Parses the issue body (markdown with ### headers from the revoke_agent template),
validates that the agent URN exists in registry.json, and appends the entry
to revoked_agents.json.
Writes validation errors or success to result.json.

Usage (from GitHub Actions):
  python scripts/process_revocation.py --body "$ISSUE_BODY" --issue-number N --output result.json
"""

from __future__ import annotations

import argparse
import json
import logging
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

from pydantic import ValidationError

# Ensure scripts/lib and src are on path when run from repo root (e.g. in CI)
_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT / "scripts"))
if str(_REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT / "src"))

from lib.debug_id import generate_debug_id  # noqa: E402
from lib.registry_io import (  # noqa: E402
    load_registry,
    load_revoked,
    sanitize_input,
    save_revoked,
    write_validation_result,
)

from asap.client.revocation import RevokedAgentsList, RevokedEntry  # noqa: E402

logger = logging.getLogger(__name__)

# GitHub Issue Form body mapping (header label -> field name)
_HEADER_TO_FIELD = {
    "Agent URN": "urn",
    "Reason": "reason",
}


def parse_issue_body(body: str) -> dict[str, str]:
    if not body or not body.strip():
        return {}

    fields: dict[str, str] = {}

    parts = re.split(r"(?im)^###\s+", body)
    for part in parts:
        part = part.strip()
        if not part:
            continue

        first_line, _, rest = part.partition("\n")
        header = first_line.strip()
        value = rest.strip()

        field = _HEADER_TO_FIELD.get(header)
        if field:
            max_len = 500 if field == "reason" else 200
            fields[field] = sanitize_input(value, max_length=max_len)

    return fields


def _fail_revocation(output_path: str, errors: list[str], issue_number: str) -> None:
    debug_id = generate_debug_id()
    err_str = "; ".join(errors)
    logger.info(
        json.dumps(
            {
                "event": "revocation.validation_failed",
                "debug_id": debug_id,
                "errors": err_str,
                "issue_number": issue_number,
            }
        )
    )
    write_validation_result(output_path, errors=err_str, debug_id=debug_id)


def run(
    body: str,
    issue_number: str,
    output_path: str,
    registry_path: str = "registry.json",
    revoked_path: str = "revoked_agents.json",
) -> None:
    errors: list[str] = []

    form = parse_issue_body(body)
    urn = (form.get("urn") or "").strip()
    reason = (form.get("reason") or "").strip()

    if not urn:
        errors.append("Missing required field: Agent URN")
    if not reason:
        errors.append("Missing required field: Reason")

    if errors:
        _fail_revocation(output_path, errors, issue_number)
        return

    # Basic URN format check
    if not urn.startswith("urn:asap:agent:"):
        errors.append(f"Invalid URN format: must start with 'urn:asap:agent:'. Got: {urn[:50]}...")
        _fail_revocation(output_path, errors, issue_number)
        return

    agents = load_registry(registry_path)
    if not any(a.get("id") == urn for a in agents):
        errors.append(
            f"Agent {urn!r} not found in the registry. "
            "The agent must be registered before it can be revoked."
        )
        _fail_revocation(output_path, errors, issue_number)
        return

    revoked_data = load_revoked(revoked_path)
    try:
        revoked_list = RevokedAgentsList.model_validate(revoked_data)
    except ValidationError as e:
        errors.append(f"revoked_agents.json schema invalid: {e!s}")
        _fail_revocation(output_path, errors, issue_number)
        return

    if any(entry.urn == urn for entry in revoked_list.revoked):
        errors.append(f"Agent {urn!r} is already in the revocation list.")
        _fail_revocation(output_path, errors, issue_number)
        return

    revoked_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    revoked_list.revoked.append(RevokedEntry(urn=urn, reason=reason, revoked_at=revoked_at))
    save_revoked(revoked_path, revoked_list.model_dump())
    write_validation_result(output_path, valid=True)


def main() -> None:
    parser = argparse.ArgumentParser(description="Process agent revocation from issue body")
    parser.add_argument("--body", required=True, help="Issue body (markdown)")
    parser.add_argument("--issue-number", required=True, help="Issue number (for logging)")
    parser.add_argument("--output", required=True, help="Path to write result.json")
    parser.add_argument(
        "--registry",
        default="registry.json",
        help="Path to registry.json (default: registry.json)",
    )
    parser.add_argument(
        "--revoked",
        default="revoked_agents.json",
        help="Path to revoked_agents.json (default: revoked_agents.json)",
    )
    args = parser.parse_args()
    try:
        run(
            body=args.body,
            issue_number=args.issue_number,
            output_path=args.output,
            registry_path=args.registry,
            revoked_path=args.revoked,
        )
    except Exception as err:
        debug_id = generate_debug_id()
        logger.info(
            json.dumps(
                {
                    "event": "revocation.unexpected_error",
                    "debug_id": debug_id,
                    "issue_number": args.issue_number,
                }
            )
        )
        logger.exception("Unexpected error processing revocation: %s", err)
        try:
            write_validation_result(
                args.output, errors="Internal processing error", debug_id=debug_id
            )
        except OSError:
            logger.exception("Failed to write error output")
        sys.exit(1)


if __name__ == "__main__":
    main()
