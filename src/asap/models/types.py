"""Type aliases for ASAP protocol.

This module defines type aliases to improve code readability and
document the semantic meaning of string types.
"""

# Entity identifiers
AgentURN = str
"""Agent identifier in URN format: urn:asap:agent:{name}"""

ConversationID = str
"""Unique conversation identifier (ULID format)"""

TaskID = str
"""Unique task identifier (ULID format)"""

MessageID = str
"""Unique message identifier (ULID format)"""

ArtifactID = str
"""Unique artifact identifier (ULID format)"""

SnapshotID = str
"""Unique state snapshot identifier (ULID format)"""

PartID = str
"""Unique part identifier (ULID format)"""

# Other semantic types
URI = str
"""Uniform Resource Identifier"""

MIMEType = str
"""MIME type string (e.g., 'application/json')"""

SemanticVersion = str
"""Semantic version string (e.g., '1.0.0')"""
