#!/usr/bin/env python3
"""Assign rotated asap_version to each Lite Registry agent for realistic ecosystem demos.

Reads registry.json (wrapped `{agents: [...]}` or bare array), sets asap_version per
agent index using PROTOCOL_VERSIONS cycle, writes repo root registry.json and
apps/web/public/registry.json identically.

Keep PROTOCOL_VERSIONS in sync with apps/web/src/lib/protocol-versions.ts.

Usage (repo root): uv run python scripts/diversify_registry_asap_versions.py
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import cast

_REPO_ROOT = Path(__file__).resolve().parent.parent

PROTOCOL_VERSIONS: tuple[str, ...] = ("1.0.0", "1.1.0", "2.0.0", "2.1.0", "2.2.1")


def _agents_payload(data: object) -> tuple[list[dict[str, object]], bool]:
    """Return (agents_list, was_wrapped_dict)."""
    if isinstance(data, list):
        return cast("list[dict[str, object]]", data), False
    if isinstance(data, dict) and "agents" in data:
        inner = data["agents"]
        if isinstance(inner, list):
            return cast("list[dict[str, object]]", inner), True
    raise ValueError("registry JSON must be an array or an object with key 'agents'")


def diversify_agents(agents: list[dict[str, object]]) -> None:
    n = len(PROTOCOL_VERSIONS)
    for i, agent in enumerate(agents):
        agent["asap_version"] = PROTOCOL_VERSIONS[i % n]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print summary only; do not write files.",
    )
    args = parser.parse_args()

    registry_path = _REPO_ROOT / "registry.json"
    web_public_path = _REPO_ROOT / "apps" / "web" / "public" / "registry.json"

    if not registry_path.is_file():
        print(f"Missing {registry_path}", file=sys.stderr)
        return 1

    raw = json.loads(registry_path.read_text(encoding="utf-8"))
    agents, wrapped = _agents_payload(raw)
    diversify_agents(agents)

    out_main = registry_path
    out_web = web_public_path

    if args.dry_run:
        sample = [(a.get("id"), a.get("asap_version")) for a in agents[:8]]
        print(f"Would write {len(agents)} agents; sample: {sample}")
        return 0

    payload: dict[str, object] | list[dict[str, object]]
    if wrapped and isinstance(raw, dict):
        raw["agents"] = agents
        payload = cast("dict[str, object]", raw)
    else:
        payload = agents

    text = json.dumps(payload, indent=2, ensure_ascii=False) + "\n"
    out_main.write_text(text, encoding="utf-8")
    out_web.parent.mkdir(parents=True, exist_ok=True)
    out_web.write_text(text, encoding="utf-8")
    print(f"Wrote {len(agents)} agents to {out_main} and {out_web}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
