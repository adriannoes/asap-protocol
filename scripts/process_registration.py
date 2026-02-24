#!/usr/bin/env python3
"""Process agent registration from a GitHub Issue Form body (IssueOps).

Parses the issue body (markdown with ### headers from the register_agent template),
validates the submission against the Manifest schema and registry rules,
and either updates registry.json (valid) or writes validation errors to result.json (invalid).

Usage (from GitHub Actions):
  python scripts/process_registration.py --body "$ISSUE_BODY" --issue-number N --author "$GITHUB_ACTOR" --output result.json
"""

from __future__ import annotations

import argparse
import ipaddress
import json
import logging
import os
import re
import sys
import tempfile
from pathlib import Path
from typing import Any, cast
from urllib.parse import urlparse

import httpx
from pydantic import ValidationError

# Ensure src and scripts/lib are on path when run from repo root (e.g. in CI)
_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT / "src"))
if str(_REPO_ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT / "scripts"))

from asap.discovery.registry import generate_registry_entry  # noqa: E402
from asap.models.entities import Manifest  # noqa: E402
from lib.debug_id import generate_debug_id  # noqa: E402

logger = logging.getLogger(__name__)

# Blocked hosts for SSRF protection (CWE-918)
_BLOCKED_HOSTS = frozenset(
    {
        "localhost",
        "127.0.0.1",
        "::1",
        "0.0.0.0",
        "metadata.google.internal",
        "metadata.aws.internal",
        "169.254.169.254",
    }
)


def _is_safe_url(url: str) -> bool:
    """SSRF protection: block private IPs, loopback, cloud metadata."""
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        return False
    hostname = (parsed.hostname or "").lower()
    if hostname in _BLOCKED_HOSTS:
        return False
    try:
        addr = ipaddress.ip_address(hostname)
        if addr.is_private or addr.is_loopback or addr.is_link_local:
            return False
    except ValueError:
        pass
    return True


def _write_validation_result(
    output_path: str,
    *,
    valid: bool = False,
    errors: str = "",
    debug_id: str | None = None,
) -> None:
    out: dict[str, bool | str] = {"valid": valid, "errors": errors}
    if debug_id:
        out["debug_id"] = debug_id
    Path(output_path).write_text(json.dumps(out))


def _fail_registration(
    output_path: str, errors: list[str], issue_number: str
) -> None:
    debug_id = generate_debug_id()
    err_str = "; ".join(errors)
    logger.info(
        json.dumps(
            {
                "event": "registration.validation_failed",
                "debug_id": debug_id,
                "errors": err_str,
                "issue_number": issue_number,
            }
        )
    )
    _write_validation_result(output_path, errors=err_str, debug_id=debug_id)


# GitHub Issue Form body uses ### <label> as section headers; labels from register_agent.yml
_HEADER_TO_FIELD = {
    "Agent name (slug-friendly)": "name",
    "Description": "description",
    "Manifest URL": "manifest_url",
    "HTTP Endpoint": "http_endpoint",
    "WebSocket Endpoint (optional)": "websocket_endpoint",
    "Skills": "skills",
    "Built with (framework)": "built_with",
    "Repository URL (optional)": "repository_url",
    "Documentation URL (optional)": "documentation_url",
    "Confirmation": "confirm",
}


def sanitize_input(text: str, max_length: int = 1000) -> str:
    if not text:
        return ""
    # Strip markdown code blocks / inline code backticks, HTML tags
    clean = re.sub(r"```[\s\S]*?```", "", text)
    clean = re.sub(r"`[^`]*`", "", clean)
    clean = re.sub(r"<[^>]+>", "", clean)
    # Remove control characters except newline and tab
    clean = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", clean)
    # Clamp length to prevent DoS via huge payload
    return clean.strip()[:max_length]


def parse_issue_body(body: str) -> dict[str, str]:
    if not body or not body.strip():
        return {}

    fields: dict[str, str] = {}

    # Extract sections matching "### Header Name\n...content..."
    # We split by '### ' and then safely process chunks.
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
            max_len = 2000 if field == "description" else 500
            fields[field] = sanitize_input(value, max_length=max_len)

    return fields


def fetch_manifest(url: str, timeout: float = 15.0) -> Manifest:
    if not _is_safe_url(url):
        raise ValueError(f"Blocked URL (private/metadata): {url}")
    with httpx.Client(timeout=timeout) as client:
        resp = client.get(url)
        resp.raise_for_status()
    return Manifest.model_validate_json(resp.text)


def load_registry(path: str) -> list[dict[str, Any]]:
    p = Path(path)
    if not p.exists():
        return []
    raw: object = json.loads(p.read_text())
    if isinstance(raw, list):
        return cast(list[dict[str, Any]], raw)
    if isinstance(raw, dict) and "agents" in raw:
        return cast(list[dict[str, Any]], raw["agents"])
    return []


def save_registry(path: str, agents: list[dict[str, Any]]) -> None:
    target = Path(path)
    content = json.dumps(agents, indent=2) + "\n"
    temp_dir = target.parent if target.parent != Path() else Path.cwd()
    fd, tmp = tempfile.mkstemp(dir=temp_dir, suffix=".tmp")
    try:
        with os.fdopen(fd, "w") as f:
            f.write(content)
        Path(tmp).replace(target)
    except BaseException:
        Path(tmp).unlink(missing_ok=True)
        raise


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
    manifest_url = (parsed.get("manifest_url") or "").strip()
    http_endpoint = (parsed.get("http_endpoint") or "").strip()
    websocket_endpoint = (parsed.get("websocket_endpoint") or "").strip()
    skills_str = (parsed.get("skills") or "").strip()
    built_with = (parsed.get("built_with") or "").strip() or None
    repository_url = (parsed.get("repository_url") or "").strip() or None
    documentation_url = (parsed.get("documentation_url") or "").strip() or None

    if not name:
        errors.append("Missing required field: name")
    if not manifest_url:
        errors.append("Missing required field: manifest_url")
    if not http_endpoint:
        errors.append("Missing required field: http_endpoint")
    if not skills_str:
        errors.append("Missing required field: skills")

    if errors:
        _fail_registration(output_path, errors, issue_number)
        return

    skills = [s.strip() for s in skills_str.split(",") if s.strip()]

    # Expected agent URN: urn:asap:agent:<github_username>:<name>
    # Normalize author to lowercase for URN (GitHub usernames are case-insensitive)
    expected_id = f"urn:asap:agent:{author.lower()}:{name}"

    try:
        manifest = fetch_manifest(manifest_url)
    except ValueError:
        errors.append(f"Blocked URL (private/metadata): {manifest_url}")
        _fail_registration(output_path, errors, issue_number)
        return
    except httpx.HTTPError:
        errors.append(f"Manifest URL unreachable: {manifest_url}")
        _fail_registration(output_path, errors, issue_number)
        return
    except ValidationError as e:
        error_count = e.error_count()
        errors.append(
            f"Manifest failed schema validation ({error_count} error(s)). "
            "Ensure it follows the ASAP Manifest format."
        )
        _fail_registration(output_path, errors, issue_number)
        return

    if manifest.id != expected_id:
        errors.append(f"Manifest id must be {expected_id!r}, got {manifest.id!r}")
    if manifest.name != name:
        errors.append(f"Manifest name must match issue name {name!r}, got {manifest.name!r}")

    manifest_skills = [s.id for s in manifest.capabilities.skills]
    for sk in skills:
        if sk not in manifest_skills:
            errors.append(f"Skill {sk!r} not declared in manifest (manifest has {manifest_skills})")

    if manifest.endpoints.asap != http_endpoint:
        errors.append(
            f"HTTP endpoint must match manifest (manifest has {manifest.endpoints.asap!r})"
        )
    if websocket_endpoint and manifest.endpoints.events != websocket_endpoint:
        errors.append(
            f"WebSocket endpoint must match manifest (manifest has {manifest.endpoints.events!r})"
        )

    if errors:
        _fail_registration(output_path, errors, issue_number)
        return

    # Uniqueness: id must not already exist in registry
    agents = load_registry(registry_path)
    existing_ids = {a.get("id") for a in agents if isinstance(a, dict)}
    if manifest.id in existing_ids:
        errors.append(f"Agent id {manifest.id!r} is already registered")
        _fail_registration(output_path, errors, issue_number)
        return

    endpoints = {
        "http": http_endpoint,
        "manifest": manifest_url,
    }
    if websocket_endpoint:
        endpoints["ws"] = websocket_endpoint

    try:
        entry = generate_registry_entry(
            manifest,
            endpoints,
            repository_url=repository_url,
            documentation_url=documentation_url,
            built_with=built_with,
        )
    except ValidationError as e:
        error_count = e.error_count()
        errors.append(
            f"Registry entry validation failed ({error_count} error(s)). "
            "Check manifest and endpoint format."
        )
        _fail_registration(output_path, errors, issue_number)
        return

    agents.append(entry.model_dump(mode="json"))
    save_registry(registry_path, agents)
    _write_validation_result(output_path, valid=True)


def main() -> None:
    parser = argparse.ArgumentParser(description="Process agent registration from issue body")
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
    except Exception:
        debug_id = generate_debug_id()
        logger.info(
            json.dumps(
                {
                    "event": "registration.unexpected_error",
                    "debug_id": debug_id,
                    "issue_number": args.issue_number,
                }
            )
        )
        logger.exception("Unexpected error processing registration")
        try:
            _write_validation_result(
                args.output, errors="Internal processing error", debug_id=debug_id
            )
        except OSError:
            logger.exception("Failed to write error output")
        sys.exit(1)


if __name__ == "__main__":
    main()
