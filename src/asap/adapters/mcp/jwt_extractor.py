"""JWT extraction helpers for MCP Auth Bridge (v2.5.0)."""

from __future__ import annotations

import os

from asap.mcp.protocol import CallToolRequestParams

_META_JWT_KEY = "asap_agent_jwt"
_ENV_JWT_KEY = "ASAP_AGENT_JWT"


def default_jwt_extractor(params: CallToolRequestParams) -> str | None:
    """Extract Agent JWT from ``tools/call`` params or dev-only environment.

    Reads ``params.meta["asap_agent_jwt"]`` (MCP ``_meta`` field). Falls back to
    ``ASAP_AGENT_JWT`` environment variable for single-agent local testing only.

    Args:
        params: Parsed ``tools/call`` request parameters.

    Returns:
        Stripped JWT string, or ``None`` when no token is present.

    Example:
        >>> from asap.mcp.protocol import CallToolRequestParams
        >>> params = CallToolRequestParams.model_validate(
        ...     {"name": "t", "_meta": {"asap_agent_jwt": "  token  "}}
        ... )
        >>> default_jwt_extractor(params)
        'token'
    """
    meta = params.meta or {}
    token = meta.get(_META_JWT_KEY)
    if isinstance(token, str) and token.strip():
        return token.strip()

    env_token = os.environ.get(_ENV_JWT_KEY)
    if isinstance(env_token, str) and env_token.strip():
        return env_token.strip()

    return None
