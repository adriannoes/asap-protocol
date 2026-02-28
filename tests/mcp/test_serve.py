"""Tests for asap-mcp-server (FastMCP-based serve.py).

Requires [mcp] extra: uv sync --extra mcp
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest

pytest.importorskip("mcp")

from asap.discovery.registry import LiteRegistry, RegistryEntry
from asap.mcp.serve import (
    _create_mcp_server,
    _parse_args,
    _search_registry,
    main,
)


class TestSearchRegistry:
    """Tests for _search_registry."""

    def test_empty_query_returns_all_agents(self) -> None:
        """Empty query returns all agents."""
        registry = LiteRegistry(
            version="1.0",
            updated_at=datetime.now(timezone.utc),
            agents=[
                RegistryEntry(
                    id="urn:asap:agent:a",
                    name="Agent A",
                    description="First agent",
                    endpoints={"http": "https://a.example.com"},
                    skills=["skill1"],
                    asap_version="1.0",
                ),
            ],
        )
        result = _search_registry(registry, "")
        assert len(result) == 1
        assert result[0]["id"] == "urn:asap:agent:a"

    def test_query_matches_name(self) -> None:
        """Query matches agent name (case-insensitive)."""
        registry = LiteRegistry(
            version="1.0",
            updated_at=datetime.now(timezone.utc),
            agents=[
                RegistryEntry(
                    id="urn:asap:agent:foo",
                    name="Weather Agent",
                    description="Gets weather",
                    endpoints={"http": "https://w.example.com"},
                    skills=[],
                    asap_version="1.0",
                ),
            ],
        )
        result = _search_registry(registry, "weather")
        assert len(result) == 1
        assert result[0]["name"] == "Weather Agent"

    def test_query_matches_description(self) -> None:
        """Query matches agent description."""
        registry = LiteRegistry(
            version="1.0",
            updated_at=datetime.now(timezone.utc),
            agents=[
                RegistryEntry(
                    id="urn:asap:agent:x",
                    name="X",
                    description="Code review assistant",
                    endpoints={"http": "https://x.example.com"},
                    skills=[],
                    asap_version="1.0",
                ),
            ],
        )
        result = _search_registry(registry, "code review")
        assert len(result) == 1

    def test_query_matches_skill(self) -> None:
        """Query matches skill identifier."""
        registry = LiteRegistry(
            version="1.0",
            updated_at=datetime.now(timezone.utc),
            agents=[
                RegistryEntry(
                    id="urn:asap:agent:y",
                    name="Y",
                    description="Y",
                    endpoints={"http": "https://y.example.com"},
                    skills=["web_search", "summarize"],
                    asap_version="1.0",
                ),
            ],
        )
        result = _search_registry(registry, "web_search")
        assert len(result) == 1
        assert "web_search" in result[0]["skills"]

    def test_query_no_match_returns_empty(self) -> None:
        """Query with no match returns empty list."""
        registry = LiteRegistry(
            version="1.0",
            updated_at=datetime.now(timezone.utc),
            agents=[
                RegistryEntry(
                    id="urn:asap:agent:z",
                    name="Z",
                    description="Z",
                    endpoints={"http": "https://z.example.com"},
                    skills=[],
                    asap_version="1.0",
                ),
            ],
        )
        result = _search_registry(registry, "nonexistent")
        assert result == []


class TestParseArgs:
    """Tests for _parse_args."""

    def test_default_args(self) -> None:
        """Default args use stdio transport."""
        import sys

        old_argv = sys.argv
        try:
            sys.argv = ["asap-mcp-server"]
            args = _parse_args()
            assert args.transport == "stdio"
            assert args.whitelist_urns == []
            assert args.registry_url is not None
        finally:
            sys.argv = old_argv

    def test_whitelist_urns(self) -> None:
        """--whitelist-urns parses URNs."""
        import sys

        old_argv = sys.argv
        try:
            sys.argv = [
                "asap-mcp-server",
                "--whitelist-urns",
                "urn:asap:agent:foo",
                "urn:asap:agent:bar",
            ]
            args = _parse_args()
            assert args.whitelist_urns == ["urn:asap:agent:foo", "urn:asap:agent:bar"]
        finally:
            sys.argv = old_argv

    def test_registry_url(self) -> None:
        """--registry-url overrides default."""
        import sys

        old_argv = sys.argv
        try:
            sys.argv = [
                "asap-mcp-server",
                "--registry-url",
                "https://custom.example.com/registry.json",
            ]
            args = _parse_args()
            assert args.registry_url == "https://custom.example.com/registry.json"
        finally:
            sys.argv = old_argv


class TestCreateMcpServer:
    """Tests for _create_mcp_server."""

    @pytest.mark.asyncio
    async def test_creates_server_with_tools(self) -> None:
        """Server has asap_invoke and asap_discover tools."""
        mcp = _create_mcp_server()
        tools_list = await mcp.list_tools()
        names = [t.name for t in tools_list]
        assert "asap_invoke" in names
        assert "asap_discover" in names

    @pytest.mark.asyncio
    async def test_whitelist_adds_tools(self) -> None:
        """Whitelist URNs add top-level tools."""
        mcp = _create_mcp_server(whitelist_urns=["urn:asap:agent:foo"])
        tools_list = await mcp.list_tools()
        names = [t.name for t in tools_list]
        assert "asap_invoke" in names
        assert "asap_discover" in names
        assert "asap_urn_asap_agent_foo" in names

    @pytest.mark.asyncio
    async def test_asap_discover_via_search_registry(self) -> None:
        """_search_registry produces valid JSON-serializable output."""
        registry = LiteRegistry(
            version="1.0",
            updated_at=datetime.now(timezone.utc),
            agents=[
                RegistryEntry(
                    id="urn:asap:agent:test",
                    name="Test Agent",
                    description="Test",
                    endpoints={"http": "https://test.example.com"},
                    skills=[],
                    asap_version="1.0",
                ),
            ],
        )
        matches = _search_registry(registry, "")
        result_str = json.dumps(matches)
        parsed = json.loads(result_str)
        assert isinstance(parsed, list)
        assert len(parsed) == 1
        assert parsed[0]["id"] == "urn:asap:agent:test"

    @pytest.mark.asyncio
    async def test_asap_invoke_tool_returns_error_on_resolution_failure(self) -> None:
        """asap_invoke tool returns JSON with error key when resolve fails."""
        with patch("asap.mcp.serve.MarketClient") as mock_client_class:
            mock_client = mock_client_class.return_value
            mock_client.resolve = AsyncMock(
                side_effect=ValueError("Agent not found in registry: urn:asap:agent:fake")
            )
            mcp = _create_mcp_server()
            result = await mcp.call_tool(
                "asap_invoke",
                {"urn": "urn:asap:agent:fake", "payload": {}},
            )
        content, _ = result
        assert len(content) > 0
        text = content[0].text if hasattr(content[0], "text") else str(content[0])
        parsed = json.loads(text)
        assert "error" in parsed
        assert "not found" in parsed["error"].lower() or "fake" in parsed["error"].lower()


class TestMain:
    """Tests for main entry point."""

    def test_main_calls_mcp_run(self) -> None:
        """main() creates server and calls mcp.run()."""
        with (
            patch("asap.mcp.serve._create_mcp_server") as mock_create,
            patch("asap.mcp.serve._parse_args") as mock_parse,
        ):
            mock_parse.return_value = type(
                "Args",
                (),
                {
                    "whitelist_urns": [],
                    "registry_url": "https://example.com/registry.json",
                    "auth_token": None,
                    "transport": "stdio",
                },
            )()
            mock_mcp = mock_create.return_value
            main()
            mock_create.assert_called_once()
            mock_mcp.run.assert_called_once_with(transport="stdio")
