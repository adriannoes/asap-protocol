"""Tests for Task payload models (requests, responses, updates, cancellations)."""


class TestTaskRequest:
    """Test suite for TaskRequest payload model."""

    def test_task_request_creation_minimal(self):
        """Test creating a TaskRequest with minimal required fields."""
        from asap.models.payloads import TaskRequest

        request = TaskRequest(
            conversation_id="conv_01HX5K3MQVN8",
            skill_id="web_research",
            input={"query": "AI trends"},
        )

        assert request.conversation_id == "conv_01HX5K3MQVN8"
        assert request.skill_id == "web_research"
        assert request.input["query"] == "AI trends"
        assert request.parent_task_id is None
        assert request.config is None

    def test_task_request_with_parent_task(self):
        """Test TaskRequest with parent_task_id."""
        from asap.models.payloads import TaskRequest

        request = TaskRequest(
            conversation_id="conv_123",
            parent_task_id="task_parent_456",
            skill_id="analysis",
            input={"data": [1, 2, 3]},
        )

        assert request.parent_task_id == "task_parent_456"

    def test_task_request_with_config(self):
        """Test TaskRequest with configuration."""
        from asap.models.payloads import TaskRequest

        config = {
            "timeout_seconds": 600,
            "priority": "normal",
            "idempotency_key": "idem_01HX5K9T",
            "streaming": True,
            "persist_state": True,
        }

        request = TaskRequest(
            conversation_id="conv_123",
            skill_id="web_research",
            input={"query": "test"},
            config=config,
        )

        assert request.config is not None
        assert request.config["timeout_seconds"] == 600
        assert request.config["streaming"] is True
        assert request.config["persist_state"] is True

    def test_task_request_json_schema(self):
        """Test that TaskRequest generates valid JSON Schema."""
        from asap.models.payloads import TaskRequest

        schema = TaskRequest.model_json_schema()

        assert schema["type"] == "object"
        assert "conversation_id" in schema["properties"]
        assert "skill_id" in schema["properties"]
        assert "input" in schema["properties"]
        assert "config" in schema["properties"]

        required = set(schema["required"])
        assert "conversation_id" in required
        assert "skill_id" in required
        assert "input" in required


class TestTaskResponse:
    """Test suite for TaskResponse payload model."""

    def test_task_response_creation_minimal(self):
        """Test creating a TaskResponse with minimal required fields."""
        from asap.models.payloads import TaskResponse

        response = TaskResponse(task_id="task_01HX5K4N", status="completed")

        assert response.task_id == "task_01HX5K4N"
        assert response.status == "completed"
        assert response.result is None
        assert response.final_state is None
        assert response.metrics is None

    def test_task_response_with_result(self):
        """Test TaskResponse with result data."""
        from asap.models.payloads import TaskResponse

        result = {"summary": "Analysis complete with 3 key findings", "artifacts": ["art_01HX5K6Q"]}

        response = TaskResponse(task_id="task_123", status="completed", result=result)

        assert response.result is not None
        assert response.result["summary"] == "Analysis complete with 3 key findings"
        assert len(response.result["artifacts"]) == 1

    def test_task_response_with_final_state(self):
        """Test TaskResponse with final state snapshot."""
        from asap.models.payloads import TaskResponse

        final_state = {"version": 5, "data": {"completed": True, "findings": 3}}

        response = TaskResponse(task_id="task_123", status="completed", final_state=final_state)

        assert response.final_state is not None
        assert response.final_state["version"] == 5

    def test_task_response_with_metrics(self):
        """Test TaskResponse with execution metrics."""
        from asap.models.payloads import TaskResponse

        metrics = {"duration_ms": 45000, "tokens_used": 12500}

        response = TaskResponse(task_id="task_123", status="completed", metrics=metrics)

        assert response.metrics is not None
        assert response.metrics["duration_ms"] == 45000
        assert response.metrics["tokens_used"] == 12500

    def test_task_response_json_schema(self):
        """Test that TaskResponse generates valid JSON Schema."""
        from asap.models.payloads import TaskResponse

        schema = TaskResponse.model_json_schema()

        assert schema["type"] == "object"
        assert "task_id" in schema["properties"]
        assert "status" in schema["properties"]

        required = set(schema["required"])
        assert "task_id" in required
        assert "status" in required


class TestTaskUpdate:
    """Test suite for TaskUpdate payload model."""

    def test_task_update_progress(self):
        """Test TaskUpdate with progress type."""
        from asap.models.payloads import TaskUpdate

        progress = {
            "percent": 65,
            "message": "Synthesizing findings...",
            "estimated_remaining_seconds": 120,
        }

        update = TaskUpdate(
            task_id="task_123", update_type="progress", status="working", progress=progress
        )

        assert update.task_id == "task_123"
        assert update.update_type == "progress"
        assert update.status == "working"
        assert update.progress is not None
        assert update.progress["percent"] == 65
        assert update.input_request is None

    def test_task_update_input_required(self):
        """Test TaskUpdate with input_required type."""
        from asap.models.payloads import TaskUpdate

        input_request = {
            "prompt": "Multiple interpretations found. Please clarify:",
            "options": [
                {"id": "opt_1", "label": "Focus on cloud infrastructure"},
                {"id": "opt_2", "label": "Focus on on-premise solutions"},
            ],
            "schema": {"$ref": "#/definitions/ClarificationInput"},
        }

        update = TaskUpdate(
            task_id="task_123",
            update_type="input_required",
            status="input_required",
            input_request=input_request,
        )

        assert update.update_type == "input_required"
        assert update.status == "input_required"
        assert update.input_request is not None
        assert len(update.input_request["options"]) == 2
        assert update.progress is None

    def test_task_update_json_schema(self):
        """Test that TaskUpdate generates valid JSON Schema."""
        from asap.models.payloads import TaskUpdate

        schema = TaskUpdate.model_json_schema()

        assert schema["type"] == "object"
        assert "task_id" in schema["properties"]
        assert "update_type" in schema["properties"]
        assert "status" in schema["properties"]

        required = set(schema["required"])
        assert "task_id" in required
        assert "update_type" in required
        assert "status" in required

    def test_task_update_progress_percent_not_numeric_raises_error(self):
        """Test that non-numeric progress.percent raises ValueError."""
        import pytest

        from asap.models.payloads import TaskUpdate

        with pytest.raises(ValueError, match="progress.percent must be a number"):
            TaskUpdate(
                task_id="task_123",
                update_type="progress",
                status="working",
                progress={"percent": "fifty"},  # String instead of number
            )

    def test_task_update_progress_percent_out_of_range_raises_error(self):
        """Test that progress.percent outside 0-100 raises ValueError."""
        import pytest

        from asap.models.payloads import TaskUpdate

        with pytest.raises(ValueError, match="progress.percent must be between 0 and 100"):
            TaskUpdate(
                task_id="task_123",
                update_type="progress",
                status="working",
                progress={"percent": 150},  # Over 100
            )

        with pytest.raises(ValueError, match="progress.percent must be between 0 and 100"):
            TaskUpdate(
                task_id="task_123",
                update_type="progress",
                status="working",
                progress={"percent": -10},  # Negative
            )

    def test_task_update_progress_without_percent_is_valid(self):
        """Test that progress without percent field is valid."""
        from asap.models.payloads import TaskUpdate

        update = TaskUpdate(
            task_id="task_123",
            update_type="progress",
            status="working",
            progress={"message": "Working..."},  # No percent field
        )

        assert update.progress["message"] == "Working..."

    def test_task_update_progress_percent_at_boundaries(self):
        """Test that progress.percent at 0 and 100 are valid."""
        from asap.models.payloads import TaskUpdate

        update_zero = TaskUpdate(
            task_id="task_123",
            update_type="progress",
            status="working",
            progress={"percent": 0},
        )
        assert update_zero.progress["percent"] == 0

        update_hundred = TaskUpdate(
            task_id="task_456",
            update_type="progress",
            status="working",
            progress={"percent": 100},
        )
        assert update_hundred.progress["percent"] == 100


class TestTaskCancel:
    """Test suite for TaskCancel payload model."""

    def test_task_cancel_creation(self):
        """Test creating a TaskCancel request."""
        from asap.models.payloads import TaskCancel

        cancel = TaskCancel(task_id="task_123", reason="User requested cancellation")

        assert cancel.task_id == "task_123"
        assert cancel.reason == "User requested cancellation"

    def test_task_cancel_optional_reason(self):
        """Test TaskCancel with optional reason."""
        from asap.models.payloads import TaskCancel

        cancel = TaskCancel(task_id="task_456")

        assert cancel.task_id == "task_456"
        assert cancel.reason is None

    def test_task_cancel_json_schema(self):
        """Test that TaskCancel generates valid JSON Schema."""
        from asap.models.payloads import TaskCancel

        schema = TaskCancel.model_json_schema()

        assert schema["type"] == "object"
        assert "task_id" in schema["properties"]
        assert "reason" in schema["properties"]

        required = set(schema["required"])
        assert "task_id" in required


class TestMessageSend:
    """Test suite for MessageSend payload model."""

    def test_message_send_creation(self):
        """Test creating a MessageSend payload."""
        from asap.models.payloads import MessageSend

        message_send = MessageSend(
            task_id="task_123",
            message_id="msg_456",
            sender="urn:asap:agent:coordinator",
            role="user",
            parts=["part_789"],
        )

        assert message_send.task_id == "task_123"
        assert message_send.message_id == "msg_456"
        assert message_send.sender == "urn:asap:agent:coordinator"
        assert message_send.role == "user"
        assert len(message_send.parts) == 1

    def test_message_send_multiple_parts(self):
        """Test MessageSend with multiple parts."""
        from asap.models.payloads import MessageSend

        message_send = MessageSend(
            task_id="task_123",
            message_id="msg_456",
            sender="urn:asap:agent:assistant",
            role="assistant",
            parts=["part_1", "part_2", "part_3"],
        )

        assert len(message_send.parts) == 3
        assert message_send.role == "assistant"

    def test_message_send_json_schema(self):
        """Test that MessageSend generates valid JSON Schema."""
        from asap.models.payloads import MessageSend

        schema = MessageSend.model_json_schema()

        assert schema["type"] == "object"
        assert "task_id" in schema["properties"]
        assert "message_id" in schema["properties"]
        assert "sender" in schema["properties"]
        assert "role" in schema["properties"]
        assert "parts" in schema["properties"]

        required = set(schema["required"])
        assert "task_id" in required
        assert "message_id" in required
        assert "sender" in required
        assert "role" in required
        assert "parts" in required


class TestStateQuery:
    """Test suite for StateQuery payload model."""

    def test_state_query_creation(self):
        """Test creating a StateQuery payload."""
        from asap.models.payloads import StateQuery

        query = StateQuery(task_id="task_123")

        assert query.task_id == "task_123"
        assert query.version is None

    def test_state_query_with_version(self):
        """Test StateQuery with specific version."""
        from asap.models.payloads import StateQuery

        query = StateQuery(task_id="task_123", version=5)

        assert query.task_id == "task_123"
        assert query.version == 5

    def test_state_query_json_schema(self):
        """Test that StateQuery generates valid JSON Schema."""
        from asap.models.payloads import StateQuery

        schema = StateQuery.model_json_schema()

        assert schema["type"] == "object"
        assert "task_id" in schema["properties"]
        assert "version" in schema["properties"]

        required = set(schema["required"])
        assert "task_id" in required


class TestStateRestore:
    """Test suite for StateRestore payload model."""

    def test_state_restore_creation(self):
        """Test creating a StateRestore payload."""
        from asap.models.payloads import StateRestore

        restore = StateRestore(task_id="task_123", snapshot_id="snap_456")

        assert restore.task_id == "task_123"
        assert restore.snapshot_id == "snap_456"

    def test_state_restore_json_schema(self):
        """Test that StateRestore generates valid JSON Schema."""
        from asap.models.payloads import StateRestore

        schema = StateRestore.model_json_schema()

        assert schema["type"] == "object"
        assert "task_id" in schema["properties"]
        assert "snapshot_id" in schema["properties"]

        required = set(schema["required"])
        assert "task_id" in required
        assert "snapshot_id" in required


class TestArtifactNotify:
    """Test suite for ArtifactNotify payload model."""

    def test_artifact_notify_creation(self):
        """Test creating an ArtifactNotify payload."""
        from asap.models.payloads import ArtifactNotify

        notify = ArtifactNotify(artifact_id="art_123", task_id="task_456")

        assert notify.artifact_id == "art_123"
        assert notify.task_id == "task_456"
        assert notify.name is None

    def test_artifact_notify_with_name(self):
        """Test ArtifactNotify with optional name."""
        from asap.models.payloads import ArtifactNotify

        notify = ArtifactNotify(
            artifact_id="art_123", task_id="task_456", name="Q3 Market Analysis Report"
        )

        assert notify.name == "Q3 Market Analysis Report"

    def test_artifact_notify_json_schema(self):
        """Test that ArtifactNotify generates valid JSON Schema."""
        from asap.models.payloads import ArtifactNotify

        schema = ArtifactNotify.model_json_schema()

        assert schema["type"] == "object"
        assert "artifact_id" in schema["properties"]
        assert "task_id" in schema["properties"]
        assert "name" in schema["properties"]

        required = set(schema["required"])
        assert "artifact_id" in required
        assert "task_id" in required


class TestMcpToolCall:
    """Test suite for McpToolCall payload model."""

    def test_mcp_tool_call_creation(self):
        """Test creating an McpToolCall payload."""
        from asap.models.payloads import McpToolCall

        tool_call = McpToolCall(
            request_id="req_123",
            tool_name="web_search",
            arguments={"query": "AI trends", "max_results": 10},
        )

        assert tool_call.request_id == "req_123"
        assert tool_call.tool_name == "web_search"
        assert tool_call.arguments["query"] == "AI trends"
        assert tool_call.mcp_context is None

    def test_mcp_tool_call_with_context(self):
        """Test McpToolCall with MCP context."""
        from asap.models.payloads import McpToolCall

        mcp_context = {"server": "mcp://tools.example.com", "session_id": "sess_456"}

        tool_call = McpToolCall(
            request_id="req_123",
            tool_name="analyze_data",
            arguments={"data": [1, 2, 3]},
            mcp_context=mcp_context,
        )

        assert tool_call.mcp_context is not None
        assert tool_call.mcp_context["server"] == "mcp://tools.example.com"

    def test_mcp_tool_call_json_schema(self):
        """Test that McpToolCall generates valid JSON Schema."""
        from asap.models.payloads import McpToolCall

        schema = McpToolCall.model_json_schema()

        assert schema["type"] == "object"
        assert "request_id" in schema["properties"]
        assert "tool_name" in schema["properties"]
        assert "arguments" in schema["properties"]
        assert "mcp_context" in schema["properties"]

        required = set(schema["required"])
        assert "request_id" in required
        assert "tool_name" in required
        assert "arguments" in required


class TestMcpToolResult:
    """Test suite for McpToolResult payload model."""

    def test_mcp_tool_result_success(self):
        """Test creating a successful McpToolResult."""
        from asap.models.payloads import McpToolResult

        result = McpToolResult(
            request_id="req_123",
            success=True,
            result={"findings": ["finding1", "finding2"], "count": 2},
        )

        assert result.request_id == "req_123"
        assert result.success is True
        assert result.result["count"] == 2
        assert result.error is None

    def test_mcp_tool_result_failure(self):
        """Test creating a failed McpToolResult."""
        from asap.models.payloads import McpToolResult

        result = McpToolResult(
            request_id="req_123", success=False, error="Tool execution failed: timeout"
        )

        assert result.success is False
        assert result.error == "Tool execution failed: timeout"
        assert result.result is None

    def test_mcp_tool_result_json_schema(self):
        """Test that McpToolResult generates valid JSON Schema."""
        from asap.models.payloads import McpToolResult

        schema = McpToolResult.model_json_schema()

        assert schema["type"] == "object"
        assert "request_id" in schema["properties"]
        assert "success" in schema["properties"]
        assert "result" in schema["properties"]
        assert "error" in schema["properties"]

        required = set(schema["required"])
        assert "request_id" in required
        assert "success" in required


class TestMcpResourceFetch:
    """Test suite for McpResourceFetch payload model."""

    def test_mcp_resource_fetch_creation(self):
        """Test creating an McpResourceFetch payload."""
        from asap.models.payloads import McpResourceFetch

        fetch = McpResourceFetch(resource_uri="mcp://server/resources/data_123")

        assert fetch.resource_uri == "mcp://server/resources/data_123"

    def test_mcp_resource_fetch_various_uris(self):
        """Test McpResourceFetch with different URI schemes."""
        from asap.models.payloads import McpResourceFetch

        uris = ["mcp://server/resource", "asap://resource/123", "https://example.com/resource"]

        for uri in uris:
            fetch = McpResourceFetch(resource_uri=uri)
            assert fetch.resource_uri == uri

    def test_mcp_resource_fetch_json_schema(self):
        """Test that McpResourceFetch generates valid JSON Schema."""
        from asap.models.payloads import McpResourceFetch

        schema = McpResourceFetch.model_json_schema()

        assert schema["type"] == "object"
        assert "resource_uri" in schema["properties"]

        required = set(schema["required"])
        assert "resource_uri" in required


class TestMcpResourceData:
    """Test suite for McpResourceData payload model."""

    def test_mcp_resource_data_creation(self):
        """Test creating an McpResourceData payload."""
        from asap.models.payloads import McpResourceData

        data = McpResourceData(
            resource_uri="mcp://server/resources/data_123",
            content={"data": [1, 2, 3], "metadata": {"source": "api"}},
        )

        assert data.resource_uri == "mcp://server/resources/data_123"
        assert data.content["data"] == [1, 2, 3]
        assert data.content["metadata"]["source"] == "api"

    def test_mcp_resource_data_text_content(self):
        """Test McpResourceData with text content."""
        from asap.models.payloads import McpResourceData

        data = McpResourceData(
            resource_uri="mcp://server/docs/readme",
            content={"text": "This is a readme file", "format": "markdown"},
        )

        assert data.content["text"] == "This is a readme file"
        assert data.content["format"] == "markdown"

    def test_mcp_resource_data_json_schema(self):
        """Test that McpResourceData generates valid JSON Schema."""
        from asap.models.payloads import McpResourceData

        schema = McpResourceData.model_json_schema()

        assert schema["type"] == "object"
        assert "resource_uri" in schema["properties"]
        assert "content" in schema["properties"]

        required = set(schema["required"])
        assert "resource_uri" in required
        assert "content" in required
