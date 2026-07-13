"""ASAP-side smoke for NeMo Agent Toolkit Path A (no nvidia-nat required).

Validates protect_server + env JWT fallback in-process, then optionally exercises
stdio via the mcp_auth_bridge-style client patterns.

Exit codes:
    0 — all checks passed
    1 — assertion / auth failure
    2 — usage / import error

Run from repo root::

    uv run python examples/nemo_agent_toolkit_asap/smoke_asap_side.py
"""

from __future__ import annotations

import argparse
import asyncio
import importlib.util
import os
import sys
from pathlib import Path
from types import ModuleType
from typing import Any

from asap.mcp.auth.errors import AUTH_REQUIRED
from asap.mcp.client import MCPClient

_EXAMPLE_DIR = Path(__file__).resolve().parent
_REPO_ROOT = _EXAMPLE_DIR.parents[1]
_SERVER_SCRIPT = _EXAMPLE_DIR / "asap_mcp_server.py"


def _load_asap_mcp_server() -> ModuleType:
    """Import ``asap_mcp_server`` from this example directory."""
    spec = importlib.util.spec_from_file_location(
        "nemo_asap_mcp_server_smoke",
        _SERVER_SCRIPT,
    )
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load {_SERVER_SCRIPT}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _text_from_call_result(result: dict[str, Any]) -> str:
    """Extract concatenated text blocks from an MCP CallToolResult dict."""
    parts: list[str] = []
    for block in result.get("content", []):
        if isinstance(block, dict) and block.get("type") == "text":
            parts.append(str(block.get("text", "")))
    return "".join(parts)


async def run_inprocess_smoke() -> None:
    """Prove public echo, auth_required without JWT, and env JWT happy path.

    Example:
        await run_inprocess_smoke()
    """
    module = _load_asap_mcp_server()

    # Negative: no env JWT, no _meta → asap:auth_required
    os.environ.pop("ASAP_AGENT_JWT", None)
    server_neg, _identity_neg = await module.build_and_prepare_server(
        inject_env_jwt=False,
    )
    denied = await server_neg._handle_tools_call(
        {"name": "secure_action", "arguments": {"action": "denied"}},
    )
    if denied.get("isError") is not True:
        raise AssertionError(
            f"expected secure_action without JWT to error, got {denied!r}",
        )
    denied_text = _text_from_call_result(denied)
    if AUTH_REQUIRED not in denied_text:
        raise AssertionError(
            f"expected {AUTH_REQUIRED!r} in error text, got {denied_text!r}",
        )
    print("OK: secure_action without JWT → asap:auth_required")

    # Happy: inject env JWT (NAT Path A carriage)
    server, identity = await module.build_and_prepare_server(inject_env_jwt=True)
    echo = await server._handle_tools_call(
        {"name": "echo", "arguments": {"message": "nat-path-a"}},
    )
    if echo.get("isError") is True:
        raise AssertionError(f"echo failed: {echo!r}")
    echo_text = _text_from_call_result(echo)
    if "nat-path-a" not in echo_text:
        raise AssertionError(f"echo missing payload, got {echo_text!r}")
    print("OK: echo (public) succeeded")

    secure = await server._handle_tools_call(
        {"name": "secure_action", "arguments": {"action": "path-a"}},
    )
    if secure.get("isError") is True:
        raise AssertionError(
            f"secure_action with env JWT failed: {_text_from_call_result(secure)!r}",
        )
    secure_text = _text_from_call_result(secure)
    if "executed: path-a" not in secure_text:
        raise AssertionError(f"secure_action unexpected result: {secure_text!r}")
    print("OK: secure_action with ASAP_AGENT_JWT env fallback succeeded")
    print(f"OK: demo agent_id={identity.agent_session.agent_id}")


async def run_stdio_client_smoke() -> None:
    """Subprocess stdio smoke: spawn asap_mcp_server and call tools via MCPClient.

    Example:
        await run_stdio_client_smoke()
    """
    server_command = [sys.executable, str(_SERVER_SCRIPT)]
    client = MCPClient(
        server_command,
        allowed_binaries=frozenset({os.path.basename(sys.executable)}),
    )
    async with client:
        tools = await client.list_tools()
        names = [t.name for t in tools]
        if "echo" not in names or "secure_action" not in names:
            raise AssertionError(f"expected echo+secure_action tools, got {names!r}")
        print(f"OK: stdio tools/list → {names}")

        # Server injects ASAP_AGENT_JWT; call without _meta (NAT behavior)
        echo = await client.call_tool("echo", {"message": "stdio-smoke"})
        if echo.is_error:
            raise AssertionError(f"stdio echo failed: {echo.content!r}")
        print("OK: stdio echo")

        secure = await client.call_tool("secure_action", {"action": "stdio-smoke"})
        if secure.is_error:
            raise AssertionError(
                f"stdio secure_action without _meta failed "
                f"(env JWT should be injected by server): {secure.content!r}",
            )
        print("OK: stdio secure_action via server-injected ASAP_AGENT_JWT")


def main() -> None:
    """Run ASAP-side smoke checks (in-process always; stdio optional)."""
    parser = argparse.ArgumentParser(
        description="ASAP-side smoke for nemo_agent_toolkit_asap Path A",
    )
    parser.add_argument(
        "--stdio",
        action="store_true",
        help="Also spawn asap_mcp_server over stdio and call tools via MCPClient",
    )
    args = parser.parse_args()
    os.chdir(_REPO_ROOT)

    async def _all() -> None:
        await run_inprocess_smoke()
        if args.stdio:
            await run_stdio_client_smoke()

    try:
        asyncio.run(_all())
    except Exception as exc:  # noqa: BLE001 — CLI smoke reports any failure
        print(f"FAIL: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
    print("ASAP-side Path A smoke passed.")


if __name__ == "__main__":
    main()
