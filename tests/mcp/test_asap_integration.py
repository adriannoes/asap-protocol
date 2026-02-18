"""Integration tests for MCP server with ASAP protocol operations.

This module tests the cross-cutting integration between MCP and ASAP:
- MCP tools that invoke ASAP client operations
- MCP server exposing ASAP primitives correctly
- Error propagation from ASAP to MCP responses

These tests verify that the MCP layer correctly wraps and exposes
ASAP functionality to external tool callers.
"""

from __future__ import annotations

import asyncio
import json
from typing import TYPE_CHECKING, Any

import pytest
from fastapi import FastAPI
from httpx import ASGITransport

from asap.mcp.protocol import JSONRPCRequest
from asap.mcp.server import MCPServer
from asap.models.entities import Manifest
from asap.models.enums import TaskStatus
from asap.models.envelope import Envelope
from asap.models.payloads import TaskRequest, TaskResponse
from asap.transport.client import ASAPClient
from asap.transport.handlers import HandlerRegistry
from asap.transport.server import create_app

from tests.factories import create_test_manifest

if TYPE_CHECKING:
    pass


def _create_asap_app(manifest: Manifest) -> FastAPI:
    """Create an ASAP FastAPI app with handlers."""
    registry = HandlerRegistry()

    def echo_handler(envelope: Envelope, manifest: Manifest) -> Envelope:
        input_data = envelope.payload_dict.get("input", {})
        return Envelope(
            asap_version="0.1",
            sender=manifest.id,
            recipient=envelope.sender,
            payload_type="task.response",
            payload=TaskResponse(
                task_id="task-123",
                status=TaskStatus.COMPLETED,
                result={"echo": input_data},
            ).model_dump(),
            correlation_id=envelope.id,
        )

    registry.register("task.request", echo_handler)
    return create_app(manifest, registry)


class TestMCPToolsInvokingASAP:
    """Tests for MCP tools that invoke ASAP client operations."""

    @pytest.mark.asyncio
    async def test_mcp_tool_can_call_asap_client(self) -> None:
        """MCP tool should be able to invoke ASAP client and return result."""
        manifest = create_test_manifest()
        asap_app = _create_asap_app(manifest)
        transport = ASGITransport(app=asap_app)

        mcp_server = MCPServer(name="asap-bridge", version="1.0.0")

        async def send_message_tool(message: str) -> dict[str, Any]:
            """Tool that sends a message via ASAP client."""
            async with ASAPClient(
                "http://localhost:8000",
                require_https=False,
                transport=transport,
            ) as client:
                envelope = Envelope(
                    asap_version="0.1",
                    sender="urn:asap:agent:mcp-client",
                    recipient="urn:asap:agent:test-server",
                    payload_type="task.request",
                    payload=TaskRequest(
                        conversation_id="conv-mcp",
                        skill_id="echo",
                        input={"message": message},
                    ).model_dump(),
                )
                response = await client.send(envelope)
                return {
                    "status": "success",
                    "response_type": response.payload_type,
                    "result": response.payload_dict.get("result", {}),
                }

        mcp_server.register_tool(
            "send_asap_message",
            send_message_tool,
            {
                "type": "object",
                "properties": {"message": {"type": "string"}},
                "required": ["message"],
            },
            description="Send a message via ASAP protocol",
        )

        result = await mcp_server._handle_tools_call(
            {
                "name": "send_asap_message",
                "arguments": {"message": "Hello from MCP!"},
            }
        )

        assert result["isError"] is False
        content_text = result["content"][0]["text"]
        parsed = json.loads(content_text)
        assert parsed["status"] == "success"
        assert parsed["response_type"] == "task.response"
        assert "echo" in parsed["result"]

    @pytest.mark.asyncio
    async def test_mcp_tool_handles_asap_errors(self) -> None:
        """MCP tool should properly handle ASAP client errors."""
        manifest = create_test_manifest()
        registry = HandlerRegistry()

        def failing_handler(envelope: Envelope, manifest: Manifest) -> Envelope:
            raise RuntimeError("Intentional ASAP error")

        registry.register("task.request", failing_handler)
        asap_app = create_app(manifest, registry)
        transport = ASGITransport(app=asap_app)

        mcp_server = MCPServer(name="asap-bridge", version="1.0.0")

        async def send_message_tool(message: str) -> dict[str, Any]:
            """Tool that may fail when ASAP returns error."""
            async with ASAPClient(
                "http://localhost:8000",
                require_https=False,
                transport=transport,
            ) as client:
                envelope = Envelope(
                    asap_version="0.1",
                    sender="urn:asap:agent:mcp-client",
                    recipient="urn:asap:agent:test-server",
                    payload_type="task.request",
                    payload=TaskRequest(
                        conversation_id="conv-mcp",
                        skill_id="echo",
                        input={"message": message},
                    ).model_dump(),
                )
                await client.send(envelope)

        mcp_server.register_tool(
            "send_asap_message",
            send_message_tool,
            {
                "type": "object",
                "properties": {"message": {"type": "string"}},
                "required": ["message"],
            },
            description="Send a message via ASAP protocol",
        )

        result = await mcp_server._handle_tools_call(
            {
                "name": "send_asap_message",
                "arguments": {"message": "This will fail"},
            }
        )

        assert result["isError"] is True
        content_text = result["content"][0]["text"]
        assert "error" in content_text.lower() or "Error" in content_text


class TestMCPExposingASAPPrimitives:
    """Tests for MCP server exposing ASAP primitives as tools."""

    @pytest.fixture
    def asap_bridge_server(self) -> tuple[MCPServer, FastAPI, ASGITransport]:
        """Create MCP server with ASAP primitive tools."""
        manifest = create_test_manifest()
        asap_app = _create_asap_app(manifest)
        transport = ASGITransport(app=asap_app)

        mcp_server = MCPServer(
            name="asap-mcp-bridge",
            version="1.0.0",
            description="MCP server exposing ASAP primitives",
        )

        _transport = transport

        async def discover_agent(url: str) -> dict[str, Any]:
            """Discover agent capabilities via manifest."""
            async with ASAPClient(
                url,
                require_https=False,
                transport=_transport,
            ) as client:
                manifest = await client.discover_manifest()
                if manifest:
                    return {
                        "id": manifest.id,
                        "name": manifest.name,
                        "version": manifest.version,
                        "skills": [s.id for s in manifest.capabilities.skills],
                    }
                return {"error": "Could not discover manifest"}

        async def send_task(
            agent_url: str,
            skill_id: str,
            input_data: dict[str, Any],
        ) -> dict[str, Any]:
            """Send a task to an ASAP agent."""
            async with ASAPClient(
                agent_url,
                require_https=False,
                transport=_transport,
            ) as client:
                envelope = Envelope(
                    asap_version="0.1",
                    sender="urn:asap:agent:mcp-client",
                    recipient="urn:asap:agent:test-server",
                    payload_type="task.request",
                    payload=TaskRequest(
                        conversation_id="conv-mcp",
                        skill_id=skill_id,
                        input=input_data,
                    ).model_dump(),
                )
                response = await client.send(envelope)
                return {
                    "task_id": response.payload_dict.get("task_id"),
                    "status": response.payload_dict.get("status"),
                    "result": response.payload_dict.get("result"),
                }

        mcp_server.register_tool(
            "asap_discover",
            discover_agent,
            {
                "type": "object",
                "properties": {"url": {"type": "string"}},
                "required": ["url"],
            },
            description="Discover an ASAP agent's capabilities",
        )

        mcp_server.register_tool(
            "asap_send_task",
            send_task,
            {
                "type": "object",
                "properties": {
                    "agent_url": {"type": "string"},
                    "skill_id": {"type": "string"},
                    "input_data": {"type": "object"},
                },
                "required": ["agent_url", "skill_id", "input_data"],
            },
            description="Send a task to an ASAP agent",
        )

        return mcp_server, asap_app, transport

    @pytest.mark.asyncio
    async def test_tools_list_exposes_asap_primitives(
        self,
        asap_bridge_server: tuple[MCPServer, FastAPI, ASGITransport],
    ) -> None:
        """MCP tools/list should expose ASAP primitive operations."""
        mcp_server, _, _ = asap_bridge_server

        result = mcp_server._handle_tools_list(None)

        assert "tools" in result
        tool_names = [t["name"] for t in result["tools"]]
        assert "asap_discover" in tool_names
        assert "asap_send_task" in tool_names

    @pytest.mark.asyncio
    async def test_asap_send_task_via_mcp(
        self,
        asap_bridge_server: tuple[MCPServer, FastAPI, ASGITransport],
    ) -> None:
        """MCP asap_send_task tool should successfully invoke ASAP agent."""
        mcp_server, _, _ = asap_bridge_server

        result = await mcp_server._handle_tools_call(
            {
                "name": "asap_send_task",
                "arguments": {
                    "agent_url": "http://localhost:8000",
                    "skill_id": "echo",
                    "input_data": {"message": "test via MCP"},
                },
            }
        )

        assert result["isError"] is False
        content_text = result["content"][0]["text"]
        parsed = json.loads(content_text)
        assert parsed["status"] == TaskStatus.COMPLETED.value
        assert "result" in parsed


class TestASAPErrorPropagationToMCP:
    """Tests for error propagation from ASAP to MCP responses."""

    @pytest.mark.asyncio
    async def test_asap_connection_error_propagates_to_mcp(self) -> None:
        """ASAP connection errors should be properly reported in MCP tool result."""
        mcp_server = MCPServer(name="test", version="1.0.0")

        async def connect_to_invalid(url: str) -> dict[str, Any]:
            """Tool that tries to connect to invalid ASAP endpoint."""
            async with ASAPClient(
                url,
                require_https=False,
                timeout=1.0,
            ) as client:
                envelope = Envelope(
                    asap_version="0.1",
                    sender="urn:asap:agent:mcp-client",
                    recipient="urn:asap:agent:invalid",
                    payload_type="task.request",
                    payload=TaskRequest(
                        conversation_id="conv",
                        skill_id="test",
                        input={},
                    ).model_dump(),
                )
                await client.send(envelope)
                return {"status": "success"}

        mcp_server.register_tool(
            "connect_invalid",
            connect_to_invalid,
            {
                "type": "object",
                "properties": {"url": {"type": "string"}},
                "required": ["url"],
            },
            description="Connect to potentially invalid URL",
        )

        result = await mcp_server._handle_tools_call(
            {
                "name": "connect_invalid",
                "arguments": {"url": "http://127.0.0.1:59999"},
            }
        )

        assert result["isError"] is True
        content_text = result["content"][0]["text"]
        assert "error" in content_text.lower() or "connect" in content_text.lower()

    @pytest.mark.asyncio
    async def test_asap_validation_error_propagates_to_mcp(self) -> None:
        """ASAP validation errors should be properly reported in MCP tool result."""
        manifest = create_test_manifest()
        asap_app = _create_asap_app(manifest)
        transport = ASGITransport(app=asap_app)

        mcp_server = MCPServer(name="test", version="1.0.0")

        async def send_invalid_envelope() -> dict[str, Any]:
            """Tool that sends an invalid envelope."""
            async with ASAPClient(
                "http://localhost:8000",
                require_https=False,
                transport=transport,
            ) as client:
                envelope = Envelope(
                    asap_version="0.1",
                    sender="urn:asap:agent:mcp-client",
                    recipient="urn:asap:agent:test-server",
                    payload_type="invalid.payload.type",
                    payload={},
                )
                await client.send(envelope)
                return {"status": "success"}

        mcp_server.register_tool(
            "send_invalid",
            send_invalid_envelope,
            {"type": "object", "additionalProperties": False},
            description="Send invalid envelope",
        )

        result = await mcp_server._handle_tools_call(
            {
                "name": "send_invalid",
                "arguments": {},
            }
        )

        assert result["isError"] is True


class TestMCPDispatchWithASAPTools:
    """Tests for MCP dispatch flow with ASAP-based tools."""

    @pytest.mark.asyncio
    async def test_full_jsonrpc_flow_with_asap_tool(self) -> None:
        """Test complete JSON-RPC request/response flow for ASAP tool."""
        manifest = create_test_manifest()
        asap_app = _create_asap_app(manifest)
        transport = ASGITransport(app=asap_app)

        mcp_server = MCPServer(name="asap-bridge", version="1.0.0")

        async def echo_via_asap(message: str) -> str:
            """Echo a message through ASAP agent."""
            async with ASAPClient(
                "http://localhost:8000",
                require_https=False,
                transport=transport,
            ) as client:
                envelope = Envelope(
                    asap_version="0.1",
                    sender="urn:asap:agent:mcp-client",
                    recipient="urn:asap:agent:test-server",
                    payload_type="task.request",
                    payload=TaskRequest(
                        conversation_id="conv-mcp",
                        skill_id="echo",
                        input={"message": message},
                    ).model_dump(),
                )
                response = await client.send(envelope)
                result = response.payload_dict.get("result", {})
                return f"ASAP echoed: {result.get('echo', {}).get('message', '')}"

        mcp_server.register_tool(
            "echo_asap",
            echo_via_asap,
            {
                "type": "object",
                "properties": {"message": {"type": "string"}},
                "required": ["message"],
            },
            description="Echo via ASAP protocol",
        )

        request = JSONRPCRequest(
            id=1,
            method="tools/call",
            params={
                "name": "echo_asap",
                "arguments": {"message": "Hello ASAP!"},
            },
        )

        response_line = await mcp_server._dispatch_request(request)
        assert response_line is not None

        response_data = json.loads(response_line)
        assert "result" in response_data
        assert response_data["result"]["isError"] is False

        content = response_data["result"]["content"][0]
        assert content["type"] == "text"
        assert "ASAP echoed:" in content["text"]
        assert "Hello ASAP!" in content["text"]

    @pytest.mark.asyncio
    async def test_concurrent_asap_tool_calls(self) -> None:
        """Test that multiple concurrent MCP tool calls to ASAP work correctly."""
        manifest = create_test_manifest()
        asap_app = _create_asap_app(manifest)
        transport = ASGITransport(app=asap_app)

        mcp_server = MCPServer(name="asap-bridge", version="1.0.0")

        async def echo_via_asap(message: str, delay: float = 0) -> dict[str, Any]:
            """Echo with optional delay for concurrency testing."""
            if delay > 0:
                await asyncio.sleep(delay)

            async with ASAPClient(
                "http://localhost:8000",
                require_https=False,
                transport=transport,
            ) as client:
                envelope = Envelope(
                    asap_version="0.1",
                    sender="urn:asap:agent:mcp-client",
                    recipient="urn:asap:agent:test-server",
                    payload_type="task.request",
                    payload=TaskRequest(
                        conversation_id=f"conv-{message}",
                        skill_id="echo",
                        input={"message": message},
                    ).model_dump(),
                )
                response = await client.send(envelope)
                return {
                    "message": message,
                    "status": response.payload_dict.get("status"),
                }

        mcp_server.register_tool(
            "echo_asap",
            echo_via_asap,
            {
                "type": "object",
                "properties": {
                    "message": {"type": "string"},
                    "delay": {"type": "number"},
                },
                "required": ["message"],
            },
            description="Echo via ASAP with optional delay",
        )

        tasks = [
            mcp_server._handle_tools_call(
                {
                    "name": "echo_asap",
                    "arguments": {"message": f"concurrent-{i}", "delay": 0.01},
                }
            )
            for i in range(5)
        ]

        results = await asyncio.gather(*tasks)

        assert len(results) == 5
        for result in results:
            assert result["isError"] is False
            content = json.loads(result["content"][0]["text"])
            assert content["status"] == TaskStatus.COMPLETED.value
