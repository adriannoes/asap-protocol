"""Mock n8n/Activepieces-style workflow HTTP API for the offline demo and tests."""

from __future__ import annotations

import json
import re

import httpx

# Exact path match under /api/v1 — rejects suffix/prefix spoofing (PR #291 hardening).
_LIST_WORKFLOWS = re.compile(r"^/api/v1/workflows$")
_GET_WORKFLOW_BY_ID = re.compile(r"^/api/v1/workflows/[^/]+$")
_TRIGGER_WORKFLOW = re.compile(r"^/api/v1/workflows/[^/]+/trigger$")


def mock_workflow_upstream(request: httpx.Request) -> httpx.Response:
    """Respond to canonical workflow mock paths without contacting a live SaaS.

    Paths must match ``/api/v1/workflows``, ``/api/v1/workflows/{id}``, or
    ``/api/v1/workflows/{id}/trigger`` exactly (no suffix/prefix spoofing).

    Example::

        transport = httpx.MockTransport(mock_workflow_upstream)
        async with httpx.AsyncClient(transport=transport) as http:
            ...
    """
    path = request.url.path.rstrip("/") or "/"
    if request.method == "GET" and _LIST_WORKFLOWS.match(path):
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
    if request.method == "POST" and _TRIGGER_WORKFLOW.match(path):
        body = request.content or b""
        if body:
            try:
                parsed: object = json.loads(body)
            except json.JSONDecodeError as exc:
                return httpx.Response(
                    400,
                    text=(
                        f"unexpected body: invalid JSON for trigger "
                        f"(error={exc.msg!r}, pos={exc.pos})"
                    ),
                )
            if not isinstance(parsed, dict):
                return httpx.Response(
                    400,
                    text=(
                        f"unexpected body: expected JSON object for trigger, "
                        f"got {type(parsed).__name__}"
                    ),
                )
            if "payload" in parsed and not isinstance(parsed["payload"], dict):
                return httpx.Response(
                    400,
                    text=(
                        "unexpected body: trigger 'payload' must be a JSON object "
                        f"when present, got {type(parsed['payload']).__name__}"
                    ),
                )
        return httpx.Response(
            200,
            json={"executionId": "exec-1", "status": "running"},
        )
    return httpx.Response(404, text=f"unexpected request: {request.method} {request.url}")
