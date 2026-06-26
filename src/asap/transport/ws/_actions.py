"""Close-action enum for the WS server receive loop (3.4).

Lives in its own module so :mod:`asap.transport.ws.server` (the receive loop and
per-message processing) and :mod:`asap.transport.ws._dispatch` (the envelope
dispatch layer) can both import it without a circular dependency.
"""

from __future__ import annotations

from enum import Enum

from asap.transport.ws.codecs import WS_CLOSE_GOING_AWAY, WS_CLOSE_POLICY_VIOLATION


class WSCloseAction(Enum):
    """Per-message outcome for the WS receive loop (3.4).

    - ``CONTINUE``: keep the receive loop alive.
    - ``CLOSE_RATE_LIMITED``: close with ``WS_CLOSE_POLICY_VIOLATION`` (1008).
    - ``CLOSE_FATAL``: close with ``WS_CLOSE_GOING_AWAY`` (1001).
    """

    CONTINUE = "continue"
    CLOSE_RATE_LIMITED = "close_rate_limited"
    CLOSE_FATAL = "close_fatal"


def _ws_close_code(action: WSCloseAction) -> int:
    """Map a close action to its RFC 6455 close code."""
    if action is WSCloseAction.CLOSE_RATE_LIMITED:
        return WS_CLOSE_POLICY_VIOLATION
    return WS_CLOSE_GOING_AWAY


__all__ = ["WSCloseAction", "_ws_close_code"]
