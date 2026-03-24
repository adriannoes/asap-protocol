"""Agent lifecycle management — lifetime clocks, expiry, and reactivation.

Evaluates three independent clocks that govern agent session validity:

1. **Session TTL** — idle timeout since last use.
2. **Max lifetime** — wall-clock cap since activation.
3. **Absolute lifetime** — hard limit since creation (survives reactivation).

Public exports:
    check_agent_expiry: Evaluate the three clocks for an agent session.
    extend_session: Touch ``last_used_at`` to keep the session alive.
    reactivate_agent: Reset session/max clocks and decay capabilities.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal

from asap.auth.identity import AgentSession, HostIdentity

ExpiryStatus = Literal["active", "expired", "revoked"]


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def check_agent_expiry(agent: AgentSession) -> ExpiryStatus:
    """Evaluate the three lifetime clocks and return the resulting status.

    Clock precedence (most severe wins):
    - Absolute lifetime exceeded → ``"revoked"`` (permanent, no reactivation)
    - Max lifetime exceeded → ``"expired"``
    - Session TTL exceeded → ``"expired"``
    - Otherwise → ``"active"``
    """
    now = _utc_now()

    # Clock 3: absolute lifetime (hard limit since creation, irreversible)
    if agent.absolute_lifetime is not None and now - agent.created_at > agent.absolute_lifetime:
        return "revoked"

    # Clock 2: max lifetime (since activation)
    if (
        agent.max_lifetime is not None
        and agent.activated_at is not None
        and now - agent.activated_at > agent.max_lifetime
    ):
        return "expired"

    # Clock 1: session TTL (since last use)
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
    host: HostIdentity,
) -> AgentSession:
    """Reactivate an expired agent session.

    Resets the session TTL and max lifetime clocks by updating
    ``activated_at`` and ``last_used_at`` to now.  The absolute lifetime
    clock is **not** reset — if it has been exceeded, reactivation fails
    with :class:`ValueError`.

    Capability decay to host defaults is handled by the caller (endpoint
    layer), which has access to the :class:`CapabilityRegistry`.

    Raises:
        ValueError: If the absolute lifetime has been exceeded (permanent
            revocation) or the agent is already revoked.
    """
    now = _utc_now()

    if agent.status == "revoked":
        msg = f"Agent {agent.agent_id} is permanently revoked"
        raise ValueError(msg)

    # Absolute lifetime check — cannot reactivate past this
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
