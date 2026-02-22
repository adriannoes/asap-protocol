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

# Ensure src is on path when run from repo root (e.g. in CI)
_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT / "src"))

from asap.discovery.registry import generate_registry_entry  # noqa: E402
from asap.models.entities import Manifest  # noqa: E402

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


def _write_validation_result(output_path: str, *, valid: bool = False, errors: str = "") -> None:
    Path(output_path).write_text(json.dumps({"valid": valid, "errors": errors}))


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


def parse_issue_body(body: str) -> dict[str, str]:
    """Extract form values from GitHub Issue Form markdown (### <label> sections)."""
    if not body or not body.strip():
        return {}

    fields: dict[str, str] = {}
    # Split by ### and then by newline to get header and value
    parts = re.split(r"\n### ", body.strip(), flags=re.IGNORECASE)
    for part in parts:
        part = part.strip()
        if not part:
            continue
        first_line, _, rest = part.partition("\n")
        header = first_line.strip()
        if header.startswith("###"):
            header = header[3:].strip()
        value = rest.split("\n### ")[0].strip() if rest else ""
        field = _HEADER_TO_FIELD.get(header)
        if field:
            fields[field] = value
    return fields


def fetch_manifest(url: str, timeout: float = 15.0) -> Manifest:
    """Fetch and validate manifest from URL. Raises ValueError/httpx.HTTPError/ValidationError on failure."""
    if not _is_safe_url(url):
        raise ValueError(f"Blocked URL (private/metadata): {url}")
    with httpx.Client(timeout=timeout) as client:
        resp = client.get(url)
        resp.raise_for_status()
    return Manifest.model_validate_json(resp.text)


def load_registry(path: str) -> list[dict[str, Any]]:
    """Load registry from JSON file. Supports array or LiteRegistry wrapper."""
    p = Path(path)
    if not p.exists():
        return []
    raw: Any = json.loads(p.read_text())
    if isinstance(raw, list):
        return cast(list[dict[str, Any]], raw)
    if isinstance(raw, dict) and "agents" in raw:
        return cast(list[dict[str, Any]], raw["agents"])
    return []


def save_registry(path: str, agents: list[dict[str, Any]]) -> None:
    """Write agents list to registry JSON file atomically."""
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
        _write_validation_result(output_path, errors="; ".join(errors))
        return

    skills = [s.strip() for s in skills_str.split(",") if s.strip()]

    # Expected agent URN: urn:asap:agent:<github_username>:<name>
    # Normalize author to lowercase for URN (GitHub usernames are case-insensitive)
    expected_id = f"urn:asap:agent:{author.lower()}:{name}"

    try:
        manifest = fetch_manifest(manifest_url)
    except ValueError:
        errors.append(f"Blocked URL (private/metadata): {manifest_url}")
        _write_validation_result(output_path, errors="; ".join(errors))
        return
    except httpx.HTTPError:
        errors.append(f"Manifest URL unreachable: {manifest_url}")
        _write_validation_result(output_path, errors="; ".join(errors))
        return
    except ValidationError as e:
        error_count = e.error_count()
        errors.append(
            f"Manifest failed schema validation ({error_count} error(s)). "
            "Ensure it follows the ASAP Manifest format."
        )
        _write_validation_result(output_path, errors="; ".join(errors))
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
        _write_validation_result(output_path, errors="; ".join(errors))
        return

    # Uniqueness: id must not already exist in registry
    agents = load_registry(registry_path)
    existing_ids = {a.get("id") for a in agents if isinstance(a, dict)}
    if manifest.id in existing_ids:
        errors.append(f"Agent id {manifest.id!r} is already registered")
        _write_validation_result(output_path, errors="; ".join(errors))
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
        _write_validation_result(output_path, errors="; ".join(errors))
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
        logger.exception("Unexpected error processing registration")
        try:
            _write_validation_result(args.output, errors="Internal processing error")
        except OSError:
            logger.exception("Failed to write error output")
        sys.exit(1)


if __name__ == "__main__":
    main()
