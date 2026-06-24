"""Minimal MCP client for the MCP Auth Bridge example.

Calls ``echo`` (no JWT) and ``secure_action`` (JWT via ``_meta.asap_agent_jwt``).

Run (server prints JWT on stderr; or set ASAP_AGENT_JWT):
    uv run python examples/mcp_auth_bridge/client.py --jwt '<token>'
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
from typing import Any

from asap.mcp.client import MCPClient


async def _call_tool_with_meta(
    client: MCPClient,
    name: str,
    arguments: dict[str, Any],
    *,
    jwt: str | None = None,
) -> dict[str, Any]:
    """Invoke ``tools/call`` with optional ``_meta.asap_agent_jwt``."""
    if not client._initialized:
        raise RuntimeError("Not initialized; call connect() first")
    params: dict[str, Any] = {"name": name, "arguments": arguments}
    if jwt:
        params["_meta"] = {"asap_agent_jwt": jwt}
    req_id = client._next_id()
    await client._send(
        {
            "jsonrpc": "2.0",
            "id": req_id,
            "method": "tools/call",
            "params": params,
        }
    )
    raw = await client._receive()
    if raw is None:
        raise RuntimeError("No response to tools/call")
    if "error" in raw:
        err = raw["error"]
        return {
            "content": [{"type": "text", "text": err.get("message", str(err))}],
            "isError": True,
        }
    result = raw["result"]
    if not isinstance(result, dict):
        raise RuntimeError(f"Unexpected tools/call result: {result!r}")
    return result


def _text_content(result: dict[str, Any]) -> str:
    """Extract text from a ``CallToolResult`` dict."""
    parts: list[str] = []
    for block in result.get("content", []):
        if isinstance(block, dict) and block.get("type") == "text":
            parts.append(str(block.get("text", "")))
    return "".join(parts)


async def _run(*, jwt: str | None) -> int:
    server_command = [sys.executable, "examples/mcp_auth_bridge/server.py"]
    client = MCPClient(
        server_command,
        allowed_binaries=frozenset({os.path.basename(sys.executable)}),
    )

    async with client:
        tools = await client.list_tools()
        print("Tools:", [t.name for t in tools])

        echo = await client.call_tool("echo", {"message": "hello"})
        if echo.is_error:
            print("echo failed:", echo.content, file=sys.stderr)
            return 1
        print("echo:", _text_content(echo.model_dump()))

        secure = await _call_tool_with_meta(
            client,
            "secure_action",
            {"action": "demo"},
            jwt=jwt,
        )
        if secure.get("isError"):
            print("secure_action failed:", _text_content(secure), file=sys.stderr)
            return 1
        print("secure_action:", _text_content(secure))

    return 0


def main() -> None:
    """Parse args and exercise public vs protected MCP tools."""
    parser = argparse.ArgumentParser(description="MCP Auth Bridge example client")
    parser.add_argument(
        "--jwt",
        default=os.environ.get("ASAP_AGENT_JWT"),
        help="Agent JWT for secure_action (default: ASAP_AGENT_JWT env)",
    )
    args = parser.parse_args()
    if not args.jwt:
        print(
            "Missing JWT: pass --jwt or set ASAP_AGENT_JWT (copy demo token from server stderr).",
            file=sys.stderr,
        )
        raise SystemExit(2)
    raise SystemExit(asyncio.run(_run(jwt=args.jwt)))


if __name__ == "__main__":
    main()
