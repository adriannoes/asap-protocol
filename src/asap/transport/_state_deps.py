"""Typed FastAPI dependencies for ``app.state``-bound transport services.

Centralizes the ``getattr`` + ``HTTPException`` + ``cast`` boilerplate that the
REST/identity route families previously repeated inline. Two policies:

- ``rate_limiter`` is **optional**: a missing ``app.state.limiter`` is treated as
  "rate limiting disabled" (preserves the historic usage/SLA no-op fallback that
  ``tests/economics/test_usage_api.py::test_usage_api_ignores_missing_limiter``
  pins). It never raises 503.
- ``require_identity_limiter`` is **required**: a missing
  ``app.state.identity_limiter`` previously raised a bare ``AttributeError`` from
  ``request.app.state.identity_limiter.check(request)``; it now surfaces a clean
  503 so clients see a configured error instead of a 500.

``require_state`` is the shared helper both policies (and the ``*_api.py`` storage
dependencies) build on: read an attribute off ``app.state`` and raise a typed 503
with the supplied message when it is absent, returning the value cast to its
declared type for the caller.

Example:
    >>> from fastapi import Depends, APIRouter
    >>> from asap.transport._state_deps import require_identity_limiter
    >>> router = APIRouter()
    >>> @router.post("/asap/agent/register")
    ... async def register(_limiter: None = Depends(require_identity_limiter)) -> None:
    ...     ...
"""

from __future__ import annotations

from typing import Any, cast

from fastapi import HTTPException, Request

from asap.transport.rate_limit import ASAPRateLimiter


def require_state(request: Request, attr: str, message: str) -> Any:
    """Return ``request.app.state.<attr>`` or raise a clean 503.

    Replaces the repeated ``getattr`` + inline ``HTTPException`` + ``cast``
    pattern in the REST/identity route families. Raises 503 (not
    ``AttributeError``) when the attribute is missing so an incompletely
    configured server reports a typed error instead of a 500.

    Args:
        request: The FastAPI request carrying ``app.state``.
        attr: Name of the state attribute to read.
        message: 503 ``detail`` text when the attribute is absent.

    Returns:
        The state attribute value (untyped; callers narrow via ``cast`` at the
        typed dependency layer).
    """
    value = getattr(request.app.state, attr, None)
    if value is None:
        raise HTTPException(status_code=503, detail=message)
    return value


def rate_limiter(request: Request) -> ASAPRateLimiter | None:
    """Return the optional per-app rate limiter, or ``None`` when disabled.

    A missing ``app.state.limiter`` means rate limiting is intentionally off
    (the historic usage/SLA fallback); the dependency is a no-op in that case
    rather than a 503. Callers should still invoke ``limiter.check(request)``
    only when the return value is not ``None``.
    """
    return getattr(request.app.state, "limiter", None)


def require_identity_limiter(request: Request) -> ASAPRateLimiter:
    """Return the identity-route rate limiter, raising 503 if unconfigured.

    The identity endpoints (``/asap/agent/*``, ``/asap/capability/*``, and
    ``/asap/agent/request-capability``) previously called
    ``request.app.state.identity_limiter.check(request)`` inline, which raised
    ``AttributeError`` (surfacing as HTTP 500) when the limiter was not wired.
    This dependency converts that into a clean 503.

    Returns:
        The ``ASAPRateLimiter`` bound to ``app.state.identity_limiter``.
    """
    limiter = getattr(request.app.state, "identity_limiter", None)
    if limiter is None:
        raise HTTPException(
            status_code=503,
            detail="Identity rate limiter not configured (identity_limiter not set)",
        )
    return cast(ASAPRateLimiter, limiter)
