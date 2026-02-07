"""Scope-based authorization for ASAP Protocol.

Defines OAuth2 scope constants and a FastAPI dependency to enforce
required scopes on protected routes.
"""

from __future__ import annotations

from typing import Callable, cast

from fastapi import HTTPException, Request

from asap.auth.middleware import OAuth2Claims

# Scope constants for ASAP operations
SCOPE_READ = "asap:read"  # Query agent info (e.g. manifest, health)
SCOPE_EXECUTE = "asap:execute"  # Send task requests
SCOPE_ADMIN = "asap:admin"  # Manage agent (e.g. config, lifecycle)

HTTP_FORBIDDEN = 403
HTTP_UNAUTHORIZED = 401
ERROR_AUTH_REQUIRED = "Authentication required"
ERROR_INSUFFICIENT_SCOPE = "Insufficient scope"


def require_scope(scope: str) -> Callable[[Request], OAuth2Claims]:
    """FastAPI dependency factory: require a specific OAuth2 scope.

    Use as: Depends(require_scope(SCOPE_EXECUTE)).
    Returns the request's OAuth2Claims if the token has the required scope;
    raises 401 if no valid OAuth2 context, 403 if scope is missing.

    Args:
        scope: Required scope string (e.g. SCOPE_EXECUTE).

    Returns:
        A dependency callable that FastAPI will invoke with Request.

    Example:
        >>> from fastapi import Depends
        >>> from asap.auth.scopes import require_scope, SCOPE_EXECUTE
        >>>
        >>> @app.post("/asap")
        >>> async def handle_asap(
        ...     claims: OAuth2Claims = Depends(require_scope(SCOPE_EXECUTE)),
        ... ):
        ...     return {"sub": claims.sub}
    """

    def _dependency(request: Request) -> OAuth2Claims:
        claims = getattr(request.state, "oauth2_claims", None)
        if claims is None or not isinstance(claims, OAuth2Claims):
            raise HTTPException(
                status_code=HTTP_UNAUTHORIZED,
                detail=ERROR_AUTH_REQUIRED,
                headers={"WWW-Authenticate": "Bearer"},
            )
        if scope not in claims.scope:
            raise HTTPException(
                status_code=HTTP_FORBIDDEN,
                detail=ERROR_INSUFFICIENT_SCOPE,
            )
        return cast(OAuth2Claims, claims)

    return _dependency
