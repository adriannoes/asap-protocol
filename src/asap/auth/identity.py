"""Host and agent session models for per-runtime identity (Ed25519)."""

from __future__ import annotations

import base64
import hashlib
import json
from datetime import datetime, timedelta, timezone
from typing import Any, Literal, Protocol, runtime_checkable

from pydantic import Field

from asap.models.base import ASAPBaseModel

HostStatus = Literal["active", "pending", "revoked"]
AgentMode = Literal["delegated", "autonomous"]
AgentSessionStatus = Literal["pending", "active", "expired", "revoked"]


class HostIdentity(ASAPBaseModel):
    """Registered host identity for the agent JWT hierarchy."""

    host_id: str
    name: str | None = None
    public_key: dict[str, Any]
    user_id: str | None = None
    default_capabilities: list[str] = Field(default_factory=list)
    status: HostStatus
    created_at: datetime
    updated_at: datetime


@runtime_checkable
class HostStore(Protocol):
    """Persistence layer for registered host identities."""

    async def save(self, host: HostIdentity) -> None:
        """Persist or replace a host record."""
        ...

    async def get(self, host_id: str) -> HostIdentity | None:
        """Return the host by id, or None if missing."""
        ...

    async def get_by_public_key(self, thumbprint: str) -> HostIdentity | None:
        """Resolve a host by JWK thumbprint (RFC 7638 SHA-256)."""
        ...

    async def revoke(self, host_id: str) -> None:
        """Mark the host as revoked."""
        ...


class AgentSession(ASAPBaseModel):
    """Agent session bound to a host and a JWK public key."""

    agent_id: str
    host_id: str
    public_key: dict[str, Any]
    mode: AgentMode
    status: AgentSessionStatus
    session_ttl: timedelta | None = None
    max_lifetime: timedelta | None = None
    absolute_lifetime: timedelta | None = None
    activated_at: datetime | None = None
    last_used_at: datetime | None = None
    created_at: datetime


@runtime_checkable
class AgentStore(Protocol):
    """Persistence layer for agent sessions under a host."""

    async def save(self, agent: AgentSession) -> None:
        """Persist or replace an agent session."""
        ...

    async def get(self, agent_id: str) -> AgentSession | None:
        """Return the session by agent id, or None if missing."""
        ...

    async def list_by_host(self, host_id: str) -> list[AgentSession]:
        """List all agent sessions for a host."""
        ...

    async def revoke(self, agent_id: str) -> None:
        """Revoke a single agent session."""
        ...

    async def revoke_by_host(self, host_id: str) -> None:
        """Revoke every agent session belonging to the host."""
        ...


def jwk_thumbprint_sha256(public_key: dict[str, Any]) -> str:
    """RFC 7638 JWK thumbprint using SHA-256 (base64url, no padding)."""
    canonical = json.dumps(public_key, sort_keys=True, separators=(",", ":"))
    digest = hashlib.sha256(canonical.encode("utf-8")).digest()
    return base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class InMemoryHostStore:
    """In-memory `HostStore` for development and tests.

    Optionally cascades host revocation to an `AgentStore` when provided.
    """

    def __init__(self, agent_store: AgentStore | None = None) -> None:
        self._hosts: dict[str, HostIdentity] = {}
        self._thumb_to_host_id: dict[str, str] = {}
        self._agent_store = agent_store

    async def save(self, host: HostIdentity) -> None:
        """Persist or replace a host and refresh the thumbprint index."""
        previous = self._hosts.get(host.host_id)
        if previous is not None:
            old_tp = jwk_thumbprint_sha256(previous.public_key)
            new_tp = jwk_thumbprint_sha256(host.public_key)
            if old_tp != new_tp and self._thumb_to_host_id.get(old_tp) == host.host_id:
                del self._thumb_to_host_id[old_tp]
        thumb = jwk_thumbprint_sha256(host.public_key)
        self._thumb_to_host_id[thumb] = host.host_id
        self._hosts[host.host_id] = host

    async def get(self, host_id: str) -> HostIdentity | None:
        return self._hosts.get(host_id)

    async def get_by_public_key(self, thumbprint: str) -> HostIdentity | None:
        host_id = self._thumb_to_host_id.get(thumbprint)
        if host_id is None:
            return None
        return self._hosts.get(host_id)

    async def revoke(self, host_id: str) -> None:
        host = self._hosts.get(host_id)
        if host is None or host.status == "revoked":
            return
        now = _utc_now()
        updated = host.model_copy(update={"status": "revoked", "updated_at": now})
        self._hosts[host_id] = updated
        if self._agent_store is not None:
            await self._agent_store.revoke_by_host(host_id)


class InMemoryAgentStore:
    """In-memory `AgentStore` for development and tests."""

    def __init__(self) -> None:
        self._agents: dict[str, AgentSession] = {}

    async def save(self, agent: AgentSession) -> None:
        self._agents[agent.agent_id] = agent

    async def get(self, agent_id: str) -> AgentSession | None:
        return self._agents.get(agent_id)

    async def list_by_host(self, host_id: str) -> list[AgentSession]:
        return sorted(
            (a for a in self._agents.values() if a.host_id == host_id),
            key=lambda s: s.agent_id,
        )

    async def revoke(self, agent_id: str) -> None:
        agent = self._agents.get(agent_id)
        if agent is None or agent.status == "revoked":
            return
        self._agents[agent_id] = agent.model_copy(update={"status": "revoked"})

    async def revoke_by_host(self, host_id: str) -> None:
        for aid in [a.agent_id for a in self._agents.values() if a.host_id == host_id]:
            await self.revoke(aid)
