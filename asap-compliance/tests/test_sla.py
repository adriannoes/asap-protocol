"""Tests for SLA validator - timeout and progress compliance."""

from __future__ import annotations

from typing import TYPE_CHECKING

import httpx
import pytest

from asap_compliance.config import ComplianceConfig
from asap_compliance.validators.handshake import CheckResult
from asap_compliance.validators.sla import (
    SlaResult,
    validate_sla,
    validate_sla_async,
    _check_progress_schema,
)

if TYPE_CHECKING:
    from fastapi import FastAPI


class TestProgressSchema:
    def test_progress_schema_valid(self) -> None:
        results = _check_progress_schema()
        check = next((r for r in results if r.name == "sla_progress_schema"), None)
        assert check is not None
        assert check.passed


class TestSlaKnownGood:
    @pytest.mark.asyncio
    async def test_sla_passes_against_echo_agent(self, good_agent_app: "FastAPI") -> None:
        transport = httpx.ASGITransport(app=good_agent_app)
        async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
            config = ComplianceConfig(
                agent_url="http://testserver",
                timeout_seconds=10.0,
            )
            result = await validate_sla_async(config, client=client)

        assert result.progress_schema_ok
        assert result.timeout_ok
        assert result.passed

    @pytest.mark.asyncio
    async def test_task_completes_within_timeout(self, good_agent_app: "FastAPI") -> None:
        transport = httpx.ASGITransport(app=good_agent_app)
        async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
            config = ComplianceConfig(
                agent_url="http://testserver",
                timeout_seconds=5.0,
            )
            result = await validate_sla_async(config, client=client)

        timeout_check = next((c for c in result.checks if c.name == "sla_task_timeout"), None)
        assert timeout_check is not None
        assert timeout_check.passed


class TestSlaSkipChecks:
    """Tests for skip_checks configuration."""

    def test_skip_sla_check_passes_without_agent(self) -> None:
        """When skip_checks includes 'sla', timeout check is skipped."""
        config = ComplianceConfig(
            agent_url="http://127.0.0.1:17999",
            timeout_seconds=0.5,
            skip_checks=["sla"],
        )
        result = validate_sla(config)
        assert result.timeout_ok
        assert result.passed
        skip_check = next(
            (c for c in result.checks if "skipped" in c.message.lower()),
            None,
        )
        assert skip_check is not None
        assert skip_check.passed


class TestSlaResult:
    def test_passed_true_when_all_ok(self) -> None:
        result = SlaResult(
            timeout_ok=True,
            progress_schema_ok=True,
            checks=[CheckResult("x", True, "ok")],
        )
        assert result.passed

    def test_passed_false_when_timeout_fails(self) -> None:
        result = SlaResult(
            timeout_ok=False,
            progress_schema_ok=True,
            checks=[],
        )
        assert not result.passed

    def test_passed_false_when_progress_schema_fails(self) -> None:
        result = SlaResult(
            timeout_ok=True,
            progress_schema_ok=False,
            checks=[],
        )
        assert not result.passed
