"""Tests for ASAP protocol enumerations.

This module tests the enum classes defined in asap.models.enums:
- TaskStatus: Task lifecycle states
- MessageRole: Message author roles
- UpdateType: Task update categories
"""

import pytest

from asap.models.enums import MessageRole, TaskStatus, UpdateType


class TestTaskStatus:
    """Tests for TaskStatus enum."""

    def test_all_status_values_exist(self) -> None:
        """Test that all expected status values are defined."""
        expected_statuses = [
            "SUBMITTED",
            "WORKING",
            "COMPLETED",
            "FAILED",
            "CANCELLED",
            "INPUT_REQUIRED",
        ]
        for status_name in expected_statuses:
            assert hasattr(TaskStatus, status_name)

    def test_status_string_values(self) -> None:
        """Test that status values match expected strings."""
        assert TaskStatus.SUBMITTED.value == "submitted"
        assert TaskStatus.WORKING.value == "working"
        assert TaskStatus.COMPLETED.value == "completed"
        assert TaskStatus.FAILED.value == "failed"
        assert TaskStatus.CANCELLED.value == "cancelled"
        assert TaskStatus.INPUT_REQUIRED.value == "input_required"

    def test_is_terminal_for_completed(self) -> None:
        """Test that COMPLETED is a terminal state."""
        assert TaskStatus.COMPLETED.is_terminal() is True

    def test_is_terminal_for_failed(self) -> None:
        """Test that FAILED is a terminal state."""
        assert TaskStatus.FAILED.is_terminal() is True

    def test_is_terminal_for_cancelled(self) -> None:
        """Test that CANCELLED is a terminal state."""
        assert TaskStatus.CANCELLED.is_terminal() is True

    def test_is_terminal_for_submitted(self) -> None:
        """Test that SUBMITTED is not a terminal state."""
        assert TaskStatus.SUBMITTED.is_terminal() is False

    def test_is_terminal_for_working(self) -> None:
        """Test that WORKING is not a terminal state."""
        assert TaskStatus.WORKING.is_terminal() is False

    def test_is_terminal_for_input_required(self) -> None:
        """Test that INPUT_REQUIRED is not a terminal state."""
        assert TaskStatus.INPUT_REQUIRED.is_terminal() is False

    def test_terminal_states_classmethod(self) -> None:
        """Test terminal_states() returns correct frozenset."""
        terminal = TaskStatus.terminal_states()

        assert isinstance(terminal, frozenset)
        assert TaskStatus.COMPLETED in terminal
        assert TaskStatus.FAILED in terminal
        assert TaskStatus.CANCELLED in terminal
        assert TaskStatus.SUBMITTED not in terminal
        assert TaskStatus.WORKING not in terminal
        assert TaskStatus.INPUT_REQUIRED not in terminal

    def test_terminal_states_is_immutable(self) -> None:
        """Test that terminal_states() returns a frozenset (immutable)."""
        terminal = TaskStatus.terminal_states()

        # frozenset should not have add/remove methods
        assert not hasattr(terminal, "add")
        assert not hasattr(terminal, "remove")

    def test_status_comparison(self) -> None:
        """Test that status values can be compared."""
        assert TaskStatus.COMPLETED == TaskStatus.COMPLETED
        assert TaskStatus.COMPLETED != TaskStatus.FAILED

    def test_status_from_string(self) -> None:
        """Test creating status from string value."""
        status = TaskStatus("completed")
        assert status == TaskStatus.COMPLETED

    def test_invalid_status_raises_error(self) -> None:
        """Test that invalid status string raises ValueError."""
        with pytest.raises(ValueError):
            TaskStatus("invalid_status")

    def test_status_iteration(self) -> None:
        """Test that all statuses can be iterated."""
        statuses = list(TaskStatus)
        assert len(statuses) == 6


class TestMessageRole:
    """Tests for MessageRole enum."""

    def test_all_role_values_exist(self) -> None:
        """Test that all expected role values are defined."""
        expected_roles = ["USER", "ASSISTANT", "SYSTEM"]
        for role_name in expected_roles:
            assert hasattr(MessageRole, role_name)

    def test_role_string_values(self) -> None:
        """Test that role values match expected strings."""
        assert MessageRole.USER.value == "user"
        assert MessageRole.ASSISTANT.value == "assistant"
        assert MessageRole.SYSTEM.value == "system"

    def test_role_comparison(self) -> None:
        """Test that role values can be compared."""
        assert MessageRole.USER == MessageRole.USER
        assert MessageRole.USER != MessageRole.ASSISTANT

    def test_role_from_string(self) -> None:
        """Test creating role from string value."""
        role = MessageRole("user")
        assert role == MessageRole.USER

    def test_invalid_role_raises_error(self) -> None:
        """Test that invalid role string raises ValueError."""
        with pytest.raises(ValueError):
            MessageRole("invalid_role")

    def test_role_iteration(self) -> None:
        """Test that all roles can be iterated."""
        roles = list(MessageRole)
        assert len(roles) == 3


class TestUpdateType:
    """Tests for UpdateType enum."""

    def test_all_update_type_values_exist(self) -> None:
        """Test that all expected update type values are defined."""
        expected_types = ["PROGRESS", "INPUT_REQUIRED", "STATUS_CHANGE"]
        for type_name in expected_types:
            assert hasattr(UpdateType, type_name)

    def test_update_type_string_values(self) -> None:
        """Test that update type values match expected strings."""
        assert UpdateType.PROGRESS.value == "progress"
        assert UpdateType.INPUT_REQUIRED.value == "input_required"
        assert UpdateType.STATUS_CHANGE.value == "status_change"

    def test_update_type_comparison(self) -> None:
        """Test that update type values can be compared."""
        assert UpdateType.PROGRESS == UpdateType.PROGRESS
        assert UpdateType.PROGRESS != UpdateType.STATUS_CHANGE

    def test_update_type_from_string(self) -> None:
        """Test creating update type from string value."""
        update_type = UpdateType("progress")
        assert update_type == UpdateType.PROGRESS

    def test_invalid_update_type_raises_error(self) -> None:
        """Test that invalid update type string raises ValueError."""
        with pytest.raises(ValueError):
            UpdateType("invalid_type")

    def test_update_type_iteration(self) -> None:
        """Test that all update types can be iterated."""
        update_types = list(UpdateType)
        assert len(update_types) == 3


class TestEnumIntegration:
    """Integration tests for enum usage patterns."""

    def test_task_status_in_pydantic_serialization(self) -> None:
        """Test that TaskStatus works correctly in Pydantic models."""
        from asap.models.payloads import TaskResponse

        response = TaskResponse(
            task_id="task_123",
            status=TaskStatus.COMPLETED,
            result={"data": "test"},
        )

        # Serialization should work
        data = response.model_dump()
        assert data["status"] == "completed"

        # Deserialization should work
        restored = TaskResponse(**data)
        assert restored.status == TaskStatus.COMPLETED

    def test_message_role_in_pydantic_serialization(self) -> None:
        """Test that MessageRole works correctly in Pydantic models."""
        from datetime import datetime, timezone

        from asap.models.entities import Message

        message = Message(
            id="msg_123",
            task_id="task_123",
            sender="urn:asap:agent:test",
            role=MessageRole.USER,
            parts=[],
            timestamp=datetime.now(timezone.utc),
        )

        # Serialization should work
        data = message.model_dump()
        assert data["role"] == "user"

        # Deserialization should work
        restored = Message(**data)
        assert restored.role == MessageRole.USER

    def test_update_type_in_pydantic_serialization(self) -> None:
        """Test that UpdateType works correctly in Pydantic models."""
        from asap.models.payloads import TaskUpdate

        update = TaskUpdate(
            task_id="task_123",
            update_type=UpdateType.PROGRESS,
            status=TaskStatus.WORKING,
            progress={"percent": 50, "message": "In progress"},
        )

        # Serialization should work
        data = update.model_dump()
        assert data["update_type"] == "progress"

        # Deserialization should work
        restored = TaskUpdate(**data)
        assert restored.update_type == UpdateType.PROGRESS

    def test_enum_json_schema_generation(self) -> None:
        """Test that enums generate correct JSON schema."""
        from asap.models.payloads import TaskResponse

        schema = TaskResponse.model_json_schema()

        # Status should be in the schema
        assert "status" in schema["properties"]

        # Check that it references the enum definition
        status_schema = schema["properties"]["status"]
        # The status should reference TaskStatus enum
        assert "$ref" in status_schema or "enum" in status_schema or "allOf" in status_schema
