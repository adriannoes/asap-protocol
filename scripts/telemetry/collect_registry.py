#!/usr/bin/env python3
"""Count agents in the public `registry.json` mirror and optionally diff vs a prior snapshot.

Loads the Lite Registry JSON (root ``agents`` array or a bare array of entries) from a
HTTPS URL (default: GitHub raw mirror) or a local path, matching
``jq '.agents | length'`` for the wrapped format.

``--previous`` may point to either:

- output from an earlier run of this script (uses ``agent_count``), or
- a saved copy of ``registry.json`` (agents are counted the same way).
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import httpx

DEFAULT_REGISTRY_URL = (
    "https://raw.githubusercontent.com/adriannoes/asap-protocol/main/registry.json"
)
REQUEST_TIMEOUT_SECONDS = 30.0


def count_registry_agents(raw: object) -> int:
    """Return the number of agent entries (array root or ``.agents`` list).

    Raises:
        ValueError: If JSON root is not a supported registry shape.
    """
    if isinstance(raw, list):
        return len(raw)
    if isinstance(raw, dict):
        agents = raw.get("agents")
        if isinstance(agents, list):
            return len(agents)
    msg = "registry must be a JSON array or an object with an 'agents' array"
    raise ValueError(msg)


def detect_registry_format(raw: object) -> str:
    """Return ``lite_registry`` or ``array`` for telemetry metadata."""
    if isinstance(raw, list):
        return "array"
    if isinstance(raw, dict) and isinstance(raw.get("agents"), list):
        return "lite_registry"
    raise ValueError("unsupported registry shape")


def fetch_registry_json(url: str, client: httpx.Client | None = None) -> object:
    """GET JSON from ``url`` (``http`` or ``https`` only)."""
    parsed = urlparse(url)
    if parsed.scheme not in ("https", "http"):
        msg = f"unsupported URL scheme for registry fetch: {parsed.scheme!r}"
        raise ValueError(msg)
    close_client = client is None
    http = client or httpx.Client(
        timeout=REQUEST_TIMEOUT_SECONDS,
        follow_redirects=True,
    )
    try:
        response = http.get(url)
        response.raise_for_status()
        return response.json()
    finally:
        if close_client:
            http.close()


def resolve_previous_agent_count(raw: object) -> int:
    """Resolve count from prior telemetry JSON or a registry document."""
    if isinstance(raw, dict):
        previous = raw.get("agent_count")
        if isinstance(previous, int):
            return previous
    return count_registry_agents(raw)


def load_previous_count(path: Path) -> int:
    """Load and resolve agent count from a previous snapshot file."""
    prev_raw: object = json.loads(path.read_text(encoding="utf-8"))
    return resolve_previous_agent_count(prev_raw)


def collect_registry_snapshot(
    raw: object,
    *,
    registry_ref: str,
    previous_count: int | None,
) -> dict[str, Any]:
    """Build telemetry dict for one registry fetch."""
    collected_at = datetime.now(UTC).replace(microsecond=0).isoformat()
    count = count_registry_agents(raw)
    fmt = detect_registry_format(raw)
    growth: int | None = None if previous_count is None else count - previous_count
    return {
        "source": "registry_mirror",
        "registry_ref": registry_ref,
        "format": fmt,
        "collected_at": collected_at,
        "agent_count": count,
        "previous_agent_count": previous_count,
        "growth": growth,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Count agents in registry.json mirror and optionally diff vs a prior file."
    )
    parser.add_argument(
        "--url",
        default=DEFAULT_REGISTRY_URL,
        help="HTTPS URL of registry.json (ignored when --registry-path is set).",
    )
    parser.add_argument(
        "--registry-path",
        type=Path,
        default=None,
        help="Read registry JSON from this local path instead of --url.",
    )
    parser.add_argument(
        "--previous",
        type=Path,
        default=None,
        help=(
            "Optional prior snapshot: earlier collector output (agent_count) or "
            "saved registry.json."
        ),
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        help="Write JSON to this path instead of stdout",
    )
    args = parser.parse_args(argv)

    previous_count: int | None = None
    if args.previous is not None:
        if not args.previous.is_file():
            print(f"Previous snapshot not found: {args.previous}", file=sys.stderr)
            return 1
        try:
            previous_count = load_previous_count(args.previous)
        except (json.JSONDecodeError, ValueError, OSError) as exc:
            print(f"Failed to read previous snapshot: {exc}", file=sys.stderr)
            return 1

    registry_ref: str
    try:
        if args.registry_path is not None:
            if not args.registry_path.is_file():
                print(f"Registry file not found: {args.registry_path}", file=sys.stderr)
                return 1
            registry_ref = str(args.registry_path.resolve())
            raw: object = json.loads(args.registry_path.read_text(encoding="utf-8"))
        else:
            registry_ref = args.url
            raw = fetch_registry_json(args.url)
    except httpx.HTTPStatusError as exc:
        print(
            f"HTTP {exc.response.status_code} fetching registry: {exc.request.url!s}",
            file=sys.stderr,
        )
        return 1
    except (httpx.HTTPError, json.JSONDecodeError, ValueError, OSError) as exc:
        print(f"Registry load failed: {exc}", file=sys.stderr)
        return 1

    try:
        report = collect_registry_snapshot(
            raw,
            registry_ref=registry_ref,
            previous_count=previous_count,
        )
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    text = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text, encoding="utf-8")
    else:
        sys.stdout.write(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
