"""Pytest plugin for ASAP compliance harness.

Provides:
- Fixture: compliance_harness
- Marker: @pytest.mark.asap_compliance
"""

from __future__ import annotations

import os

import pytest

from asap_compliance.config import ComplianceConfig

MARKER_NAME = "asap_compliance"
MARKER_HELP = "Marks a test as an ASAP protocol compliance test."


def pytest_addoption(parser: pytest.Parser) -> None:
    """Register command-line options for the compliance harness."""
    group = parser.getgroup("asap-compliance", description="ASAP protocol compliance options")
    group.addoption(
        "--asap-agent-url",
        action="store",
        dest="asap_agent_url",
        default=os.environ.get("ASAP_AGENT_URL", "http://localhost:8000"),
        help="Base URL of the ASAP agent under test (default: ASAP_AGENT_URL or http://localhost:8000)",
    )
    group.addoption(
        "--asap-timeout",
        action="store",
        type=float,
        dest="asap_timeout",
        default=30.0,
        help="HTTP timeout in seconds for compliance requests (default: 30.0)",
    )


def pytest_configure(config: pytest.Config) -> None:
    """Register the asap_compliance marker."""
    config.addinivalue_line("markers", f"{MARKER_NAME}: {MARKER_HELP}")


@pytest.fixture
def compliance_harness(request: pytest.FixtureRequest) -> ComplianceConfig:
    """Provide ComplianceConfig for compliance tests.

    Reads agent URL and timeout from pytest options (--asap-agent-url, --asap-timeout)
    or environment variable ASAP_AGENT_URL.
    """
    config = request.config
    agent_url = config.getoption("asap_agent_url", default="http://localhost:8000")
    timeout = config.getoption("asap_timeout", default=30.0)
    return ComplianceConfig(
        agent_url=agent_url,
        timeout_seconds=timeout,
        test_categories=["handshake", "schema", "state"],
    )
