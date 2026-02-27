"""MarketClient and ResolvedAgent: resolve URN from registry, verify trust/revocation, run tasks (SDK-001, SDK-002)."""

from __future__ import annotations

from typing import Any

import httpx

from asap.client.cache import get_registry
from asap.client.http_client import get_with_429_retry
from asap.client.revocation import is_revoked
from asap.client.trust import verify_agent_trust
from asap.crypto.models import SignedManifest
from asap.discovery.registry import (
    DEFAULT_REGISTRY_URL,
    RegistryEntry,
    find_by_id,
)
from asap.discovery.wellknown import WELLKNOWN_MANIFEST_PATH
from asap.errors import AgentRevokedException
from asap.models.constants import ASAP_PROTOCOL_VERSION
from asap.models.envelope import Envelope
from asap.models.entities import Manifest
from asap.models.ids import generate_id
from asap.models.payloads import TaskRequest
from asap.transport.client import ASAPClient

# Default sender URN when SDK consumer does not identify as an agent.
DEFAULT_SENDER_URN: str = "urn:asap:agent:sdk-consumer"


def _manifest_url_from_entry(entry: RegistryEntry) -> str:
    manifest = entry.endpoints.get("manifest")
    if manifest:
        return manifest
    http_base = entry.endpoints.get("http")
    if not http_base:
        raise ValueError(
            f"Registry entry {entry.id} has no 'manifest' or 'http' endpoint. "
            f"endpoints={list(entry.endpoints.keys())}"
        )
    return http_base.rstrip("/") + WELLKNOWN_MANIFEST_PATH


class MarketClient:
    def __init__(
        self,
        registry_url: str = DEFAULT_REGISTRY_URL,
        revoked_url: str | None = None,
        auth_token: str | None = None,
    ) -> None:
        self.registry_url = registry_url
        self.revoked_url = revoked_url
        self.auth_token = auth_token

    async def resolve(self, urn: str) -> "ResolvedAgent":
        registry = await get_registry(self.registry_url)
        entry = find_by_id(registry, urn)
        if entry is None:
            raise ValueError(f"Agent not found in registry: {urn}")

        manifest_url = _manifest_url_from_entry(entry)
        client = httpx.AsyncClient()
        try:
            response = await get_with_429_retry(client, manifest_url)
            response.raise_for_status()
            signed = SignedManifest.model_validate_json(response.text)
        finally:
            await client.aclose()

        verify_agent_trust(signed)

        revoked = await is_revoked(urn, revoked_url=self.revoked_url)
        if revoked:
            raise AgentRevokedException(urn)

        return ResolvedAgent(manifest=signed.manifest, entry=entry, client=self)


class ResolvedAgent:
    def __init__(
        self,
        manifest: Manifest,
        entry: RegistryEntry,
        client: MarketClient,
    ) -> None:
        self.manifest = manifest
        self.entry = entry
        self.client = client

    async def run(
        self,
        payload: dict[str, Any],
        auth_token: str | None = None,
    ) -> dict[str, Any]:
        task_request = TaskRequest.model_validate(payload)
        sender = DEFAULT_SENDER_URN
        envelope = Envelope(
            asap_version=ASAP_PROTOCOL_VERSION,
            sender=sender,
            recipient=self.manifest.id,
            payload_type="task.request",
            payload=task_request,
            correlation_id=generate_id(),
        )

        http_endpoint = self.entry.endpoints.get("http")
        if not http_endpoint:
            raise ValueError(f"Agent {self.entry.id} has no 'http' endpoint; cannot run task.")

        token = auth_token if auth_token is not None else self.client.auth_token
        async with ASAPClient(http_endpoint, auth_token=token) as transport:
            response_envelope = await transport.send(envelope)

        resp_payload = response_envelope.payload
        if hasattr(resp_payload, "result") and resp_payload.result is not None:
            return resp_payload.result
        if hasattr(resp_payload, "model_dump"):
            return resp_payload.model_dump()
        return dict(resp_payload) if isinstance(resp_payload, dict) else {"result": resp_payload}
