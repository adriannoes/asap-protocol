"""Configuration for ASAP compliance harness."""

from __future__ import annotations

from pydantic import BaseModel, Field


class ComplianceConfig(BaseModel):
    agent_url: str = Field(..., description="Base URL of the agent under test")
    timeout_seconds: float = Field(default=30.0, gt=0, description="HTTP timeout in seconds")
    test_categories: list[str] = Field(
        default=["handshake", "schema", "state"],
        description="Test categories to run",
    )
    sla_skill_id: str = Field(
        default="echo",
        description="Skill ID for SLA and state validation (agent must implement this skill)",
    )
    skip_checks: list[str] = Field(
        default_factory=list,
        description="Check names to skip (e.g. 'sla' to skip SLA timeout check)",
    )
