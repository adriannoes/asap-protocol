"""Integration tests for state machine validation - full lifecycle and failure scenarios."""

from __future__ import annotations

from typing import TYPE_CHECKING

import httpx
import pytest

from asap_compliance.config import ComplianceConfig
from asap_compliance.validators.handshake import validate_handshake_async
from asap_compliance.validators.schema import validate_schema
from asap_compliance.validators.state import validate_state_machine_async
from asap_compliance.validators.sla import validate_sla_async

if TYPE_CHECKING:
    from fastapi import FastAPI


class TestFullTaskLifecycle:
    @pytest.mark.asyncio
    async def test_full_compliance_pipeline_passes(self, good_agent_app: "FastAPI") -> None:
        transport = httpx.ASGITransport(app=good_agent_app)
        async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
            config = ComplianceConfig(
                agent_url="http://testserver",
                timeout_seconds=10.0,
                test_categories=["handshake", "schema", "state"],
            )

            handshake_result = await validate_handshake_async(config, client=client)
            assert handshake_result.passed, f"Handshake failed: {handshake_result.checks}"

            state_result = await validate_state_machine_async(config, client=client)
            assert state_result.passed, f"State machine failed: {state_result.checks}"

            sla_result = await validate_sla_async(config, client=client)
            assert sla_result.passed, f"SLA failed: {sla_result.checks}"

    @pytest.mark.asyncio
    async def test_state_machine_validation_standalone(self, good_agent_app: "FastAPI") -> None:
        transport = httpx.ASGITransport(app=good_agent_app)
        async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
            config = ComplianceConfig(
                agent_url="http://testserver",
                timeout_seconds=5.0,
            )
            result = await validate_state_machine_async(config, client=client)
        assert result.passed
        assert result.transitions_ok
        assert result.terminal_ok


class TestFailureScenarios:
    def test_sla_fails_when_agent_unreachable(self) -> None:
        from asap_compliance.validators.sla import validate_sla

        config = ComplianceConfig(
            agent_url="http://127.0.0.1:17999",
            timeout_seconds=0.5,
        )
        result = validate_sla(config)
        assert not result.timeout_ok
        assert not result.passed

    def test_state_fails_when_agent_unreachable(self) -> None:
        from asap_compliance.validators.state import validate_state_machine

        config = ComplianceConfig(
            agent_url="http://127.0.0.1:17999",
            timeout_seconds=0.5,
        )
        result = validate_state_machine(config)
        assert not result.passed

    @pytest.mark.asyncio
    async def test_handshake_fails_on_bad_agent(self) -> None:
        config = ComplianceConfig(
            agent_url="http://127.0.0.1:17999",
            timeout_seconds=0.5,
        )
        result = await validate_handshake_async(config)
        assert not result.passed
        assert not result.connection_ok

    def test_schema_rejects_invalid_envelope(self) -> None:
        invalid_data = {
            "asap_version": "0.1",
            "sender": "urn:asap:agent:a",
            "recipient": "urn:asap:agent:b",
            "payload_type": "task.request",
            "payload": {"invalid": "missing required fields"},
        }
        result = validate_schema(invalid_data)
        assert not result.passed
        assert not result.payload_ok
