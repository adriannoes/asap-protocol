"""MCP tool integration example for ASAP protocol.

This module shows how to call MCP (Model Context Protocol) tools via ASAP
envelopes: build McpToolCall and McpToolResult payloads, wrap them in
Envelopes, and send/receive using ASAPClient.

Payload types:
    - mcp_tool_call: Request to invoke an MCP tool (tool_name, arguments).
    - mcp_tool_result: Response with success/result or error.

Run:
    uv run python -m asap.examples.mcp_integration
    uv run python -m asap.examples.mcp_integration --agent-url http://127.0.0.1:8000
"""

from __future__ import annotations

import argparse
import asyncio
from typing import Any, Sequence

from asap.models.envelope import Envelope
from asap.models.ids import generate_id
from asap.models.payloads import McpToolCall, McpToolResult
from asap.observability import get_logger
from asap.transport.client import ASAPClient

logger = get_logger(__name__)

# Default agent that might expose MCP tools (e.g. echo or a custom MCP gateway)
DEFAULT_AGENT_ID = "urn:asap:agent:mcp-gateway"
DEFAULT_SENDER_ID = "urn:asap:agent:caller"
DEFAULT_AGENT_URL = "http://127.0.0.1:8000"


def build_mcp_tool_call_envelope(
    tool_name: str,
    arguments: dict[str, Any],
    recipient_id: str = DEFAULT_AGENT_ID,
    sender_id: str = DEFAULT_SENDER_ID,
    request_id: str | None = None,
    mcp_context: dict[str, Any] | None = None,
) -> Envelope:
    """Build an ASAP envelope containing an MCP tool call request.

    Args:
        tool_name: Name of the MCP tool to invoke (e.g. "web_search", "read_file").
        arguments: JSON-serializable arguments for the tool.
        recipient_id: URN of the agent that will execute the MCP tool.
        sender_id: URN of the calling agent.
        request_id: Optional request ID for correlation; generated if not provided.
        mcp_context: Optional MCP context (server URL, session, etc.).

    Returns:
        Envelope with payload_type "mcp_tool_call" and McpToolCall payload.
    """
    req_id = request_id or generate_id()
    payload = McpToolCall(
        request_id=req_id,
        tool_name=tool_name,
        arguments=arguments,
        mcp_context=mcp_context,
    )
    return Envelope(
        asap_version="0.1",
        sender=sender_id,
        recipient=recipient_id,
        payload_type="mcp_tool_call",
        payload=payload.model_dump(),
        trace_id=generate_id(),
    )


def build_mcp_tool_result_envelope(
    request_id: str,
    success: bool,
    result: dict[str, Any] | None = None,
    error: str | None = None,
    recipient_id: str = DEFAULT_SENDER_ID,
    sender_id: str = DEFAULT_AGENT_ID,
    correlation_id: str | None = None,
) -> Envelope:
    """Build an ASAP envelope containing an MCP tool result (response).

    Args:
        request_id: ID of the original McpToolCall request.
        success: Whether the tool call succeeded.
        result: Result data when success=True; must be None when success=False.
        error: Error message when success=False; must be None when success=True.
        recipient_id: URN of the agent that sent the tool call (caller).
        sender_id: URN of the agent that executed the tool (gateway).
        correlation_id: Envelope ID of the request envelope for tracking.

    Returns:
        Envelope with payload_type "mcp_tool_result" and McpToolResult payload.
    """
    payload = McpToolResult(
        request_id=request_id,
        success=success,
        result=result,
        error=error,
    )
    return Envelope(
        asap_version="0.1",
        sender=sender_id,
        recipient=recipient_id,
        payload_type="mcp_tool_result",
        payload=payload.model_dump(),
        trace_id=generate_id(),
        correlation_id=correlation_id,
    )


async def send_mcp_tool_call(
    base_url: str,
    tool_name: str,
    arguments: dict[str, Any],
    sender_id: str = DEFAULT_SENDER_ID,
    recipient_id: str = DEFAULT_AGENT_ID,
) -> Envelope:
    """Send an MCP tool call envelope to an agent and return the response envelope.

    The agent at base_url must handle "mcp_tool_call" and return an envelope
    with payload_type "mcp_tool_result". If the agent does not implement MCP,
    the request may fail with a connection or handler error.

    Args:
        base_url: Base URL of the agent (no trailing /asap).
        tool_name: MCP tool name to invoke.
        arguments: Tool arguments.
        sender_id: Sender URN.
        recipient_id: Recipient URN.

    Returns:
        Response envelope (e.g. mcp_tool_result) from the agent.
    """
    envelope = build_mcp_tool_call_envelope(
        tool_name=tool_name,
        arguments=arguments,
        recipient_id=recipient_id,
        sender_id=sender_id,
    )
    logger.info(
        "asap.mcp_integration.sending",
        tool_name=tool_name,
        envelope_id=envelope.id,
    )
    async with ASAPClient(base_url) as client:
        response = await client.send(envelope)
    logger.info(
        "asap.mcp_integration.received",
        payload_type=response.payload_type,
        response_id=response.id,
    )
    return response


def run_demo_local() -> None:
    """Demonstrate building MCP envelopes without sending (no server required).

    Builds a tool call envelope and a corresponding tool result envelope
    to show the expected shape for MCP integration.
    """
    request_id = generate_id()
    call_envelope = build_mcp_tool_call_envelope(
        tool_name="web_search",
        arguments={"query": "ASAP protocol", "max_results": 5},
        request_id=request_id,
        mcp_context={"server": "mcp://tools.example.com"},
    )
    logger.info(
        "asap.mcp_integration.tool_call_envelope",
        envelope_id=call_envelope.id,
        payload_type=call_envelope.payload_type,
        tool_name=call_envelope.payload_dict.get("tool_name"),
    )

    result_envelope = build_mcp_tool_result_envelope(
        request_id=request_id,
        success=True,
        result={"findings": ["result1", "result2"], "count": 2},
        correlation_id=call_envelope.id,
    )
    logger.info(
        "asap.mcp_integration.tool_result_envelope",
        envelope_id=result_envelope.id,
        payload_type=result_envelope.payload_type,
        success=result_envelope.payload_dict.get("success"),
    )


async def run_demo_remote(agent_url: str) -> None:
    """Send a real MCP tool call to an agent (agent must support mcp_tool_call).

    If the agent does not register a handler for mcp_tool_call, the request
    will fail; this demo is for use with an MCP-capable agent.
    """
    try:
        response = await send_mcp_tool_call(
            base_url=agent_url,
            tool_name="echo",
            arguments={"message": "hello from MCP example"},
        )
        logger.info(
            "asap.mcp_integration.remote_complete",
            payload_type=response.payload_type,
            payload=response.payload,
        )
    except Exception as e:
        logger.warning(
            "asap.mcp_integration.remote_failed",
            error=str(e),
            message="Ensure the agent supports mcp_tool_call or run without --agent-url",
        )
        raise


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    """Parse command-line arguments for the MCP integration demo."""
    parser = argparse.ArgumentParser(
        description="Call MCP tools via ASAP envelopes (build and optionally send)."
    )
    parser.add_argument(
        "--agent-url",
        default=None,
        help="Base URL of an agent that handles mcp_tool_call (optional; if omitted, only build envelopes).",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> None:
    """Build MCP envelopes and optionally send to an agent."""
    args = parse_args(argv)
    run_demo_local()
    if args.agent_url:
        asyncio.run(run_demo_remote(args.agent_url))


if __name__ == "__main__":
    main()
