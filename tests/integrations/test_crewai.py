"""Tests for CrewAI integration (CrewAIAsapTool)."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, patch

import httpx
import pytest

from asap.client.market import MarketClient
from asap.discovery.registry import LiteRegistry, RegistryEntry
from asap.errors import SignatureVerificationError
from asap.models.entities import Capability, Endpoint, Manifest, Skill
from asap.models.payloads import TaskResponse

pytest.importorskip("crewai")

from asap.integrations.crewai import CrewAIAsapTool

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


def _resolve_patches() -> tuple:
    """Context patches so MarketClient.resolve(urn) succeeds."""
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
    return (
        patch("asap.client.market.get_registry", new_callable=AsyncMock),
        patch("asap.client.market.verify_agent_trust"),
        patch("asap.client.market.is_revoked", new_callable=AsyncMock),
        patch("asap.client.market.httpx.AsyncClient", return_value=mock_http),
    )


def test_crewai_tool_import_when_installed() -> None:
    """CrewAIAsapTool is importable when crewai is installed."""
    from asap.integrations.crewai import CrewAIAsapTool

    assert CrewAIAsapTool is not None
    assert hasattr(CrewAIAsapTool, "_run")
    assert hasattr(CrewAIAsapTool, "_arun")


def test_crewai_tool_invoke_with_mock_client() -> None:
    """Tool _run resolves agent and runs task; returns result as str (JSON for dict)."""
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
            tool = CrewAIAsapTool(
                TEST_URN, client=MarketClient(registry_url="https://reg.example/registry.json")
            )
            out = tool._run(input={"message": "hello"})

    assert isinstance(out, str)
    assert json.loads(out) == {"output": "done"}
    mock_send.assert_awaited_once()


@pytest.mark.asyncio
async def test_crewai_tool_arun_returns_result() -> None:
    """Tool _arun resolves and runs; returns result as str."""
    task_response = TaskResponse(
        task_id="task-1",
        status="completed",
        result={"answer": 42},
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
            tool = CrewAIAsapTool(
                TEST_URN, client=MarketClient(registry_url="https://reg.example/registry.json")
            )
            out = await tool._arun(input={"q": "test"})

    assert isinstance(out, str)
    assert json.loads(out) == {"answer": 42}


def test_crewai_tool_returns_error_string_on_agent_revoked() -> None:
    """When resolve raises AgentRevokedException (via is_revoked), tool returns error string."""
    p_get, p_verify, p_revoked, p_http = _resolve_patches()
    with p_get as mock_get, p_verify as mock_verify, p_revoked as mock_revoked, p_http:
        mock_get.return_value = _lite_registry()
        mock_verify.return_value = True
        mock_revoked.return_value = True
        tool = CrewAIAsapTool(
            TEST_URN, client=MarketClient(registry_url="https://reg.example/registry.json")
        )
        out = tool._run(input={"x": "y"})

    assert isinstance(out, str)
    assert "Error:" in out
    assert "revoked" in out.lower() or "Agent" in out


def test_crewai_tool_returns_error_string_on_signature_error() -> None:
    """When resolve raises SignatureVerificationError, tool returns error string."""
    p_get, p_verify, p_revoked, p_http = _resolve_patches()
    with p_get as mock_get, p_verify as mock_verify, p_revoked, p_http:
        mock_get.return_value = _lite_registry()
        mock_verify.side_effect = SignatureVerificationError("invalid signature", {})
        tool = CrewAIAsapTool(
            TEST_URN, client=MarketClient(registry_url="https://reg.example/registry.json")
        )
        out = tool._run(input={})

    assert isinstance(out, str)
    assert "Error:" in out
