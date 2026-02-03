"""Tests for ASAP protocol error handling."""

from asap.errors import (
    ASAPError,
    InvalidTransitionError,
    MalformedEnvelopeError,
    TaskNotFoundError,
    TaskAlreadyCompletedError,
    ThreadPoolExhaustedError,
)


class TestASAPError:
    """Test ASAPError base class."""

    def test_basic_error_creation(self) -> None:
        """Test creating a basic ASAPError."""
        error = ASAPError(code="asap:test/error", message="Test error message")

        assert error.code == "asap:test/error"
        assert error.message == "Test error message"
        assert error.details == {}
        assert str(error) == "Test error message"

    def test_error_with_details(self) -> None:
        """Test ASAPError with additional details."""
        details = {"context": "test", "value": 42}
        error = ASAPError(
            code="asap:test/detailed_error", message="Detailed error", details=details
        )

        assert error.code == "asap:test/detailed_error"
        assert error.message == "Detailed error"
        assert error.details == details

    def test_error_details_immutability(self) -> None:
        """Test that details dict is not shared between instances."""
        error1 = ASAPError("code", "msg", {"key": "value1"})
        error2 = ASAPError("code", "msg", {"key": "value2"})

        assert error1.details["key"] == "value1"
        assert error2.details["key"] == "value2"


class TestInvalidTransitionError:
    """Test InvalidTransitionError class."""

    def test_basic_transition_error(self) -> None:
        """Test creating an InvalidTransitionError."""
        error = InvalidTransitionError(from_state="working", to_state="completed")

        assert error.code == "asap:protocol/invalid_state"
        assert error.from_state == "working"
        assert error.to_state == "completed"
        assert "Invalid transition from 'working' to 'completed'" in str(error)

    def test_transition_error_with_details(self) -> None:
        """Test InvalidTransitionError with additional details."""
        details = {"task_id": "task-123", "reason": "business_logic"}
        error = InvalidTransitionError(from_state="completed", to_state="working", details=details)

        assert error.code == "asap:protocol/invalid_state"
        assert error.from_state == "completed"
        assert error.to_state == "working"
        assert error.details["task_id"] == "task-123"
        assert error.details["reason"] == "business_logic"
        assert error.details["from_state"] == "completed"
        assert error.details["to_state"] == "working"

    def test_transition_error_inheritance(self) -> None:
        """Test that InvalidTransitionError inherits from ASAPError."""
        error = InvalidTransitionError("state1", "state2")

        assert isinstance(error, ASAPError)
        assert isinstance(error, Exception)


class TestMalformedEnvelopeError:
    """Test MalformedEnvelopeError class."""

    def test_basic_malformed_envelope_error(self) -> None:
        """Test creating a MalformedEnvelopeError."""
        error = MalformedEnvelopeError(reason="missing required field 'id'")

        assert error.code == "asap:protocol/malformed_envelope"
        assert error.reason == "missing required field 'id'"
        assert "Malformed envelope: missing required field 'id'" in str(error)

    def test_malformed_envelope_error_with_details(self) -> None:
        """Test MalformedEnvelopeError with additional details."""
        details = {"field": "payload", "expected_type": "dict"}
        error = MalformedEnvelopeError(reason="invalid payload type", details=details)

        assert error.code == "asap:protocol/malformed_envelope"
        assert error.details == details

    def test_malformed_envelope_error_inheritance(self) -> None:
        """Test that MalformedEnvelopeError inherits from ASAPError."""
        error = MalformedEnvelopeError("test reason")

        assert isinstance(error, ASAPError)
        assert isinstance(error, Exception)


class TestTaskNotFoundError:
    """Test TaskNotFoundError class."""

    def test_basic_task_not_found_error(self) -> None:
        """Test creating a TaskNotFoundError."""
        error = TaskNotFoundError(task_id="task-123")

        assert error.code == "asap:task/not_found"
        assert error.task_id == "task-123"
        assert "Task not found: task-123" in str(error)

    def test_task_not_found_error_with_details(self) -> None:
        """Test TaskNotFoundError with additional details."""
        details = {"searched_in": "database", "timestamp": "2026-01-19T10:00:00Z"}
        error = TaskNotFoundError(task_id="task-456", details=details)

        assert error.code == "asap:task/not_found"
        assert error.task_id == "task-456"
        assert error.details["searched_in"] == "database"
        assert error.details["task_id"] == "task-456"  # Should be included in details

    def test_task_not_found_error_inheritance(self) -> None:
        """Test that TaskNotFoundError inherits from ASAPError."""
        error = TaskNotFoundError("task-789")

        assert isinstance(error, ASAPError)
        assert isinstance(error, Exception)


class TestTaskAlreadyCompletedError:
    """Test TaskAlreadyCompletedError class."""

    def test_basic_task_already_completed_error(self) -> None:
        """Test creating a TaskAlreadyCompletedError."""
        error = TaskAlreadyCompletedError(task_id="task-123", current_status="completed")

        assert error.code == "asap:task/already_completed"
        assert error.task_id == "task-123"
        assert error.current_status == "completed"
        assert "Task already completed: task-123 (status: completed)" in str(error)

    def test_task_already_completed_error_with_details(self) -> None:
        """Test TaskAlreadyCompletedError with additional details."""
        details = {"completed_at": "2026-01-19T09:30:00Z", "output_size": 1024}
        error = TaskAlreadyCompletedError(
            task_id="task-456", current_status="failed", details=details
        )

        assert error.code == "asap:task/already_completed"
        assert error.task_id == "task-456"
        assert error.current_status == "failed"
        assert error.details["completed_at"] == "2026-01-19T09:30:00Z"
        assert error.details["task_id"] == "task-456"  # Should be included in details
        assert error.details["current_status"] == "failed"  # Should be included in details

    def test_task_already_completed_error_inheritance(self) -> None:
        """Test that TaskAlreadyCompletedError inherits from ASAPError."""
        error = TaskAlreadyCompletedError("task-789", "cancelled")

        assert isinstance(error, ASAPError)
        assert isinstance(error, Exception)


class TestErrorSerialization:
    """Test error serialization to dictionary."""

    def test_asap_error_to_dict_basic(self) -> None:
        """Test basic ASAPError serialization to dictionary."""
        error = ASAPError(code="asap:test/error", message="Test error message")
        result = error.to_dict()

        assert result == {
            "code": "asap:test/error",
            "message": "Test error message",
            "details": {},
        }

    def test_asap_error_to_dict_with_details(self) -> None:
        """Test ASAPError serialization with details."""
        details = {"context": "test", "value": 42, "nested": {"key": "value"}}
        error = ASAPError(
            code="asap:test/detailed_error", message="Detailed error", details=details
        )
        result = error.to_dict()

        assert result == {
            "code": "asap:test/detailed_error",
            "message": "Detailed error",
            "details": details,
        }

    def test_invalid_transition_error_to_dict(self) -> None:
        """Test InvalidTransitionError serialization."""
        error = InvalidTransitionError(from_state="working", to_state="completed")
        result = error.to_dict()

        assert result["code"] == "asap:protocol/invalid_state"
        assert "Invalid transition from 'working' to 'completed'" in result["message"]
        assert result["details"]["from_state"] == "working"
        assert result["details"]["to_state"] == "completed"

    def test_malformed_envelope_error_to_dict(self) -> None:
        """Test MalformedEnvelopeError serialization."""
        error = MalformedEnvelopeError(reason="missing required field 'id'")
        result = error.to_dict()

        assert result["code"] == "asap:protocol/malformed_envelope"
        assert "Malformed envelope: missing required field 'id'" in result["message"]
        assert result["details"] == {}

    def test_task_not_found_error_to_dict(self) -> None:
        """Test TaskNotFoundError serialization."""
        error = TaskNotFoundError(task_id="task-123")
        result = error.to_dict()

        assert result["code"] == "asap:task/not_found"
        assert "Task not found: task-123" in result["message"]
        assert result["details"]["task_id"] == "task-123"

    def test_task_already_completed_error_to_dict(self) -> None:
        """Test TaskAlreadyCompletedError serialization."""
        error = TaskAlreadyCompletedError(task_id="task-123", current_status="completed")
        result = error.to_dict()

        assert result["code"] == "asap:task/already_completed"
        assert "Task already completed: task-123 (status: completed)" in result["message"]
        assert result["details"]["task_id"] == "task-123"
        assert result["details"]["current_status"] == "completed"

    def test_error_to_dict_is_json_serializable(self) -> None:
        """Test that to_dict() returns JSON-serializable data."""
        import json

        error = ASAPError(
            code="asap:test/error",
            message="Test error",
            details={"number": 42, "string": "value", "list": [1, 2, 3]},
        )
        result = error.to_dict()

        # Should not raise exception
        json_str = json.dumps(result)
        assert isinstance(json_str, str)

        # Should be able to parse back
        parsed = json.loads(json_str)
        assert parsed == result


class TestThreadPoolExhaustedError:
    """Test ThreadPoolExhaustedError class."""

    def test_basic_thread_pool_exhausted_error(self) -> None:
        """Test creating a ThreadPoolExhaustedError."""
        error = ThreadPoolExhaustedError(max_threads=10, active_threads=10)

        assert error.code == "asap:transport/thread_pool_exhausted"
        assert error.max_threads == 10
        assert error.active_threads == 10
        assert "Thread pool exhausted: 10/10 threads in use" in str(error)
        assert "Service temporarily unavailable" in str(error)

    def test_thread_pool_exhausted_error_with_details(self) -> None:
        """Test ThreadPoolExhaustedError with additional details."""
        details = {"queue_size": 100, "rejected_requests": 5}
        error = ThreadPoolExhaustedError(max_threads=20, active_threads=18, details=details)

        assert error.code == "asap:transport/thread_pool_exhausted"
        assert error.max_threads == 20
        assert error.active_threads == 18
        assert error.details["queue_size"] == 100
        assert error.details["rejected_requests"] == 5
        assert error.details["max_threads"] == 20
        assert error.details["active_threads"] == 18

    def test_thread_pool_exhausted_error_inheritance(self) -> None:
        """Test that ThreadPoolExhaustedError inherits from ASAPError."""
        error = ThreadPoolExhaustedError(max_threads=5, active_threads=5)

        assert isinstance(error, ASAPError)
        assert isinstance(error, Exception)

    def test_thread_pool_exhausted_error_to_dict(self) -> None:
        """Test ThreadPoolExhaustedError serialization."""
        error = ThreadPoolExhaustedError(max_threads=15, active_threads=15)
        result = error.to_dict()

        assert result["code"] == "asap:transport/thread_pool_exhausted"
        assert "Thread pool exhausted" in result["message"]
        assert result["details"]["max_threads"] == 15
        assert result["details"]["active_threads"] == 15
