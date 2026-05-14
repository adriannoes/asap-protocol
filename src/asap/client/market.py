"""MarketClient and ResolvedAgent: resolve URN from registry, verify trust/revocation, run tasks (SDK-001, SDK-002)."""

from __future__ import annotations

import asyncio
from typing import Any

import httpx
from pydantic import Field

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
from asap.models.base import ASAPBaseModel
from asap.models.constants import ASAP_PROTOCOL_VERSION
from asap.models.envelope import Envelope
from asap.models.entities import Manifest
from asap.models.ids import generate_id
from asap.models.payloads import TaskRequest, TaskResponse
from asap.observability import get_logger
from asap.transport.client import ASAPClient

logger = get_logger(__name__)

# Default sender URN when SDK consumer does not identify as an agent.
DEFAULT_SENDER_URN: str = "urn:asap:agent:sdk-consumer"


class AgentSummary(ASAPBaseModel):
    """Agent discovery summary from registry."""

    urn: str = Field(..., description="Agent URN")
    name: str = Field(..., description="Agent name")
    skill_ids: list[str] = Field(default_factory=list, description="Skill IDs from registry")


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
    """Resolve agent URNs from the Lite Registry (cached), validate manifests, check revocation, run tasks."""

    def __init__(
        self,
        registry_url: str = DEFAULT_REGISTRY_URL,
        revoked_url: str | None = None,
        auth_token: str | None = None,
        sender_urn: str = DEFAULT_SENDER_URN,
        registry_cache_ttl_seconds: int | None = None,
    ) -> None:
        self.registry_url = registry_url
        self.revoked_url = revoked_url
        self.auth_token = auth_token
        self.sender_urn = sender_urn
        self._registry_cache_ttl = registry_cache_ttl_seconds

    async def resolve(self, urn: str) -> "ResolvedAgent":
        """Fetch registry, manifest, validate trust and revocation; return ResolvedAgent. Raises ValueError, SignatureVerificationError, AgentRevokedException, or httpx.HTTPStatusError."""
        logger.info("resolve_start", urn=urn, registry_url=self.registry_url)
        registry = await get_registry(self.registry_url, ttl_seconds=self._registry_cache_ttl)
        entry = find_by_id(registry, urn)
        if entry is None:
            raise ValueError(f"Agent not found in registry: {urn}")

        manifest_url = _manifest_url_from_entry(entry)
        async with httpx.AsyncClient() as client:
            response = await get_with_429_retry(client, manifest_url)
            response.raise_for_status()
            signed = SignedManifest.model_validate_json(response.text)

        _, revoked = await asyncio.gather(
            asyncio.to_thread(verify_agent_trust, signed),
            is_revoked(urn, revoked_url=self.revoked_url),
        )
        if revoked:
            logger.warning("agent_revoked", urn=urn)
            raise AgentRevokedException(urn)

        logger.info("resolve_success", urn=urn, manifest_id=signed.manifest.id)
        return ResolvedAgent(manifest=signed.manifest, entry=entry, client=self)

    async def list_agents(self) -> list[AgentSummary]:
        """List agents from registry (no manifest fetch). Use resolve(urn) for full manifest."""
        registry = await get_registry(self.registry_url, ttl_seconds=self._registry_cache_ttl)
        return [AgentSummary(urn=e.id, name=e.name, skill_ids=e.skills) for e in registry.agents]


class ResolvedAgent:
    """Verified agent from resolve(); use .run() to send task requests."""

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
        """Send a ``task.request`` envelope and return the ``TaskResponse.result`` dict.

        Contract (v2.2.1, formalizing PR-73 follow-up):

        - The remote agent MUST respond with a ``task.response`` envelope whose payload is a
          :class:`~asap.models.payloads.TaskResponse`. The ``result`` field is returned as a
          ``dict[str, Any]``; when the server leaves ``result`` unset (``None``), an empty dict
          is returned so callers can safely index into it.
        - If the response payload is **not** a ``TaskResponse``, a :class:`TypeError` is raised
          so protocol violations surface at the call site instead of being silently coerced
          into a dict. Callers that need the full envelope (status, ``task_id``, metrics,
          ``final_state``) should use :class:`~asap.transport.client.ASAPClient` directly.

        Args:
            payload: The ``TaskRequest`` payload as a plain dict (validated before sending).
            auth_token: Optional bearer token override; falls back to the client default.

        Returns:
            The unwrapped ``TaskResponse.result`` dict (possibly empty).
        """
        task_request = TaskRequest.model_validate(payload)
        sender = self.client.sender_urn
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
        if not isinstance(resp_payload, TaskResponse):
            raise TypeError(
                f"expected TaskResponse payload from {self.entry.id}, "
                f"got {type(resp_payload).__name__}"
            )
        return resp_payload.result or {}
