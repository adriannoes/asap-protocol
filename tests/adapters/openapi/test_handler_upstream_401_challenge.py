"""Upstream HTTP 401 → ASAP challenge metadata on FatalError (CHAL-004)."""

from __future__ import annotations

import httpx
import pytest

from asap.adapters.openapi.capability_mapper import OpenAPIExecutionKind, OpenAPICapability
from asap.adapters.openapi.handler import OpenAPIUpstreamHandler
from asap.errors import FatalError
from asap.models.entities import Skill
from asap.transport.challenge import format_www_authenticate_asap


@pytest.mark.asyncio
async def test_openapi_upstream_401_adds_www_authenticate_detail() -> None:
    discovery = "https://adapter.example/.well-known/asap/manifest.json"

    def _handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/unauth"
        return httpx.Response(401, json={"detail": "unauthorized"})

    transport = httpx.MockTransport(_handler)
    async with httpx.AsyncClient(transport=transport, base_url="http://upstream.example") as client:
        cap = OpenAPICapability(
            skill=Skill(
                id="ping",
                description="ping upstream",
                input_schema={"type": "object", "properties": {}},
            ),
            http_method="get",
            path_template="/unauth",
            execution_kind=OpenAPIExecutionKind.SYNC,
        )
        upstream = OpenAPIUpstreamHandler.from_capabilities(
            base_url="http://upstream.example",
            capabilities=[cap],
            http_client=client,
            asap_challenge_discovery_url=discovery,
        )
        with pytest.raises(FatalError) as ei:
            await upstream.execute("ping", {})
        exc = ei.value
        assert exc.details.get("_www_authenticate_asap") == format_www_authenticate_asap(discovery)
        assert exc.details.get("status_code") == 401
