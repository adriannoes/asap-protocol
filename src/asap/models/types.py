"""Type aliases for ASAP protocol.

This module defines type aliases to improve code readability and
document the semantic meaning of string types.
"""

from typing import TypeAlias

# Entity identifiers
AgentURN: TypeAlias = str
"""Agent identifier in URN format: urn:asap:agent:{name}"""

ConversationID: TypeAlias = str
"""Unique conversation identifier (ULID format)"""

TaskID: TypeAlias = str
"""Unique task identifier (ULID format)"""

MessageID: TypeAlias = str
"""Unique message identifier (ULID format)"""

ArtifactID: TypeAlias = str
"""Unique artifact identifier (ULID format)"""

SnapshotID: TypeAlias = str
"""Unique state snapshot identifier (ULID format)"""

PartID: TypeAlias = str
"""Unique part identifier (ULID format)"""

# Other semantic types
URI: TypeAlias = str
"""Uniform Resource Identifier"""

MIMEType: TypeAlias = str
"""MIME type string (e.g., 'application/json')"""

SemanticVersion: TypeAlias = str
"""Semantic version string (e.g., '1.0.0')"""
