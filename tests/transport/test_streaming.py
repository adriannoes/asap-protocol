"""Tests for TaskStream payload, SSE ``/asap/stream``, and streaming handlers."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any, AsyncIterator

import httpx
import pytest
from httpx import ASGITransport

from asap.models.constants import ASAP_DEFAULT_TRANSPORT_VERSION, ASAP_VERSION_HEADER
from asap.models.entities import Manifest
from asap.models.envelope import Envelope
from asap.models.enums import TaskStatus
from asap.models.payloads import TaskRequest, TaskStream
from asap.transport.handlers import HandlerRegistry, create_echo_handler
from asap.transport.jsonrpc import ASAP_METHOD, VERSION_INCOMPATIBLE
from asap.transport.server import create_app

if TYPE_CHECKING:
    from asap.transport.rate_limit import ASAPRateLimiter


async def _word_stream_handler(envelope: Envelope, manifest: Any) -> AsyncIterator[Envelope]:
    """Yield one TaskStream envelope per word in ``input.text``."""
    req = TaskRequest.model_validate(envelope.payload_dict)
    text = str(req.input.get("text", "hello stream"))
    words = text.split() or ["empty"]
    cid = envelope.correlation_id or envelope.id or "corr"
    n = len(words)
    for i, w in enumerate(words):
        is_final = i == n - 1
        pl = TaskStream(
            chunk=w + (" " if not is_final else ""),
            progress=(i + 1) / n,
            final=is_final,
            status=TaskStatus.COMPLETED if is_final else TaskStatus.WORKING,
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


@pytest.mark.anyio
async def test_taskstream_envelope_roundtrip(sample_manifest: Manifest) -> None:
    payloads = TaskStream(chunk="x", progress=0.5, final=False, status=TaskStatus.WORKING)
    env = Envelope(
        asap_version="0.1",
        sender="urn:asap:agent:a",
        recipient=sample_manifest.id,
        payload_type="TaskStream",
        payload=payloads.model_dump(mode="json"),
        correlation_id="c1",
    )
    restored = Envelope.model_validate(env.model_dump(mode="json"))
    assert restored.payload_type == "TaskStream"
    assert isinstance(restored.payload, TaskStream)
    assert restored.payload.chunk == "x"


@pytest.mark.anyio
async def test_asap_stream_sse_endpoint(
    sample_manifest: Manifest,
    isolated_rate_limiter: ASAPRateLimiter | None,
) -> None:
    registry = HandlerRegistry()
    registry.register("task.request", create_echo_handler())
    registry.register_streaming_handler("task.request", _word_stream_handler)
    app = create_app(sample_manifest, registry, rate_limit="999999/minute")
    if isolated_rate_limiter is not None:
        app.state.limiter = isolated_rate_limiter

    tr = TaskRequest(
        conversation_id="conv-1",
        skill_id="echo",
        input={"text": "one two"},
    )
    env = Envelope(
        asap_version="0.1",
        sender="urn:asap:agent:client",
        recipient=sample_manifest.id,
        payload_type="task.request",
        payload=tr.model_dump(),
        correlation_id="corr-stream-1",
    )
    rpc = {
        "jsonrpc": "2.0",
        "method": ASAP_METHOD,
        "params": {"envelope": env.model_dump(mode="json")},
        "id": 1,
    }

    transport = ASGITransport(app=app)
    async with (
        httpx.AsyncClient(transport=transport, base_url="http://test") as client,
        client.stream("POST", "/asap/stream", json=rpc) as response,
    ):
        assert response.status_code == 200
        buf = ""
        events: list[Envelope] = []
        async for chunk in response.aiter_text():
            buf += chunk
            while "\n\n" in buf:
                raw_event, buf = buf.split("\n\n", 1)
                for line in raw_event.split("\n"):
                    stripped = line.strip()
                    if stripped.startswith("data:"):
                        payload_json = stripped[5:].strip()
                        events.append(Envelope.model_validate(json.loads(payload_json)))

    assert len(events) == 2
    assert events[0].payload_dict.get("chunk") == "one "
    assert events[0].payload_dict.get("final") is False
    assert events[-1].payload_dict.get("final") is True
    assert events[-1].payload_dict.get("status") == "completed"


@pytest.mark.anyio
async def test_asap_stream_negotiates_first_supported_wire_version(
    sample_manifest: Manifest,
    isolated_rate_limiter: ASAPRateLimiter | None,
) -> None:
    """`/asap/stream` uses the first supported ASAP-Version token and echoes it."""
    registry = HandlerRegistry()
    registry.register("task.request", create_echo_handler())
    registry.register_streaming_handler("task.request", _word_stream_handler)
    app = create_app(sample_manifest, registry, rate_limit="999999/minute")
    if isolated_rate_limiter is not None:
        app.state.limiter = isolated_rate_limiter

    env = Envelope(
        asap_version="0.1",
        sender="urn:asap:agent:client",
        recipient=sample_manifest.id,
        payload_type="task.request",
        payload=TaskRequest(
            conversation_id="conv-version-stream-ok",
            skill_id="echo",
            input={"text": "one two"},
        ).model_dump(),
        correlation_id="corr-version-stream-ok",
    )
    rpc = {
        "jsonrpc": "2.0",
        "method": ASAP_METHOD,
        "params": {"envelope": env.model_dump(mode="json")},
        "id": 2,
    }

    transport = ASGITransport(app=app)
    async with (
        httpx.AsyncClient(transport=transport, base_url="http://test") as client,
        client.stream(
            "POST",
            "/asap/stream",
            json=rpc,
            headers={ASAP_VERSION_HEADER: "2.2, 2.1"},
        ) as response,
    ):
        assert response.status_code == 200
        assert response.headers.get(ASAP_VERSION_HEADER) == "2.2"
        assert response.headers["content-type"].startswith("text/event-stream")

        buf = ""
        events: list[Envelope] = []
        async for chunk in response.aiter_text():
            buf += chunk
            while "\n\n" in buf:
                raw_event, buf = buf.split("\n\n", 1)
                for line in raw_event.split("\n"):
                    stripped = line.strip()
                    if stripped.startswith("data:"):
                        payload_json = stripped[5:].strip()
                        events.append(Envelope.model_validate(json.loads(payload_json)))

    assert len(events) == 2
    assert events[-1].payload_dict.get("final") is True


@pytest.mark.anyio
async def test_asap_stream_rejects_incompatible_wire_version(
    sample_manifest: Manifest,
    isolated_rate_limiter: ASAPRateLimiter | None,
) -> None:
    """`/asap/stream` returns JSON-RPC VERSION_INCOMPATIBLE when header has no match."""
    registry = HandlerRegistry()
    registry.register("task.request", create_echo_handler())
    registry.register_streaming_handler("task.request", _word_stream_handler)
    app = create_app(sample_manifest, registry, rate_limit="999999/minute")
    if isolated_rate_limiter is not None:
        app.state.limiter = isolated_rate_limiter

    env = Envelope(
        asap_version="0.1",
        sender="urn:asap:agent:client",
        recipient=sample_manifest.id,
        payload_type="task.request",
        payload=TaskRequest(
            conversation_id="conv-version-stream-bad",
            skill_id="echo",
            input={"text": "one two"},
        ).model_dump(),
        correlation_id="corr-version-stream-bad",
    )
    rpc = {
        "jsonrpc": "2.0",
        "method": ASAP_METHOD,
        "params": {"envelope": env.model_dump(mode="json")},
        "id": 3,
    }

    transport = ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/asap/stream",
            json=rpc,
            headers={ASAP_VERSION_HEADER: "9.9"},
        )

    assert response.status_code == 200
    assert response.headers.get(ASAP_VERSION_HEADER) == ASAP_DEFAULT_TRANSPORT_VERSION
    assert response.headers["content-type"].startswith("application/json")
    payload = response.json()
    assert payload.get("error", {}).get("code") == VERSION_INCOMPATIBLE
    assert payload.get("error", {}).get("data", {}).get("requested") == "9.9"
