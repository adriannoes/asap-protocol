"""Tests for PydanticAI integration (asap_tool_for_urn)."""

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

pytest.importorskip("pydantic_ai")

from asap.integrations.pydanticai import asap_tool_for_urn

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


def test_pydanticai_asap_tool_for_urn_import_when_installed() -> None:
    """asap_tool_for_urn is importable when pydantic-ai is installed."""
    from asap.integrations.pydanticai import asap_tool_for_urn

    assert asap_tool_for_urn is not None
    assert callable(asap_tool_for_urn)


def test_asap_tool_for_urn_returns_tool_with_mock_client() -> None:
    """asap_tool_for_urn returns a PydanticAI Tool; invoking it runs agent and returns str."""
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
            tool = asap_tool_for_urn(
                TEST_URN,
                client=MarketClient(registry_url="https://reg.example/registry.json"),
            )
            # Tool wraps an async function; call it directly for testing.
            result = asyncio.run(tool.function(input={"message": "hello"}))

    assert isinstance(result, str)
    assert json.loads(result) == {"output": "done"}
    mock_send.assert_awaited_once()


def test_asap_tool_for_urn_raises_value_error_when_resolve_fails() -> None:
    """When resolve fails (e.g. agent revoked), asap_tool_for_urn raises ValueError."""
    p_get, p_verify, p_revoked, p_http = _resolve_patches()
    with p_get as mock_get, p_verify as mock_verify, p_revoked as mock_revoked, p_http:
        mock_get.return_value = _lite_registry()
        mock_verify.return_value = True
        mock_revoked.return_value = True  # agent revoked -> resolve raises
        with pytest.raises(ValueError, match="Failed to resolve agent"):
            asap_tool_for_urn(
                TEST_URN,
                client=MarketClient(registry_url="https://reg.example/registry.json"),
            )


def test_asap_tool_for_urn_raises_on_signature_error() -> None:
    """When verify_agent_trust raises SignatureVerificationError, asap_tool_for_urn raises ValueError."""
    p_get, p_verify, p_revoked, p_http = _resolve_patches()
    with p_get as mock_get, p_verify as mock_verify, p_revoked, p_http:
        mock_get.return_value = _lite_registry()
        mock_verify.side_effect = SignatureVerificationError("invalid signature", {})
        with pytest.raises(ValueError, match="Failed to resolve agent"):
            asap_tool_for_urn(
                TEST_URN,
                client=MarketClient(registry_url="https://reg.example/registry.json"),
            )
