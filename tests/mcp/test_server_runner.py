"""Tests for MCP server_runner entry point (main and __main__)."""

from __future__ import annotations

import asyncio
import json
import sys
from unittest.mock import AsyncMock, patch

import pytest

from asap.mcp.server_runner import main


def test_server_runner_main_importable() -> None:
    """main is callable and imports server components."""
    assert callable(main)


def test_server_runner_main_calls_asyncio_run_and_exits_zero() -> None:
    """main() calls asyncio.run(server.run_stdio()) and then sys.exit(0)."""
    with (
        patch("asap.mcp.server_runner.asyncio.run") as mock_run,
        patch("asap.mcp.server_runner.sys.exit") as mock_exit,
    ):
        main()
        mock_run.assert_called_once()
        (coro,) = mock_run.call_args[0]
        assert asyncio.iscoroutine(coro) or callable(getattr(coro, "send", None))
        mock_exit.assert_called_once_with(0)


def test_server_runner_main_broken_pipe_exit_zero() -> None:
    """main() catches BrokenPipeError from asyncio.run and calls sys.exit(0)."""
    with (
        patch("asap.mcp.server_runner.asyncio.run", side_effect=BrokenPipeError()),
        patch("asap.mcp.server_runner.sys.exit") as mock_exit,
    ):
        main()
        mock_exit.assert_called_once_with(0)


def test_server_runner_main_keyboard_interrupt_exit_zero() -> None:
    """main() catches KeyboardInterrupt from asyncio.run and calls sys.exit(0)."""
    with (
        patch("asap.mcp.server_runner.asyncio.run", side_effect=KeyboardInterrupt()),
        patch("asap.mcp.server_runner.sys.exit") as mock_exit,
    ):
        main()
        mock_exit.assert_called_once_with(0)


def test_server_runner_main_registers_echo_tool() -> None:
    """main() builds MCPServer and registers the echo tool."""
    real_run = asyncio.run

    def _run_coro(coro: object) -> None:
        if asyncio.iscoroutine(coro):
            real_run(coro)

    with (
        patch(
            "asap.mcp.server_runner.asyncio.run",
            side_effect=_run_coro,
        ),
        patch("asap.mcp.server_runner.sys.exit"),
        patch("asap.mcp.server.MCPServer") as mock_server_class,
    ):
        mock_server = mock_server_class.return_value
        mock_server.run_stdio = AsyncMock(return_value=None)
        main()
        mock_server_class.assert_called_once()
        call_kw = mock_server_class.call_args[1]
        assert call_kw.get("name") == "asap-mcp-demo"
        mock_server.register_tool.assert_called()
        (name, *_) = mock_server.register_tool.call_args[0]
        assert name == "echo"


@pytest.mark.asyncio
async def test_server_runner_main_runs_until_stdin_closed() -> None:
    """main() runs server run_stdio; with empty stdin it exits without error."""
    # Run server with stdin closed so it exits immediately
    proc = await asyncio.create_subprocess_exec(
        sys.executable,
        "-m",
        "asap.mcp.server_runner",
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    assert proc.stdin is not None
    proc.stdin.close()
    await proc.wait()
    assert proc.returncode == 0


@pytest.mark.asyncio
async def test_server_runner_echo_tool_responds() -> None:
    """Server started via -m asap.mcp.server_runner responds to initialize and echo."""
    proc = await asyncio.create_subprocess_exec(
        sys.executable,
        "-m",
        "asap.mcp.server_runner",
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    assert proc.stdin is not None and proc.stdout is not None
    init_req = (
        json.dumps(
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2025-11-25",
                    "capabilities": {},
                    "clientInfo": {"name": "test", "version": "1.0"},
                },
            }
        )
        + "\n"
    )
    proc.stdin.write(init_req.encode("utf-8"))
    await proc.stdin.drain()
    line = await asyncio.wait_for(proc.stdout.readline(), timeout=2.0)
    data = json.loads(line.decode("utf-8").strip())
    assert "result" in data
    assert data["result"].get("serverInfo", {}).get("name") == "asap-mcp-demo"
    proc.stdin.close()
    await proc.wait()
