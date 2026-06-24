"""Pydantic models for MCP Auth Bridge compliance manifest checks."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class McpManifestSkill(BaseModel):
    """Manifest skill entry referenced by MCP-DISC-003."""

    model_config = ConfigDict(extra="ignore")

    id: str
    description: str | None = None


class McpManifestCapabilities(BaseModel):
    """Capabilities block in an MCP auth bridge manifest."""

    model_config = ConfigDict(extra="ignore")

    mcp_tools: list[str] = Field(default_factory=list)
    skills: list[McpManifestSkill] = Field(default_factory=list)


class McpAuthManifest(BaseModel):
    """Manifest document validated for MCP auth bridge alignment checks."""

    model_config = ConfigDict(extra="ignore")

    capabilities: McpManifestCapabilities
