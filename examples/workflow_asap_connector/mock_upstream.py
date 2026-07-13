"""Mock n8n/Activepieces-style workflow HTTP API for the offline demo and tests."""

from __future__ import annotations

import re

import httpx

# Exact one-segment workflow id (excludes /workflows/{id}/trigger).
_GET_WORKFLOW_BY_ID = re.compile(r"^/api/v1/workflows/[^/]+$")


def mock_workflow_upstream(request: httpx.Request) -> httpx.Response:
    """Respond to workflow mock paths without contacting a live SaaS.

    Example::

        transport = httpx.MockTransport(mock_workflow_upstream)
        async with httpx.AsyncClient(transport=transport) as http:
            ...
    """
    path = request.url.path.rstrip("/") or "/"
    if request.method == "GET" and path.endswith("/workflows"):
        return httpx.Response(
            200,
            json={
                "workflows": [
                    {"id": "wf-demo", "name": "Demo Workflow", "active": True},
                ],
            },
        )
    if request.method == "GET" and _GET_WORKFLOW_BY_ID.match(path):
        workflow_id = path.rsplit("/", 1)[-1]
        return httpx.Response(
            200,
            json={"id": workflow_id, "name": "Demo Workflow", "active": True},
        )
    if request.method == "POST" and path.endswith("/trigger"):
        return httpx.Response(
            200,
            json={"executionId": "exec-1", "status": "running"},
        )
    return httpx.Response(404, text=f"unexpected request: {request.method} {request.url}")
