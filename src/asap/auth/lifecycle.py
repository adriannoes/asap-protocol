"""Agent session expiry (session TTL, max lifetime, absolute lifetime) and reactivation."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal

from asap.auth.identity import AgentSession, HostIdentity

ExpiryStatus = Literal["active", "expired", "revoked"]


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def check_agent_expiry(agent: AgentSession) -> ExpiryStatus:
    """Return ``active``, ``expired``, or ``revoked`` (absolute limit exceeded)."""
    now = _utc_now()

    if agent.absolute_lifetime is not None and now - agent.created_at > agent.absolute_lifetime:
        return "revoked"

    if (
        agent.max_lifetime is not None
        and agent.activated_at is not None
        and now - agent.activated_at > agent.max_lifetime
    ):
        return "expired"

    if (
        agent.session_ttl is not None
        and agent.last_used_at is not None
        and now - agent.last_used_at > agent.session_ttl
    ):
        return "expired"

    return "active"


def extend_session(agent: AgentSession) -> AgentSession:
    """Update ``last_used_at`` to now, keeping the session alive."""
    return agent.model_copy(update={"last_used_at": _utc_now()})


def reactivate_agent(
    agent: AgentSession,
    _host: HostIdentity,
) -> AgentSession:
    """Reset activation and last-used time; fail if revoked or past absolute lifetime."""
    now = _utc_now()

    if agent.status == "revoked":
        msg = f"Agent {agent.agent_id} is permanently revoked"
        raise ValueError(msg)

    if agent.absolute_lifetime is not None and now - agent.created_at > agent.absolute_lifetime:
        msg = f"Agent {agent.agent_id} has exceeded absolute lifetime; reactivation is not possible"
        raise ValueError(msg)

    return agent.model_copy(
        update={
            "status": "active",
            "activated_at": now,
            "last_used_at": now,
        }
    )
