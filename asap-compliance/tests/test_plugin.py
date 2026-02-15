"""Tests for the pytest plugin (fixture and marker)."""

from __future__ import annotations

import pytest

from asap_compliance.config import ComplianceConfig


@pytest.mark.asap_compliance
def test_compliance_harness_fixture(compliance_harness: ComplianceConfig) -> None:
    """Verify compliance_harness fixture returns ComplianceConfig."""
    assert isinstance(compliance_harness, ComplianceConfig)
    assert compliance_harness.agent_url
    assert compliance_harness.timeout_seconds > 0
    assert "handshake" in compliance_harness.test_categories


def test_compliance_config_defaults() -> None:
    """Verify ComplianceConfig default values."""
    from asap_compliance.config import ComplianceConfig

    config = ComplianceConfig(agent_url="https://agent.example.com")
    assert config.agent_url == "https://agent.example.com"
    assert config.timeout_seconds == 30.0
    assert config.test_categories == ["handshake", "schema", "state"]
