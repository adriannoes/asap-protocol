"""PetStore OpenAPI → ASAP adapter demo (Compliance Harness v2 + findPetsByStatus)."""

from __future__ import annotations

import argparse
import asyncio
import os
from pathlib import Path
from typing import Any

import httpx
from httpx import ASGITransport

from asap.adapters.openapi import PETSTORE_OPENAPI_URL, OpenAPIAdapterBundle, create_from_openapi
from asap.economics.audit import InMemoryAuditStore
from asap.models.enums import TaskStatus
from asap.models.envelope import Envelope
from asap.models.payloads import TaskRequest, TaskResponse
from asap.testing.compliance import run_compliance_harness_v2
from asap.transport.client import ASAPClient
from asap.transport.rate_limit import create_test_limiter
from asap.transport.server import create_app

_FRAGMENT = Path(__file__).resolve().parent / "openapi-fragment.json"


def _pets_preview(result: dict[str, Any] | None) -> str:
    if result is None:
        return "(no result)"
    for key in ("value", "data", "body", "items", "_json"):
        v = result.get(key)
        if isinstance(v, list):
            return f"{len(v)} item(s) via {key!r}"
    for _k, v in result.items():
        if isinstance(v, list):
            return f"{len(v)} item(s) in list field"
    return str(result)[:200]


def _mock_upstream(request: httpx.Request) -> httpx.Response:
    if request.method == "GET" and "findByStatus" in request.url.path:
        return httpx.Response(
            200,
            json=[{"id": 1, "name": "DemoPet", "status": "available"}],
        )
    return httpx.Response(404, text=f"unexpected request: {request.method} {request.url}")


async def _run(*, live_petstore: bool) -> None:
    timeout = 60.0
    if live_petstore:
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as http:
            bundle = await create_from_openapi(
                spec_url=PETSTORE_OPENAPI_URL,
                http_client=http,
                default_capabilities="GET",
                manifest_id="urn:asap:agent:openapi-petstore-example",
                asap_endpoint="http://127.0.0.1:8000/asap",
            )
            await _harness_and_call(bundle)
        return

    transport = httpx.MockTransport(_mock_upstream)
    async with httpx.AsyncClient(transport=transport, timeout=timeout) as http:
        bundle = await create_from_openapi(
            spec_path=_FRAGMENT,
            http_client=http,
            default_capabilities="GET",
            manifest_id="urn:asap:agent:openapi-petstore-example",
            asap_endpoint="http://127.0.0.1:8000/asap",
        )
        await _harness_and_call(bundle)


async def _harness_and_call(bundle: OpenAPIAdapterBundle) -> None:
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
        failed = [c for c in report.checks if not c.passed]
        detail = [(c.name, c.message) for c in failed]
        msg = f"Compliance Harness v2 score {report.score}: {detail}"
        raise SystemExit(msg)

    inproc = ASGITransport(app=app)
    envelope = Envelope(
        asap_version="0.1",
        sender="urn:asap:agent:petstore-example-client",
        recipient=bundle.manifest.id,
        payload_type="task.request",
        payload=TaskRequest(
            conversation_id="conv-petstore-example",
            skill_id="findPetsByStatus",
            input={"status": "available"},
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
    print("findPetsByStatus:", _pets_preview(task_response.result))


def main() -> None:
    parser = argparse.ArgumentParser(description="OpenAPI PetStore ASAP demo")
    parser.add_argument(
        "--live",
        action="store_true",
        help="Load spec from petstore3.swagger.io (real network; remote API may error)",
    )
    args = parser.parse_args()
    live = args.live or os.environ.get("ASAP_PETSTORE_LIVE") == "1"
    asyncio.run(_run(live_petstore=live))


if __name__ == "__main__":
    main()
