"""MCP Auth Bridge compliance transports (stdio subprocess and mocks)."""

from __future__ import annotations

import asyncio
import json
import os
from contextlib import suppress
from dataclasses import dataclass
from typing import Any, Protocol

from asap.mcp.client import MCPClient
from asap.mcp.protocol import CallToolResult

from asap_compliance.config import COMPLIANCE_ENV_VAR, McpAuthComplianceConfig

_COMPLIANCE_JSON_PREFIX = "ASAP_COMPLIANCE_JSON:"


@dataclass
class McpAuthProbeTokens:
    """JWT probe tokens parsed from a compliance-enabled MCP server."""

    valid_jwt: str
    wrong_capability_jwt: str
    constraint_violation_action: str = "forbidden-action"


class McpAuthTransport(Protocol):
    """Black-box MCP transport for compliance checks."""

    async def connect(self) -> McpAuthProbeTokens: ...

    async def list_tool_names(self) -> list[str]: ...

    async def call_tool(
        self,
        name: str,
        arguments: dict[str, Any] | None = None,
        *,
        jwt: str | None = None,
    ) -> CallToolResult: ...

    async def disconnect(self) -> None: ...


def _parse_probe_tokens(stderr_text: str) -> McpAuthProbeTokens:
    """Parse compliance probe JWTs emitted on server stderr."""
    for line in stderr_text.splitlines():
        if line.startswith(_COMPLIANCE_JSON_PREFIX):
            payload = json.loads(line.removeprefix(_COMPLIANCE_JSON_PREFIX))
            return McpAuthProbeTokens(
                valid_jwt=str(payload["valid_jwt"]),
                wrong_capability_jwt=str(payload["wrong_capability_jwt"]),
                constraint_violation_action=str(
                    payload.get("constraint_violation_action", "forbidden-action")
                ),
            )

    raise RuntimeError(
        "MCP server stderr did not include compliance probe tokens; "
        f"set {COMPLIANCE_ENV_VAR}=1 on the server subprocess"
    )


class SubprocessMcpTransport:
    """Drive an MCP server subprocess over stdio (JSON-RPC one line per message)."""

    def __init__(self, config: McpAuthComplianceConfig) -> None:
        self._config = config
        self._client: MCPClient | None = None
        self._stderr_chunks: list[bytes] = []
        self._stderr_task: asyncio.Task[None] | None = None
        self._tokens: McpAuthProbeTokens | None = None

    def _stderr_text(self) -> str:
        return b"".join(self._stderr_chunks).decode("utf-8", errors="replace")

    def _has_compliance_probe(self) -> bool:
        return any(
            line.startswith(_COMPLIANCE_JSON_PREFIX) for line in self._stderr_text().splitlines()
        )

    async def _drain_stderr(self) -> None:
        assert self._client is not None
        stderr = self._client.stderr
        if stderr is None:
            return
        while True:
            chunk = await stderr.readline()
            if not chunk:
                break
            self._stderr_chunks.append(chunk)

    async def _await_compliance_probe(self) -> str:
        loop = asyncio.get_running_loop()
        deadline = loop.time() + self._config.timeout_seconds
        while loop.time() < deadline:
            if self._has_compliance_probe():
                return self._stderr_text()
            await asyncio.sleep(0.05)
        raise RuntimeError(
            "MCP server stderr did not include compliance probe tokens within "
            f"{self._config.timeout_seconds}s; set {COMPLIANCE_ENV_VAR}=1 on the server subprocess"
        )

    async def connect(self) -> McpAuthProbeTokens:
        env = os.environ.copy()
        if self._config.compliance_env:
            env[COMPLIANCE_ENV_VAR] = "1"
        # Stdio MCP uses stdout for JSON-RPC; suppress INFO logs that would corrupt the stream.
        env.setdefault("ASAP_LOG_LEVEL", "CRITICAL")

        self._client = MCPClient(
            list(self._config.server_command),
            receive_timeout=self._config.timeout_seconds,
            allowed_binaries=self._config.allowed_binaries,
            subprocess_env=env,
        )
        connect_task = asyncio.create_task(self._client.connect())
        while self._client.stderr is None:
            await asyncio.sleep(0.01)
            if connect_task.done():
                break
        self._stderr_task = asyncio.create_task(self._drain_stderr())
        await connect_task

        stderr_text = await self._await_compliance_probe()
        self._tokens = _parse_probe_tokens(stderr_text)
        return self._tokens

    async def list_tool_names(self) -> list[str]:
        assert self._client is not None
        tools = await self._client.list_tools()
        return [tool.name for tool in tools]

    async def call_tool(
        self,
        name: str,
        arguments: dict[str, Any] | None = None,
        *,
        jwt: str | None = None,
    ) -> CallToolResult:
        assert self._client is not None
        meta = {"asap_agent_jwt": jwt} if jwt is not None else None
        return await self._client.call_tool(name, arguments, meta=meta)

    async def disconnect(self) -> None:
        if self._stderr_task is not None:
            self._stderr_task.cancel()
            with suppress(asyncio.CancelledError):
                await self._stderr_task
            self._stderr_task = None
        if self._client is not None:
            await self._client.disconnect()
            self._client = None


class MockMcpTransport:
    """In-memory MCP transport for unit tests (predetermined responses)."""

    def __init__(
        self,
        *,
        tool_names: list[str],
        responses: dict[tuple[str, str | None], CallToolResult],
        tokens: McpAuthProbeTokens,
    ) -> None:
        self._tool_names = tool_names
        self._responses = responses
        self._tokens = tokens
        self._connected = False

    async def connect(self) -> McpAuthProbeTokens:
        self._connected = True
        return self._tokens

    async def list_tool_names(self) -> list[str]:
        if not self._connected:
            raise RuntimeError("Not connected")
        return list(self._tool_names)

    async def call_tool(
        self,
        name: str,
        arguments: dict[str, Any] | None = None,
        *,
        jwt: str | None = None,
    ) -> CallToolResult:
        if not self._connected:
            raise RuntimeError("Not connected")
        key = (name, jwt)
        if key not in self._responses:
            raise KeyError(f"No mock response for tool={name!r} jwt={jwt!r}")
        return self._responses[key]

    async def disconnect(self) -> None:
        self._connected = False
