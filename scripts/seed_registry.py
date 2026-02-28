#!/usr/bin/env python3
"""Seed registry.json with 100+ mock agents for launch cold start (Task 4.5.1).

Generates agents with online_check=False so the UI skips reachability checks
and seeded agents do not appear as "Unreachable". Use for social proof and
to validate client-side load testing (Task 4.2.1).

Usage (from repo root):
  uv run python scripts/seed_registry.py [--count 120] [--registry path/to/registry.json]
"""

from __future__ import annotations

import argparse
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

# Ensure src is on path when run from repo root (e.g. in CI)
_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT / "src"))

from asap.discovery.registry import LiteRegistry, RegistryEntry  # noqa: E402
from asap.models.entities import VerificationStatus  # noqa: E402
from asap.models.enums import VerificationState  # noqa: E402

DEFAULT_COUNT = 120
SKILLS_POOL = [
    "code_review",
    "summarize",
    "translate",
    "search",
    "analyze",
    "synthesize",
    "planning",
    "qa",
    "documentation",
]
FRAMEWORKS = ["CrewAI", "LangChain", "AutoGen", "Custom", "PydanticAI"]

# New realistic name components
NAME_ADJECTIVES = [
    "Global",
    "Secure",
    "Fast",
    "Elastic",
    "Open",
    "Prime",
    "Neural",
    "Deep",
    "Fluent",
    "Quick",
]
SKILL_TO_NAME = {
    "code_review": "Reviewer",
    "summarize": "Summarist",
    "translate": "Interpreter",
    "search": "Navigator",
    "analyze": "Analyst",
    "synthesize": "Architect",
    "planning": "Strategist",
    "qa": "Validator",
    "documentation": "Scribe",
}

SKILL_TO_CATEGORY = {
    "code_review": "Coding",
    "summarize": "Productivity",
    "translate": "Other",
    "search": "Research",
    "analyze": "Data",
    "synthesize": "Data",
    "planning": "Productivity",
    "qa": "Coding",
    "documentation": "Productivity",
}

DESCRIPTION_TEMPLATES = [
    "Professional {skill} assistant for autonomous workflows.",
    "Specialized agent for high-precision {skill}.",
    "Reference {skill} node compatible with ASAP 1.1.",
    "High-performance {skill} service.",
]


def build_seed_agents(count: int) -> list[RegistryEntry]:
    entries: list[RegistryEntry] = []
    for i in range(count):
        primary_skill = SKILLS_POOL[i % len(SKILLS_POOL)]
        adj = NAME_ADJECTIVES[i % len(NAME_ADJECTIVES)]
        base_name = SKILL_TO_NAME.get(primary_skill, "Agent")

        # Make name unique but professional
        name = f"{adj} {base_name} {(i // 10) + 1 if i >= 10 else ''}".strip()
        agent_id = f"urn:asap:agent:seed:agent-{i}"

        skills = [primary_skill, SKILLS_POOL[(i + 1) % len(SKILLS_POOL)]]
        if i % 3 == 0:
            skills.append(SKILLS_POOL[(i + 2) % len(SKILLS_POOL)])

        desc_tpl = DESCRIPTION_TEMPLATES[i % len(DESCRIPTION_TEMPLATES)]
        description = desc_tpl.format(skill=primary_skill.replace("_", " "))

        category = SKILL_TO_CATEGORY.get(primary_skill, "Other")
        # Add some variety to tags
        tags = [primary_skill.replace("_", "-"), category.lower()]
        if i % 2 == 0:
            tags.append("enterprise")
        if i % 5 == 0:
            tags.append("verified")

        base_url = "https://example.com/seed"
        entry = RegistryEntry(
            id=agent_id,
            name=name,
            description=description,
            endpoints={
                "http": f"{base_url}/{i}/asap",
                "manifest": f"{base_url}/{i}/.well-known/asap/manifest.json",
            },
            skills=skills,
            category=category,
            tags=tags,
            asap_version="1.1.0",
            repository_url="https://github.com/asap-protocol/examples" if i % 4 == 0 else None,
            documentation_url=None,
            built_with=FRAMEWORKS[i % len(FRAMEWORKS)],
            verification=VerificationStatus(status=VerificationState.VERIFIED)
            if i % 5 == 0
            else None,
            online_check=False,
        )
        entries.append(entry)
    return entries


def write_registry(registry_path: Path, agents: list[RegistryEntry]) -> None:
    registry = LiteRegistry(
        version="1.0",
        updated_at=datetime.now(timezone.utc),
        agents=agents,
    )
    content = registry.model_dump_json(indent=2) + "\n"
    target = registry_path.resolve()
    target.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=target.parent, suffix=".tmp")
    try:
        with open(fd, "w") as f:
            f.write(content)
        Path(tmp).replace(target)
    except BaseException:
        Path(tmp).unlink(missing_ok=True)
        raise


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Seed registry.json with mock agents for launch cold start."
    )
    parser.add_argument(
        "--count",
        type=int,
        default=DEFAULT_COUNT,
        help=f"Number of agents to generate (default: {DEFAULT_COUNT})",
    )
    parser.add_argument(
        "--registry",
        type=Path,
        default=Path("registry.json"),
        help="Path to registry.json (default: registry.json)",
    )
    args = parser.parse_args()

    if args.count < 100:
        print("Warning: --count should be at least 100 for launch cold start.", file=sys.stderr)
    if args.count < 1:
        print("Error: --count must be positive.", file=sys.stderr)
        return 1

    agents = build_seed_agents(args.count)
    write_registry(args.registry, agents)
    print(f"Wrote {len(agents)} seed agents to {args.registry}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
