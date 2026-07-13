"""Workflow OpenAPI → ASAP adapter demo (Compliance Harness v2 + listWorkflows).

Maps a local mock n8n/Activepieces-style workflow HTTP API into ASAP skills via
``asap.adapters.openapi.create_from_openapi`` (LAB2-001 reuse; no new adapter package).
"""

from __future__ import annotations

import argparse
import asyncio
import os
from pathlib import Path
from typing import Any

import httpx
from fastapi import FastAPI
from httpx import ASGITransport

from asap.adapters.openapi import OpenAPIAdapterBundle, create_from_openapi
from asap.economics.audit import InMemoryAuditStore
from asap.models.enums import TaskStatus
from asap.models.envelope import Envelope
from asap.models.payloads import TaskRequest, TaskResponse
from asap.testing.compliance import run_compliance_harness_v2
from asap.transport.client import ASAPClient
from asap.transport.rate_limit import create_test_limiter
from asap.transport.server import create_app

from mock_upstream import mock_workflow_upstream

_FRAGMENT = Path(__file__).resolve().parent / "openapi-fragment.json"
_MANIFEST_ID = "urn:asap:agent:openapi-workflow-connector-example"


def _workflows_preview(result: dict[str, Any] | None) -> str:
    """Return a short human-readable summary of a listWorkflows result."""
    if result is None:
        return "(no result)"
    for key in ("workflows", "value", "data", "body", "items", "_json"):
        value = result.get(key)
        if isinstance(value, list):
            return f"{len(value)} workflow(s) via {key!r}"
    for _key, value in result.items():
        if isinstance(value, list):
            return f"{len(value)} workflow(s) in list field"
    return str(result)[:200]


async def _build_bundle(
    http: httpx.AsyncClient,
    *,
    upstream_base_url: str | None = None,
) -> OpenAPIAdapterBundle:
    """Build the OpenAPI→ASAP bundle with a shared open httpx client."""
    kwargs: dict[str, Any] = {
        "spec_path": _FRAGMENT,
        "http_client": http,
        "default_capabilities": "all",
        "manifest_id": _MANIFEST_ID,
        "asap_endpoint": "http://127.0.0.1:8000/asap",
    }
    if upstream_base_url is not None:
        kwargs["upstream_base_url"] = upstream_base_url.rstrip("/")
    return await create_from_openapi(**kwargs)


async def _run(*, live_base_url: str | None) -> None:
    """Build the OpenAPI→ASAP bundle and run harness + listWorkflows."""
    timeout = 60.0
    if live_base_url:
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as http:
            bundle = await _build_bundle(http, upstream_base_url=live_base_url)
            await _harness_and_call(bundle)
        return

    transport = httpx.MockTransport(mock_workflow_upstream)
    async with httpx.AsyncClient(transport=transport, timeout=timeout) as http:
        bundle = await _build_bundle(http)
        await _harness_and_call(bundle)


async def _harness_and_call(bundle: OpenAPIAdapterBundle) -> None:
    """Run Compliance Harness v2 then invoke ``listWorkflows`` in-process."""
    skill_ids = sorted(skill.id for skill in bundle.manifest.capabilities.skills)
    print(f"skills: {skill_ids}")

    audit = InMemoryAuditStore()
    app = create_app(
        bundle.manifest,
        bundle.registry,
        audit_store=audit,
        rate_limit="999999/minute",
    )
    app.state.limiter = create_test_limiter()

    report = await run_compliance_harness_v2(app)
    print(report.summary)
    if report.score < 1.0:
        failed = [check for check in report.checks if not check.passed]
        detail = [(check.name, check.message) for check in failed]
        msg = f"Compliance Harness v2 score {report.score}: {detail}"
        raise SystemExit(msg)

    await _invoke_list_workflows(bundle, app)


async def _invoke_list_workflows(
    bundle: OpenAPIAdapterBundle,
    app: FastAPI,
) -> None:
    """Send an in-process ``listWorkflows`` task.request and print a preview."""
    inproc = ASGITransport(app=app)
    envelope = Envelope(
        asap_version="0.1",
        sender="urn:asap:agent:workflow-example-client",
        recipient=bundle.manifest.id,
        payload_type="task.request",
        payload=TaskRequest(
            conversation_id="conv-workflow-example",
            skill_id="listWorkflows",
            input={},
        ).model_dump(),
    )
    async with ASAPClient(
        "http://testserver",
        transport=inproc,
        require_https=False,
    ) as client:
        response = await client.send(envelope)

    if response.payload_type != "task.response":
        raise SystemExit(f"unexpected payload_type: {response.payload_type!r}")
    task_response = TaskResponse.model_validate(response.payload_dict)
    if task_response.status != TaskStatus.COMPLETED:
        raise SystemExit(f"task not completed: {task_response.status}")
    print("listWorkflows:", _workflows_preview(task_response.result))


def main() -> None:
    """CLI entrypoint for the workflow → ASAP connector demo."""
    parser = argparse.ArgumentParser(description="Workflow OpenAPI → ASAP demo")
    parser.add_argument(
        "--live-base-url",
        default=os.environ.get("ASAP_WORKFLOW_BASE_URL"),
        help="Optional live workflow API base URL (overrides mock upstream)",
    )
    args = parser.parse_args()
    asyncio.run(_run(live_base_url=args.live_base_url or None))


if __name__ == "__main__":
    main()
