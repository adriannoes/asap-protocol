"""Payload models for ASAP protocol messages.

Payloads define the content of protocol messages for different operations
like task requests, responses, updates, state management, and MCP integration.
"""

from typing import Any, Literal, Union

from pydantic import ConfigDict, Field, field_validator, model_validator

from asap.models.base import ASAPBaseModel
from asap.models.enums import MessageRole, TaskStatus, UpdateType
from asap.models.types import (
    AgentURN,
    ArtifactID,
    ConversationID,
    MessageID,
    PartID,
    SnapshotID,
    TaskID,
)


class TaskRequestConfig(ASAPBaseModel):
    """TaskRequest.config (extra allowed)."""

    model_config = ConfigDict(extra="allow")

    timeout_seconds: int | None = Field(
        default=None, ge=1, description="Maximum execution time in seconds"
    )
    priority: str | None = Field(
        default=None, description="Task priority (e.g., 'low', 'normal', 'high')"
    )
    idempotency_key: str | None = Field(default=None, description="Key for idempotent execution")
    streaming: bool | None = Field(default=None, description="Whether to stream progress updates")
    persist_state: bool | None = Field(
        default=None, description="Whether to persist state snapshots"
    )
    model: str | None = Field(default=None, description="LLM model identifier")
    temperature: float | None = Field(default=None, ge=0, le=2, description="LLM temperature (0-2)")


class TaskMetrics(ASAPBaseModel):
    """TaskResponse.metrics (extra allowed)."""

    model_config = ConfigDict(extra="allow")

    duration_ms: int | None = Field(
        default=None, ge=0, description="Execution duration in milliseconds"
    )
    tokens_in: int | None = Field(default=None, ge=0, description="Input token count")
    tokens_out: int | None = Field(default=None, ge=0, description="Output token count")
    tokens_used: int | None = Field(
        default=None, ge=0, description="Total tokens (fallback for tokens_out)"
    )
    api_calls: int | None = Field(default=None, ge=0, description="Number of API calls")


class TaskRequest(ASAPBaseModel):
    """Request to execute a task on an agent.

    TaskRequest initiates task execution, specifying the skill to invoke,
    input data, and optional configuration parameters.

    Attributes:
        conversation_id: ID of the conversation this task belongs to
        parent_task_id: Optional ID of parent task (for subtasks)
        skill_id: Identifier of the skill to execute
        input: Input data for the skill (JSON-serializable)
        config: Optional configuration (timeout, priority, streaming, etc.)
    """

    conversation_id: ConversationID = Field(..., description="Parent conversation ID")
    parent_task_id: TaskID | None = Field(default=None, description="Parent task ID for subtasks")
    skill_id: str = Field(..., description="Skill identifier to execute")
    input: dict[str, Any] = Field(..., description="Input data for the skill (skill-specific)")
    config: TaskRequestConfig | None = Field(
        default=None, description="Optional configuration (timeout, priority, streaming, etc.)"
    )


class TaskResponse(ASAPBaseModel):
    """Response to a task execution request.

    TaskResponse provides the final result of task execution, including
    status, result data, final state snapshot, and execution metrics.

    Attributes:
        task_id: ID of the completed task
        status: Final task status (completed, failed, cancelled, etc.)
        result: Optional result data (summary, artifacts, etc.)
        final_state: Optional final state snapshot
        metrics: Optional execution metrics (duration, tokens used, etc.)
    """

    task_id: TaskID = Field(..., description="Task identifier")
    status: TaskStatus = Field(..., description="Final task status")
    result: dict[str, Any] | None = Field(
        default=None, description="Result data (summary, artifacts, etc.)"
    )
    final_state: dict[str, Any] | None = Field(default=None, description="Final state snapshot")
    metrics: TaskMetrics | None = Field(
        default=None, description="Execution metrics (duration, tokens, etc.)"
    )


class TaskUpdate(ASAPBaseModel):
    """Update on task execution progress or status.

    TaskUpdate provides real-time updates during task execution, including
    progress information or requests for additional input.

    Attributes:
        task_id: ID of the task being updated
        update_type: Type of update (progress, input_required, etc.)
        status: Current task status
        progress: Optional progress information (percent, message, ETA)
        input_request: Optional request for additional input from user
    """

    task_id: TaskID = Field(..., description="Task identifier")
    update_type: UpdateType = Field(..., description="Update type (progress, input_required)")
    status: TaskStatus = Field(..., description="Current task status")
    progress: dict[str, Any] | None = Field(
        default=None, description="Progress info (percent, message, ETA)"
    )
    input_request: dict[str, Any] | None = Field(
        default=None, description="Request for additional input"
    )

    @field_validator("progress")
    @classmethod
    def validate_progress_percent(cls, v: dict[str, Any] | None) -> dict[str, Any] | None:
        if v and "percent" in v:
            percent = v["percent"]
            if not isinstance(percent, (int, float)):
                raise ValueError("progress.percent must be a number")
            if not (0 <= percent <= 100):
                raise ValueError("progress.percent must be between 0 and 100")
        return v


class TaskCancel(ASAPBaseModel):
    """Request to cancel a running task.

    TaskCancel requests cancellation of a task that is currently executing.
    The agent should attempt graceful cancellation and cleanup.

    Attributes:
        task_id: ID of the task to cancel
        reason: Optional reason for cancellation
    """

    task_id: TaskID = Field(..., description="Task identifier to cancel")
    reason: str | None = Field(default=None, description="Optional cancellation reason")


class MessageSend(ASAPBaseModel):
    """Send a message within a task conversation.

    MessageSend exchanges conversation turns between agents during
    task execution, containing message content as parts.

    Attributes:
        task_id: ID of the task this message belongs to
        message_id: Unique identifier for this message
        sender: Agent URN of the message sender
        role: Message role (user, assistant, system)
        parts: List of part IDs that make up this message
    """

    task_id: TaskID = Field(..., description="Parent task ID")
    message_id: MessageID = Field(..., description="Unique message identifier")
    sender: AgentURN = Field(..., description="Sender agent URN")
    role: MessageRole = Field(..., description="Message role (user, assistant, system)")
    parts: list[PartID] = Field(..., description="Part IDs making up this message")


class StateQuery(ASAPBaseModel):
    """Request a state snapshot for a task.

    StateQuery requests the current or a specific version of a task's
    state snapshot for inspection or restoration.

    Attributes:
        task_id: ID of the task to query state for
        version: Optional specific version number to retrieve
    """

    task_id: TaskID = Field(..., description="Task identifier")
    version: int | None = Field(default=None, description="Optional specific version to retrieve")


class StateRestore(ASAPBaseModel):
    """Restore a task to a previous state snapshot.

    StateRestore requests restoration of a task to a previously saved
    state snapshot, enabling rollback and recovery scenarios.

    Attributes:
        task_id: ID of the task to restore
        snapshot_id: ID of the snapshot to restore from
    """

    task_id: TaskID = Field(..., description="Task identifier")
    snapshot_id: SnapshotID = Field(..., description="Snapshot ID to restore from")


class ArtifactNotify(ASAPBaseModel):
    """Notify about artifact creation or availability.

    ArtifactNotify informs agents when a new artifact has been created
    or is available for retrieval.

    Attributes:
        artifact_id: ID of the artifact
        task_id: ID of the task that produced the artifact
        name: Optional human-readable artifact name
    """

    artifact_id: ArtifactID = Field(..., description="Artifact identifier")
    task_id: TaskID = Field(..., description="Parent task ID")
    name: str | None = Field(default=None, description="Optional human-readable artifact name")


class McpToolCall(ASAPBaseModel):
    """Call an MCP tool.

    McpToolCall invokes a tool provided by an MCP server, enabling
    agents to leverage external capabilities and integrations.

    Attributes:
        request_id: Unique identifier for this tool call request
        tool_name: Name of the MCP tool to invoke
        arguments: Arguments to pass to the tool (JSON-serializable)
        mcp_context: Optional MCP-specific context (server, session, etc.)
    """

    request_id: str = Field(..., description="Unique request identifier")
    tool_name: str = Field(..., description="MCP tool name to invoke")
    arguments: dict[str, Any] = Field(..., description="Tool arguments (JSON-serializable)")
    mcp_context: dict[str, Any] | None = Field(
        default=None, description="Optional MCP context (server, session, etc.)"
    )


class McpToolResult(ASAPBaseModel):
    """Result of an MCP tool call.

    McpToolResult provides the outcome of an MCP tool invocation,
    including success status, result data, or error information.

    Attributes:
        request_id: ID of the original tool call request
        success: Whether the tool call succeeded
        result: Optional result data (if successful)
        error: Optional error message (if failed)
    """

    request_id: str = Field(..., description="Original request identifier")
    success: bool = Field(..., description="Whether tool call succeeded")
    result: dict[str, Any] | None = Field(default=None, description="Result data (if successful)")
    error: str | None = Field(default=None, description="Error message (if failed)")

    @model_validator(mode="after")
    def validate_result_error_exclusivity(self) -> "McpToolResult":
        if self.success:
            if self.result is None:
                raise ValueError("result must be provided when success=True")
            if self.error is not None:
                raise ValueError("error must be None when success=True")
        else:
            if self.error is None:
                raise ValueError("error must be provided when success=False")
            if self.result is not None:
                raise ValueError("result must be None when success=False")
        return self


class McpResourceFetch(ASAPBaseModel):
    """Request to fetch an MCP resource.

    McpResourceFetch requests retrieval of a resource from an MCP server,
    such as documentation, data, or other content.

    Attributes:
        resource_uri: URI of the MCP resource to fetch
    """

    resource_uri: str = Field(..., description="MCP resource URI to fetch")


class McpResourceData(ASAPBaseModel):
    """Data from an MCP resource.

    McpResourceData provides the content of a fetched MCP resource.

    Attributes:
        resource_uri: URI of the resource
        content: Resource content (JSON-serializable)
    """

    resource_uri: str = Field(..., description="MCP resource URI")
    content: dict[str, Any] = Field(..., description="Resource content (JSON-serializable)")


class MessageAck(ASAPBaseModel):
    """Application-level ack for WebSocket state-changing messages (ADR-16)."""

    original_envelope_id: str = Field(..., description="Envelope ID being acknowledged")
    status: Literal["received", "processed", "rejected"] = Field(...)
    error: str | None = Field(default=None, description="Reason when rejected")


# Normalized payload_type -> PayloadType class (Envelope strict validation).
PAYLOAD_TYPE_REGISTRY: dict[str, type[ASAPBaseModel]] = {
    "taskrequest": TaskRequest,
    "taskresponse": TaskResponse,
    "taskupdate": TaskUpdate,
    "taskcancel": TaskCancel,
    "messagesend": MessageSend,
    "statequery": StateQuery,
    "staterestore": StateRestore,
    "artifactnotify": ArtifactNotify,
    "mcptoolcall": McpToolCall,
    "mcptoolresult": McpToolResult,
    "mcpresourcefetch": McpResourceFetch,
    "mcpresourcedata": McpResourceData,
    "messageack": MessageAck,
}

# Union type for all payload types
# Note: The discriminator (payload_type) will be in the Envelope, not in individual payloads
PayloadType = Union[
    TaskRequest,
    TaskResponse,
    TaskUpdate,
    TaskCancel,
    MessageSend,
    StateQuery,
    StateRestore,
    ArtifactNotify,
    McpToolCall,
    McpToolResult,
    McpResourceFetch,
    McpResourceData,
    MessageAck,
]
"""Union type of all ASAP payload types.

PayloadType represents any of the 13 payload types used in ASAP protocol messages.
The actual payload type discrimination is done via the 'payload_type' field in the
Envelope that wraps these payloads.

Payload types:
- Task operations: TaskRequest, TaskResponse, TaskUpdate, TaskCancel
- Messaging: MessageSend
- State management: StateQuery, StateRestore, ArtifactNotify
- MCP integration: McpToolCall, McpToolResult, McpResourceFetch, McpResourceData
- WebSocket reliability: MessageAck (ADR-16)
"""
