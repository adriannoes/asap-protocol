"""In-process tests for MCPServer.run_stdio with injected stdin/stdout."""

from __future__ import annotations

import io
import json

import pytest

from asap.mcp.server import MCPServer


class _StdinRaisesEOF(io.TextIOBase):
    """TextIO that raises EOFError on readline."""

    def readline(self, size: int = -1) -> str:
        raise EOFError()


@pytest.mark.asyncio
async def test_run_stdio_ping_request_returns_response() -> None:
    """run_stdio with a single ping request writes JSON-RPC response to stdout."""
    server = MCPServer(name="t", version="0.1.0")
    stdin = io.StringIO('{"jsonrpc":"2.0","id":1,"method":"ping"}\n')
    stdout = io.StringIO()
    await server.run_stdio(stdin=stdin, stdout=stdout)
    out = stdout.getvalue().strip()
    assert out
    data = json.loads(out)
    assert "result" in data
    assert data["result"] == {}
    assert "error" not in data


@pytest.mark.asyncio
async def test_run_stdio_notification_writes_nothing() -> None:
    """run_stdio with a notification (no id) does not write a response line."""
    server = MCPServer(name="t", version="0.1.0")
    stdin = io.StringIO('{"jsonrpc":"2.0","method":"notifications/initialized"}\n')
    stdout = io.StringIO()
    await server.run_stdio(stdin=stdin, stdout=stdout)
    assert stdout.getvalue() == ""


@pytest.mark.asyncio
async def test_run_stdio_invalid_notification_does_not_crash() -> None:
    """run_stdio with invalid notification (parse error) hits notification_error path."""
    server = MCPServer(name="t", version="0.1.0")
    stdin = io.StringIO('{"jsonrpc":"2.0","method":123}\n')
    stdout = io.StringIO()
    await server.run_stdio(stdin=stdin, stdout=stdout)
    assert stdout.getvalue() == ""


@pytest.mark.asyncio
async def test_run_stdio_blank_line_stops_producer() -> None:
    """run_stdio with blank line (read_stdin returns None) exits without error."""
    server = MCPServer(name="t", version="0.1.0")
    stdin = io.StringIO("\n")
    stdout = io.StringIO()
    await server.run_stdio(stdin=stdin, stdout=stdout)
    assert stdout.getvalue() == ""


@pytest.mark.asyncio
async def test_run_stdio_invalid_json_line_skipped() -> None:
    """run_stdio with invalid JSON line puts None in queue and exits."""
    server = MCPServer(name="t", version="0.1.0")
    stdin = io.StringIO("not json\n")
    stdout = io.StringIO()
    await server.run_stdio(stdin=stdin, stdout=stdout)
    assert stdout.getvalue() == ""


@pytest.mark.asyncio
async def test_run_stdio_json_array_line_skipped() -> None:
    """run_stdio with JSON array (non-dict) line is skipped."""
    server = MCPServer(name="t", version="0.1.0")
    stdin = io.StringIO("[1, 2, 3]\n")
    stdout = io.StringIO()
    await server.run_stdio(stdin=stdin, stdout=stdout)
    assert stdout.getvalue() == ""


@pytest.mark.asyncio
async def test_run_stdio_malformed_request_returns_internal_error() -> None:
    """run_stdio with request that has id and method but invalid shape returns -32603 and same id."""
    server = MCPServer(name="t", version="0.1.0")
    stdin = io.StringIO('{"jsonrpc":"2.0","id":1,"method":123}\n')
    stdout = io.StringIO()
    await server.run_stdio(stdin=stdin, stdout=stdout)
    out = stdout.getvalue().strip()
    assert out
    data = json.loads(out)
    assert "error" in data
    assert data["error"]["code"] == -32603
    assert data.get("id") == 1


@pytest.mark.asyncio
async def test_run_stdio_stdin_eof_exits_without_crash() -> None:
    """run_stdio when read_stdin raises EOFError exits without writing to stdout."""
    server = MCPServer(name="t", version="0.1.0")
    stdin = _StdinRaisesEOF()
    stdout = io.StringIO()
    await server.run_stdio(stdin=stdin, stdout=stdout)
    assert stdout.getvalue() == ""
