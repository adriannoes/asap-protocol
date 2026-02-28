"""Tests for Vercel AI SDK bridge (create_asap_tools_router)."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import httpx
from fastapi import FastAPI
from fastapi.testclient import TestClient

from asap.discovery.registry import LiteRegistry, RegistryEntry
from asap.integrations.vercel_ai import (
    ASAP_INVOKE_TOOL_DEF,
    create_asap_tools_router,
)

TEST_URN = "urn:asap:agent:test-agent"
TEST_HTTP = "https://agent.example.com/asap"
TEST_MANIFEST_URL = "https://agent.example.com/.well-known/asap/manifest.json"


def _registry_entry() -> RegistryEntry:
    return RegistryEntry(
        id=TEST_URN,
        name="Test Agent",
        description="Test",
        endpoints={"http": TEST_HTTP, "manifest": TEST_MANIFEST_URL},
        skills=[],
        asap_version="0.1",
    )


def _lite_registry() -> LiteRegistry:
    from datetime import datetime, timezone

    return LiteRegistry(
        version="1.0",
        updated_at=datetime.now(timezone.utc),
        agents=[_registry_entry()],
    )


def _signed_manifest_json() -> str:
    from asap.models.entities import Capability, Endpoint, Manifest, Skill

    manifest = Manifest(
        id=TEST_URN,
        name="Test Agent",
        version="1.0.0",
        description="Echo agent",
        capabilities=Capability(
            asap_version="0.1",
            skills=[Skill(id="echo", description="Echo")],
            state_persistence=False,
        ),
        endpoints=Endpoint(asap=TEST_HTTP),
    )
    from asap.crypto.models import SignatureBlock, SignedManifest
    from asap.crypto.trust_levels import TrustLevel

    sig = SignatureBlock(
        alg="ed25519",
        signature="A" * 88,
        trust_level=TrustLevel.SELF_SIGNED,
    )
    signed = SignedManifest(manifest=manifest, signature=sig, public_key=None)
    return signed.model_dump_json()


def _app_with_router(whitelist_urns: list[str] | None = None) -> FastAPI:
    app = FastAPI()
    router = create_asap_tools_router(
        registry_url="https://reg.example/registry.json",
        whitelist_urns=whitelist_urns,
    )
    app.include_router(router, prefix="/api/asap", tags=["asap-tools"])
    return app


def test_get_tools_returns_asap_invoke() -> None:
    """GET /tools returns asap_invoke tool definition."""
    app = _app_with_router()
    client = TestClient(app)
    r = client.get("/api/asap/tools")
    assert r.status_code == 200
    data = r.json()
    assert "tools" in data
    assert len(data["tools"]) >= 1
    first = data["tools"][0]
    assert first["name"] == "asap_invoke"
    assert "parameters" in first
    assert first["parameters"]["type"] == "object"
    assert "urn" in first["parameters"]["properties"]
    assert "payload" in first["parameters"]["properties"]


def test_post_invoke_returns_error_for_unknown_urn() -> None:
    """POST /invoke returns error when agent not found."""
    app = _app_with_router()
    client = TestClient(app)
    r = client.post(
        "/api/asap/invoke",
        json={"urn": "urn:asap:agent:nonexistent", "payload": {}},
    )
    assert r.status_code == 200
    data = r.json()
    assert "error" in data
    assert data["error"]


def test_post_invoke_with_mock_succeeds() -> None:
    """POST /invoke returns result when agent resolves and runs."""
    from asap.models.payloads import TaskResponse

    task_response = TaskResponse(
        task_id="task-1",
        status="completed",
        result={"output": "done"},
        final_state=None,
        metrics=None,
    )
    response_envelope = AsyncMock()
    response_envelope.payload = task_response
    mock_send = AsyncMock(return_value=response_envelope)
    mock_transport = AsyncMock()
    mock_transport.send = mock_send
    mock_transport.__aenter__ = AsyncMock(return_value=mock_transport)
    mock_transport.__aexit__ = AsyncMock(return_value=None)

    _resp = httpx.Response(
        200,
        text=_signed_manifest_json(),
        request=httpx.Request("GET", TEST_MANIFEST_URL),
    )
    mock_http = AsyncMock()
    mock_http.get = AsyncMock(return_value=_resp)
    mock_http.aclose = AsyncMock()
    mock_http.__aenter__ = AsyncMock(return_value=mock_http)
    mock_http.__aexit__ = AsyncMock(return_value=None)

    patches = (
        patch("asap.client.market.get_registry", new_callable=AsyncMock),
        patch("asap.client.market.verify_agent_trust"),
        patch("asap.client.market.is_revoked", new_callable=AsyncMock),
        patch("asap.client.market.httpx.AsyncClient", return_value=mock_http),
        patch("asap.client.market.ASAPClient", return_value=mock_transport),
    )
    with (
        patches[0] as p_get,
        patches[1] as p_verify,
        patches[2] as p_revoked,
        patches[3],
        patches[4],
    ):
        p_get.return_value = _lite_registry()
        p_verify.return_value = True
        p_revoked.return_value = False
        app = _app_with_router()
        client = TestClient(app)
        r = client.post(
            "/api/asap/invoke",
            json={"urn": TEST_URN, "payload": {"message": "hello"}},
        )
    assert r.status_code == 200
    data = r.json()
    assert "result" in data
    assert data["result"] == {"output": "done"}


def test_get_discover_returns_agents() -> None:
    """GET /discover returns registry search results."""
    with patch("asap.integrations.vercel_ai.get_registry", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = _lite_registry()
        app = _app_with_router()
        client = TestClient(app)
        r = client.get("/api/asap/discover?query=test")
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, list)
    assert len(data) >= 1
    assert data[0]["id"] == TEST_URN


def test_asap_invoke_tool_def_has_required_schema() -> None:
    """ASAP_INVOKE_TOOL_DEF has valid JSON Schema structure."""
    assert ASAP_INVOKE_TOOL_DEF["parameters"]["type"] == "object"
    assert "urn" in ASAP_INVOKE_TOOL_DEF["parameters"]["properties"]
    assert "payload" in ASAP_INVOKE_TOOL_DEF["parameters"]["properties"]
    assert "urn" in ASAP_INVOKE_TOOL_DEF["parameters"]["required"]
    assert "payload" in ASAP_INVOKE_TOOL_DEF["parameters"]["required"]
