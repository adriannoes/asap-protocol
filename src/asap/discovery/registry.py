"""Lite Registry client for discovering agents from static registry.json (SD-11, ADR-15).

The Lite Registry is a static JSON file (e.g. on GitHub Pages). This module provides
typed Pydantic models for the registry schema and helpers to fetch, parse, and filter
listed agents.
"""

from __future__ import annotations

import asyncio
import threading
import time
from datetime import datetime
from typing import Any

import httpx
from pydantic import Field, field_validator

from asap.models.base import ASAPBaseModel
from asap.models.entities import Manifest, VerificationStatus
from asap.models.validators import validate_agent_urn
from asap.models.types import AgentURN

# Default URL for the official Lite Registry (GitHub Pages).
DEFAULT_REGISTRY_URL: str = "https://asap-protocol.github.io/registry/registry.json"
# Default cache TTL in seconds (15 minutes).
DEFAULT_REGISTRY_TTL_SECONDS: int = 900

# Module-level cache: registry_url -> (expiry_monotonic, LiteRegistry).
_registry_cache: dict[str, tuple[float, "LiteRegistry"]] = {}
_registry_locks: dict[str, asyncio.Lock] = {}
_registry_locks_guard = threading.Lock()


class RegistryEntry(ASAPBaseModel):
    """Single agent entry in the Lite Registry.

    Represents an agent listed in registry.json with multi-endpoint support
    (HTTP, WebSocket, manifest URL) per ADR-15.

    Attributes:
        id: Unique agent identifier (URN format).
        name: Human-readable agent name.
        description: What the agent does.
        endpoints: Map of endpoint type to URL (e.g. "http", "ws", "manifest").
        skills: List of skill identifiers the agent supports.
        asap_version: ASAP protocol version (e.g. "1.1.0").
    """

    id: AgentURN = Field(..., description="Unique agent identifier (URN format)")
    name: str = Field(..., description="Human-readable agent name")
    description: str = Field(..., description="What the agent does")
    endpoints: dict[str, str] = Field(
        ...,
        description="Map of endpoint type to URL (e.g. http, ws, manifest)",
    )
    skills: list[str] = Field(
        default_factory=list,
        description="Skill identifiers the agent supports",
    )
    asap_version: str = Field(..., description="ASAP protocol version (e.g. 1.1.0)")
    repository_url: str | None = Field(
        default=None,
        description="Optional link to source code (e.g. GitHub)",
    )
    documentation_url: str | None = Field(
        default=None,
        description="Optional link to usage documentation",
    )
    built_with: str | None = Field(
        default=None,
        description="Optional framework used to build the agent (e.g. CrewAI, LangChain)",
    )
    verification: VerificationStatus | None = Field(
        default=None,
        description="Verification status for marketplace trust badge (Task 3.6)",
    )

    @field_validator("id")
    @classmethod
    def validate_urn_format(cls, v: str) -> str:
        """Validate agent ID URN format."""
        return validate_agent_urn(v)


class LiteRegistry(ASAPBaseModel):
    """Root schema for the static Lite Registry (registry.json).

    Contains metadata and the list of registered agents. Used by
    discover_from_registry() to fetch and parse the registry.

    Attributes:
        version: Schema version of the registry (e.g. "1.0").
        updated_at: ISO datetime when the registry was last updated.
        agents: List of registry entries.
    """

    version: str = Field(..., description="Registry schema version (e.g. 1.0)")
    updated_at: datetime = Field(
        ...,
        description="When the registry was last updated (ISO 8601)",
    )
    agents: list[RegistryEntry] = Field(
        default_factory=list,
        description="List of registered agents",
    )


async def discover_from_registry(
    registry_url: str = DEFAULT_REGISTRY_URL,
    ttl_seconds: int = DEFAULT_REGISTRY_TTL_SECONDS,
    transport: httpx.AsyncBaseTransport | None = None,
) -> LiteRegistry:
    """Fetch and parse the Lite Registry from a URL, with optional caching.

    Fetches registry.json from the given URL, validates it against the
    LiteRegistry schema, and returns a typed model. Results are cached
    per URL for ttl_seconds (default 15 minutes).

    Args:
        registry_url: URL to registry.json (default: official GitHub Pages URL).
        ttl_seconds: How long to cache the result in seconds (default: 900).
        transport: Optional httpx transport for tests (e.g. MockTransport).

    Returns:
        Parsed LiteRegistry with agents list.

    Raises:
        httpx.HTTPError: On network or protocol errors.
        pydantic.ValidationError: If the response does not match LiteRegistry schema.
    """
    with _registry_locks_guard:
        if registry_url not in _registry_locks:
            _registry_locks[registry_url] = asyncio.Lock()
        url_lock = _registry_locks[registry_url]
    async with url_lock:
        now = time.monotonic()
        cached = _registry_cache.get(registry_url)
        if cached is not None:
            expiry, registry = cached
            if now < expiry:
                return registry
            _registry_cache.pop(registry_url, None)

        client_kwargs: dict[str, Any] = {"timeout": httpx.Timeout(30.0)}
        if transport is not None:
            client_kwargs["transport"] = transport

        async with httpx.AsyncClient(**client_kwargs) as client:
            response = await client.get(registry_url)
            response.raise_for_status()
            registry = LiteRegistry.model_validate_json(response.text)

        _registry_cache[registry_url] = (now + ttl_seconds, registry)
        return registry


def reset_registry_cache() -> None:
    """Clear the module-level registry cache and coalescing locks (for test isolation)."""
    with _registry_locks_guard:
        _registry_cache.clear()
        _registry_locks.clear()


def find_by_skill(registry: LiteRegistry, skill: str) -> list[RegistryEntry]:
    """Return agents that support the given skill.

    Args:
        registry: Parsed LiteRegistry from discover_from_registry().
        skill: Skill identifier to filter by (e.g. "code_review").

    Returns:
        List of RegistryEntry whose skills list contains skill (case-sensitive).
    """
    return [e for e in registry.agents if skill in e.skills]


def find_by_id(registry: LiteRegistry, agent_id: str) -> RegistryEntry | None:
    """Return the registry entry for the given agent ID, or None if not found.

    Args:
        registry: Parsed LiteRegistry from discover_from_registry().
        agent_id: Agent URN (e.g. "urn:asap:agent:example").

    Returns:
        The matching RegistryEntry, or None if no agent has that id.
    """
    for e in registry.agents:
        if e.id == agent_id:
            return e
    return None


def generate_registry_entry(
    manifest: Manifest,
    endpoints: dict[str, str],
    *,
    repository_url: str | None = None,
    documentation_url: str | None = None,
    built_with: str | None = None,
) -> RegistryEntry:
    """Build a RegistryEntry from an existing Manifest and endpoint map.

    Use this to create a PR-ready registry entry from an agent's manifest and
    its public URLs (http, ws, manifest). The result is validated against the
    Lite Registry schema.

    Args:
        manifest: Agent manifest (from well-known or in-memory).
        endpoints: Map of endpoint type to URL (e.g. "http", "ws", "manifest").

    Returns:
        Valid RegistryEntry suitable for inclusion in registry.json.

    Raises:
        pydantic.ValidationError: If the generated entry fails schema validation.
    """
    skills = [s.id for s in manifest.capabilities.skills]
    return RegistryEntry(
        id=manifest.id,
        name=manifest.name,
        description=manifest.description,
        endpoints=endpoints,
        skills=skills,
        asap_version=manifest.capabilities.asap_version,
        repository_url=repository_url or None,
        documentation_url=documentation_url or None,
        built_with=(built_with.strip() or None) if built_with else None,
    )
