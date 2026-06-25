"""ASAP WebSocket transport package (``asap.transport.ws``).

Decomposed from the original monolithic ``asap/transport/websocket.py`` in the
v2.5.1 thermo-nuclear patch (Sprint S2 Task 3). Each concern lives in a focused
module kept under the 400-LOC ceiling:

- :mod:`asap.transport.ws.codecs` — frame codecs + constants (no binary/base64 path).
- :mod:`asap.transport.ws.client` — :class:`WebSocketTransport` connection/send/receive.
- :mod:`asap.transport.ws._recv` — inbound frame dispatch mixin for the transport.
- :mod:`asap.transport.ws._ack` — ADR-16 pending-ack retransmit mixin + :class:`PendingAck`.
- :mod:`asap.transport.ws._errors` — :class:`WebSocketRemoteError`.
- :mod:`asap.transport.ws.pool` — :class:`WebSocketConnectionPool`.
- :mod:`asap.transport.ws.server` — :func:`handle_websocket_connection`, heartbeat, SLA.
- :mod:`asap.transport.ws._actions` — :class:`WSCloseAction` close-decision enum.
- :mod:`asap.transport.ws._dispatch` — direct envelope dispatch (3.2) + message helpers.

The legacy ``asap.transport.websocket`` module remains as a thin re-export shim
(deprecation window) so ``from asap.transport.websocket import ...`` and test
patches on the ``asap.transport.websocket`` path keep working.
"""

from __future__ import annotations

from asap.transport.ws._actions import WSCloseAction
from asap.transport.ws._ack import PendingAck
from asap.transport.ws._errors import WebSocketRemoteError
from asap.transport.ws.client import (
    OnMessageCallback,
    WebSocketTransport,
    _reconnect_delay,
)
from asap.transport.ws.codecs import (
    ACK_CHECK_INTERVAL,
    ASAP_ACK_METHOD,
    DEFAULT_ACK_TIMEOUT,
    DEFAULT_MAX_ACK_RETRIES,
    DEFAULT_POOL_IDLE_TIMEOUT,
    DEFAULT_POOL_MAX_SIZE,
    DEFAULT_WS_RECEIVE_TIMEOUT,
    FRAME_ENCODING_JSON,
    HEARTBEAT_FRAME_TYPE_PING,
    HEARTBEAT_FRAME_TYPE_PONG,
    HEARTBEAT_PING_INTERVAL,
    PAYLOAD_TYPES_REQUIRING_ACK,
    RECONNECT_INITIAL_BACKOFF,
    RECONNECT_MAX_BACKOFF,
    SLA_BREACH_NOTIFICATION_METHOD,
    SLA_SUBSCRIBE_METHOD,
    SLA_UNSUBSCRIBE_METHOD,
    STALE_CONNECTION_TIMEOUT,
    WS_CLOSE_AUTH_REQUIRED,
    WS_CLOSE_GOING_AWAY,
    WS_CLOSE_POLICY_VIOLATION,
    WS_CLOSE_REASON_SHUTDOWN,
    _build_ack_notification_frame,
    _is_heartbeat_pong,
    decode_frame_to_json,
    encode_envelope_frame,
)
from asap.transport.ws.pool import WebSocketConnectionPool
from asap.transport.ws.server import (
    _heartbeat_loop,
    _process_ws_message,
    broadcast_sla_breach,
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
]
