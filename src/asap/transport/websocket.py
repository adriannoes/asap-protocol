"""WebSocket transport for ASAP protocol (legacy re-export shim).

This module was the monolithic 1168-LOC WebSocket transport. The v2.5.1
thermo-nuclear patch (Sprint S2 Task 3) decomposed it into the
:mod:`asap.transport.ws` package (``codecs`` / ``client`` / ``server`` /
``pool`` / ``_recv`` / ``_ack`` / ``_dispatch`` / ``_actions`` / ``_errors``).

``websocket.py`` is kept as a **thin re-export shim** for the deprecation
window so existing ``from asap.transport.websocket import ...`` import paths and
test patches on the ``asap.transport.websocket`` module path keep working. New
code should import from :mod:`asap.transport.ws` directly.

Patchability: tests patch ``asap.transport.websocket.websockets.connect``,
``asap.transport.websocket.encode_envelope_frame`` and
``asap.transport.websocket.HEARTBEAT_PING_INTERVAL``. The WS package reads these
through this shim (``_shim.websockets`` / ``_shim.encode_envelope_frame`` /
``_shim.HEARTBEAT_PING_INTERVAL``) at call time, so the patches stay effective —
the same attribute-lookup pattern Task 1.0 uses for ``server.logger``. For that
to work, ``websockets`` and the re-exported names below MUST be bound on this
module before :mod:`asap.transport.ws` is imported (the ``ws`` import is last).

Removed in this patch (acceptance): the WS fake-request synthesis (3.2 — WS now
dispatches envelopes directly via ``ASAPRequestHandler._prepare_request`` +
``registry.dispatch_async``/``dispatch_stream_async``) and the binary framing
path (3.3 — frames are JSON text only). ``FRAME_ENCODING_BINARY`` is retained
as a deprecated alias so legacy imports resolve; the binary *behavior* is gone.
"""

from __future__ import annotations

# ``websockets`` is bound here (before the ``ws`` import below) so the WS client
# can read it as ``_shim.websockets`` and test patches on
# ``asap.transport.websocket.websockets.connect`` stay effective.
import websockets  # noqa: F401 — re-exported for patch seams and downstream use

from typing import Literal

# --- Patchable names bound before the ws import --------------------------------
# These are re-exported from ``asap.transport.ws.codecs`` but ALSO bound on this
# shim so tests patching ``asap.transport.websocket.<name>`` are observed by the
# WS package (which reads them via ``_shim.<name>`` at call time).
from asap.transport.ws.codecs import (  # noqa: F401 — re-exported / patch seams
    ASAP_ACK_METHOD,
    HEARTBEAT_PING_INTERVAL,
    PAYLOAD_TYPES_REQUIRING_ACK,
    encode_envelope_frame,
)

# Deprecated alias retained for import compatibility; the binary framing path is
# gone (3.3). Scoped to the shim, not re-exported from ``ws/``.
FRAME_ENCODING_BINARY: Literal["binary"] = "binary"

# --- Public surface re-exported from the ws package ----------------------------
from asap.transport.ws import (  # noqa: E402,F401 — bound after patchable names above
    ACK_CHECK_INTERVAL,
    DEFAULT_ACK_TIMEOUT,
    DEFAULT_MAX_ACK_RETRIES,
    DEFAULT_POOL_IDLE_TIMEOUT,
    DEFAULT_POOL_MAX_SIZE,
    DEFAULT_WS_RECEIVE_TIMEOUT,
    FRAME_ENCODING_JSON,
    HEARTBEAT_FRAME_TYPE_PING,
    HEARTBEAT_FRAME_TYPE_PONG,
    OnMessageCallback,
    PendingAck,
    RECONNECT_INITIAL_BACKOFF,
    RECONNECT_MAX_BACKOFF,
    SLA_BREACH_NOTIFICATION_METHOD,
    SLA_SUBSCRIBE_METHOD,
    SLA_UNSUBSCRIBE_METHOD,
    STALE_CONNECTION_TIMEOUT,
    WSCloseAction,
    WS_CLOSE_AUTH_REQUIRED,
    WS_CLOSE_GOING_AWAY,
    WS_CLOSE_POLICY_VIOLATION,
    WS_CLOSE_REASON_SHUTDOWN,
    WebSocketConnectionPool,
    WebSocketRemoteError,
    WebSocketTransport,
    _build_ack_notification_frame,
    _heartbeat_loop,
    _is_heartbeat_pong,
    _process_ws_message,
    _reconnect_delay,
    broadcast_sla_breach,
    decode_frame_to_json,
    handle_websocket_connection,
)

__all__ = [
    "ACK_CHECK_INTERVAL",
    "ASAP_ACK_METHOD",
    "DEFAULT_ACK_TIMEOUT",
    "DEFAULT_MAX_ACK_RETRIES",
    "DEFAULT_POOL_IDLE_TIMEOUT",
    "DEFAULT_POOL_MAX_SIZE",
    "DEFAULT_WS_RECEIVE_TIMEOUT",
    "FRAME_ENCODING_BINARY",
    "FRAME_ENCODING_JSON",
    "HEARTBEAT_FRAME_TYPE_PING",
    "HEARTBEAT_FRAME_TYPE_PONG",
    "HEARTBEAT_PING_INTERVAL",
    "OnMessageCallback",
    "PAYLOAD_TYPES_REQUIRING_ACK",
    "PendingAck",
    "RECONNECT_INITIAL_BACKOFF",
    "RECONNECT_MAX_BACKOFF",
    "SLA_BREACH_NOTIFICATION_METHOD",
    "SLA_SUBSCRIBE_METHOD",
    "SLA_UNSUBSCRIBE_METHOD",
    "STALE_CONNECTION_TIMEOUT",
    "WSCloseAction",
    "WS_CLOSE_AUTH_REQUIRED",
    "WS_CLOSE_GOING_AWAY",
    "WS_CLOSE_POLICY_VIOLATION",
    "WS_CLOSE_REASON_SHUTDOWN",
    "WebSocketConnectionPool",
    "WebSocketRemoteError",
    "WebSocketTransport",
    "_build_ack_notification_frame",
    "_heartbeat_loop",
    "_is_heartbeat_pong",
    "_process_ws_message",
    "_reconnect_delay",
    "broadcast_sla_breach",
    "decode_frame_to_json",
    "encode_envelope_frame",
    "handle_websocket_connection",
    "websockets",
]
