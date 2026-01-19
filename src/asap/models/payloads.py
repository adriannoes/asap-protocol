"""Payload models for ASAP protocol messages.

Payloads define the content of protocol messages for different operations
like task requests, responses, updates, state management, and MCP integration.
"""

from typing import Any, Union

from pydantic import Field

from asap.models.base import ASAPBaseModel
from asap.models.enums import TaskStatus, UpdateType
from asap.models.types import (
    AgentURN,
    ArtifactID,
    ConversationID,
    MessageID,
    PartID,
    SnapshotID,
    TaskID,
)


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

    Example:
        >>> request = TaskRequest(
        ...     conversation_id="conv_01HX5K3MQVN8",
        ...     skill_id="web_research",
        ...     input={"query": "AI infrastructure market trends Q3 2025"},
        ...     config={"timeout_seconds": 600, "streaming": True}
        ... )
    """

    conversation_id: ConversationID = Field(..., description="Parent conversation ID")
    parent_task_id: TaskID | None = Field(default=None, description="Parent task ID for subtasks")
    skill_id: str = Field(..., description="Skill identifier to execute")
    input: dict[str, Any] = Field(..., description="Input data for the skill")
    config: dict[str, Any] | None = Field(
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

    Example:
        >>> response = TaskResponse(
        ...     task_id="task_01HX5K4N",
        ...     status="completed",
        ...     result={"summary": "Analysis complete", "artifacts": ["art_123"]},
        ...     metrics={"duration_ms": 45000, "tokens_used": 12500}
        ... )
    """

    task_id: TaskID = Field(..., description="Task identifier")
    status: TaskStatus = Field(..., description="Final task status")
    result: dict[str, Any] | None = Field(
        default=None, description="Result data (summary, artifacts, etc.)"
    )
    final_state: dict[str, Any] | None = Field(default=None, description="Final state snapshot")
    metrics: dict[str, Any] | None = Field(
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

    Example:
        >>> # Progress update
        >>> update = TaskUpdate(
        ...     task_id="task_123",
        ...     update_type="progress",
        ...     status="working",
        ...     progress={"percent": 65, "message": "Synthesizing findings..."}
        ... )
        >>>
        >>> # Input required update
        >>> update = TaskUpdate(
        ...     task_id="task_123",
        ...     update_type="input_required",
        ...     status="input_required",
        ...     input_request={"prompt": "Please clarify:", "options": [...]}
        ... )
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


class TaskCancel(ASAPBaseModel):
    """Request to cancel a running task.

    TaskCancel requests cancellation of a task that is currently executing.
    The agent should attempt graceful cancellation and cleanup.

    Attributes:
        task_id: ID of the task to cancel
        reason: Optional reason for cancellation

    Example:
        >>> cancel = TaskCancel(
        ...     task_id="task_123",
        ...     reason="User requested cancellation"
        ... )
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

    Example:
        >>> message = MessageSend(
        ...     task_id="task_123",
        ...     message_id="msg_456",
        ...     sender="urn:asap:agent:coordinator",
        ...     role="user",
        ...     parts=["part_789"]
        ... )
    """

    task_id: TaskID = Field(..., description="Parent task ID")
    message_id: MessageID = Field(..., description="Unique message identifier")
    sender: AgentURN = Field(..., description="Sender agent URN")
    role: str = Field(..., description="Message role (user, assistant, system)")
    parts: list[PartID] = Field(..., description="Part IDs making up this message")


class StateQuery(ASAPBaseModel):
    """Request a state snapshot for a task.

    StateQuery requests the current or a specific version of a task's
    state snapshot for inspection or restoration.

    Attributes:
        task_id: ID of the task to query state for
        version: Optional specific version number to retrieve

    Example:
        >>> # Query latest state
        >>> query = StateQuery(task_id="task_123")
        >>>
        >>> # Query specific version
        >>> query = StateQuery(task_id="task_123", version=5)
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

    Example:
        >>> restore = StateRestore(
        ...     task_id="task_123",
        ...     snapshot_id="snap_456"
        ... )
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

    Example:
        >>> notify = ArtifactNotify(
        ...     artifact_id="art_123",
        ...     task_id="task_456",
        ...     name="Q3 Market Analysis Report"
        ... )
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

    Example:
        >>> tool_call = McpToolCall(
        ...     request_id="req_123",
        ...     tool_name="web_search",
        ...     arguments={"query": "AI trends", "max_results": 10},
        ...     mcp_context={"server": "mcp://tools.example.com"}
        ... )
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

    Example:
        >>> # Successful result
        >>> result = McpToolResult(
        ...     request_id="req_123",
        ...     success=True,
        ...     result={"findings": ["finding1", "finding2"]}
        ... )
        >>>
        >>> # Failed result
        >>> result = McpToolResult(
        ...     request_id="req_123",
        ...     success=False,
        ...     error="Tool execution failed: timeout"
        ... )
    """

    request_id: str = Field(..., description="Original request identifier")
    success: bool = Field(..., description="Whether tool call succeeded")
    result: dict[str, Any] | None = Field(default=None, description="Result data (if successful)")
    error: str | None = Field(default=None, description="Error message (if failed)")


class McpResourceFetch(ASAPBaseModel):
    """Request to fetch an MCP resource.

    McpResourceFetch requests retrieval of a resource from an MCP server,
    such as documentation, data, or other content.

    Attributes:
        resource_uri: URI of the MCP resource to fetch

    Example:
        >>> fetch = McpResourceFetch(
        ...     resource_uri="mcp://server/resources/data_123"
        ... )
    """

    resource_uri: str = Field(..., description="MCP resource URI to fetch")


class McpResourceData(ASAPBaseModel):
    """Data from an MCP resource.

    McpResourceData provides the content of a fetched MCP resource.

    Attributes:
        resource_uri: URI of the resource
        content: Resource content (JSON-serializable)

    Example:
        >>> data = McpResourceData(
        ...     resource_uri="mcp://server/resources/data_123",
        ...     content={"data": [1, 2, 3], "metadata": {"source": "api"}}
        ... )
    """

    resource_uri: str = Field(..., description="MCP resource URI")
    content: dict[str, Any] = Field(..., description="Resource content (JSON-serializable)")


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
]
"""Union type of all ASAP payload types.

PayloadType represents any of the 12 payload types used in ASAP protocol messages.
The actual payload type discrimination is done via the 'payload_type' field in the
Envelope that wraps these payloads.

Payload types:
- Task operations: TaskRequest, TaskResponse, TaskUpdate, TaskCancel
- Messaging: MessageSend
- State management: StateQuery, StateRestore, ArtifactNotify
- MCP integration: McpToolCall, McpToolResult, McpResourceFetch, McpResourceData
"""
