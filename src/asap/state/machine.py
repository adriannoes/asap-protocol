"""ASAP Task State Machine.

This module implements the task state machine for the ASAP protocol,
managing valid state transitions and providing transition validation.
"""

from typing import Dict, Set

from asap.errors import InvalidTransitionError
from asap.models.entities import Task
from asap.models.enums import TaskStatus


# Valid state transitions mapping
VALID_TRANSITIONS: Dict[TaskStatus, Set[TaskStatus]] = {
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
    """
    return to_status in VALID_TRANSITIONS[from_status]


def transition(task: Task, new_status: TaskStatus) -> Task:
    """Transition a task to a new status with validation.

    Args:
        task: The task to transition
        new_status: The target status

    Returns:
        New task instance with updated status

    Raises:
        InvalidTransitionError: If the transition is not valid
    """
    if not can_transition(task.status, new_status):
        raise InvalidTransitionError(
            from_state=task.status.value, to_state=new_status.value, details={"task_id": task.id}
        )

    # Create new task instance with updated status (immutable approach)
    return task.model_copy(update={"status": new_status})
