"""Echo agent example for ASAP protocol.

This module defines a minimal echo agent with a manifest and FastAPI app.
It uses the default handler registry to echo task input as output.
"""

from __future__ import annotations

import argparse
from typing import Sequence

from fastapi import FastAPI
import uvicorn

from asap.models.entities import Capability, Endpoint, Manifest, Skill
from asap.transport.handlers import HandlerRegistry, create_echo_handler
from asap.transport.server import create_app

DEFAULT_AGENT_ID = "urn:asap:agent:echo-agent"
DEFAULT_AGENT_NAME = "Echo Agent"
DEFAULT_AGENT_VERSION = "0.3.0"
DEFAULT_AGENT_DESCRIPTION = "Echoes task input as output"
DEFAULT_ASAP_HOST = "127.0.0.1"
DEFAULT_ASAP_PORT = 8001
DEFAULT_ASAP_ENDPOINT = f"http://{DEFAULT_ASAP_HOST}:{DEFAULT_ASAP_PORT}/asap"


def build_manifest(asap_endpoint: str = DEFAULT_ASAP_ENDPOINT) -> Manifest:
    """Build the manifest for the echo agent.

    Args:
        asap_endpoint: URL where the agent receives ASAP messages.

    Returns:
        Manifest describing the echo agent's capabilities and endpoints.
    """
    return Manifest(
        id=DEFAULT_AGENT_ID,
        name=DEFAULT_AGENT_NAME,
        version=DEFAULT_AGENT_VERSION,
        description=DEFAULT_AGENT_DESCRIPTION,
        capabilities=Capability(
            asap_version="0.1",
            skills=[Skill(id="echo", description="Echo back the input")],
            state_persistence=False,
        ),
        endpoints=Endpoint(asap=asap_endpoint),
    )


def create_echo_app(asap_endpoint: str = DEFAULT_ASAP_ENDPOINT) -> FastAPI:
    """Create the FastAPI app for the echo agent.

    Args:
        asap_endpoint: URL where the agent receives ASAP messages.

    Returns:
        Configured FastAPI app.
    """
    manifest = build_manifest(asap_endpoint)
    registry = HandlerRegistry()
    registry.register("task.request", create_echo_handler())
    return create_app(manifest, registry)


app = create_echo_app()


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    """Parse command-line arguments for the echo agent.

    Args:
        argv: Optional list of CLI arguments for testing.

    Returns:
        Parsed argparse namespace.
    """
    parser = argparse.ArgumentParser(description="Run the ASAP echo agent.")
    parser.add_argument(
        "--host",
        default=DEFAULT_ASAP_HOST,
        help="Host to bind the echo agent server.",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=DEFAULT_ASAP_PORT,
        help="Port to bind the echo agent server.",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> None:
    """Run the echo agent with configurable host and port."""
    args = parse_args(argv)
    endpoint = f"http://{args.host}:{args.port}/asap"
    agent_app = create_echo_app(endpoint)
    uvicorn.run(agent_app, host=args.host, port=args.port)


if __name__ == "__main__":
    main()
