"""Tests for Lite Registry client (SD-11, ADR-15)."""

from __future__ import annotations

import httpx
import pytest
from pydantic import ValidationError

from asap.discovery import registry as registry_module
from asap.discovery.registry import (
    LiteRegistry,
    RegistryEntry,
    discover_from_registry,
    find_by_id,
    find_by_skill,
    generate_registry_entry,
)
from asap.models.entities import Capability, Endpoint, Manifest, Skill


VALID_REGISTRY_JSON = """{
  "version": "1.0",
  "updated_at": "2026-02-07T00:00:00Z",
  "agents": [
    {
      "id": "urn:asap:agent:alpha",
      "name": "Alpha Agent",
      "description": "First test agent",
      "endpoints": {"http": "https://alpha.example.com/asap", "manifest": "https://alpha.example.com/.well-known/asap/manifest.json"},
      "skills": ["code_review", "summarization"],
      "asap_version": "1.1.0"
    },
    {
      "id": "urn:asap:agent:beta",
      "name": "Beta Agent",
      "description": "Second test agent",
      "endpoints": {"http": "https://beta.example.com/asap"},
      "skills": ["code_review"],
      "asap_version": "1.1.0"
    }
  ]
}"""


@pytest.fixture(autouse=True)
def clear_registry_cache() -> None:
    """Clear module-level registry cache before each test for isolation."""
    registry_module._registry_cache.clear()


class TestRegistrySchemaValidation:
    """RegistryEntry and LiteRegistry validate correctly."""

    def test_valid_registry_entry_parses(self) -> None:
        """Valid RegistryEntry dict parses and serializes to JSON."""
        data = {
            "id": "urn:asap:agent:example",
            "name": "Example",
            "description": "Example agent",
            "endpoints": {"http": "https://example.com/asap"},
            "skills": ["skill_a"],
            "asap_version": "1.1.0",
        }
        entry = RegistryEntry.model_validate(data)
        assert entry.id == data["id"]
        assert entry.name == data["name"]
        assert entry.model_dump_json()

    def test_valid_lite_registry_parses(self) -> None:
        """Valid LiteRegistry JSON parses."""
        reg = LiteRegistry.model_validate_json(VALID_REGISTRY_JSON)
        assert reg.version == "1.0"
        assert len(reg.agents) == 2
        assert reg.agents[0].id == "urn:asap:agent:alpha"

    def test_invalid_registry_entry_rejects_extra_fields(self) -> None:
        """RegistryEntry with extra fields raises ValidationError (extra='forbid')."""
        data = {
            "id": "urn:asap:agent:example",
            "name": "Example",
            "description": "Example",
            "endpoints": {"http": "https://example.com/asap"},
            "skills": [],
            "asap_version": "1.1.0",
            "unknown_field": "forbidden",
        }
        with pytest.raises(ValidationError):
            RegistryEntry.model_validate(data)

    def test_invalid_registry_entry_missing_required_raises(self) -> None:
        """RegistryEntry missing required field raises ValidationError."""
        data = {
            "id": "urn:asap:agent:example",
            "name": "Example",
            "endpoints": {"http": "https://example.com/asap"},
            "skills": [],
            "asap_version": "1.1.0",
        }
        with pytest.raises(ValidationError):
            RegistryEntry.model_validate(data)


class TestDiscoverFromRegistry:
    """discover_from_registry fetches and parses from URL."""

    @pytest.mark.asyncio
    async def test_fetches_and_parses_from_mock_url(self) -> None:
        """discover_from_registry returns parsed LiteRegistry from mock URL."""

        def mock_transport(request: httpx.Request) -> httpx.Response:
            return httpx.Response(status_code=200, content=VALID_REGISTRY_JSON.encode())

        reg = await discover_from_registry(
            registry_url="https://test.example/registry.json",
            transport=httpx.MockTransport(mock_transport),
        )
        assert reg.version == "1.0"
        assert len(reg.agents) == 2
        assert reg.agents[0].name == "Alpha Agent"
        assert reg.agents[1].skills == ["code_review"]

    @pytest.mark.asyncio
    async def test_cache_used_second_call_does_not_fetch(self) -> None:
        """Second discover_from_registry for same URL returns cached result; no second HTTP call."""
        call_count = 0

        def mock_transport(request: httpx.Request) -> httpx.Response:
            nonlocal call_count
            call_count += 1
            return httpx.Response(status_code=200, content=VALID_REGISTRY_JSON.encode())

        url = "https://cache-test.example/registry.json"
        reg1 = await discover_from_registry(
            registry_url=url, transport=httpx.MockTransport(mock_transport)
        )
        reg2 = await discover_from_registry(
            registry_url=url, transport=httpx.MockTransport(mock_transport)
        )

        assert call_count == 1
        assert reg1.version == reg2.version
        assert len(reg1.agents) == len(reg2.agents)

    @pytest.mark.asyncio
    async def test_network_error_raised(self) -> None:
        """discover_from_registry raises on HTTP error (e.g. 500)."""

        def mock_transport(request: httpx.Request) -> httpx.Response:
            return httpx.Response(status_code=500, content=b"Internal Server Error")

        with pytest.raises(httpx.HTTPStatusError):
            await discover_from_registry(
                registry_url="https://fail.example/registry.json",
                transport=httpx.MockTransport(mock_transport),
            )

    @pytest.mark.asyncio
    async def test_invalid_json_raises_validation_error(self) -> None:
        """Response that is not valid LiteRegistry JSON raises ValidationError."""

        def mock_transport(request: httpx.Request) -> httpx.Response:
            return httpx.Response(status_code=200, content=b'{"not": "a valid registry"}')

        with pytest.raises(ValidationError):
            await discover_from_registry(
                registry_url="https://bad.example/registry.json",
                transport=httpx.MockTransport(mock_transport),
            )


class TestFindBySkill:
    """find_by_skill returns correct agents."""

    def test_find_by_skill_returns_matching_agents(self) -> None:
        """find_by_skill returns only agents that list the skill."""
        reg = LiteRegistry.model_validate_json(VALID_REGISTRY_JSON)
        code_review = find_by_skill(reg, "code_review")
        summarization = find_by_skill(reg, "summarization")
        missing = find_by_skill(reg, "nonexistent")

        assert len(code_review) == 2
        assert all("code_review" in e.skills for e in code_review)
        assert len(summarization) == 1
        assert summarization[0].id == "urn:asap:agent:alpha"
        assert len(missing) == 0


class TestFindById:
    """find_by_id returns entry or None."""

    def test_find_by_id_returns_entry(self) -> None:
        """find_by_id returns the matching RegistryEntry."""
        reg = LiteRegistry.model_validate_json(VALID_REGISTRY_JSON)
        entry = find_by_id(reg, "urn:asap:agent:beta")
        assert entry is not None
        assert entry.name == "Beta Agent"

    def test_find_by_id_returns_none_when_missing(self) -> None:
        """find_by_id returns None when no agent has that id."""
        reg = LiteRegistry.model_validate_json(VALID_REGISTRY_JSON)
        assert find_by_id(reg, "urn:asap:agent:nonexistent") is None


class TestGenerateRegistryEntry:
    """generate_registry_entry builds valid RegistryEntry from Manifest."""

    def test_generates_valid_entry_from_manifest(self) -> None:
        """generate_registry_entry produces valid RegistryEntry with correct fields."""
        manifest = Manifest(
            id="urn:asap:agent:my-agent",
            name="My Agent",
            version="1.0.0",
            description="Does things",
            capabilities=Capability(
                asap_version="1.1.0",
                skills=[
                    Skill(id="skill_x", description="X"),
                    Skill(id="skill_y", description="Y"),
                ],
            ),
            endpoints=Endpoint(asap="https://example.com/asap", events=None),
        )
        endpoints = {
            "http": "https://example.com/asap",
            "manifest": "https://example.com/.well-known/asap/manifest.json",
        }
        entry = generate_registry_entry(manifest, endpoints)
        assert entry.id == manifest.id
        assert entry.name == manifest.name
        assert entry.description == manifest.description
        assert entry.endpoints == endpoints
        assert entry.skills == ["skill_x", "skill_y"]
        assert entry.asap_version == "1.1.0"
        assert entry.model_dump_json()
