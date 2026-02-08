"""Health endpoint handler for ASAP agent liveness detection.

Serves GET /.well-known/asap/health for agent health/liveness checks.
"""

from __future__ import annotations

import time

from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from asap.models.constants import ASAP_PROTOCOL_VERSION
from asap.models.entities import Manifest

WELLKNOWN_HEALTH_PATH = "/.well-known/asap/health"
"""Standard path for the ASAP agent health endpoint (RFC 8615 well-known)."""

CONTENT_TYPE_JSON = "application/json"
"""Content-Type for health JSON response."""

STATUS_HEALTHY = "healthy"
STATUS_UNHEALTHY = "unhealthy"


class HealthLoad(BaseModel):
    """Optional load metrics for health response.

    Attributes:
        active_tasks: Number of tasks currently being processed.
        queue_depth: Number of tasks waiting in queue.
    """

    active_tasks: int = Field(default=0, ge=0, description="Tasks currently being processed")
    queue_depth: int = Field(default=0, ge=0, description="Tasks waiting in queue")


class HealthStatus(BaseModel):
    """Response model for GET /.well-known/asap/health.

    Attributes:
        status: "healthy" or "unhealthy".
        agent_id: Agent URN from manifest.
        version: Agent semantic version.
        asap_version: ASAP protocol version supported.
        uptime_seconds: Seconds since server start.
        load: Optional load metrics (active_tasks, queue_depth).
    """

    status: str = Field(..., description="healthy or unhealthy")
    agent_id: str = Field(..., description="Agent URN")
    version: str = Field(..., description="Agent semantic version")
    asap_version: str = Field(default=ASAP_PROTOCOL_VERSION, description="ASAP protocol version")
    uptime_seconds: float = Field(..., ge=0, description="Seconds since server start")
    load: HealthLoad | None = Field(default=None, description="Optional load metrics")


def compute_uptime_seconds(started_at: float) -> float:
    """Compute uptime in seconds from a start timestamp.

    Args:
        started_at: Unix timestamp (from time.time()) when server started.

    Returns:
        Uptime in seconds.
    """
    return max(0.0, time.time() - started_at)


def get_health_response(
    manifest: Manifest,
    started_at: float,
    *,
    is_healthy: bool = True,
    load: HealthLoad | None = None,
) -> tuple[HealthStatus, int]:
    """Build health status and HTTP status code for GET /.well-known/asap/health.

    Returns a tuple of (HealthStatus model, status_code). Use 200 for healthy,
    503 for unhealthy (e.g., when agent marks itself as degraded).

    Args:
        manifest: The agent's manifest (for agent_id, version).
        started_at: Unix timestamp when server started (for uptime_seconds).
        is_healthy: Whether the agent considers itself healthy. If False, returns 503.
        load: Optional load metrics (active_tasks, queue_depth).

    Returns:
        Tuple of (HealthStatus, status_code) where status_code is 200 or 503.
    """
    status = STATUS_HEALTHY if is_healthy else STATUS_UNHEALTHY
    uptime = compute_uptime_seconds(started_at)
    health = HealthStatus(
        status=status,
        agent_id=manifest.id,
        version=manifest.version,
        asap_version=manifest.capabilities.asap_version,
        uptime_seconds=round(uptime, 2),
        load=load,
    )
    status_code = 200 if is_healthy else 503
    return health, status_code


def build_health_json_response(
    manifest: Manifest,
    started_at: float,
    *,
    is_healthy: bool = True,
    load: HealthLoad | None = None,
) -> tuple[dict[str, object], int]:
    """Build health JSON body and HTTP status code for the health endpoint."""
    health, status_code = get_health_response(
        manifest, started_at, is_healthy=is_healthy, load=load
    )
    body = health.model_dump()
    return body, status_code


async def get_health_response_async(
    manifest: Manifest,
    started_at: float,
    *,
    is_healthy: bool = True,
    load: HealthLoad | None = None,
) -> JSONResponse:
    """Return FastAPI JSONResponse for GET /.well-known/asap/health."""
    body, status_code = build_health_json_response(
        manifest, started_at, is_healthy=is_healthy, load=load
    )
    return JSONResponse(content=body, status_code=status_code, media_type=CONTENT_TYPE_JSON)
