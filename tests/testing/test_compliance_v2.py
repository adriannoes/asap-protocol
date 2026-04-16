"""Tests for Compliance Harness v2."""

from __future__ import annotations

import json

import pytest
from httpx import ASGITransport, AsyncClient
from pydantic import ValidationError

from asap.economics.audit import InMemoryAuditStore
from asap.models.entities import Capability, Endpoint, Manifest, Skill
from asap.testing.compliance import (
    ALL_CATEGORIES,
    CheckResult,
    ComplianceReport,
    check_audit,
    check_batch,
    check_errors,
    check_streaming,
    check_versioning,
    run_compliance_harness_v2,
)
from asap.transport.handlers import HandlerRegistry, create_echo_handler
from asap.transport.rate_limit import create_test_limiter
from fastapi import FastAPI

from asap.transport.server import create_app


def _test_manifest() -> Manifest:
    return Manifest(
        id="urn:asap:agent:compliance-test",
        name="Compliance Test Agent",
        version="1.0.0",
        description="Test agent for compliance harness",
        capabilities=Capability(
            asap_version="0.1",
            skills=[Skill(id="echo", description="Echo")],
            state_persistence=False,
        ),
        endpoints=Endpoint(asap="http://test/asap"),
    )


def _test_app() -> FastAPI:
    manifest = _test_manifest()
    reg = HandlerRegistry()
    reg.register("task.request", create_echo_handler())
    audit = InMemoryAuditStore()
    app = create_app(manifest, reg, audit_store=audit)
    app.state.limiter = create_test_limiter()
    return app


class TestRunComplianceHarness:
    async def test_full_run(self) -> None:
        app = _test_app()
        report = await run_compliance_harness_v2(app)
        assert isinstance(report, ComplianceReport)
        assert report.version == "2.0"
        assert report.score >= 0.0
        assert len(report.checks) > 0
        assert report.summary != ""

    async def test_json_export(self) -> None:
        app = _test_app()
        report = await run_compliance_harness_v2(app)
        json_str = report.to_json()
        data = json.loads(json_str)
        assert "checks" in data
        assert "score" in data
        assert "summary" in data

    async def test_category_filter(self) -> None:
        app = _test_app()
        report = await run_compliance_harness_v2(app, categories=["errors"])
        assert report.categories_run == ["errors"]
        assert all(c.category == "errors" for c in report.checks)

    async def test_all_categories_covered(self) -> None:
        assert "identity" in ALL_CATEGORIES
        assert "streaming" in ALL_CATEGORIES
        assert "errors" in ALL_CATEGORIES
        assert "versioning" in ALL_CATEGORIES
        assert "batch" in ALL_CATEGORIES
        assert "audit" in ALL_CATEGORIES


class TestIndividualChecks:
    async def test_errors_check(self) -> None:
        app = _test_app()
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            results = await check_errors(client)
            assert len(results) >= 2
            names = [r.name for r in results]
            assert "error_method_not_found" in names
            assert "error_parse_error" in names

    async def test_versioning_check(self) -> None:
        app = _test_app()
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            results = await check_versioning(client)
            assert len(results) >= 1

    async def test_batch_check(self) -> None:
        app = _test_app()
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            results = await check_batch(client)
            assert len(results) >= 2
            batch_arr = next(r for r in results if r.name == "batch_array_response")
            assert batch_arr.passed

    async def test_audit_check(self) -> None:
        app = _test_app()
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            results = await check_audit(client)
            assert len(results) >= 1
            ep = next(r for r in results if r.name == "audit_endpoint_exists")
            assert ep.passed

    async def test_streaming_check(self) -> None:
        app = _test_app()
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            results = await check_streaming(client)
            assert len(results) >= 1


class TestCheckResultModel:
    def test_frozen(self) -> None:
        cr = CheckResult(name="test", category="cat", passed=True)
        with pytest.raises(ValidationError):
            cr.name = "modified"

    def test_score_calculation(self) -> None:
        report = ComplianceReport(
            timestamp=__import__("datetime").datetime.now(__import__("datetime").timezone.utc),
            categories_run=["test"],
            checks=[
                CheckResult(name="a", category="test", passed=True),
                CheckResult(name="b", category="test", passed=False),
            ],
            score=0.5,
            summary="1/2 checks passed (50%)",
        )
        assert report.score == 0.5
        assert len(report.checks) == 2
