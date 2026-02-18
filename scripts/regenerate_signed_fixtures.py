#!/usr/bin/env -S uv run python
"""Regenerate verified_manifest.json and self_signed_manifest.json fixtures.

Run when Manifest model changes (e.g. new fields like sla) so signatures match
the current canonical form. Requires tests/fixtures/asap_ca/ to exist.

Usage:
    uv run python scripts/regenerate_signed_fixtures.py
"""

from __future__ import annotations

import json
from pathlib import Path

from asap.crypto.keys import generate_keypair, load_private_key_from_pem
from asap.crypto.signing import sign_manifest
from asap.crypto.trust import sign_with_ca
from asap.models.entities import Capability, Endpoint, Manifest, Skill

FIXTURES_DIR = Path(__file__).resolve().parent.parent / "tests" / "fixtures"
ASAP_CA_DIR = FIXTURES_DIR / "asap_ca"


def _fixture_manifest() -> Manifest:
    """Manifest matching the original fixture structure (fixture-agent)."""
    return Manifest(
        id="urn:asap:agent:fixture-agent",
        name="Fixture Agent",
        version="1.0.0",
        description="Test fixture agent",
        capabilities=Capability(
            asap_version="0.1",
            skills=[Skill(id="echo", description="Echo", input_schema=None, output_schema=None)],
            state_persistence=False,
            streaming=False,
            mcp_tools=[],
        ),
        endpoints=Endpoint(asap="https://example.com/asap", events=None),
        auth=None,
        signature=None,
        sla=None,
        ttl_seconds=300,
    )


def main() -> None:
    manifest = _fixture_manifest()
    ca_pem = (ASAP_CA_DIR / "ca_private.pem").read_bytes()
    ca_key = load_private_key_from_pem(ca_pem)
    agent_key, _ = generate_keypair()

    verified = sign_with_ca(manifest, agent_key, ca_key)
    verified_path = FIXTURES_DIR / "verified_manifest.json"
    verified_path.write_text(
        json.dumps(verified.model_dump(mode="json")),
        encoding="utf-8",
    )
    print(f"Wrote {verified_path}")

    self_signed = sign_manifest(manifest, agent_key)
    self_signed_dict = self_signed.model_dump(mode="json")
    self_signed_dict["signature"]["trust_level"] = "self-signed"
    self_signed_path = FIXTURES_DIR / "self_signed_manifest.json"
    self_signed_path.write_text(json.dumps(self_signed_dict), encoding="utf-8")
    print(f"Wrote {self_signed_path}")


if __name__ == "__main__":
    main()
