"""Mock n8n/Activepieces-style workflow HTTP API for the offline demo and tests."""

from __future__ import annotations

import httpx


def mock_workflow_upstream(request: httpx.Request) -> httpx.Response:
    """Respond to workflow mock paths without contacting a live SaaS.

    Example::

        transport = httpx.MockTransport(mock_workflow_upstream)
        async with httpx.AsyncClient(transport=transport) as http:
            ...
    """
    path = request.url.path
    if request.method == "GET" and path.rstrip("/").endswith("/workflows"):
        return httpx.Response(
            200,
            json={
                "workflows": [
                    {"id": "wf-demo", "name": "Demo Workflow", "active": True},
                ],
            },
        )
    if request.method == "GET" and "/workflows/" in path:
        workflow_id = path.rstrip("/").rsplit("/", 1)[-1]
        return httpx.Response(
            200,
            json={"id": workflow_id, "name": "Demo Workflow", "active": True},
        )
    if request.method == "POST" and path.rstrip("/").endswith("/trigger"):
        return httpx.Response(
            200,
            json={"executionId": "exec-1", "status": "running"},
        )
    return httpx.Response(404, text=f"unexpected request: {request.method} {request.url}")
