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
    http_client: httpx.AsyncClient | None = None,
) -> bool:
    """Fetch revoked list (no cache); True if URN revoked. Optional http_client for pooling (Sprint E2: wrap HTTPStatusError in ASAPError)."""
    url = revoked_url or os.environ.get("ASAP_REVOKED_AGENTS_URL", DEFAULT_REVOKED_URL)
    client = http_client or httpx.AsyncClient()
    to_close = None if http_client is not None else client
    try:
        response = await client.get(url)
        response.raise_for_status()
    finally:
        if to_close is not None:
            await to_close.aclose()
    payload = response.json()
    return any(e.get("urn") == urn for e in payload.get("revoked", []))
