"""Minimal MCP client for the MCP Auth Bridge example.

Calls ``echo`` (no JWT) and ``secure_action`` (JWT via ``_meta.asap_agent_jwt``).

Run from any directory (server path is resolved relative to this file):
    uv run python examples/mcp_auth_bridge/client.py --jwt '<token>'
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
from pathlib import Path
from typing import Any

from asap.mcp.client import MCPClient

_SERVER_SCRIPT = Path(__file__).resolve().parent / "server.py"


def _text_content(result: dict[str, Any]) -> str:
    """Extract text from a ``CallToolResult`` dict."""
    parts: list[str] = []
    for block in result.get("content", []):
        if isinstance(block, dict) and block.get("type") == "text":
            parts.append(str(block.get("text", "")))
    return "".join(parts)


async def _run(*, jwt: str | None) -> int:
    server_command = [sys.executable, str(_SERVER_SCRIPT)]
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

        secure = await client.call_tool(
            "secure_action",
            {"action": "demo"},
            meta={"asap_agent_jwt": jwt},
        )
        if secure.is_error:
            print("secure_action failed:", _text_content(secure.model_dump()), file=sys.stderr)
            return 1
        print("secure_action:", _text_content(secure.model_dump()))

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
