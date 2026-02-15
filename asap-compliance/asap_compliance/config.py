"""Configuration for ASAP compliance harness."""

from __future__ import annotations

from pydantic import BaseModel, Field


class ComplianceConfig(BaseModel):
    """Configuration for running compliance tests against an ASAP agent.

    Attributes:
        agent_url: Base URL of the agent under test (e.g. https://agent.example.com).
        timeout_seconds: HTTP request timeout in seconds.
        test_categories: Categories to run (handshake, schema, state, sla).
    """

    agent_url: str = Field(..., description="Base URL of the agent under test")
    timeout_seconds: float = Field(default=30.0, gt=0, description="HTTP timeout in seconds")
    test_categories: list[str] = Field(
        default=["handshake", "schema", "state"],
        description="Test categories to run",
    )
