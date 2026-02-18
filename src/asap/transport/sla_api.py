"""SLA REST API (v1.3). Requires sla_storage on app state.

**Security (v1.3):** This API is intended for local/operator use only. Endpoints
are unauthenticated by default. When exposing beyond localhost, configure
OAuth2 or network-level access controls. Rate limiting is applied per-client.
"""

from __future__ import annotations

from datetime import datetime
from typing import cast

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import JSONResponse

from asap.economics.sla import (
    SLADefinition,
    SLAMetrics,
    aggregate_sla_metrics,
    evaluate_breach_conditions,
    rolling_window_bounds,
)
from asap.economics.sla_storage import SLAStorage
from asap.models.entities import Manifest


def _rate_limit_sla(request: Request) -> None:
    """Apply rate limiting to SLA API endpoints (uses app.state.limiter)."""
    limiter = getattr(request.app.state, "limiter", None)
    if limiter is not None:
        limiter.check(request)


def get_sla_storage(request: Request) -> SLAStorage:
    storage = getattr(request.app.state, "sla_storage", None)
    if storage is None:
        from fastapi import HTTPException

        raise HTTPException(
            status_code=503,
            detail="SLA API not configured (sla_storage not set)",
        )
    return cast(SLAStorage, storage)


def get_manifest(request: Request) -> Manifest | None:
    """Return manifest from app state if set (for SLA compliance calculation)."""
    return getattr(request.app.state, "manifest", None)


def _compute_compliance_percent(
    sla: SLADefinition | None,
    metrics: SLAMetrics,
) -> float | None:
    """Compute compliance percentage: 100 if no breaches, else weighted by severity."""
    if sla is None:
        return None
    conditions = evaluate_breach_conditions(sla, metrics)
    if not conditions:
        return 100.0
    critical_count = sum(1 for c in conditions if c.severity == "critical")
    warning_count = sum(1 for c in conditions if c.severity == "warning")
    if critical_count > 0:
        return max(0.0, 100.0 - 25.0 * critical_count - 5.0 * warning_count)
    return max(0.0, 100.0 - 5.0 * warning_count)


def create_sla_router() -> APIRouter:
    """Create the SLA API router with GET /sla, /sla/history, /sla/breaches."""
    router = APIRouter(
        prefix="/sla",
        tags=["sla"],
        dependencies=[Depends(_rate_limit_sla)],
    )

    @router.get("")
    async def get_sla(
        agent_id: str | None = Query(default=None, description="Filter by agent"),
        window: str = Query(
            default="24h",
            description="Rolling window: 1h, 24h, 7d, 30d",
        ),
        storage: SLAStorage = Depends(get_sla_storage),
        manifest: Manifest | None = Depends(get_manifest),
    ) -> JSONResponse:
        """Current SLA status per agent with compliance percentage."""
        if window not in ("1h", "24h", "7d", "30d"):
            from fastapi import HTTPException

            raise HTTPException(
                status_code=400,
                detail="window must be one of: 1h, 24h, 7d, 30d",
            )
        start, end = rolling_window_bounds(window)
        metrics_list = await storage.query_metrics(
            agent_id=agent_id,
            start=start,
            end=end,
        )
        if not metrics_list:
            return JSONResponse(
                content={
                    "data": [],
                    "window": window,
                    "period_start": start.isoformat(),
                    "period_end": end.isoformat(),
                }
            )
        agents_seen: set[str] = set()
        results: list[dict] = []
        for m in metrics_list:
            if m.agent_id in agents_seen:
                continue
            agents_seen.add(m.agent_id)
            agent_metrics = [x for x in metrics_list if x.agent_id == m.agent_id]
            aggregated = aggregate_sla_metrics(agent_metrics)
            if aggregated is None:
                continue
            sla = manifest.sla if manifest and manifest.id == m.agent_id else None
            compliance = _compute_compliance_percent(sla, aggregated)
            results.append(
                {
                    "agent_id": m.agent_id,
                    "metrics": aggregated.model_dump(mode="json"),
                    "compliance_percent": compliance,
                }
            )
        return JSONResponse(
            content={
                "data": results,
                "window": window,
                "period_start": start.isoformat(),
                "period_end": end.isoformat(),
            }
        )

    @router.get("/history")
    async def get_sla_history(
        agent_id: str | None = Query(default=None, description="Filter by agent"),
        start: datetime | None = Query(default=None, description="Start of time range"),
        end: datetime | None = Query(default=None, description="End of time range"),
        limit: int | None = Query(default=100, ge=1, le=1000, description="Max records"),
        offset: int = Query(default=0, ge=0, description="Records to skip"),
        storage: SLAStorage = Depends(get_sla_storage),
    ) -> JSONResponse:
        """Historical SLA metrics with pagination."""
        metrics = await storage.query_metrics(
            agent_id=agent_id,
            start=start,
            end=end,
        )
        total = len(metrics)
        paginated = metrics[offset : offset + (limit or 100)]
        return JSONResponse(
            content={
                "data": [m.model_dump(mode="json") for m in paginated],
                "count": len(paginated),
                "total": total,
                "offset": offset,
                "limit": limit or 100,
            }
        )

    @router.get("/breaches")
    async def get_sla_breaches(
        agent_id: str | None = Query(default=None, description="Filter by agent"),
        severity: str | None = Query(
            default=None,
            description="Filter by severity: warning, critical",
        ),
        start: datetime | None = Query(default=None, description="Start of time range"),
        end: datetime | None = Query(default=None, description="End of time range"),
        storage: SLAStorage = Depends(get_sla_storage),
    ) -> JSONResponse:
        """List SLA breaches with optional filters."""
        if severity is not None and severity not in ("warning", "critical"):
            from fastapi import HTTPException

            raise HTTPException(
                status_code=400,
                detail="severity must be one of: warning, critical",
            )
        breaches = await storage.query_breaches(
            agent_id=agent_id,
            start=start,
            end=end,
        )
        if severity is not None:
            breaches = [b for b in breaches if b.severity == severity]
        return JSONResponse(
            content={
                "data": [b.model_dump(mode="json") for b in breaches],
                "count": len(breaches),
            }
        )

    return router
