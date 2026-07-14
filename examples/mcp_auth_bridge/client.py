"""Minimal MCP client for the MCP Auth Bridge example.

Spawns ``server.py`` as a stdio child, reads the demo Agent JWT from that
child's stderr, then calls ``echo`` (public) and ``secure_action`` (JWT via
``_meta.asap_agent_jwt``).

Keys are minted in the child process — a JWT pasted from another terminal
will fail signature checks. Prefer the default self-contained path.

``ASAP_AGENT_JWT`` in the shell is **not** read automatically (stale exports
would skip stderr capture). Pass ``--jwt`` only for an explicit override.

Run from any directory (server path is resolved relative to this file)::

    uv run python examples/mcp_auth_bridge/client.py
"""

from __future__ import annotations

import argparse
import asyncio
import os
import re
import sys
from contextlib import suppress
from pathlib import Path
from typing import Any

from asap.mcp.client import MCPClient

_SERVER_SCRIPT = Path(__file__).resolve().parent / "server.py"
_JWT_MARKER = "Minted demo Agent JWT"
_STDERR_POLL_INTERVAL_S = 0.05
_DEFAULT_JWT_WAIT_S = 30.0
# Compact JWTs start with base64url header ``eyJ`` — redact before logging.
_JWT_LINE_RE = re.compile(r"^eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+$")


def _text_content(result: dict[str, Any]) -> str:
    """Extract text from a ``CallToolResult`` dict."""
    parts: list[str] = []
    for block in result.get("content", []):
        if isinstance(block, dict) and block.get("type") == "text":
            parts.append(str(block.get("text", "")))
    return "".join(parts)


def _looks_like_jwt(token: str) -> bool:
    """Return True when ``token`` has a compact JWT shape (three base64url parts)."""
    return token.count(".") == 2 and token.startswith("eyJ")


def redact_jwt_from_text(text: str) -> str:
    """Replace compact JWT lines/tokens in ``text`` so logs never leak demo JWTs.

    Example::

        safe = redact_jwt_from_text(child_stderr)
    """
    redacted_lines: list[str] = []
    for line in text.splitlines():
        stripped = line.strip()
        if _looks_like_jwt(stripped) or _JWT_LINE_RE.match(stripped):
            redacted_lines.append("[REDACTED_JWT]")
        else:
            redacted_lines.append(line)
    joined = "\n".join(redacted_lines)
    # Also scrub inline compact JWTs that share a line with other text.
    return re.sub(
        r"eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+",
        "[REDACTED_JWT]",
        joined,
    )


def parse_demo_jwt_from_stderr(stderr_text: str) -> str:
    """Extract the minted demo Agent JWT from the example server stderr banner.

    Only lines **after** the mint marker are considered (no global ``eyJ`` scan).

    Example::

        jwt = parse_demo_jwt_from_stderr(captured_stderr)
    """
    lines = stderr_text.splitlines()
    for index, line in enumerate(lines):
        if _JWT_MARKER not in line:
            continue
        for candidate in lines[index + 1 :]:
            stripped = candidate.strip()
            if _looks_like_jwt(stripped):
                return stripped

    preview = redact_jwt_from_text(stderr_text[:500])
    raise RuntimeError(
        "MCP Auth Bridge server stderr did not include a demo Agent JWT "
        f"(expected a compact JWT on a line after {_JWT_MARKER!r}). "
        f"stderr preview: {preview!r}"
    )


async def _drain_stderr(
    client: MCPClient,
    chunks: list[bytes],
) -> None:
    """Append child stderr lines until the stream closes."""
    stderr = client.stderr
    if stderr is None:
        return
    while True:
        chunk = await stderr.readline()
        if not chunk:
            break
        chunks.append(chunk)


def _stderr_text(chunks: list[bytes]) -> str:
    """Decode accumulated stderr chunks as UTF-8 text."""
    return b"".join(chunks).decode("utf-8", errors="replace")


async def _await_demo_jwt(chunks: list[bytes], *, timeout_seconds: float) -> str:
    """Poll drained stderr until the demo JWT appears or ``timeout_seconds`` elapses."""
    loop = asyncio.get_running_loop()
    deadline = loop.time() + timeout_seconds
    while loop.time() < deadline:
        try:
            return parse_demo_jwt_from_stderr(_stderr_text(chunks))
        except RuntimeError:
            await asyncio.sleep(_STDERR_POLL_INTERVAL_S)
    preview = redact_jwt_from_text(_stderr_text(chunks)[:500])
    raise RuntimeError(
        "Timed out waiting for demo Agent JWT on MCP server stderr within "
        f"{timeout_seconds}s; stderr preview: {preview!r}"
    )


async def _connect_and_resolve_jwt(
    client: MCPClient,
    *,
    jwt_override: str | None,
    jwt_wait_seconds: float,
) -> tuple[str, asyncio.Task[None]]:
    """Connect, drain stderr, and resolve the Agent JWT for ``secure_action``.

    Provenance (v2.5.3 Phase 1.2 / PR #291 review): auto-capture from the child
    this client spawned — cross-process paste fails ``bad_signature``. Stale
    ``ASAP_AGENT_JWT`` exports are ignored unless ``--jwt`` is passed.
    """
    stderr_chunks: list[bytes] = []
    connect_task = asyncio.create_task(client.connect())
    while client.stderr is None:
        await asyncio.sleep(0.01)
        if connect_task.done():
            break

    drain_task = asyncio.create_task(_drain_stderr(client, stderr_chunks))
    await connect_task

    if jwt_override:
        return jwt_override, drain_task
    jwt = await _await_demo_jwt(stderr_chunks, timeout_seconds=jwt_wait_seconds)
    return jwt, drain_task


async def _run(*, jwt_override: str | None, jwt_wait_seconds: float) -> int:
    """Spawn the example server, resolve JWT, exercise public and protected tools."""
    server_command = [sys.executable, str(_SERVER_SCRIPT)]
    env = os.environ.copy()
    # Prefer server-side stderr routing; keep CRITICAL as a belt-and-suspenders default.
    env.setdefault("ASAP_LOG_LEVEL", "CRITICAL")

    client = MCPClient(
        server_command,
        allowed_binaries=frozenset({os.path.basename(sys.executable)}),
        subprocess_env=env,
    )
    drain_task: asyncio.Task[None] | None = None

    try:
        jwt, drain_task = await _connect_and_resolve_jwt(
            client,
            jwt_override=jwt_override,
            jwt_wait_seconds=jwt_wait_seconds,
        )
        if jwt_override is None:
            print("Using demo Agent JWT captured from child server stderr.")

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
    finally:
        if drain_task is not None:
            drain_task.cancel()
            with suppress(asyncio.CancelledError):
                await drain_task
        await client.disconnect()

    return 0


def main() -> None:
    """Parse args and exercise public vs protected MCP tools.

    Example::

        uv run python examples/mcp_auth_bridge/client.py
    """
    parser = argparse.ArgumentParser(
        description=(
            "MCP Auth Bridge example client (spawns server.py and captures "
            "demo JWT from child stderr by default)"
        ),
    )
    parser.add_argument(
        "--jwt",
        default=None,
        help=(
            "Optional Agent JWT override for secure_action _meta "
            "(must be minted by this client's child server). "
            "Default: capture from child stderr. Does not read ASAP_AGENT_JWT."
        ),
    )
    parser.add_argument(
        "--jwt-wait-seconds",
        type=float,
        default=_DEFAULT_JWT_WAIT_S,
        help=f"Seconds to wait for demo JWT on child stderr (default: {_DEFAULT_JWT_WAIT_S})",
    )
    args = parser.parse_args()
    raise SystemExit(
        asyncio.run(
            _run(
                jwt_override=args.jwt,
                jwt_wait_seconds=args.jwt_wait_seconds,
            )
        )
    )


if __name__ == "__main__":
    main()
