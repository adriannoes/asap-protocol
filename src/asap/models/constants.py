"""Constants for ASAP protocol.

This module defines protocol-wide constants used across the codebase.
"""

# Protocol version
ASAP_PROTOCOL_VERSION = "0.1"

# Default configuration values
DEFAULT_TIMEOUT_SECONDS = 600
MAX_TASK_DEPTH = 10  # Maximum nesting level for subtasks
MAX_REQUEST_SIZE = 10 * 1024 * 1024  # 10MB maximum request size

# Timestamp validation constants for replay attack prevention
MAX_ENVELOPE_AGE_SECONDS = 300  # 5 minutes
"""Maximum age of an envelope timestamp before it is considered stale.

This prevents replay attacks by rejecting envelopes that are too old.
The 5-minute window balances security (preventing old message replays)
with practical network latency and clock skew tolerance.
"""

MAX_FUTURE_TOLERANCE_SECONDS = 30  # 30 seconds
"""Maximum future timestamp tolerance to account for clock skew.

Envelopes with timestamps more than 30 seconds in the future are rejected
to prevent attacks using artificially future-dated messages. This tolerance
accounts for reasonable clock synchronization differences between systems.
"""

# URN patterns
AGENT_URN_PATTERN = r"^urn:asap:agent:[a-z0-9-]+(?::[a-z0-9-]+)?$"
