"""asap-mcp-server: MCP server exposing ASAP agents via FastMCP (mcp SDK).

Provides asap_invoke(urn, payload) and asap_discover(query) tools, with optional
--whitelist-urns to expose specific agents as top-level tools. Uses Stdio transport
by default (Claude Desktop, Cursor).

Usage:
    uv run asap-mcp-server
    uv run asap-mcp-server --whitelist-urns urn:asap:agent:foo urn:asap:agent:bar
    uvx asap-mcp-server  # when published to PyPI
"""

from __future__ import annotations

import argparse
import json
import os
from typing import Any

from asap.client.cache import get_registry
from asap.client.market import MarketClient
from asap.discovery.registry import DEFAULT_REGISTRY_URL, LiteRegistry

# Lazy import: mcp is optional ([mcp] extra).
try:
    from mcp.server.fastmcp import FastMCP
except ImportError as _import_error:
    _mcp_import_error = _import_error
    FastMCP = None  # type: ignore[assignment]

_SERVER_NAME = "asap-mcp-server"
_SERVER_VERSION = "1.0.0"


def _search_registry(registry: LiteRegistry, query: str) -> list[dict[str, Any]]:
    q = query.strip().lower()
    if not q:
        return [e.model_dump() for e in registry.agents]
    matches = [
        e
        for e in registry.agents
        if q in e.name.lower()
        or q in (e.description or "").lower()
        or q in e.id.lower()
        or any(q in s.lower() for s in e.skills)
    ]
    return [e.model_dump() for e in matches]


def _create_mcp_server(
    registry_url: str = DEFAULT_REGISTRY_URL,
    whitelist_urns: list[str] | None = None,
    auth_token: str | None = None,
) -> "FastMCP":
    if FastMCP is None:
        raise RuntimeError(
            "mcp package is required. Install with: uv sync --extra mcp"
        ) from _mcp_import_error

    client = MarketClient(
        registry_url=registry_url,
        auth_token=auth_token,
    )

    mcp = FastMCP(
        _SERVER_NAME,
        instructions=(
            "ASAP Protocol MCP server (v%s). Use asap_discover to search agents, "
            "then asap_invoke with the URN and payload to run them." % _SERVER_VERSION
        ),
    )

    @mcp.tool()
    async def asap_invoke(urn: str, payload: dict[str, Any]) -> str:
        try:
            agent = await client.resolve(urn)
            result = await agent.run(payload)
            return json.dumps(result)
        except Exception as e:
            return json.dumps({"error": str(e)})

    @mcp.tool()
    async def asap_discover(query: str = "") -> str:
        try:
            registry = await get_registry(registry_url)
            matches = _search_registry(registry, query)
            return json.dumps(matches)
        except Exception as e:
            return json.dumps({"error": str(e)})

    if whitelist_urns:
        for urn in whitelist_urns:
            _register_whitelist_tool(mcp, client, urn)

    return mcp


def _register_whitelist_tool(
    mcp: "FastMCP",
    client: MarketClient,
    urn: str,
) -> None:
    safe_name = urn.replace(":", "_").replace(".", "_")
    tool_name = f"asap_{safe_name}"

    @mcp.tool(name=tool_name)
    async def _whitelist_invoke(payload: dict[str, Any]) -> str:
        try:
            agent = await client.resolve(urn)
            result = await agent.run(payload)
            return json.dumps(result)
        except Exception as e:
            return json.dumps({"error": str(e)})


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="asap-mcp-server",
        description="MCP server exposing ASAP agents (asap_invoke, asap_discover).",
    )
    parser.add_argument(
        "--whitelist-urns",
        nargs="*",
        default=[],
        help="Expose these URNs as top-level tools (e.g. urn:asap:agent:foo)",
    )
    parser.add_argument(
        "--registry-url",
        default=os.environ.get("ASAP_REGISTRY_URL", DEFAULT_REGISTRY_URL),
        help="Lite Registry URL (default: ASAP_REGISTRY_URL or official registry)",
    )
    parser.add_argument(
        "--auth-token",
        default=os.environ.get("ASAP_AUTH_TOKEN"),
        help="Bearer token for agent endpoints (default: ASAP_AUTH_TOKEN)",
    )
    parser.add_argument(
        "--transport",
        choices=["stdio", "sse", "streamable-http"],
        default="stdio",
        help="MCP transport (default: stdio for Claude Desktop/Cursor)",
    )
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    whitelist = args.whitelist_urns if args.whitelist_urns else None
    mcp = _create_mcp_server(
        registry_url=args.registry_url,
        whitelist_urns=whitelist,
        auth_token=args.auth_token,
    )
    mcp.run(transport=args.transport)


if __name__ == "__main__":
    main()
