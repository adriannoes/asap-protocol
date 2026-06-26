"""Health, readiness, metrics, and discovery route group.

Exposes liveness/readiness probes, the agent manifest, the well-known
health endpoint, and Prometheus metrics. These routes are unauthenticated
and read their dependencies (``manifest``, ``server_started_at``) from
``request.app.state``.
"""

from __future__ import annotations

import time

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, PlainTextResponse, Response

from asap.discovery import health as discovery_health
from asap.discovery import wellknown
from asap.models.entities import Manifest
from asap.observability import get_metrics


def create_health_router() -> APIRouter:
    """Create the health/discovery/metrics router.

    Registers ``GET /health``, ``GET /ready``,
    ``GET /.well-known/asap/manifest.json``, ``GET /.well-known/asap/health``,
    and ``GET /asap/metrics``. The manifest and well-known health endpoints
    require ``app.state.manifest`` to be set (always set by ``create_app``).
    """
    router = APIRouter(tags=["health"])

    @router.get("/health")
    async def health() -> JSONResponse:
        """Liveness probe: always OK if the process is running.

        Used by Kubernetes livenessProbe and Docker HEALTHCHECK.
        """
        return JSONResponse(status_code=200, content={"status": "ok"})

    @router.get("/ready")
    async def ready() -> JSONResponse:
        """Readiness probe: OK when the server is ready to accept traffic."""
        return JSONResponse(status_code=200, content={"status": "ok"})

    @router.get(wellknown.WELLKNOWN_MANIFEST_PATH)
    async def get_manifest(request: Request) -> Response:
        """Return the agent's manifest for discovery."""
        manifest: Manifest = request.app.state.manifest
        return await wellknown.get_manifest_response(manifest, request)

    @router.get(discovery_health.WELLKNOWN_HEALTH_PATH)
    async def get_wellknown_health(request: Request) -> JSONResponse:
        """Return agent health/liveness status (200 healthy, 503 unhealthy)."""
        manifest: Manifest = request.app.state.manifest
        started_at: float = request.app.state.server_started_at
        return await discovery_health.get_health_response_async(manifest, started_at)

    @router.get("/asap/metrics")
    async def get_metrics_endpoint() -> PlainTextResponse:
        """Return Prometheus-compatible metrics.

        Example:
            curl http://localhost:8000/asap/metrics
        """
        metrics = get_metrics()
        return PlainTextResponse(
            content=metrics.export_prometheus(),
            media_type="application/openmetrics-text; version=1.0.0; charset=utf-8",
        )

    return router


def monotonic_started_at() -> float:
    """Capture a monotonic start timestamp for the well-known health route."""
    return time.monotonic()


__all__ = ["create_health_router", "monotonic_started_at"]
