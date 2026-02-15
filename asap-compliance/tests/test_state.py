"""Tests for state machine validator - transition and terminal state compliance."""

from __future__ import annotations

from asap.models.enums import TaskStatus

from asap_compliance.validators.handshake import CheckResult
from asap_compliance.validators.state import (
    StateResult,
    validate_state_machine,
    validate_state_transitions,
    validate_terminal_states,
)


class TestTransitionValidation:
    def test_submitted_to_working_allowed(self) -> None:
        result = validate_state_machine()
        check = next(
            (c for c in result.checks if c.name == "submitted_to_working_allowed"),
            None,
        )
        assert check is not None
        assert check.passed

    def test_completed_to_working_rejected(self) -> None:
        result = validate_state_machine()
        check = next(
            (c for c in result.checks if c.name == "completed_to_working_rejected"),
            None,
        )
        assert check is not None
        assert check.passed

    def test_all_valid_paths_work(self) -> None:
        results = validate_state_transitions()
        path_checks = [r for r in results if r.name in ("valid_path", "all_valid_paths")]
        assert len(path_checks) >= 1
        assert all(r.passed for r in path_checks)


class TestTerminalStateValidation:
    def test_completed_is_terminal(self) -> None:
        result = validate_state_machine()
        check = next(
            (c for c in result.checks if c.name == "completed_is_terminal"),
            None,
        )
        assert check is not None
        assert check.passed
        assert TaskStatus.COMPLETED.is_terminal()

    def test_failed_is_terminal(self) -> None:
        result = validate_state_machine()
        check = next(
            (c for c in result.checks if c.name == "failed_is_terminal"),
            None,
        )
        assert check is not None
        assert check.passed
        assert TaskStatus.FAILED.is_terminal()

    def test_no_transitions_from_terminal(self) -> None:
        results = validate_terminal_states()
        terminal_check = next(
            (r for r in results if r.name == "no_transitions_from_terminal"),
            None,
        )
        assert terminal_check is not None
        assert terminal_check.passed


class TestTransitionRaisesInvalidTransition:
    def test_transition_raises_for_invalid(self) -> None:
        result = validate_state_machine()
        check = next(
            (c for c in result.checks if c.name == "transition_raises_invalid"),
            None,
        )
        assert check is not None
        assert check.passed


class TestStateResult:
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


class TestValidateStateMachineFull:
    def test_validate_state_machine_passes(self) -> None:
        result = validate_state_machine()
        assert result.passed
        assert result.transitions_ok
        assert result.terminal_ok
        assert all(c.passed for c in result.checks)
