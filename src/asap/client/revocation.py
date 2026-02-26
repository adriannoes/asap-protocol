"""Revocation check for SDK consumers.

Fetches revoked_agents.json and checks if an agent URN is revoked.
SEC-004, REV-003: SDK checks before run(); no caching.
"""

from __future__ import annotations

import os

import httpx
from pydantic import BaseModel, ConfigDict, Field

DEFAULT_REVOKED_URL = (
    "https://raw.githubusercontent.com/adriannoes/asap-protocol/main/revoked_agents.json"
)


class RevokedEntry(BaseModel):
    model_config = ConfigDict(extra="forbid")

    urn: str = Field(...)
    reason: str = Field(...)
    revoked_at: str = Field(...)


class RevokedAgentsList(BaseModel):
    model_config = ConfigDict(extra="forbid")

    revoked: list[RevokedEntry] = Field(default_factory=list)
    version: str = Field(default="1.0")


async def is_revoked(
    urn: str,
    revoked_url: str | None = None,
    transport: httpx.AsyncBaseTransport | None = None,
) -> bool:
    """Fetch revoked_agents.json (no cache) and return True if URN is in the list."""
    url = revoked_url or os.environ.get("ASAP_REVOKED_AGENTS_URL", DEFAULT_REVOKED_URL)
    if transport is not None:
        client = httpx.AsyncClient(transport=transport)
    else:
        client = httpx.AsyncClient()
    async with client as http_client:
        response = await http_client.get(url)
        response.raise_for_status()
    data = response.json()
    parsed = RevokedAgentsList.model_validate(data)
    return any(entry.urn == urn for entry in parsed.revoked)
