"""JWT extraction helpers for MCP Auth Bridge (v2.5.0)."""

from __future__ import annotations

import os

from asap.mcp.protocol import CallToolRequestParams

_META_JWT_KEY = "asap_agent_jwt"
_ENV_JWT_KEY = "ASAP_AGENT_JWT"


def default_jwt_extractor(
    params: CallToolRequestParams,
    *,
    allow_env_fallback: bool = False,
) -> str | None:
    """Extract Agent JWT from ``tools/call`` params or optional dev-only environment.

    Reads ``params.meta["asap_agent_jwt"]`` (MCP ``_meta`` field). When
    ``allow_env_fallback`` is ``True``, falls back to ``ASAP_AGENT_JWT`` for
    single-agent local testing only.

    Args:
        params: Parsed ``tools/call`` request parameters.
        allow_env_fallback: When ``True``, read ``ASAP_AGENT_JWT`` if meta is absent.
            Defaults to ``False`` so production cannot inherit a process-wide token.

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

    if not allow_env_fallback:
        return None

    env_token = os.environ.get(_ENV_JWT_KEY)
    if isinstance(env_token, str) and env_token.strip():
        return env_token.strip()

    return None
