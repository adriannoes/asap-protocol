"""FastAPI entrypoint for the registry-bot service.

Mounts ``POST /registry/agents`` from :mod:`asap.registry.auto_registration` when the
monorepo package is installed. Adds :class:`~asap.auth.middleware.OAuth2Middleware`
when ``ASAP_AUTH_JWKS_URI`` is set (path ``/registry``). GitHub PR flow uses
``GITHUB_TOKEN`` + ``GITHUB_REPOSITORY`` via :class:`~asap.registry.bot_pr.BotPRSettings`.
"""

from __future__ import annotations

import os
import sys
from typing import Any

from fastapi import FastAPI
from fastapi.responses import JSONResponse


def _bot_settings_from_env() -> Any:
    """Build :class:`~asap.registry.bot_pr.BotPRSettings` or return ``None`` if unset."""
    from asap.registry.bot_pr import BotPRSettings

    repo = os.environ.get("GITHUB_REPOSITORY", "").strip()
    token = os.environ.get("GITHUB_TOKEN", "").strip()
    if not repo or "/" not in repo or not token:
        return None
    owner, name = repo.split("/", 1)
    base = os.environ.get("GITHUB_BASE_BRANCH", "main").strip() or "main"
    return BotPRSettings(owner=owner, repo=name, base_branch=base, github_token=token)


def create_app() -> FastAPI:
    """Build the FastAPI application."""
    app = FastAPI(
        title="ASAP Registry Bot",
        version="0.1.0",
        description="Lite Registry auto-registration HTTP service",
    )

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok", "service": "registry-bot"}

    try:
        from asap.auth.middleware import OAuth2Middleware
        from asap.registry.auto_registration import (
            REGISTRY_REGISTER_SCOPE,
            AutoRegistrationConfig,
            create_auto_registration_router,
        )
        from asap.registry.receipt_cache import create_registration_receipt_cache
        from asap.transport.rate_limit import create_registration_rate_limiter
    except ModuleNotFoundError:

        @app.post("/registry/agents")
        async def registration_unavailable() -> JSONResponse:
            return JSONResponse(
                status_code=503,
                content={
                    "detail": (
                        "asap.registry.auto_registration is not available. Install "
                        "asap-protocol from the monorepo (editable) or a release that "
                        "ships the registry package."
                    ),
                },
            )

        return app

    jwks_uri = os.environ.get("ASAP_AUTH_JWKS_URI", "").strip()
    if jwks_uri:
        app.add_middleware(
            OAuth2Middleware,
            jwks_uri=jwks_uri,
            required_scope=REGISTRY_REGISTER_SCOPE,
            path_prefix="/registry",
            manifest_id=None,
        )

    cfg = AutoRegistrationConfig(bot_settings=_bot_settings_from_env())
    app.state.registration_limiter = create_registration_rate_limiter()
    app.state.registration_receipt_cache = create_registration_receipt_cache()
    app.include_router(create_auto_registration_router(cfg))
    return app


app = create_app()


def run() -> None:
    """CLI entry: ``uv run registry-bot`` (uvicorn on ``REGISTRY_BOT_HOST`` / port)."""
    import uvicorn

    host = os.environ.get("REGISTRY_BOT_HOST", "0.0.0.0")
    port_s = os.environ.get("PORT", os.environ.get("REGISTRY_BOT_PORT", "8080"))
    try:
        port = int(port_s)
    except ValueError:
        sys.stderr.write(f"Invalid PORT/REGISTRY_BOT_PORT: {port_s!r}\n")
        raise SystemExit(2) from None
    uvicorn.run(
        "registry_bot.app:app",
        host=host,
        port=port,
        factory=False,
    )


__all__ = ["app", "create_app", "run"]
