"""End-to-end streaming: server streaming handler and ``ASAPClient.stream``."""

from __future__ import annotations

from typing import Any, AsyncIterator

import httpx
import pytest

from asap.models.entities import Manifest
from asap.models.envelope import Envelope
from asap.models.enums import TaskStatus
from asap.models.payloads import TaskRequest, TaskStream
from asap.transport.client import ASAPClient
from asap.transport.handlers import HandlerRegistry
from asap.transport.rate_limit import ASAPRateLimiter
from asap.transport.server import create_app


async def _streaming_echo(envelope: Envelope, manifest: Any) -> AsyncIterator[Envelope]:
    req = TaskRequest.model_validate(envelope.payload_dict)
    words = str(req.input.get("text", "hi")).split() or ["x"]
    cid = envelope.correlation_id or envelope.id or "e2e"
    n = len(words)
    for i, w in enumerate(words):
        final = i == n - 1
        pl = TaskStream(
            chunk=w,
            progress=(i + 1) / n,
            final=final,
            status=TaskStatus.COMPLETED if final else TaskStatus.WORKING,
        )
        yield Envelope(
            asap_version=envelope.asap_version,
            sender=manifest.id,
            recipient=envelope.sender,
            payload_type="TaskStream",
            payload=pl.model_dump(mode="json"),
            correlation_id=cid,
            trace_id=envelope.trace_id,
        )


@pytest.mark.asyncio()
async def test_streaming_pipeline_client_consumes_sse(
    sample_manifest: Manifest,
    isolated_rate_limiter: ASAPRateLimiter | None,
) -> None:
    registry = HandlerRegistry()
    registry.register_streaming_handler("task.request", _streaming_echo)
    app = create_app(sample_manifest, registry, rate_limit="999999/minute")
    if isolated_rate_limiter is not None:
        app.state.limiter = isolated_rate_limiter

    tr = TaskRequest(
        conversation_id="e2e-conv",
        skill_id="stream",
        input={"text": "hello world"},
    )
    env = Envelope(
        asap_version="0.1",
        sender="urn:asap:agent:e2e-client",
        recipient=sample_manifest.id,
        payload_type="task.request",
        payload=tr.model_dump(),
    )
    transport = httpx.ASGITransport(app=app)
    async with ASAPClient(
        "http://e2e-agent",
        transport=transport,
        require_https=False,
    ) as client:
        chunks = [e async for e in client.stream(env)]

    assert len(chunks) == 2
    assert chunks[0].payload_dict.get("chunk") == "hello"
    assert chunks[0].payload_dict.get("final") is False
    assert chunks[-1].payload_dict.get("chunk") == "world"
    assert chunks[-1].payload_dict.get("final") is True
    expected_cid = env.correlation_id or env.id
    assert chunks[-1].correlation_id == expected_cid
