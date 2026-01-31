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

NONCE_TTL_SECONDS = MAX_ENVELOPE_AGE_SECONDS * 2  # 10 minutes by default
"""Time-to-live for nonce values in seconds.

Nonces are stored with a TTL of 2x the maximum envelope age to ensure they
expire after the envelope would have been rejected anyway. This provides a
safety margin for edge cases where an envelope might be processed near the
age limit, while preventing the nonce store from growing unbounded.

The 2x multiplier ensures that:
- Nonces remain valid for the full envelope validation window
- Nonces expire shortly after envelopes would be rejected, preventing unbounded growth
- There's a buffer for clock skew and processing delays
"""

# URN patterns and limits
AGENT_URN_PATTERN = r"^urn:asap:agent:[a-z0-9-]+(?::[a-z0-9-]+)?$"
MAX_URN_LENGTH = 256
"""Maximum length for agent URNs to prevent abuse and ensure consistent storage."""

# Authentication schemes
SUPPORTED_AUTH_SCHEMES = frozenset({"bearer", "basic"})
"""Supported authentication schemes for agent access.

Currently supports:
- bearer: Bearer token authentication (RFC 6750)
- basic: HTTP Basic authentication (RFC 7617)

Future support planned:
- oauth2: OAuth 2.0 authentication flow
- hmac: HMAC-based authentication
"""

# Retry and backoff constants
DEFAULT_BASE_DELAY = 1.0
"""Default base delay in seconds for exponential backoff.

This is the initial delay before the first retry attempt. Subsequent retries
will use exponential backoff: base_delay * (2 ** attempt) + jitter.
"""

DEFAULT_MAX_DELAY = 60.0
"""Maximum delay in seconds for exponential backoff.

This caps the maximum delay between retry attempts, preventing excessively
long waits while still providing exponential backoff for transient failures.
"""

DEFAULT_CIRCUIT_BREAKER_THRESHOLD = 5
"""Default threshold for circuit breaker pattern.

Number of consecutive failures required before opening the circuit breaker
and preventing further requests to a failing endpoint.
"""

DEFAULT_CIRCUIT_BREAKER_TIMEOUT = 60.0
"""Default timeout in seconds before circuit breaker transitions from OPEN to HALF_OPEN.

After this timeout, the circuit breaker will allow a test request to determine
if the service has recovered before closing the circuit.
"""
