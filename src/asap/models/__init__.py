"""ASAP Protocol Models.

This module provides all the Pydantic models for the ASAP protocol,
including entities, parts, payloads, and the envelope wrapper.
"""

# Base models
from asap.models.base import ASAPBaseModel

# Constants
from asap.models.constants import (
    AGENT_URN_PATTERN,
    ASAP_PROTOCOL_VERSION,
    DEFAULT_TIMEOUT_SECONDS,
    MAX_TASK_DEPTH,
)

# Enums
from asap.models.enums import MessageRole, TaskStatus, UpdateType

# Type aliases
from asap.models.types import (
    AgentURN,
    ArtifactID,
    ConversationID,
    MessageID,
    MIMEType,
    PartID,
    SemanticVersion,
    SnapshotID,
    TaskID,
    URI,
)

# ID utilities
from asap.models.ids import extract_timestamp, generate_id

# Entities
from asap.models.entities import (
    Agent,
    Artifact,
    AuthScheme,
    Capability,
    Conversation,
    Endpoint,
    Manifest,
    Message,
    Skill,
    StateSnapshot,
    Task,
)

# Parts
from asap.models.parts import (
    DataPart,
    FilePart,
    Part,
    PartType,
    ResourcePart,
    TemplatePart,
    TextPart,
)

# Payloads
from asap.models.payloads import (
    ArtifactNotify,
    McpResourceData,
    McpResourceFetch,
    McpToolCall,
    McpToolResult,
    MessageSend,
    PayloadType,
    StateQuery,
    StateRestore,
    TaskCancel,
    TaskRequest,
    TaskResponse,
    TaskUpdate,
)

# Envelope
from asap.models.envelope import Envelope

__all__ = [
    # Base
    "ASAPBaseModel",
    # Constants
    "AGENT_URN_PATTERN",
    "ASAP_PROTOCOL_VERSION",
    "DEFAULT_TIMEOUT_SECONDS",
    "MAX_TASK_DEPTH",
    # Enums
    "MessageRole",
    "TaskStatus",
    "UpdateType",
    # Type aliases
    "AgentURN",
    "ArtifactID",
    "ConversationID",
    "MessageID",
    "MIMEType",
    "PartID",
    "SemanticVersion",
    "SnapshotID",
    "TaskID",
    "URI",
    # IDs
    "generate_id",
    "extract_timestamp",
    # Entities
    "Agent",
    "Artifact",
    "AuthScheme",
    "Capability",
    "Conversation",
    "Endpoint",
    "Manifest",
    "Message",
    "Skill",
    "StateSnapshot",
    "Task",
    # Parts
    "DataPart",
    "FilePart",
    "Part",
    "PartType",
    "ResourcePart",
    "TemplatePart",
    "TextPart",
    # Payloads
    "ArtifactNotify",
    "McpResourceData",
    "McpResourceFetch",
    "McpToolCall",
    "McpToolResult",
    "MessageSend",
    "PayloadType",
    "StateQuery",
    "StateRestore",
    "TaskCancel",
    "TaskRequest",
    "TaskResponse",
    "TaskUpdate",
    # Envelope
    "Envelope",
]
