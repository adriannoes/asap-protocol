"""Property-based tests for ASAP task state machine.

Invariants: terminal states never transition; all paths eventually reach a terminal state.
"""

from __future__ import annotations

from collections import deque

from hypothesis import given
from hypothesis import strategies as st

from asap.models.enums import TaskStatus
from asap.state.machine import VALID_TRANSITIONS, can_transition


def _reachable_states(from_status: TaskStatus) -> set[TaskStatus]:
    """Return all states reachable from from_status via valid transitions (BFS)."""
    seen: set[TaskStatus] = set()
    queue: deque[TaskStatus] = deque([from_status])
    while queue:
        s = queue.popleft()
        if s in seen:
            continue
        seen.add(s)
        for t in VALID_TRANSITIONS.get(s, set()):
            if t not in seen:
                queue.append(t)
    return seen


class TestStateMachineInvariants:
    """Invariant: terminal states never transition."""

    @given(
        terminal=st.sampled_from(list(TaskStatus.terminal_states())),
        target=st.sampled_from(list(TaskStatus)),
    )
    def test_terminal_states_never_transition(
        self, terminal: TaskStatus, target: TaskStatus
    ) -> None:
        """From any terminal state, no transition to any target is valid."""
        assert not can_transition(terminal, target), (
            f"Terminal state {terminal} must not transition to {target}"
        )


class TestStateMachineReachability:
    """Property: all paths eventually reach a terminal state."""

    def test_every_non_terminal_can_reach_terminal(self) -> None:
        """From every non-terminal state, at least one terminal state is reachable."""
        terminals = TaskStatus.terminal_states()
        for status in TaskStatus:
            if status.is_terminal():
                continue
            reachable = _reachable_states(status)
            reachable_terminals = reachable & terminals
            assert len(reachable_terminals) >= 1, (
                f"Non-terminal state {status} must eventually reach a terminal state; "
                f"reachable={reachable}"
            )

    @given(start=st.sampled_from(list(TaskStatus)))
    def test_path_from_any_state_eventually_terminates(self, start: TaskStatus) -> None:
        """From any state, either it is terminal or some terminal is reachable."""
        if start.is_terminal():
            return
        reachable = _reachable_states(start)
        assert (reachable & TaskStatus.terminal_states()) != set(), (
            f"From non-terminal {start}, at least one terminal must be reachable"
        )
