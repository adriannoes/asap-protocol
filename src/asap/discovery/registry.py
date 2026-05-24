"""Lite Registry client for discovering agents from static registry.json (SD-11, ADR-15).

The Lite Registry is a static JSON file (e.g. on GitHub Pages). This module provides
typed Pydantic models for the registry schema and helpers to fetch, parse, and filter
listed agents.
"""

from __future__ import annotations

import asyncio
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

# Canonical category values (aligned with GitHub register_agent.yml). Used to normalize on parse.
REGISTRY_CATEGORIES: tuple[str, ...] = (
    "Research",
    "Coding",
    "Productivity",
    "Data",
    "Security",
    "Infrastructure",
    "Creative",
    "Finance",
    "Other",
)

# Module-level cache: registry_url -> (expiry_monotonic, LiteRegistry).
_registry_cache: dict[str, tuple[float, "LiteRegistry"]] = {}
_registry_locks: dict[str, asyncio.Lock] = {}


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
        hardware_class: Optional hardware class mirrored from manifest (v2.4+).
        inference_modes: Inference modes mirrored from manifest (v2.4+).
        hardware_io: Physical I/O types mirrored from manifest (v2.4+).
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
    category: str | None = Field(
        default=None,
        description="Category of the agent (e.g. Coding, Research)",
    )
    tags: list[str] = Field(
        default_factory=list,
        description="Tags for better discovery",
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
        description="Verification status for marketplace trust badge",
    )
    online_check: bool | None = Field(
        default=None,
        description="If False, UI skips reachability check (e.g. seeded/demo agents).",
    )
    hardware_class: str | None = Field(
        default=None,
        description="Hardware class derived from manifest capabilities.hardware.class",
    )
    inference_modes: list[str] = Field(
        default_factory=list,
        description="Inference modes derived from manifest capabilities.inference.modes",
    )
    hardware_io: list[str] = Field(
        default_factory=list,
        description="Physical I/O types derived from manifest capabilities.hardware.io",
    )

    @field_validator("id")
    @classmethod
    def validate_urn_format(cls, v: str) -> str:
        """Validate agent ID URN format."""
        return validate_agent_urn(v)

    @field_validator("category")
    @classmethod
    def normalize_category(cls, v: str | None) -> str | None:
        """Normalize category to canonical form (e.g. 'coding' -> 'Coding') for consistency."""
        if not v or not v.strip():
            return None
        v = v.strip()
        for canonical in REGISTRY_CATEGORIES:
            if v.lower() == canonical.lower():
                return canonical
        return v


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
    url_lock = _registry_locks.setdefault(registry_url, asyncio.Lock())
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
    """Clear the module-level registry cache and coalescing locks (TEST ONLY — not safe to call concurrently)."""
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


def find_by_hardware_class(registry: LiteRegistry, cls: str) -> list[RegistryEntry]:
    """Return agents with the given hardware class.

    Args:
        registry: Parsed LiteRegistry from discover_from_registry().
        cls: Hardware class identifier (e.g. "edge_accelerator").

    Returns:
        List of RegistryEntry whose hardware_class equals cls (case-sensitive).
    """
    return [e for e in registry.agents if e.hardware_class == cls]


def find_by_inference_mode(registry: LiteRegistry, mode: str) -> list[RegistryEntry]:
    """Return agents that support the given inference mode.

    Args:
        registry: Parsed LiteRegistry from discover_from_registry().
        mode: Inference mode identifier (e.g. "local_cuda").

    Returns:
        List of RegistryEntry whose inference_modes list contains mode (case-sensitive).
    """
    return [e for e in registry.agents if mode in e.inference_modes]


def find_by_io(registry: LiteRegistry, io_type: str) -> list[RegistryEntry]:
    """Return agents that expose the given hardware I/O type.

    Args:
        registry: Parsed LiteRegistry from discover_from_registry().
        io_type: I/O type identifier (e.g. "gpio").

    Returns:
        List of RegistryEntry whose hardware_io list contains io_type (case-sensitive).
    """
    return [e for e in registry.agents if io_type in e.hardware_io]


def derive_registry_hardware_fields(manifest: Manifest) -> dict[str, Any]:
    """Build RegistryEntry kwargs from manifest hardware and inference capabilities.

    Mirrors optional ``capabilities.hardware`` and ``capabilities.inference`` into
    ``hardware_class``, ``inference_modes``, and ``hardware_io`` for Lite Registry
    discovery filters (v2.4+).

    Args:
        manifest: Validated agent manifest (may omit hardware/inference).

    Returns:
        Dict suitable for ``RegistryEntry(**kwargs)`` or ``model_copy(update=...)``.
        Omitted keys when the manifest has no structured hardware/inference data.
    """
    caps = manifest.capabilities
    derived: dict[str, Any] = {}
    hardware = caps.hardware
    if hardware is not None:
        if hardware.class_ is not None:
            derived["hardware_class"] = hardware.class_.value
        if hardware.io:
            derived["hardware_io"] = [io.value for io in hardware.io]
    inference = caps.inference
    if inference is not None and inference.modes:
        derived["inference_modes"] = [mode.value for mode in inference.modes]
    return derived


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
    category: str | None = None,
    tags: list[str] | None = None,
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
    derived_hardware = derive_registry_hardware_fields(manifest)
    return RegistryEntry(
        id=manifest.id,
        name=manifest.name,
        description=manifest.description,
        endpoints=endpoints,
        skills=skills,
        category=category,
        tags=tags or [],
        asap_version=manifest.capabilities.asap_version,
        repository_url=(repository_url.strip() or None) if repository_url else None,
        documentation_url=(documentation_url.strip() or None) if documentation_url else None,
        built_with=(built_with.strip() or None) if built_with else None,
        **derived_hardware,
    )
