"""Example agent with HTTP SSE streaming (``TaskStream``) for task.request.

Runs a FastAPI app with a streaming handler registered for ``task.request``.
Chunks are emitted word-by-word with progress and a final ``TaskStream`` carrying
``TaskStatus.COMPLETED``.

Run:
    uv run python -m asap.examples.streaming_agent
"""

from __future__ import annotations

import argparse
from typing import Any, AsyncIterator, Sequence

import uvicorn
from fastapi import FastAPI

from asap.models.entities import Capability, Endpoint, Manifest, Skill
from asap.models.envelope import Envelope
from asap.models.enums import TaskStatus
from asap.models.payloads import TaskRequest, TaskStream
from asap.transport.handlers import HandlerRegistry
from asap.transport.server import create_app

DEFAULT_AGENT_ID = "urn:asap:agent:streaming-agent"
DEFAULT_ASAP_HOST = "127.0.0.1"
DEFAULT_ASAP_PORT = 8002
DEFAULT_ASAP_ENDPOINT = f"http://{DEFAULT_ASAP_HOST}:{DEFAULT_ASAP_PORT}/asap"


async def streaming_echo_handler(envelope: Envelope, manifest: Any) -> AsyncIterator[Envelope]:
    task = TaskRequest.model_validate(envelope.payload_dict)
    raw = task.input.get("message") or task.input.get("text") or "one two three"
    words = str(raw).split()
    correlation = envelope.correlation_id or envelope.id or ""
    total = len(words) or 1
    for i, word in enumerate(words):
        is_last = i == total - 1
        stream_payload = TaskStream(
            chunk=word + ("\n" if is_last else " "),
            progress=(i + 1) / total,
            final=is_last,
            status=TaskStatus.COMPLETED if is_last else TaskStatus.WORKING,
        )
        yield Envelope(
            asap_version=envelope.asap_version,
            sender=manifest.id,
            recipient=envelope.sender,
            payload_type="TaskStream",
            payload=stream_payload.model_dump(mode="json"),
            correlation_id=correlation,
            trace_id=envelope.trace_id,
        )


def build_manifest(asap_endpoint: str = DEFAULT_ASAP_ENDPOINT) -> Manifest:
    return Manifest(
        id=DEFAULT_AGENT_ID,
        name="Streaming Agent",
        version="0.1.0",
        description="Word-by-word TaskStream over /asap/stream",
        capabilities=Capability(
            asap_version="0.1",
            skills=[Skill(id="stream_echo", description="Streaming echo")],
            state_persistence=False,
        ),
        endpoints=Endpoint(asap=asap_endpoint),
    )


def create_streaming_app(asap_endpoint: str = DEFAULT_ASAP_ENDPOINT) -> FastAPI:
    manifest = build_manifest(asap_endpoint)
    registry = HandlerRegistry()
    registry.register_streaming_handler("task.request", streaming_echo_handler)
    return create_app(manifest, registry)


app = create_streaming_app()


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the ASAP streaming example agent.")
    parser.add_argument("--host", default=DEFAULT_ASAP_HOST, help="Bind host.")
    parser.add_argument("--port", type=int, default=DEFAULT_ASAP_PORT, help="Bind port.")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> None:
    args = parse_args(argv)
    endpoint = f"http://{args.host}:{args.port}/asap"
    agent_app = create_streaming_app(endpoint)
    uvicorn.run(agent_app, host=args.host, port=args.port)


if __name__ == "__main__":
    main()
