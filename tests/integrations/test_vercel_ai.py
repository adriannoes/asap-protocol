"""Tests for Vercel AI SDK bridge (create_asap_tools_router)."""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
from fastapi import FastAPI
from fastapi.testclient import TestClient

from asap.discovery.registry import LiteRegistry, RegistryEntry
from asap.integrations.vercel_ai import (
    ASAP_INVOKE_TOOL_DEF,
    _parameters_schema_from_manifest,
    _search_registry,
    create_asap_tools_router,
)
from asap.models.entities import Capability, Endpoint, Manifest, Skill
from asap.models.enums import HardwareClass, InferenceMode

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
    return LiteRegistry(
        version="1.0",
        updated_at=datetime.now(timezone.utc),
        agents=[_registry_entry()],
    )


def _signed_manifest_json() -> str:
    from asap.crypto.models import SignatureBlock, SignedManifest
    from asap.crypto.trust_levels import TrustLevel

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

    sig = SignatureBlock(
        alg="ed25519",
        signature="A" * 88,
        trust_level=TrustLevel.SELF_SIGNED,
    )
    signed = SignedManifest(manifest=manifest, signature=sig, public_key=None)
    return signed.model_dump_json()


def _app_with_router(
    whitelist_urns: list[str] | None = None,
    api_key_header: str | None = None,
    api_key_value: str | None = None,
) -> FastAPI:
    app = FastAPI()
    router = create_asap_tools_router(
        registry_url="https://reg.example/registry.json",
        whitelist_urns=whitelist_urns,
        api_key_header=api_key_header,
        api_key_value=api_key_value,
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


def test_api_key_header_returns_401_when_missing() -> None:
    """When api_key_header is set, request without header returns 401."""
    app = _app_with_router(api_key_header="X-API-Key")
    client = TestClient(app)
    r = client.get("/api/asap/tools")
    assert r.status_code == 401
    assert "detail" in r.json()
    assert "api key" in r.json()["detail"].lower() or "key" in r.json()["detail"].lower()


def test_api_key_header_accepts_valid_header() -> None:
    """When api_key_header is set, request with header returns 200."""
    app = _app_with_router(api_key_header="X-API-Key")
    client = TestClient(app)
    r = client.get("/api/asap/tools", headers={"X-API-Key": "secret"})
    assert r.status_code == 200
    data = r.json()
    assert "tools" in data
    assert len(data["tools"]) >= 1


def test_api_key_value_returns_401_when_wrong() -> None:
    """When api_key_value is set, wrong header value returns 401 Invalid API key."""
    app = _app_with_router(
        api_key_header="X-API-Key",
        api_key_value="expected-secret",
    )
    client = TestClient(app)
    r = client.get("/api/asap/tools", headers={"X-API-Key": "wrong-value"})
    assert r.status_code == 401
    assert r.json().get("detail") == "Invalid API key"


def test_api_key_value_accepts_matching_value() -> None:
    """When api_key_value is set, matching header value returns 200."""
    app = _app_with_router(
        api_key_header="X-API-Key",
        api_key_value="expected-secret",
    )
    client = TestClient(app)
    r = client.get("/api/asap/tools", headers={"X-API-Key": "expected-secret"})
    assert r.status_code == 200
    data = r.json()
    assert "tools" in data


def test_search_registry_matches_skill_string() -> None:
    reg = LiteRegistry(
        version="1.0",
        updated_at=datetime.now(timezone.utc),
        agents=[
            RegistryEntry(
                id="urn:asap:agent:x",
                name="X",
                description="Y",
                endpoints={"http": "https://x.example.com"},
                skills=["deep_research"],
                asap_version="0.1",
            ),
        ],
    )
    hits = _search_registry(reg, "research")
    assert len(hits) == 1
    assert hits[0]["id"] == "urn:asap:agent:x"


def test_search_registry_does_not_match_edge_hardware_fields() -> None:
    """Edge mirror fields are not searched today — guards future discover UX changes."""
    reg = LiteRegistry(
        version="1.0",
        updated_at=datetime.now(timezone.utc),
        agents=[
            RegistryEntry(
                id="urn:asap:agent:jetson",
                name="Jetson Agent",
                description="Generic edge agent",
                endpoints={"http": "https://jetson.example.com"},
                skills=["assistant"],
                asap_version="2.1.0",
                hardware_class=HardwareClass.EDGE_ACCELERATOR.value,
                inference_modes=[InferenceMode.LOCAL_CUDA.value],
                hardware_io=["gpio"],
            ),
        ],
    )
    assert _search_registry(reg, "local_cuda") == []
    assert _search_registry(reg, "edge_accelerator") == []
    assert _search_registry(reg, "gpio") == []


def test_list_tools_whitelist_skips_unresolvable_urn() -> None:
    """Whitelist resolve failures are skipped; asap_invoke remains available."""
    with patch("asap.integrations.vercel_ai.MarketClient") as mc_class:
        mc_class.return_value.resolve = AsyncMock(side_effect=ValueError("registry offline"))
        app = FastAPI()
        app.include_router(
            create_asap_tools_router(whitelist_urns=[TEST_URN]),
            prefix="/api/asap",
        )
        client = TestClient(app)
        response = client.get("/api/asap/tools")

    assert response.status_code == 200
    tool_names = [tool["name"] for tool in response.json()["tools"]]
    assert tool_names == ["asap_invoke"]


def test_parameters_schema_from_manifest_branches() -> None:
    empty = Manifest(
        id=TEST_URN,
        name="N",
        version="1",
        description="D",
        capabilities=Capability(asap_version="0.1", skills=[], state_persistence=False),
        endpoints=Endpoint(asap=TEST_HTTP),
    )
    fallback = _parameters_schema_from_manifest(empty)
    assert fallback["type"] == "object"
    assert "input" in fallback["properties"]

    rich = Manifest(
        id=TEST_URN,
        name="N",
        version="1",
        description="D",
        capabilities=Capability(
            asap_version="0.1",
            skills=[
                Skill(
                    id="echo",
                    description="E",
                    input_schema={
                        "type": "object",
                        "properties": {"msg": {"type": "string"}},
                    },
                ),
            ],
            state_persistence=False,
        ),
        endpoints=Endpoint(asap=TEST_HTTP),
    )
    params = _parameters_schema_from_manifest(rich)
    assert params["properties"]["msg"]["type"] == "string"


def test_get_tools_whitelist_appends_resolved_tools() -> None:
    manifest = Manifest(
        id=TEST_URN,
        name="WL Agent",
        version="1.0.0",
        description="With schema",
        capabilities=Capability(
            asap_version="0.1",
            skills=[
                Skill(
                    id="do",
                    description="d",
                    input_schema={"type": "object", "properties": {"a": {"type": "integer"}}},
                ),
            ],
            state_persistence=False,
        ),
        endpoints=Endpoint(asap=TEST_HTTP),
    )
    mock_agent = MagicMock()
    mock_agent.manifest = manifest

    with patch("asap.integrations.vercel_ai.MarketClient") as mc_class:
        mc_class.return_value.resolve = AsyncMock(return_value=mock_agent)
        app = FastAPI()
        app.include_router(
            create_asap_tools_router(whitelist_urns=[TEST_URN]),
            prefix="/api/asap",
        )
        client = TestClient(app)
        r = client.get("/api/asap/tools")

    assert r.status_code == 200
    tools = r.json()["tools"]
    names = [t["name"] for t in tools]
    assert "asap_invoke" in names
    assert f"asap_{TEST_URN.replace(':', '_').replace('.', '_')}" in names


def test_post_invoke_agent_without_skills_returns_error() -> None:
    manifest = Manifest(
        id=TEST_URN,
        name="Empty",
        version="1.0.0",
        description="",
        capabilities=Capability(asap_version="0.1", skills=[], state_persistence=False),
        endpoints=Endpoint(asap=TEST_HTTP),
    )
    mock_agent = MagicMock()
    mock_agent.manifest = manifest

    with patch("asap.integrations.vercel_ai.MarketClient") as mc_class:
        mc_class.return_value.resolve = AsyncMock(return_value=mock_agent)
        app = FastAPI()
        app.include_router(create_asap_tools_router(), prefix="/api/asap")
        client = TestClient(app)
        r = client.post(
            "/api/asap/invoke",
            json={"urn": TEST_URN, "payload": {}},
        )

    assert r.status_code == 200
    assert r.json().get("error") == "Agent has no skills"


def test_post_invoke_wraps_non_dict_upstream_result() -> None:
    manifest = Manifest(
        id=TEST_URN,
        name="T",
        version="1.0.0",
        description="",
        capabilities=Capability(
            asap_version="0.1",
            skills=[Skill(id="echo", description="E")],
            state_persistence=False,
        ),
        endpoints=Endpoint(asap=TEST_HTTP),
    )
    mock_agent = MagicMock()
    mock_agent.manifest = manifest
    mock_agent.run = AsyncMock(return_value="plain-result")

    with patch("asap.integrations.vercel_ai.MarketClient") as mc_class:
        mc_class.return_value.resolve = AsyncMock(return_value=mock_agent)
        app = FastAPI()
        app.include_router(create_asap_tools_router(), prefix="/api/asap")
        client = TestClient(app)
        r = client.post(
            "/api/asap/invoke",
            json={"urn": TEST_URN, "payload": {"input": "raw"}},
        )

    assert r.status_code == 200
    body = r.json()
    assert body.get("result") == {"value": "plain-result"}
    mock_agent.run.assert_awaited_once()
    payload_sent = mock_agent.run.await_args.args[0]
    assert payload_sent["skill_id"] == "echo"


def test_post_invoke_non_dict_input_nested_value() -> None:
    manifest = Manifest(
        id=TEST_URN,
        name="T",
        version="1.0.0",
        description="",
        capabilities=Capability(
            asap_version="0.1",
            skills=[Skill(id="echo", description="E")],
            state_persistence=False,
        ),
        endpoints=Endpoint(asap=TEST_HTTP),
    )
    mock_agent = MagicMock()
    mock_agent.manifest = manifest
    mock_agent.run = AsyncMock(return_value={"ok": True})

    with patch("asap.integrations.vercel_ai.MarketClient") as mc_class:
        mc_class.return_value.resolve = AsyncMock(return_value=mock_agent)
        app = FastAPI()
        app.include_router(create_asap_tools_router(), prefix="/api/asap")
        client = TestClient(app)
        r = client.post(
            "/api/asap/invoke",
            json={"urn": TEST_URN, "payload": {"input": 99}},
        )

    assert r.status_code == 200
    call_kw = mock_agent.run.await_args.args[0]
    assert call_kw["input"] == {"value": 99}


def test_get_discover_returns_502_when_registry_fails() -> None:
    with patch("asap.integrations.vercel_ai.get_registry", new_callable=AsyncMock) as mock_gr:
        mock_gr.side_effect = RuntimeError("network down")
        app = _app_with_router()
        client = TestClient(app)
        r = client.get("/api/asap/discover")

    assert r.status_code == 502
