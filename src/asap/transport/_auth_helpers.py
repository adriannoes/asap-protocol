"""Shared authentication helpers for transport route modules."""

from __future__ import annotations

from typing import Any

from fastapi import Request
from fastapi.responses import JSONResponse

from asap.auth.agent_jwt import (
    HOST_REVOKED_ERROR,
    JwtVerifyResult,
    verify_host_jwt,
)
from asap.auth.identity import HostStore
from asap.auth.jti_replay_cache import JtiReplayCacheProtocol

# ``identity_host_store`` and ``identity_jwt_audience`` are attached to
# ``app.state`` by :func:`asap.transport.server.create_app`; read at call time
# so the helper stays decoupled from the server factory.
_HOST_STORE_ATTR = "identity_host_store"
_JWT_AUDIENCE_ATTR = "identity_jwt_audience"


def bearer_token_from_request(request: Request) -> str | None:
    """Return raw Bearer token from the ``Authorization`` header, if present."""
    auth = request.headers.get("Authorization")
    if not auth or not auth.startswith("Bearer "):
        return None
    return auth[7:].strip() or None


async def verify_host_bearer(
    request: Request,
    *,
    jti_replay_cache: JtiReplayCacheProtocol | None,
    require_active_host: bool = True,
    record_jti: bool = True,
) -> tuple[JwtVerifyResult | None, JSONResponse | None]:
    """Verify a Host JWT Bearer token and enforce host liveness.

    Single canonical Host-JWT verifier for the transport package. Mirrors the
    strict behaviour previously inlined in ``agent_routes``: 401 when no token
    or signature/claim verification fails, 400 on a missing ``iss`` claim, and
    403 when the resolved host is ``revoked`` (gated by ``require_active_host``
    so non-identity routes can opt out if needed). Pass ``record_jti=False`` to
    perform a read-only replay check against ``jti_replay_cache`` without
    consuming the token for subsequent polling requests.

    Returns ``(result, None)`` on success or ``(None, JSONResponse)`` on
    failure. Callers should propagate the error response unchanged.

    Example:
        >>> result, err = await verify_host_bearer(
        ...     request, jti_replay_cache=cache
        ... )
        >>> if err is not None:
        ...     return err
    """
    token = bearer_token_from_request(request)
    if not token:
        return None, JSONResponse(
            status_code=401,
            content={"detail": "Authentication required"},
            headers={"WWW-Authenticate": "Bearer"},
        )

    host_store: HostStore = getattr(request.app.state, _HOST_STORE_ATTR)
    expected_audience: str | list[str] = getattr(request.app.state, _JWT_AUDIENCE_ATTR)
    result = await verify_host_jwt(
        token,
        host_store,
        expected_audience=expected_audience,
        jti_replay_cache=jti_replay_cache,
        record_jti=record_jti,
    )
    if not result.ok:
        # ``verify_host_jwt`` short-circuits revoked hosts to ``ok=False`` with
        # ``error == HOST_REVOKED_ERROR`` before we can inspect ``result.host``
        # (which is left ``None``); surface that as 403 (not 401) so a revoked
        # HOST is rejected with the same status the strict verifier returned for
        # the agent-identity routes. The shared constant avoids a fragile literal
        # match across modules (CR#7).
        if require_active_host and result.error == HOST_REVOKED_ERROR:
            return None, JSONResponse(status_code=403, content={"detail": "host revoked"})
        return None, JSONResponse(
            status_code=401,
            content={"detail": result.error or "Invalid host token"},
        )

    claims: dict[str, Any] | None = result.claims
    if claims is None:
        return None, JSONResponse(status_code=401, content={"detail": "Invalid host token"})

    iss = claims.get("iss")
    if not isinstance(iss, str) or not iss.strip():
        return None, JSONResponse(
            status_code=400,
            content={"detail": "missing iss in host JWT"},
        )

    # Defensive re-check: a future ``verify_host_jwt`` change that returns a
    # revoked host with ``ok=True`` must still be rejected here.
    if require_active_host:
        host = result.host
        if host is not None and host.status == "revoked":
            return None, JSONResponse(status_code=403, content={"detail": "host revoked"})

    return result, None
