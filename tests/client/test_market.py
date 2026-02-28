"""Tests for MarketClient and ResolvedAgent (SDK-001, SDK-002)."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import httpx
import pytest

from asap.client.market import MarketClient, ResolvedAgent
from asap.discovery.registry import LiteRegistry, RegistryEntry
from asap.errors import AgentRevokedException, SignatureVerificationError
from asap.models.entities import Capability, Endpoint, Manifest, Skill
from asap.models.payloads import TaskResponse

# Minimal RegistryEntry and LiteRegistry for resolve tests.
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
        description="Test",
        capabilities=Capability(
            asap_version="0.1",
            skills=[Skill(id="echo", description="Echo")],
            state_persistence=False,
        ),
        endpoints=Endpoint(asap=TEST_HTTP),
    )


def _signed_manifest_json() -> str:
    """Minimal signed manifest JSON (signature not verified in tests when patched)."""
    from asap.crypto.models import SignatureBlock, SignedManifest
    from asap.crypto.trust_levels import TrustLevel

    sig = SignatureBlock(
        alg="ed25519",
        signature="A" * 88,
        trust_level=TrustLevel.SELF_SIGNED,
    )
    signed = SignedManifest(manifest=_manifest(), signature=sig, public_key=None)
    return signed.model_dump_json()


@pytest.mark.asyncio
async def test_resolve_success_returns_resolved_agent() -> None:
    with (
        patch("asap.client.market.get_registry", new_callable=AsyncMock) as mock_get,
        patch("asap.client.market.verify_agent_trust") as mock_verify,
        patch("asap.client.market.is_revoked", new_callable=AsyncMock) as mock_revoked,
    ):
        mock_get.return_value = _lite_registry()
        mock_verify.return_value = True
        mock_revoked.return_value = False

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
        with patch("asap.client.market.httpx.AsyncClient", return_value=mock_http):
            client = MarketClient(registry_url="https://reg.example/registry.json")
            agent = await client.resolve(TEST_URN)

    assert isinstance(agent, ResolvedAgent)
    assert agent.manifest.id == TEST_URN
    assert agent.entry.id == TEST_URN
    mock_get.assert_awaited_once()
    mock_verify.assert_called_once()
    mock_revoked.assert_awaited_once_with(TEST_URN, revoked_url=None)


@pytest.mark.asyncio
async def test_resolve_urn_not_found_raises() -> None:
    from datetime import datetime, timezone

    empty_registry = LiteRegistry(
        version="1.0",
        updated_at=datetime.now(timezone.utc),
        agents=[],
    )
    with patch("asap.client.market.get_registry", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = empty_registry
        client = MarketClient(registry_url="https://reg.example/registry.json")
        with pytest.raises(ValueError, match="Agent not found in registry: urn:asap:agent:missing"):
            await client.resolve("urn:asap:agent:missing")
    mock_get.assert_awaited_once()


@pytest.mark.asyncio
async def test_resolve_invalid_signature_raises() -> None:
    with (
        patch("asap.client.market.get_registry", new_callable=AsyncMock) as mock_get,
        patch("asap.client.market.verify_agent_trust") as mock_verify,
    ):
        mock_get.return_value = _lite_registry()
        mock_verify.side_effect = SignatureVerificationError("invalid signature", {})

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
        with patch("asap.client.market.httpx.AsyncClient", return_value=mock_http):
            client = MarketClient(registry_url="https://reg.example/registry.json")
            with pytest.raises(SignatureVerificationError, match="invalid signature"):
                await client.resolve(TEST_URN)
    mock_verify.assert_called_once()


@pytest.mark.asyncio
async def test_resolve_revoked_raises() -> None:
    with (
        patch("asap.client.market.get_registry", new_callable=AsyncMock) as mock_get,
        patch("asap.client.market.verify_agent_trust") as mock_verify,
        patch("asap.client.market.is_revoked", new_callable=AsyncMock) as mock_revoked,
    ):
        mock_get.return_value = _lite_registry()
        mock_verify.return_value = True
        mock_revoked.return_value = True

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
        with patch("asap.client.market.httpx.AsyncClient", return_value=mock_http):
            client = MarketClient(registry_url="https://reg.example/registry.json")
            with pytest.raises(AgentRevokedException, match=TEST_URN):
                await client.resolve(TEST_URN)
    mock_revoked.assert_awaited_once()


@pytest.mark.asyncio
async def test_run_success_returns_result_dict() -> None:
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

    with patch("asap.client.market.ASAPClient", return_value=mock_transport):
        client = MarketClient()
        agent = ResolvedAgent(manifest=_manifest(), entry=_registry_entry(), client=client)
        payload = {
            "conversation_id": "conv-1",
            "skill_id": "echo",
            "input": {"message": "hello"},
        }
        result = await agent.run(payload)

    assert result == {"output": "done"}
    mock_send.assert_awaited_once()


@pytest.mark.asyncio
async def test_run_with_auth_token_accepts_parameter() -> None:
    task_response = TaskResponse(
        task_id="task-1",
        status="completed",
        result={"ok": True},
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

    with patch("asap.client.market.ASAPClient", return_value=mock_transport) as mock_ac:
        client = MarketClient()
        agent = ResolvedAgent(manifest=_manifest(), entry=_registry_entry(), client=client)
        result = await agent.run(
            {"conversation_id": "c", "skill_id": "echo", "input": {}},
            auth_token="secret-token",
        )
    assert result == {"ok": True}
    mock_ac.assert_called_once()
    call_kw = mock_ac.call_args[1]
    assert call_kw.get("auth_token") == "secret-token"


@pytest.mark.asyncio
async def test_run_uses_client_auth_token_when_run_auth_token_none() -> None:
    task_response = TaskResponse(
        task_id="task-1",
        status="completed",
        result={"ok": True},
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

    with patch("asap.client.market.ASAPClient", return_value=mock_transport) as mock_ac:
        client = MarketClient(auth_token="client-level-token")
        agent = ResolvedAgent(manifest=_manifest(), entry=_registry_entry(), client=client)
        await agent.run({"conversation_id": "c", "skill_id": "echo", "input": {}})
    mock_ac.assert_called_once()
    assert mock_ac.call_args[1].get("auth_token") == "client-level-token"


@pytest.mark.asyncio
async def test_resolve_429_then_200_succeeds() -> None:
    resp_429 = httpx.Response(
        429,
        headers={"Retry-After": "0"},
        request=httpx.Request("GET", TEST_MANIFEST_URL),
    )
    resp_200 = httpx.Response(
        200,
        text=_signed_manifest_json(),
        request=httpx.Request("GET", TEST_MANIFEST_URL),
    )
    mock_http = AsyncMock()
    mock_http.get = AsyncMock(side_effect=[resp_429, resp_200])
    mock_http.aclose = AsyncMock()
    mock_http.__aenter__ = AsyncMock(return_value=mock_http)
    mock_http.__aexit__ = AsyncMock(return_value=None)

    with (
        patch("asap.client.market.get_registry", new_callable=AsyncMock) as mock_get,
        patch("asap.client.market.verify_agent_trust") as mock_verify,
        patch("asap.client.market.is_revoked", new_callable=AsyncMock) as mock_revoked,
        patch("asap.client.market.httpx.AsyncClient", return_value=mock_http),
    ):
        mock_get.return_value = _lite_registry()
        mock_verify.return_value = True
        mock_revoked.return_value = False
        client = MarketClient(registry_url="https://reg.example/registry.json")
        agent = await client.resolve(TEST_URN)

    assert agent.manifest.id == TEST_URN
    assert mock_http.get.await_count == 2


@pytest.mark.asyncio
async def test_resolve_429_four_times_raises() -> None:
    resp_429 = httpx.Response(
        429,
        headers={"Retry-After": "1"},
        request=httpx.Request("GET", TEST_MANIFEST_URL),
    )
    mock_http = AsyncMock()
    mock_http.get = AsyncMock(return_value=resp_429)
    mock_http.aclose = AsyncMock()
    mock_http.__aenter__ = AsyncMock(return_value=mock_http)
    mock_http.__aexit__ = AsyncMock(return_value=None)

    with (
        patch("asap.client.market.get_registry", new_callable=AsyncMock) as mock_get,
        patch("asap.client.market.httpx.AsyncClient", return_value=mock_http),
        patch("asap.client.http_client.asyncio.sleep", new_callable=AsyncMock),
    ):
        mock_get.return_value = _lite_registry()
        client = MarketClient(registry_url="https://reg.example/registry.json")
        with pytest.raises(httpx.HTTPStatusError, match="429"):
            await client.resolve(TEST_URN)

    assert mock_http.get.await_count == 4
