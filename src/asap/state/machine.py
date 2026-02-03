"""ASAP Task State Machine.

This module implements the task state machine for the ASAP protocol,
managing valid state transitions and providing transition validation.

Example:
    >>> from asap.models.enums import TaskStatus
    >>> can_transition(TaskStatus.SUBMITTED, TaskStatus.WORKING)
    True
"""

from datetime import datetime, timezone

from asap.errors import InvalidTransitionError
from asap.models.entities import Task
from asap.models.enums import TaskStatus
from asap.observability import get_metrics
from asap.observability.tracing import state_transition_span_context

__all__ = ["TaskStatus", "can_transition", "transition", "VALID_TRANSITIONS"]

# Valid state transitions mapping
VALID_TRANSITIONS: dict[TaskStatus, set[TaskStatus]] = {
    TaskStatus.SUBMITTED: {TaskStatus.WORKING, TaskStatus.CANCELLED},
    TaskStatus.WORKING: {
        TaskStatus.COMPLETED,
        TaskStatus.FAILED,
        TaskStatus.CANCELLED,
        TaskStatus.INPUT_REQUIRED,
    },
    TaskStatus.INPUT_REQUIRED: {TaskStatus.WORKING, TaskStatus.CANCELLED},
    TaskStatus.COMPLETED: set(),  # Terminal state
    TaskStatus.FAILED: set(),  # Terminal state
    TaskStatus.CANCELLED: set(),  # Terminal state
}


def can_transition(from_status: TaskStatus, to_status: TaskStatus) -> bool:
    """Check if a transition from one status to another is valid.

    Args:
        from_status: Current task status
        to_status: Target task status

    Returns:
        True if the transition is valid, False otherwise

    Example:
        >>> can_transition(TaskStatus.SUBMITTED, TaskStatus.WORKING)
        True
        >>> can_transition(TaskStatus.COMPLETED, TaskStatus.WORKING)
        False
    """
    valid_targets = VALID_TRANSITIONS.get(from_status, set())
    return to_status in valid_targets


def transition(task: Task, new_status: TaskStatus) -> Task:
    """Transition a task to a new status with validation.

    Args:
        task: The task to transition
        new_status: The target status

    Returns:
        New task instance with updated status and updated_at timestamp

    Raises:
        InvalidTransitionError: If the transition is not valid

    Example:
        >>> task = Task(
        ...     id="task_01HX5K4N...",
        ...     conversation_id="conv_01HX5K3M...",
        ...     status=TaskStatus.SUBMITTED,
        ...     created_at=datetime.now(timezone.utc),
        ...     updated_at=datetime.now(timezone.utc),
        ... )
        >>> updated = transition(task, TaskStatus.WORKING)
        >>> updated.status
        <TaskStatus.WORKING: 'working'>
    """
    if not can_transition(task.status, new_status):
        raise InvalidTransitionError(
            from_state=task.status.value, to_state=new_status.value, details={"task_id": task.id}
        )

    with state_transition_span_context(
        from_status=task.status.value,
        to_status=new_status.value,
        task_id=task.id,
    ):
        get_metrics().increment_counter(
            "asap_state_transitions_total",
            {"from_status": task.status.value, "to_status": new_status.value},
        )
        return task.model_copy(
            update={"status": new_status, "updated_at": datetime.now(timezone.utc)}
        )
