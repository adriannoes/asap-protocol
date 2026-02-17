"""Usage metering REST API (v1.3). Requires metering_storage on app state."""

from __future__ import annotations

import csv
from typing import cast
import io
from datetime import datetime

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import JSONResponse, PlainTextResponse, Response
from pydantic import ValidationError

from asap.economics import BatchUsageRequest, MeteringQuery, UsageMetrics
from asap.economics.storage import MeteringStorage


def get_metering_storage(request: Request) -> MeteringStorage:
    storage = getattr(request.app.state, "metering_storage", None)
    if storage is None:
        from fastapi import HTTPException

        raise HTTPException(
            status_code=503,
            detail="Usage API not configured (metering_storage not set)",
        )
    return cast(MeteringStorage, storage)


def create_usage_router() -> APIRouter:
    router = APIRouter(prefix="/usage", tags=["usage"])

    @router.get("")
    async def get_usage(
        agent_id: str | None = Query(default=None, description="Filter by agent"),
        consumer_id: str | None = Query(default=None, description="Filter by consumer"),
        task_id: str | None = Query(default=None, description="Filter by task"),
        start: datetime | None = Query(default=None, description="Start of time range"),
        end: datetime | None = Query(default=None, description="End of time range"),
        limit: int | None = Query(default=None, ge=1, le=1000, description="Max events"),
        offset: int = Query(default=0, ge=0, description="Events to skip"),
        storage: MeteringStorage = Depends(get_metering_storage),
    ) -> JSONResponse:
        filters = MeteringQuery(
            agent_id=agent_id,
            consumer_id=consumer_id,
            task_id=task_id,
            start=start,
            end=end,
            limit=limit,
            offset=offset,
        )
        events = storage.query(filters)
        return JSONResponse(
            content={
                "data": [e.model_dump(mode="json") for e in events],
                "count": len(events),
            }
        )

    @router.get("/aggregate")
    async def get_usage_aggregate(
        group_by: str = Query(
            ...,
            description="Group by: agent, consumer, day, week",
        ),
        agent_id: str | None = Query(default=None, description="Filter by agent"),
        consumer_id: str | None = Query(default=None, description="Filter by consumer"),
        start: datetime | None = Query(default=None, description="Start of time range"),
        end: datetime | None = Query(default=None, description="End of time range"),
        storage: MeteringStorage = Depends(get_metering_storage),
    ) -> JSONResponse:
        if group_by not in ("agent", "consumer", "day", "week"):
            from fastapi import HTTPException

            raise HTTPException(
                status_code=400,
                detail="group_by must be one of: agent, consumer, day, week",
            )
        filters = (
            MeteringQuery(agent_id=agent_id, consumer_id=consumer_id, start=start, end=end)
            if any((agent_id, consumer_id, start, end))
            else None
        )
        aggs = storage.aggregate(group_by, filters=filters)
        return JSONResponse(
            content={
                "group_by": group_by,
                "data": [a.model_dump(mode="json") for a in aggs],
            }
        )

    @router.get("/summary")
    async def get_usage_summary(
        agent_id: str | None = Query(default=None, description="Filter by agent"),
        consumer_id: str | None = Query(default=None, description="Filter by consumer"),
        start: datetime | None = Query(default=None, description="Start of time range"),
        end: datetime | None = Query(default=None, description="End of time range"),
        storage: MeteringStorage = Depends(get_metering_storage),
    ) -> JSONResponse:
        filters = (
            MeteringQuery(
                agent_id=agent_id,
                consumer_id=consumer_id,
                start=start,
                end=end,
            )
            if any((agent_id, consumer_id, start, end))
            else None
        )
        summary = storage.summary(filters=filters)
        return JSONResponse(content=summary.model_dump(mode="json"))

    @router.post("")
    async def post_usage(
        request: Request,
        storage: MeteringStorage = Depends(get_metering_storage),
    ) -> JSONResponse:
        body = await request.json()
        try:
            metrics = UsageMetrics.model_validate(body)
        except ValidationError as e:
            from fastapi import HTTPException

            raise HTTPException(status_code=400, detail=str(e)) from e
        storage.record(metrics)
        return JSONResponse(
            status_code=201,
            content={"status": "recorded", "task_id": metrics.task_id},
        )

    @router.post("/batch")
    async def post_usage_batch(
        request: Request,
        storage: MeteringStorage = Depends(get_metering_storage),
    ) -> JSONResponse:
        body = await request.json()
        try:
            batch = BatchUsageRequest.model_validate(body)
        except ValidationError as e:
            from fastapi import HTTPException

            raise HTTPException(status_code=400, detail=str(e)) from e
        for metrics in batch.events:
            storage.record(metrics)
        return JSONResponse(
            status_code=201,
            content={
                "status": "recorded",
                "count": len(batch.events),
                "task_ids": [e.task_id for e in batch.events],
            },
        )

    @router.get("/agents")
    async def get_usage_agents(
        agent_id: str | None = Query(default=None, description="Filter by agent"),
        consumer_id: str | None = Query(default=None, description="Filter by consumer"),
        start: datetime | None = Query(default=None, description="Start of time range"),
        end: datetime | None = Query(default=None, description="End of time range"),
        storage: MeteringStorage = Depends(get_metering_storage),
    ) -> JSONResponse:
        filters = (
            MeteringQuery(
                agent_id=agent_id,
                consumer_id=consumer_id,
                start=start,
                end=end,
            )
            if any((agent_id, consumer_id, start, end))
            else None
        )
        aggs = storage.aggregate("agent", filters=filters)
        return JSONResponse(
            content={
                "data": [a.model_dump(mode="json") for a in aggs],
            }
        )

    @router.get("/consumers")
    async def get_usage_consumers(
        agent_id: str | None = Query(default=None, description="Filter by agent"),
        consumer_id: str | None = Query(default=None, description="Filter by consumer"),
        start: datetime | None = Query(default=None, description="Start of time range"),
        end: datetime | None = Query(default=None, description="End of time range"),
        storage: MeteringStorage = Depends(get_metering_storage),
    ) -> JSONResponse:
        filters = (
            MeteringQuery(
                agent_id=agent_id,
                consumer_id=consumer_id,
                start=start,
                end=end,
            )
            if any((agent_id, consumer_id, start, end))
            else None
        )
        aggs = storage.aggregate("consumer", filters=filters)
        return JSONResponse(
            content={
                "data": [a.model_dump(mode="json") for a in aggs],
            }
        )

    @router.get("/stats")
    async def get_usage_stats(
        storage: MeteringStorage = Depends(get_metering_storage),
    ) -> JSONResponse:
        stats = storage.stats()
        return JSONResponse(content=stats.model_dump(mode="json"))

    @router.post("/purge")
    async def post_usage_purge(
        storage: MeteringStorage = Depends(get_metering_storage),
    ) -> JSONResponse:
        removed = storage.purge_expired()
        return JSONResponse(
            content={"status": "purged", "removed": removed},
        )

    @router.post("/validate")
    async def post_usage_validate(request: Request) -> JSONResponse:
        body = await request.json()
        try:
            metrics = UsageMetrics.model_validate(body)
            return JSONResponse(
                content={
                    "valid": True,
                    "task_id": metrics.task_id,
                    "agent_id": metrics.agent_id,
                    "consumer_id": metrics.consumer_id,
                },
            )
        except Exception as e:
            return JSONResponse(
                status_code=200,
                content={"valid": False, "error": str(e)},
            )

    @router.get("/export")
    async def export_usage(
        format: str = Query(default="json", description="Export format: json or csv"),
        agent_id: str | None = Query(default=None),
        consumer_id: str | None = Query(default=None),
        start: datetime | None = Query(default=None),
        end: datetime | None = Query(default=None),
        limit: int | None = Query(default=10000, ge=1, le=100000),
        storage: MeteringStorage = Depends(get_metering_storage),
    ) -> Response:
        filters = MeteringQuery(
            agent_id=agent_id,
            consumer_id=consumer_id,
            start=start,
            end=end,
            limit=limit,
        )
        events = storage.query(filters)
        if format == "csv":
            output = io.StringIO()
            writer = csv.writer(output)
            writer.writerow(
                [
                    "task_id",
                    "agent_id",
                    "consumer_id",
                    "tokens_in",
                    "tokens_out",
                    "duration_ms",
                    "api_calls",
                    "timestamp",
                ]
            )
            for e in events:
                writer.writerow(
                    [
                        e.task_id,
                        e.agent_id,
                        e.consumer_id,
                        e.tokens_in,
                        e.tokens_out,
                        e.duration_ms,
                        e.api_calls,
                        e.timestamp.isoformat(),
                    ]
                )
            return PlainTextResponse(
                content=output.getvalue(),
                media_type="text/csv",
                headers={"Content-Disposition": "attachment; filename=usage_export.csv"},
            )
        return JSONResponse(
            content={"data": [e.model_dump(mode="json") for e in events]},
            headers={"Content-Disposition": "attachment; filename=usage_export.json"},
        )

    return router
