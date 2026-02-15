"""State machine validation - correct task state transitions."""

from __future__ import annotations

from dataclasses import dataclass, field

from asap.errors import InvalidTransitionError
from asap.models.entities import Task
from asap.models.enums import TaskStatus
from asap.state.machine import VALID_TRANSITIONS, can_transition, transition

from asap_compliance.validators.handshake import CheckResult

# Protocol uses SUBMITTED (not PENDING) and WORKING (not RUNNING)
# Sprint docs use PENDING/RUNNING for readability; we validate the actual enum.


@dataclass
class StateResult:
    """Aggregated result of state machine validation."""

    transitions_ok: bool
    terminal_ok: bool
    checks: list[CheckResult] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return self.transitions_ok and self.terminal_ok


def _check_submitted_to_working_allowed() -> CheckResult:
    allowed = can_transition(TaskStatus.SUBMITTED, TaskStatus.WORKING)
    return CheckResult(
        name="submitted_to_working_allowed",
        passed=allowed,
        message=(
            "SUBMITTED -> WORKING allowed"
            if allowed
            else "Expected SUBMITTED -> WORKING to be allowed"
        ),
    )


def _check_completed_to_working_rejected() -> CheckResult:
    rejected = not can_transition(TaskStatus.COMPLETED, TaskStatus.WORKING)
    return CheckResult(
        name="completed_to_working_rejected",
        passed=rejected,
        message=(
            "COMPLETED -> WORKING rejected"
            if rejected
            else "Expected COMPLETED -> WORKING to be rejected"
        ),
    )


def _check_all_valid_paths() -> list[CheckResult]:
    failures = [
        CheckResult(
            "valid_path",
            False,
            f"{f.value} -> {t.value} should be allowed but was rejected",
        )
        for f, targets in VALID_TRANSITIONS.items()
        for t in targets
        if not can_transition(f, t)
    ]
    return (
        failures
        if failures
        else [CheckResult("all_valid_paths", True, "All valid transitions allowed")]
    )


def _check_completed_is_terminal() -> CheckResult:
    terminal = TaskStatus.COMPLETED.is_terminal()
    return CheckResult(
        name="completed_is_terminal",
        passed=terminal,
        message="COMPLETED is terminal" if terminal else "Expected COMPLETED to be terminal",
    )


def _check_failed_is_terminal() -> CheckResult:
    terminal = TaskStatus.FAILED.is_terminal()
    return CheckResult(
        name="failed_is_terminal",
        passed=terminal,
        message="FAILED is terminal" if terminal else "Expected FAILED to be terminal",
    )


def _check_no_transitions_from_terminal() -> list[CheckResult]:
    results: list[CheckResult] = []
    terminal_states = TaskStatus.terminal_states()
    for status in terminal_states:
        targets = VALID_TRANSITIONS.get(status, set())
        if targets:
            results.append(
                CheckResult(
                    name="terminal_no_transitions",
                    passed=False,
                    message=(
                        f"{status.value} is terminal but has outgoing "
                        f"transitions: {[t.value for t in targets]}"
                    ),
                )
            )
    if not results:
        results.append(
            CheckResult(
                name="no_transitions_from_terminal",
                passed=True,
                message="No transitions from COMPLETED, FAILED, CANCELLED",
            )
        )
    return results


def _check_transition_raises_invalid_transition() -> CheckResult:
    from datetime import datetime, timezone

    task = Task(
        id="task_01HX5K4N0000000000000000",
        conversation_id="conv_01HX5K3MQVN800000000",
        status=TaskStatus.COMPLETED,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    try:
        transition(task, TaskStatus.WORKING)
        return CheckResult(
            name="transition_raises_invalid",
            passed=False,
            message="Expected InvalidTransitionError for COMPLETED -> WORKING",
        )
    except InvalidTransitionError:
        return CheckResult(
            name="transition_raises_invalid",
            passed=True,
            message="InvalidTransitionError raised for invalid transition",
        )


def validate_state_transitions() -> list[CheckResult]:
    results: list[CheckResult] = []
    results.append(_check_submitted_to_working_allowed())
    results.append(_check_completed_to_working_rejected())
    results.extend(_check_all_valid_paths())
    results.append(_check_transition_raises_invalid_transition())
    return results


def validate_terminal_states() -> list[CheckResult]:
    results: list[CheckResult] = []
    results.append(_check_completed_is_terminal())
    results.append(_check_failed_is_terminal())
    results.extend(_check_no_transitions_from_terminal())
    return results


def validate_state_machine() -> StateResult:
    checks: list[CheckResult] = []
    transition_results = validate_state_transitions()
    checks.extend(transition_results)
    transitions_ok = all(r.passed for r in transition_results)

    terminal_results = validate_terminal_states()
    checks.extend(terminal_results)
    terminal_ok = all(r.passed for r in terminal_results)

    return StateResult(
        transitions_ok=transitions_ok,
        terminal_ok=terminal_ok,
        checks=checks,
    )
