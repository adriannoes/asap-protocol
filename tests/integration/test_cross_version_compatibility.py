"""Cross-version compatibility tests for v1.2.0.

Verifies that signed manifests work with existing discovery and that
the compliance harness correctly validates agents serving signed manifests.
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from asap.crypto.keys import generate_keypair
from asap.crypto.signing import sign_manifest
from asap.discovery.validation import validate_signed_manifest_response
from asap.models.entities import Capability, Endpoint, Manifest, Skill
from scripts.process_registration import fetch_manifest


def _make_signed_manifest_dict() -> dict:
    """Build a valid signed manifest dict for discovery tests."""
    manifest = Manifest(
        id="urn:asap:agent:signed-discovery-test",
        name="Signed Discovery Agent",
        version="1.0.0",
        description="Agent for cross-version compatibility tests",
        capabilities=Capability(
            asap_version="0.1",
            skills=[Skill(id="echo", description="Echo")],
            state_persistence=False,
        ),
        endpoints=Endpoint(asap="https://example.com/asap"),
    )
    private_key, _ = generate_keypair()
    signed = sign_manifest(manifest, private_key)
    return signed.model_dump(mode="json")


class TestSignedManifestWithDiscovery:
    """Verify signed manifests work with existing discovery validation."""

    def test_validate_signed_manifest_response_accepts_signed_from_http(
        self,
    ) -> None:
        """Discovery validation accepts signed manifest dict (as from HTTP response)."""
        data = _make_signed_manifest_dict()
        result = validate_signed_manifest_response(data, verify_signature=True)
        assert result.id == "urn:asap:agent:signed-discovery-test"
        assert result.name == "Signed Discovery Agent"

    def test_validate_signed_manifest_response_accepts_plain_fallback(
        self,
    ) -> None:
        """Discovery validation accepts plain manifest (backward compatibility)."""
        data = {
            "id": "urn:asap:agent:plain",
            "name": "Plain Agent",
            "version": "1.0.0",
            "description": "Unsigned",
            "capabilities": {
                "asap_version": "0.1",
                "skills": [{"id": "echo", "description": "Echo"}],
                "state_persistence": False,
                "streaming": False,
                "mcp_tools": [],
            },
            "endpoints": {"asap": "http://localhost:8000/asap", "events": None},
            "auth": None,
            "signature": None,
            "ttl_seconds": 300,
        }
        result = validate_signed_manifest_response(data, verify_signature=False)
        assert result.id == "urn:asap:agent:plain"


class TestSignedManifestFixtureCompatibility:
    """Verify fixture signed manifests work with discovery (regression guard)."""

    FIXTURES_DIR = Path(__file__).resolve().parent.parent / "fixtures"

    def test_verified_manifest_fixture_validates_with_discovery(self) -> None:
        """Fixture verified_manifest.json validates via validate_signed_manifest_response."""
        path = self.FIXTURES_DIR / "verified_manifest.json"
        if not path.exists():
            pytest.skip("Fixture verified_manifest.json not found")
        data = json.loads(path.read_text(encoding="utf-8"))
        result = validate_signed_manifest_response(data, verify_signature=True)
        assert result.id == "urn:asap:agent:fixture-agent"

    def test_self_signed_manifest_fixture_validates_with_discovery(self) -> None:
        """Fixture self_signed_manifest.json validates via validate_signed_manifest_response."""
        path = self.FIXTURES_DIR / "self_signed_manifest.json"
        if not path.exists():
            pytest.skip("Fixture self_signed_manifest.json not found")
        data = json.loads(path.read_text(encoding="utf-8"))
        result = validate_signed_manifest_response(data, verify_signature=True)
        assert result.id == "urn:asap:agent:fixture-agent"


class TestRegistrationPathParity:
    """Registration fetchers must accept the same signed payloads as discovery validation."""

    def test_issueops_fetch_manifest_matches_discovery_validator(self) -> None:
        """IssueOps fetch_manifest unwraps the same signed fixture as discovery validation."""
        data = _make_signed_manifest_dict()
        discovery_result = validate_signed_manifest_response(data, verify_signature=True)
        mock_resp = MagicMock()
        mock_resp.json.return_value = data
        mock_resp.raise_for_status = MagicMock()
        mock_client = MagicMock()
        mock_client.__enter__.return_value.get.return_value = mock_resp
        mock_client.__exit__.return_value = None
        with patch("scripts.process_registration.httpx.Client", return_value=mock_client):
            issueops_result = fetch_manifest("https://example.com/manifest.json")
        assert issueops_result.id == discovery_result.id
        assert issueops_result.name == discovery_result.name
