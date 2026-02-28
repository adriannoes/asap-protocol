"""Tests for LlamaIndex integration (LlamaIndexAsapTool)."""

from __future__ import annotations

import asyncio
import json
from unittest.mock import AsyncMock, patch

import httpx
import pytest

from asap.client.market import MarketClient
from asap.discovery.registry import LiteRegistry, RegistryEntry
from asap.errors import SignatureVerificationError
from asap.models.entities import Capability, Endpoint, Manifest, Skill
from asap.models.payloads import TaskResponse

pytest.importorskip("llama_index.core.tools")

from asap.integrations.llamaindex import LlamaIndexAsapTool

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


def test_llamaindex_tool_import_when_installed() -> None:
    """LlamaIndexAsapTool is importable when llama-index-core is installed."""
    from asap.integrations.llamaindex import LlamaIndexAsapTool

    assert LlamaIndexAsapTool is not None
    assert hasattr(LlamaIndexAsapTool, "call")
    assert hasattr(LlamaIndexAsapTool, "acall")
    assert hasattr(LlamaIndexAsapTool, "metadata")


def test_llamaindex_tool_call_with_mock_client() -> None:
    """Tool call() resolves agent and runs task; returns ToolOutput with result content."""
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
            tool = LlamaIndexAsapTool(
                TEST_URN,
                client=MarketClient(registry_url="https://reg.example/registry.json"),
            )
            output = tool.call(input={"message": "hello"})

    assert output is not None
    assert hasattr(output, "content") or hasattr(output, "raw_output")
    content = getattr(output, "content", None) or getattr(output, "raw_output", "")
    assert "done" in str(content) or json.loads(content) == {"output": "done"}
    mock_send.assert_awaited_once()


def test_llamaindex_tool_acall_returns_result() -> None:
    """Tool acall() returns ToolOutput with result. Patches kept active for entire test so run() uses mock transport."""
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
            tool = LlamaIndexAsapTool(
                TEST_URN,
                client=MarketClient(registry_url="https://reg.example/registry.json"),
            )
            output = asyncio.run(tool.acall(input={"q": "test"}))

    assert output is not None
    content = getattr(output, "content", None) or getattr(output, "raw_output", "")
    assert "42" in str(content) or json.loads(content) == {"answer": 42}


def test_llamaindex_tool_raises_value_error_when_resolve_fails() -> None:
    """When resolve fails (e.g. agent revoked), LlamaIndexAsapTool raises ValueError."""
    p_get, p_verify, p_revoked, p_http = _resolve_patches()
    with p_get as mock_get, p_verify as mock_verify, p_revoked as mock_revoked, p_http:
        mock_get.return_value = _lite_registry()
        mock_verify.return_value = True
        mock_revoked.return_value = True
        with pytest.raises(ValueError, match="Failed to resolve agent"):
            LlamaIndexAsapTool(
                TEST_URN,
                client=MarketClient(registry_url="https://reg.example/registry.json"),
            )


def test_llamaindex_tool_raises_on_signature_error() -> None:
    """When verify_agent_trust raises SignatureVerificationError, constructor raises ValueError."""
    p_get, p_verify, p_revoked, p_http = _resolve_patches()
    with p_get as mock_get, p_verify as mock_verify, p_revoked, p_http:
        mock_get.return_value = _lite_registry()
        mock_verify.side_effect = SignatureVerificationError("invalid signature", {})
        with pytest.raises(ValueError, match="Failed to resolve agent"):
            LlamaIndexAsapTool(
                TEST_URN,
                client=MarketClient(registry_url="https://reg.example/registry.json"),
            )
