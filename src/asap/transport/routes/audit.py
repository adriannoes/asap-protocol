"""Audit log route group: ``GET /audit``.

Queries the tamper-evident audit log when ``app.state.audit_store`` is set.
Unauthenticated by default (local/operator use). Pass ``require_auth=True``
from ``create_app(require_operator_auth=True)`` to require an OAuth2 Bearer JWT
with scope ``asap:admin``.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse

from asap.auth.scopes import SCOPE_ADMIN, require_scope
from asap.economics.audit import AuditStore


def create_audit_router(*, require_auth: bool = False) -> APIRouter:
    """Create the audit router with ``GET /audit`` (no-op when no store is set).

    Args:
        require_auth: When True, require OAuth2 claims with scope ``asap:admin``.
    """
    deps: list[Any] = []
    if require_auth:
        deps.append(Depends(require_scope(SCOPE_ADMIN)))
    router = APIRouter(tags=["audit"], dependencies=deps)

    @router.get("/audit")
    async def get_audit_log(
        request: Request,
        urn: str | None = None,
        start: str | None = None,
        end: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> JSONResponse:
        """Query the tamper-evident audit log."""
        store: AuditStore | None = getattr(request.app.state, "audit_store", None)
        if store is None:
            return JSONResponse(status_code=404, content={"detail": "audit not configured"})

        if limit < 0 or offset < 0:
            return JSONResponse(
                status_code=400,
                content={"detail": "limit and offset must be non-negative"},
            )

        try:
            start_dt = datetime.fromisoformat(start).replace(tzinfo=timezone.utc) if start else None
            end_dt = datetime.fromisoformat(end).replace(tzinfo=timezone.utc) if end else None
        except ValueError:
            return JSONResponse(
                status_code=400,
                content={"detail": "Invalid date format. Use ISO 8601 (e.g. 2026-01-01T00:00:00)"},
            )

        entries = await store.query(
            agent_urn=urn,
            start=start_dt,
            end=end_dt,
            limit=min(limit, 1000),
            offset=offset,
        )
        return JSONResponse(
            status_code=200,
            content={
                "entries": [e.model_dump(mode="json") for e in entries],
                "count": len(entries),
            },
        )

    return router


__all__ = ["create_audit_router"]
