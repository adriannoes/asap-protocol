"""Compatibility re-export shim for the ASAP WebSocket transport.

The implementation lives in :mod:`asap.transport.ws`. This module preserves the
legacy ``asap.transport.websocket`` import path and exposes selected attributes
used by tests and downstream callers. New code should import from
:mod:`asap.transport.ws` directly.

The WS package reads patchable attributes such as ``websockets``,
``encode_envelope_frame``, and ``HEARTBEAT_PING_INTERVAL`` through this module at
call time. Keep those names bound before importing :mod:`asap.transport.ws`.
"""

from __future__ import annotations

# ``websockets`` is bound here before the ``ws`` import below.
import websockets  # noqa: F401 - Re-exported for test patching and downstream use.

from typing import Literal

# --- Patchable names bound before the ws import --------------------------------
# Re-exported for test patching.
from asap.transport.ws.codecs import (  # noqa: F401 - Re-exported for test patching.
    ASAP_ACK_METHOD,
    HEARTBEAT_PING_INTERVAL,
    PAYLOAD_TYPES_REQUIRING_ACK,
    encode_envelope_frame,
)

# Deprecated alias retained for import compatibility; binary framing is no
# longer supported. Scoped to the shim, not re-exported from ``ws/``.
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
