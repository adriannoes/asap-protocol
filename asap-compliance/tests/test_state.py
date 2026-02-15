"""Tests for state machine validator - black-box compliance of agent state transitions."""

from __future__ import annotations

from typing import TYPE_CHECKING

import httpx
import pytest

from asap_compliance.config import ComplianceConfig
from asap_compliance.validators.handshake import CheckResult
from asap_compliance.validators.state import (
    StateResult,
    validate_state_machine,
    validate_state_machine_async,
)

if TYPE_CHECKING:
    from fastapi import FastAPI


class TestStateBlackBoxKnownGood:
    """Tests against a known-good agent (echo returns COMPLETED)."""

    @pytest.mark.asyncio
    async def test_state_passes_against_good_agent(self, good_agent_app: "FastAPI") -> None:
        """State validation passes when agent returns valid terminal status."""
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
        assert all(c.passed for c in result.checks)

    @pytest.mark.asyncio
    async def test_state_terminal_status_check(
        self, compliance_config_with_transport: tuple[ComplianceConfig, httpx.AsyncClient]
    ) -> None:
        """Agent returns valid terminal status (completed/failed/cancelled)."""
        config, client = compliance_config_with_transport
        result = await validate_state_machine_async(config, client=client)
        terminal_check = next(
            (c for c in result.checks if c.name == "state_terminal_status"),
            None,
        )
        assert terminal_check is not None
        assert terminal_check.passed


class TestStateResult:
    """Tests for StateResult model."""

    def test_passed_true_when_all_ok(self) -> None:
        result = StateResult(
            transitions_ok=True,
            terminal_ok=True,
            checks=[CheckResult("x", True, "ok")],
        )
        assert result.passed

    def test_passed_false_when_transitions_fail(self) -> None:
        result = StateResult(
            transitions_ok=False,
            terminal_ok=True,
            checks=[],
        )
        assert not result.passed

    def test_passed_false_when_terminal_fails(self) -> None:
        result = StateResult(
            transitions_ok=True,
            terminal_ok=False,
            checks=[],
        )
        assert not result.passed


class TestStateSyncWrapper:
    """Tests for sync wrapper behavior."""

    def test_validate_state_machine_sync_requires_running_agent(self) -> None:
        """Sync validate_state_machine works when no event loop is running.

        Note: Uses unreachable port 17999 - we only verify the sync wrapper runs
        without crashing. For full pass, use async with good_agent_app.
        """
        config = ComplianceConfig(
            agent_url="http://127.0.0.1:17999",
            timeout_seconds=0.5,
        )
        result = validate_state_machine(config)
        assert not result.passed
        assert any(not c.passed for c in result.checks)
