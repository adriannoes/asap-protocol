"""Core entity models for the ASAP protocol.

This module defines the fundamental entities used in agent-to-agent communication:
- Agent: An autonomous entity capable of sending/receiving ASAP messages
- Manifest: Self-describing metadata about an agent's capabilities
- Conversation: Context for related interactions between agents
- Task: Fundamental unit of work with lifecycle management
- Message: Single communication turn containing parts
- Artifact: Concrete output produced by task execution
- StateSnapshot: First-class state persistence mechanism
- Skill: A specific capability that an agent can perform
- Capability: Collection of an agent's features and supported operations
- Endpoint: Network endpoints for agent communication
- AuthScheme: Authentication configuration for agent access
"""

import re
from datetime import datetime
from typing import Any

from packaging.version import InvalidVersion, Version
from pydantic import Field, field_validator, model_validator

from asap.errors import UnsupportedAuthSchemeError
from asap.models.base import ASAPBaseModel
from asap.models.constants import (
    AGENT_URN_PATTERN,
    ASAP_PROTOCOL_VERSION,
    MAX_TASK_DEPTH,
    MAX_URN_LENGTH,
    SUPPORTED_AUTH_SCHEMES,
)
from asap.models.enums import MessageRole, TaskStatus
from asap.models.types import (
    AgentURN,
    ArtifactID,
    ConversationID,
    MessageID,
    PartID,
    SemanticVersion,
    SnapshotID,
    TaskID,
)


def _validate_auth_scheme(auth: "AuthScheme") -> None:
    """Validate that all authentication schemes are supported.

    Checks each scheme in auth.schemes against SUPPORTED_AUTH_SCHEMES
    and raises UnsupportedAuthSchemeError if any scheme is invalid.

    Args:
        auth: AuthScheme instance to validate

    Raises:
        UnsupportedAuthSchemeError: If any scheme is not supported
    """
    for scheme in auth.schemes:
        scheme_lower = scheme.lower()
        if scheme_lower not in SUPPORTED_AUTH_SCHEMES:
            raise UnsupportedAuthSchemeError(
                scheme=scheme,
                supported_schemes=SUPPORTED_AUTH_SCHEMES,
            )


def _validate_agent_urn(v: str) -> str:
    """Validate agent URN format and length.

    Ensures URN matches AGENT_URN_PATTERN (urn:asap:agent:name or
    urn:asap:agent:name:sub) and does not exceed MAX_URN_LENGTH.

    Args:
        v: URN string to validate

    Returns:
        The same string if valid

    Raises:
        ValueError: If format is invalid or length exceeds MAX_URN_LENGTH
    """
    if len(v) > MAX_URN_LENGTH:
        raise ValueError(f"Agent URN must be at most {MAX_URN_LENGTH} characters, got {len(v)}")
    if not re.match(AGENT_URN_PATTERN, v):
        raise ValueError(f"Agent ID must follow URN format 'urn:asap:agent:{{name}}', got: {v}")
    return v


class Skill(ASAPBaseModel):
    """A specific capability that an agent can perform.

    Skills define what an agent can do, along with the expected input
    and output schemas for validation.

    Attributes:
        id: Unique identifier for the skill (e.g., "web_research")
        description: Human-readable description of what the skill does
        input_schema: Optional JSON Schema for validating skill inputs
        output_schema: Optional JSON Schema for validating skill outputs

    Example:
        >>> skill = Skill(
        ...     id="web_research",
        ...     description="Search and synthesize information from the web",
        ...     input_schema={"type": "object", "properties": {"query": {"type": "string"}}},
        ...     output_schema={"type": "object", "properties": {"summary": {"type": "string"}}}
        ... )
    """

    id: str = Field(..., description="Unique skill identifier")
    description: str = Field(..., description="Human-readable skill description")
    input_schema: dict[str, Any] | None = Field(
        default=None, description="JSON Schema for skill input validation"
    )
    output_schema: dict[str, Any] | None = Field(
        default=None, description="JSON Schema for skill output validation"
    )


class Capability(ASAPBaseModel):
    """Collection of an agent's features and supported operations.

    Capabilities describe what an agent can do, including skills,
    state persistence, streaming support, and MCP tool integration.

    Attributes:
        asap_version: ASAP protocol version supported (e.g., "0.1")
        skills: List of skills the agent can perform
        state_persistence: Whether the agent supports state snapshots
        streaming: Whether the agent supports streaming responses
        mcp_tools: List of MCP tool names the agent can execute

    Example:
        >>> capability = Capability(
        ...     asap_version="0.1",
        ...     skills=[Skill(id="research", description="Research skill")],
        ...     state_persistence=True,
        ...     streaming=True,
        ...     mcp_tools=["web_search"]
        ... )
    """

    asap_version: str = Field(default=ASAP_PROTOCOL_VERSION, description="ASAP protocol version")
    skills: list[Skill] = Field(default_factory=list, description="Available skills")
    state_persistence: bool = Field(default=False, description="Supports state snapshots")
    streaming: bool = Field(default=False, description="Supports streaming responses")
    mcp_tools: list[str] = Field(default_factory=list, description="Available MCP tools")


class Endpoint(ASAPBaseModel):
    """Network endpoints for agent communication.

    Defines the URLs where an agent can be reached for different
    types of communication.

    Attributes:
        asap: HTTP endpoint for ASAP protocol messages (required)
        events: Optional WebSocket endpoint for streaming events

    Example:
        >>> endpoint = Endpoint(
        ...     asap="https://api.example.com/asap",
        ...     events="wss://api.example.com/asap/events"
        ... )
    """

    asap: str = Field(..., description="HTTP endpoint for ASAP messages")
    events: str | None = Field(default=None, description="WebSocket endpoint for streaming events")


class AuthScheme(ASAPBaseModel):
    """Authentication configuration for agent access.

    Defines the authentication methods supported by an agent and
    optional OAuth2 configuration.

    Attributes:
        schemes: List of supported auth schemes (e.g., ["bearer", "oauth2"])
        oauth2: Optional OAuth2 configuration with URLs and scopes

    Example:
        >>> auth = AuthScheme(
        ...     schemes=["bearer", "oauth2"],
        ...     oauth2={
        ...         "authorization_url": "https://auth.example.com/authorize",
        ...         "token_url": "https://auth.example.com/token",
        ...         "scopes": ["asap:execute", "asap:read"]
        ...     }
        ... )
    """

    schemes: list[str] = Field(..., description="Supported authentication schemes")
    oauth2: dict[str, Any] | None = Field(
        default=None, description="OAuth2 configuration if oauth2 is in schemes"
    )


class Agent(ASAPBaseModel):
    """An autonomous entity capable of sending and receiving ASAP messages.

    Agents are symmetric peers with no inherent client/server distinction.
    Each agent has a unique identifier and publishes a manifest describing
    its capabilities.

    Attributes:
        id: Unique agent identifier (URN format, e.g., "urn:asap:agent:research-v1")
        manifest_uri: URL where the agent's manifest can be retrieved
        capabilities: List of capability strings (e.g., ["task.execute", "mcp.tools"])

    Example:
        >>> agent = Agent(
        ...     id="urn:asap:agent:research-v1",
        ...     manifest_uri="https://agents.example.com/.well-known/asap/research-v1.json",
        ...     capabilities=["task.execute", "state.persist", "mcp.tools"]
        ... )
    """

    id: AgentURN = Field(..., description="Unique agent identifier (URN format)")
    manifest_uri: str = Field(..., description="URL to agent's manifest")
    capabilities: list[str] = Field(..., min_length=1, description="Agent capability strings")

    @field_validator("id")
    @classmethod
    def validate_urn_format(cls, v: str) -> str:
        """Validate agent ID URN format and length."""
        return _validate_agent_urn(v)


class Manifest(ASAPBaseModel):
    """Self-describing metadata about an agent's capabilities.

    The manifest is analogous to A2A's Agent Card but extended with
    additional ASAP-specific features. It provides all information
    needed to interact with an agent.

    Attributes:
        id: Unique agent identifier (matches Agent.id)
        name: Human-readable agent name
        version: Semantic version of the agent
        description: Description of what the agent does
        capabilities: Detailed capability information
        endpoints: Network endpoints for communication
        auth: Optional authentication configuration
        signature: Optional cryptographic signature for manifest verification

    Example:
        >>> manifest = Manifest(
        ...     id="urn:asap:agent:research-v1",
        ...     name="Research Agent",
        ...     version="1.0.0",
        ...     description="Performs web research and summarization",
        ...     capabilities=Capability(
        ...         asap_version="0.1",
        ...         skills=[Skill(id="web_research", description="Research skill")],
        ...         state_persistence=True
        ...     ),
        ...     endpoints=Endpoint(asap="https://api.example.com/asap")
        ... )
    """

    id: AgentURN = Field(..., description="Unique agent identifier (URN format)")
    name: str = Field(..., description="Human-readable agent name")
    version: SemanticVersion = Field(..., description="Semantic version (e.g., '1.0.0')")
    description: str = Field(..., description="What the agent does")
    capabilities: Capability = Field(..., description="Agent capabilities")
    endpoints: Endpoint = Field(..., description="Communication endpoints")
    auth: AuthScheme | None = Field(default=None, description="Authentication configuration")
    signature: str | None = Field(
        default=None, description="Cryptographic signature for verification"
    )

    @field_validator("id")
    @classmethod
    def validate_urn_format(cls, v: str) -> str:
        """Validate that agent ID follows URN format and length limits."""
        return _validate_agent_urn(v)

    @field_validator("version")
    @classmethod
    def validate_semver(cls, v: str) -> str:
        """Validate semantic versioning format."""
        try:
            Version(v)
        except InvalidVersion as e:
            raise ValueError(f"Invalid semantic version '{v}': {e}") from e
        return v

    @model_validator(mode="after")
    def validate_auth_schemes(self) -> "Manifest":
        """Validate that all authentication schemes are supported.

        Raises:
            UnsupportedAuthSchemeError: If any scheme in auth.schemes is not supported

        Returns:
            Self (for method chaining)
        """
        if self.auth is not None:
            _validate_auth_scheme(self.auth)
        return self


class Conversation(ASAPBaseModel):
    """A context for related interactions between agents.

    Conversations enable shared context accumulation, task grouping,
    and state isolation between unrelated work.

    Attributes:
        id: Unique conversation identifier (ULID format)
        participants: List of agent URNs participating in the conversation
        created_at: Timestamp when the conversation was created (UTC)
        metadata: Optional metadata (e.g., purpose, TTL, tags)

    Example:
        >>> from datetime import datetime, timezone
        >>> conversation = Conversation(
        ...     id="conv_01HX5K3MQVN8...",
        ...     participants=["urn:asap:agent:coordinator", "urn:asap:agent:research-v1"],
        ...     created_at=datetime.now(timezone.utc),
        ...     metadata={"purpose": "quarterly_report_research", "ttl_hours": 72}
        ... )
    """

    id: ConversationID = Field(..., description="Unique conversation identifier (ULID)")
    participants: list[AgentURN] = Field(
        ..., min_length=1, description="Agent URNs in conversation"
    )
    created_at: datetime = Field(..., description="Creation timestamp (UTC)")
    metadata: dict[str, Any] | None = Field(
        default=None, description="Optional metadata (purpose, TTL, etc.)"
    )


class Task(ASAPBaseModel):
    """The fundamental unit of work in ASAP.

    Tasks are uniquely identified, stateful with a defined lifecycle,
    cancellable, resumable, and capable of producing artifacts.

    Attributes:
        id: Unique task identifier (ULID format)
        conversation_id: ID of the conversation this task belongs to
        parent_task_id: Optional ID of parent task (for subtasks)
        status: Current task status (submitted, working, completed, etc.)
        depth: Nesting depth (0 = root); must be ≤ MAX_TASK_DEPTH to prevent infinite recursion
        progress: Optional progress information (percent, message, ETA)
        created_at: Timestamp when the task was created (UTC)
        updated_at: Timestamp of last status update (UTC)

    Example:
        >>> from datetime import datetime, timezone
        >>> task = Task(
        ...     id="task_01HX5K4N...",
        ...     conversation_id="conv_01HX5K3MQVN8...",
        ...     status="working",
        ...     progress={"percent": 45, "message": "Analyzing search results..."},
        ...     created_at=datetime.now(timezone.utc),
        ...     updated_at=datetime.now(timezone.utc)
        ... )
    """

    id: TaskID = Field(..., description="Unique task identifier (ULID)")
    conversation_id: ConversationID = Field(..., description="Parent conversation ID")
    parent_task_id: TaskID | None = Field(default=None, description="Parent task ID for subtasks")
    status: TaskStatus = Field(..., description="Task status (submitted, working, etc.)")
    depth: int = Field(
        0,
        ge=0,
        le=MAX_TASK_DEPTH,
        description="Nesting depth for subtasks (0 = root); prevents infinite recursion",
    )
    progress: dict[str, Any] | None = Field(
        default=None, description="Progress info (percent, message, ETA)"
    )
    created_at: datetime = Field(..., description="Creation timestamp (UTC)")
    updated_at: datetime = Field(..., description="Last update timestamp (UTC)")

    def is_terminal(self) -> bool:
        """Check if task is in a terminal state (completed, failed, or cancelled)."""
        return self.status.is_terminal()

    def can_be_cancelled(self) -> bool:
        """Check if task can be cancelled (only submitted or working tasks)."""
        return self.status in {TaskStatus.SUBMITTED, TaskStatus.WORKING}


class Message(ASAPBaseModel):
    """A single communication turn containing one or more parts.

    Messages are the atomic units of communication within tasks,
    containing content parts and metadata about the sender and role.

    Attributes:
        id: Unique message identifier (ULID format)
        task_id: ID of the task this message belongs to
        sender: Agent URN of the message sender
        role: Message role (user, assistant, system)
        parts: List of part IDs or part references
        timestamp: When the message was sent (UTC)

    Example:
        >>> from datetime import datetime, timezone
        >>> message = Message(
        ...     id="msg_01HX5K5P...",
        ...     task_id="task_01HX5K4N...",
        ...     sender="urn:asap:agent:coordinator",
        ...     role="user",
        ...     parts=["part_01HX5K...", "part_01HX5L..."],
        ...     timestamp=datetime.now(timezone.utc)
        ... )
    """

    id: MessageID = Field(..., description="Unique message identifier (ULID)")
    task_id: TaskID = Field(..., description="Parent task ID")
    sender: AgentURN = Field(..., description="Sender agent URN")
    role: MessageRole = Field(..., description="Message role (user, assistant, system)")
    parts: list[PartID] = Field(..., description="Part IDs or references")
    timestamp: datetime = Field(..., description="Message timestamp (UTC)")


class Artifact(ASAPBaseModel):
    """Concrete output produced by task execution.

    Artifacts represent the tangible results of task completion,
    such as reports, data files, or other generated content.

    Attributes:
        id: Unique artifact identifier (ULID format)
        task_id: ID of the task that produced this artifact
        name: Human-readable artifact name
        parts: List of part IDs that make up this artifact
        created_at: When the artifact was created (UTC)

    Example:
        >>> from datetime import datetime, timezone
        >>> artifact = Artifact(
        ...     id="art_01HX5K6Q...",
        ...     task_id="task_01HX5K4N...",
        ...     name="Q3 Market Analysis Report",
        ...     parts=["part_01HX5K..."],
        ...     created_at=datetime.now(timezone.utc)
        ... )
    """

    id: ArtifactID = Field(..., description="Unique artifact identifier (ULID)")
    task_id: TaskID = Field(..., description="Parent task ID")
    name: str = Field(..., description="Human-readable artifact name")
    parts: list[PartID] = Field(..., description="Part IDs making up this artifact")
    created_at: datetime = Field(..., description="Creation timestamp (UTC)")


class StateSnapshot(ASAPBaseModel):
    """First-class state persistence mechanism.

    StateSnapshots enable task state to be saved and restored,
    addressing a key limitation in other agent protocols. Supports
    versioning and checkpoint flagging for important states.

    Attributes:
        id: Unique snapshot identifier (ULID format)
        task_id: ID of the task this snapshot belongs to
        version: Snapshot version number (auto-incremented)
        data: Arbitrary state data (JSON-serializable dict)
        checkpoint: Whether this is a significant checkpoint (default: False)
        created_at: When the snapshot was created (UTC)

    Example:
        >>> from datetime import datetime, timezone
        >>> snapshot = StateSnapshot(
        ...     id="snap_01HX5K7R...",
        ...     task_id="task_01HX5K4N...",
        ...     version=3,
        ...     data={"search_completed": True, "sources_analyzed": 15},
        ...     checkpoint=True,
        ...     created_at=datetime.now(timezone.utc)
        ... )
    """

    id: SnapshotID = Field(..., description="Unique snapshot identifier (ULID)")
    task_id: TaskID = Field(..., description="Parent task ID")
    version: int = Field(..., description="Snapshot version number", ge=1)
    data: dict[str, Any] = Field(..., description="State data (JSON-serializable)")
    checkpoint: bool = Field(default=False, description="Whether this is a significant checkpoint")
    created_at: datetime = Field(..., description="Creation timestamp (UTC)")
