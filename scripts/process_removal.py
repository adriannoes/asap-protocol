#!/usr/bin/env python3
"""Process agent removal from a GitHub Issue Form body (IssueOps).

Parses the issue body (markdown with ### headers from the remove_agent template),
validates that the author of the issue owns the agent (`urn:asap:agent:<author>:<name>`),
and removes it from registry.json.
Writes validation errors or success to result.json.

Usage (from GitHub Actions):
  python scripts/process_removal.py --body "$ISSUE_BODY" --issue-number N --author "$GITHUB_ACTOR" --output result.json
"""

from __future__ import annotations

import argparse
import json
import logging
import re
import sys
from pathlib import Path

# Ensure scripts/lib is on path when run from repo root (e.g. in CI)
_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT / "scripts"))

from lib.debug_id import generate_debug_id  # noqa: E402
from lib.registry_io import (  # noqa: E402
    load_registry,
    sanitize_input,
    save_registry,
    write_validation_result,
)

logger = logging.getLogger(__name__)

# GitHub Issue Form body mapping
_HEADER_TO_FIELD = {
    "Agent name (slug-friendly)": "name",
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
            fields[field] = sanitize_input(value, max_length=100)

    return fields


def _fail_removal(output_path: str, errors: list[str], issue_number: str) -> None:
    debug_id = generate_debug_id()
    err_str = "; ".join(errors)
    logger.info(
        json.dumps(
            {
                "event": "removal.validation_failed",
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
    author: str,
    output_path: str,
    registry_path: str = "registry.json",
) -> None:
    errors: list[str] = []

    parsed = parse_issue_body(body)
    name = (parsed.get("name") or "").strip()

    if not name:
        errors.append("Missing required field: name")

    if errors:
        _fail_removal(output_path, errors, issue_number)
        return

    expected_id = f"urn:asap:agent:{author.lower()}:{name}"

    agents = load_registry(registry_path)
    found_agent = next(
        (a for a in agents if isinstance(a, dict) and a.get("id") == expected_id),
        None,
    )
    if not found_agent:
        errors.append(
            f"Agent {expected_id!r} not found in the registry. "
            "Make sure you typed the exact name and that you are the original author."
        )
        _fail_removal(output_path, errors, issue_number)
        return

    agents.remove(found_agent)
    save_registry(registry_path, agents)
    write_validation_result(output_path, valid=True)


def main() -> None:
    parser = argparse.ArgumentParser(description="Process agent removal from issue body")
    parser.add_argument("--body", required=True, help="Issue body (markdown)")
    parser.add_argument("--issue-number", required=True, help="Issue number (for logging)")
    parser.add_argument("--author", required=True, help="GitHub username (issue author)")
    parser.add_argument("--output", required=True, help="Path to write result.json")
    parser.add_argument(
        "--registry",
        default="registry.json",
        help="Path to registry.json (default: registry.json)",
    )
    args = parser.parse_args()
    try:
        run(
            body=args.body,
            issue_number=args.issue_number,
            author=args.author,
            output_path=args.output,
            registry_path=args.registry,
        )
    except Exception as err:
        debug_id = generate_debug_id()
        logger.info(
            json.dumps(
                {
                    "event": "removal.unexpected_error",
                    "debug_id": debug_id,
                    "issue_number": args.issue_number,
                }
            )
        )
        logger.exception("Unexpected error processing removal: %s", err)
        try:
            write_validation_result(
                args.output, errors="Internal processing error", debug_id=debug_id
            )
        except OSError:
            logger.exception("Failed to write error output")
        sys.exit(1)


if __name__ == "__main__":
    main()
