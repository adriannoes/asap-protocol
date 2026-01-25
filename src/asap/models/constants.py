"""Constants for ASAP protocol.

This module defines protocol-wide constants used across the codebase.
"""

# Protocol version
ASAP_PROTOCOL_VERSION = "0.1"

# Default configuration values
DEFAULT_TIMEOUT_SECONDS = 600
MAX_TASK_DEPTH = 10  # Maximum nesting level for subtasks
MAX_REQUEST_SIZE = 10 * 1024 * 1024  # 10MB maximum request size

# URN patterns
AGENT_URN_PATTERN = r"^urn:asap:agent:[a-z0-9-]+(?::[a-z0-9-]+)?$"
