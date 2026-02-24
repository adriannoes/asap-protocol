"""Debug ID generator for IssueOps scripts.

Generates unique identifiers in the format ``ASAP-<timestamp>-<random>`` to
correlate error results with structured log entries.
"""

from __future__ import annotations

import secrets
import time


def generate_debug_id() -> str:
    """Return a unique debug identifier (e.g. ``ASAP-1708732800-a3f9b1``)."""
    ts = int(time.time())
    suffix = secrets.token_hex(3)
    return f"ASAP-{ts}-{suffix}"
