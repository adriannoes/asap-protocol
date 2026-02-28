"""Tests for OpenClaw integration (OpenClawAsapBridge)."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import httpx
import pytest

from asap.client.market import MarketClient
from asap.discovery.registry import LiteRegistry, RegistryEntry
from asap.errors import SignatureVerificationError
from asap.models.entities import Capability, Endpoint, Manifest, Skill

from asap.integrations.openclaw import OpenClawAsapBridge, get_result, is_error_result

TEST_URN = "urn:asap:agent:test-agent"
TEST_HTTP = "https://agent.example.com/asap"
TEST_MANIFEST_URL = "https://agent.example.com/.well-known/asap/manifest.json"


def _registry_entry() -> RegistryEntry:
    return RegistryEntry(
        id=TEST_URN,
        name="Test Agent",
        description="Test",
        endpoints={"http": TEST_HTTP, "manifest": TEST_MANIFEST_URL},
        skills=["echo", "summarize"],
        asap_version="0.1",
    )


def _lite_registry() -> LiteRegistry:
    from datetime import datetime, timezone

    return LiteRegistry(
        version="1.0",
        updated_at=datetime.now(timezone.utc),
        agents=[_registry_entry()],
    )


def _manifest() -> Manifest:
    return Manifest(
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


def _manifest_no_skills() -> Manifest:
    """Manifest with empty skills list (for run_asap_auto_skill error path)."""
    return Manifest(
        id=TEST_URN,
        name="Test Agent",
        version="1.0.0",
        description="No-skills agent",
        capabilities=Capability(
            asap_version="0.1",
            skills=[],
            state_persistence=False,
        ),
        endpoints=Endpoint(asap=TEST_HTTP),
    )


def _signed_manifest_json() -> str:
    from asap.crypto.models import SignatureBlock, SignedManifest
    from asap.crypto.trust_levels import TrustLevel

    sig = SignatureBlock(
        alg="ed25519",
        signature="A" * 88,
        trust_level=TrustLevel.SELF_SIGNED,
    )
    signed = SignedManifest(manifest=_manifest(), signature=sig, public_key=None)
    return signed.model_dump_json()


def _signed_manifest_json_no_skills() -> str:
    from asap.crypto.models import SignatureBlock, SignedManifest
    from asap.crypto.trust_levels import TrustLevel

    sig = SignatureBlock(
        alg="ed25519",
        signature="A" * 88,
        trust_level=TrustLevel.SELF_SIGNED,
    )
    signed = SignedManifest(manifest=_manifest_no_skills(), signature=sig, public_key=None)
    return signed.model_dump_json()


def _resolve_patches(*, use_no_skills_manifest: bool = False) -> tuple:
    """Context patches so MarketClient.resolve(urn) succeeds.

    If use_no_skills_manifest is True, the manifest has capabilities.skills=[].
    """
    manifest_text = (
        _signed_manifest_json_no_skills() if use_no_skills_manifest else _signed_manifest_json()
    )
    _resp = httpx.Response(
        200,
        text=manifest_text,
        request=httpx.Request("GET", TEST_MANIFEST_URL),
    )
    mock_http = AsyncMock()
    mock_http.get = AsyncMock(return_value=_resp)
    mock_http.aclose = AsyncMock()
    mock_http.__aenter__ = AsyncMock(return_value=mock_http)
    mock_http.__aexit__ = AsyncMock(return_value=None)
    return (
        patch("asap.client.market.get_registry", new_callable=AsyncMock),
        patch("asap.client.market.verify_agent_trust"),
        patch("asap.client.market.is_revoked", new_callable=AsyncMock),
        patch("asap.client.market.httpx.AsyncClient", return_value=mock_http),
    )


@pytest.mark.asyncio
async def test_openclaw_bridge_run_asap_success() -> None:
    """OpenClawAsapBridge.run_asap resolves agent and runs task."""
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

    p_get, p_verify, p_revoked, p_http = _resolve_patches()
    with p_get as mock_get, p_verify as mock_verify, p_revoked as mock_revoked, p_http:
        mock_get.return_value = _lite_registry()
        mock_verify.return_value = True
        mock_revoked.return_value = False
        with patch("asap.client.market.ASAPClient", return_value=mock_transport):
            bridge = OpenClawAsapBridge(
                client=MarketClient(registry_url="https://reg.example/registry.json")
            )
            result = await bridge.run_asap(
                TEST_URN,
                skill_id="echo",
                input_payload={"message": "hello"},
            )

    assert isinstance(result, dict)
    assert result == {"output": "done"}
    mock_send.assert_awaited_once()


@pytest.mark.asyncio
async def test_openclaw_bridge_run_asap_auto_skill_success() -> None:
    """OpenClawAsapBridge.run_asap_auto_skill uses first skill from manifest."""
    from asap.models.payloads import TaskResponse

    task_response = TaskResponse(
        task_id="task-1",
        status="completed",
        result={"echo": "hello"},
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

    p_get, p_verify, p_revoked, p_http = _resolve_patches()
    with p_get as mock_get, p_verify as mock_verify, p_revoked as mock_revoked, p_http:
        mock_get.return_value = _lite_registry()
        mock_verify.return_value = True
        mock_revoked.return_value = False
        with patch("asap.client.market.ASAPClient", return_value=mock_transport):
            bridge = OpenClawAsapBridge(
                client=MarketClient(registry_url="https://reg.example/registry.json")
            )
            result = await bridge.run_asap_auto_skill(
                TEST_URN,
                input_payload={"message": "hello"},
            )

    assert isinstance(result, dict)
    assert result == {"echo": "hello"}
    mock_send.assert_awaited_once()


@pytest.mark.asyncio
async def test_openclaw_bridge_returns_error_on_agent_revoked() -> None:
    """When resolve raises AgentRevokedException, bridge returns error string."""
    p_get, p_verify, p_revoked, p_http = _resolve_patches()
    with p_get as mock_get, p_verify as mock_verify, p_revoked as mock_revoked, p_http:
        mock_get.return_value = _lite_registry()
        mock_verify.return_value = True
        mock_revoked.return_value = True
        bridge = OpenClawAsapBridge(
            client=MarketClient(registry_url="https://reg.example/registry.json")
        )
        result = await bridge.run_asap(
            TEST_URN,
            skill_id="echo",
            input_payload={"x": "y"},
        )

    assert isinstance(result, str)
    assert "Error:" in result
    assert "revoked" in result.lower() or "Agent" in result


@pytest.mark.asyncio
async def test_openclaw_bridge_returns_error_on_signature_error() -> None:
    """When resolve raises SignatureVerificationError, bridge returns error string."""
    p_get, p_verify, p_revoked, p_http = _resolve_patches()
    with p_get as mock_get, p_verify as mock_verify, p_revoked, p_http:
        mock_get.return_value = _lite_registry()
        mock_verify.side_effect = SignatureVerificationError("invalid signature", {})
        bridge = OpenClawAsapBridge(
            client=MarketClient(registry_url="https://reg.example/registry.json")
        )
        result = await bridge.run_asap_auto_skill(TEST_URN, input_payload={})

    assert isinstance(result, str)
    assert "Error:" in result


@pytest.mark.asyncio
async def test_openclaw_bridge_run_asap_auto_skill_returns_error_when_no_skills() -> None:
    """When manifest has no skills, run_asap_auto_skill returns error string."""
    p_get, p_verify, p_revoked, p_http = _resolve_patches(use_no_skills_manifest=True)
    with p_get as mock_get, p_verify as mock_verify, p_revoked as mock_revoked, p_http:
        mock_get.return_value = _lite_registry()
        mock_verify.return_value = True
        mock_revoked.return_value = False
        bridge = OpenClawAsapBridge(
            client=MarketClient(registry_url="https://reg.example/registry.json")
        )
        result = await bridge.run_asap_auto_skill(TEST_URN, input_payload={"x": "y"})

    assert isinstance(result, str)
    assert "Error:" in result
    assert "no skills" in result.lower()


@pytest.mark.asyncio
async def test_openclaw_bridge_returns_error_on_value_error() -> None:
    """When resolve raises ValueError, bridge returns error string."""
    p_get, p_verify, p_revoked, p_http = _resolve_patches()
    with p_get as mock_get, p_verify as mock_verify, p_revoked as mock_revoked, p_http:
        mock_get.return_value = _lite_registry()
        mock_verify.return_value = True
        mock_revoked.return_value = False
        mock_get.side_effect = ValueError("Invalid URN format")
        bridge = OpenClawAsapBridge(
            client=MarketClient(registry_url="https://reg.example/registry.json")
        )
        result = await bridge.run_asap(TEST_URN, skill_id="echo", input_payload={})

    assert isinstance(result, str)
    assert "Error:" in result


def test_openclaw_bridge_import_without_openclaw_sdk() -> None:
    """OpenClawAsapBridge is importable; openclaw-sdk is optional for bridge (MarketClient only)."""
    from asap.integrations.openclaw import OpenClawAsapBridge

    bridge = OpenClawAsapBridge()
    assert bridge is not None
    assert hasattr(bridge, "run_asap")
    assert hasattr(bridge, "run_asap_auto_skill")


def test_is_error_result() -> None:
    """is_error_result identifies bridge error strings vs success dicts."""
    assert is_error_result("Error: Agent not found") is True
    assert is_error_result("Error: Agent has no skills; cannot build task request.") is True
    assert is_error_result("Something went wrong") is False
    assert is_error_result({"output": "done"}) is False
    assert is_error_result({}) is False


def test_get_result_returns_dict_on_success() -> None:
    """get_result returns dict when result is success."""
    assert get_result({"output": "done"}) == {"output": "done"}


def test_get_result_raises_on_error() -> None:
    """get_result raises ValueError when result is error string."""
    with pytest.raises(ValueError, match="Error: Agent not found"):
        get_result("Error: Agent not found")


def test_get_result_raises_type_error_when_not_dict() -> None:
    """get_result raises TypeError when result is not a dict (e.g. list)."""
    with pytest.raises(TypeError, match="Expected dict result"):
        get_result(["not", "a", "dict"])


def test_openclaw_bridge_accepts_registry_url() -> None:
    """OpenClawAsapBridge can be constructed with registry_url without building MarketClient."""
    bridge = OpenClawAsapBridge(registry_url="https://custom.registry/registry.json")
    assert bridge._client.registry_url == "https://custom.registry/registry.json"


@pytest.mark.asyncio
async def test_openclaw_bridge_list_agents() -> None:
    """OpenClawAsapBridge.list_agents returns agents from registry."""
    with patch("asap.client.market.get_registry", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = _lite_registry()
        bridge = OpenClawAsapBridge(
            client=MarketClient(registry_url="https://reg.example/registry.json")
        )
        agents = await bridge.list_agents()

    assert len(agents) == 1
    assert agents[0].urn == TEST_URN
    assert agents[0].name == "Test Agent"
    assert agents[0].skill_ids == ["echo", "summarize"]
