"""Trace parsing and ASCII visualization from ASAP structured logs.

Parses JSON log lines containing asap.request.received and asap.request.processed
events, filters by trace_id, and builds a request flow with timing for CLI output.

Expected log events (from transport/server.py):
- asap.request.received: envelope_id, trace_id, sender, recipient, payload_type
- asap.request.processed: envelope_id, trace_id, duration_ms, payload_type
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Iterable

# Event names emitted by ASAP server
EVENT_RECEIVED = "asap.request.received"
EVENT_PROCESSED = "asap.request.processed"


@dataclass(frozen=True)
class TraceHop:
    """A single hop in a trace: sender -> recipient with optional duration."""

    sender: str
    recipient: str
    duration_ms: float | None

    def format_hop(self, short_urns: bool = True) -> str:
        """Format this hop for ASCII diagram (e.g. 'A -> B (15ms)')."""
        s = _shorten_urn(self.sender) if short_urns else self.sender
        r = _shorten_urn(self.recipient) if short_urns else self.recipient
        if self.duration_ms is not None:
            return f"{s} -> {r} ({self.duration_ms:.0f}ms)"
        return f"{s} -> {r} (?)"


def _shorten_urn(urn: str) -> str:
    """Shorten URN to last segment for compact display (e.g. urn:asap:agent:foo -> foo)."""
    if ":" in urn:
        return urn.split(":")[-1]
    return urn


def parse_log_line(line: str) -> dict[str, object] | None:
    """Parse a single JSON log line.

    Args:
        line: One line of log output (e.g. structlog JSON).

    Returns:
        Parsed dict or None if not valid JSON.
    """
    line = line.strip()
    if not line:
        return None
    try:
        data = json.loads(line)
        return data if isinstance(data, dict) else None
    except json.JSONDecodeError:
        return None


def filter_records_by_trace_id(
    lines: Iterable[str], trace_id: str
) -> list[dict[str, object]]:
    """Filter and parse log lines that contain the given trace_id.

    Only lines that are valid JSON and contain trace_id (string match) are returned.
    This avoids parsing every line as JSON when scanning large files.

    Args:
        lines: Log lines (e.g. from a file or stdin).
        trace_id: Trace ID to search for.

    Returns:
        List of parsed log records that mention this trace_id.
    """
    trace_id_str = str(trace_id)
    records: list[dict[str, object]] = []
    for line in lines:
        if trace_id_str not in line:
            continue
        parsed = parse_log_line(line)
        if parsed is None:
            continue
        if parsed.get("trace_id") != trace_id_str:
            continue
        records.append(parsed)
    return records


def build_hops(records: list[dict[str, object]]) -> list[TraceHop]:
    """Build ordered list of trace hops from received/processed log records.

    Pairs asap.request.received with asap.request.processed by envelope_id to
    attach duration_ms to each hop. Sorts by received timestamp when available.

    Args:
        records: Parsed log records (from filter_records_by_trace_id).

    Returns:
        Ordered list of TraceHop (sender -> recipient, duration_ms or None).
    """
    received_by_envelope: dict[str, dict[str, object]] = {}
    processed_by_envelope: dict[str, dict[str, object]] = {}

    for r in records:
        event = r.get("event")
        envelope_id = r.get("envelope_id")
        if not isinstance(envelope_id, str):
            continue
        if event == EVENT_RECEIVED:
            received_by_envelope[envelope_id] = r
        elif event == EVENT_PROCESSED:
            processed_by_envelope[envelope_id] = r

    hops_with_meta: list[tuple[float, str, str, float | None]] = []

    for envelope_id, rec in received_by_envelope.items():
        sender = rec.get("sender")
        recipient = rec.get("recipient")
        if not isinstance(sender, str) or not isinstance(recipient, str):
            continue
        proc = processed_by_envelope.get(envelope_id)
        duration_ms: float | None = None
        if isinstance(proc, dict) and "duration_ms" in proc:
            d = proc["duration_ms"]
            if isinstance(d, (int, float)):
                duration_ms = float(d)
        ts = rec.get("timestamp")
        sort_key = _timestamp_to_sort_key(ts) if isinstance(ts, str) else 0.0
        hops_with_meta.append((sort_key, sender, recipient, duration_ms))

    hops_with_meta.sort(key=lambda x: x[0])

    return [TraceHop(sender=s, recipient=r, duration_ms=d) for (_, s, r, d) in hops_with_meta]


def _timestamp_to_sort_key(ts: str) -> float:
    """Convert ISO timestamp string to a sortable number (epoch-ish)."""
    try:
        from datetime import datetime

        dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        return dt.timestamp()
    except (ValueError, TypeError):
        return 0.0


def format_ascii_diagram(hops: list[TraceHop], short_urns: bool = True) -> str:
    """Format trace hops as a single-line ASCII diagram with timing.

    Format: Agent A -> Agent B (15ms) -> Agent C (23ms)
    Each hop shows recipient and duration; sender of first hop starts the chain.

    Args:
        hops: Ordered list of TraceHop from build_hops.
        short_urns: If True, shorten URNs to last segment for display.

    Returns:
        Single line string for CLI output.
    """
    if not hops:
        return ""
    parts: list[str] = []
    for hop in hops:
        r = _shorten_urn(hop.recipient) if short_urns else hop.recipient
        if hop.duration_ms is not None:
            parts.append(f"{r} ({hop.duration_ms:.0f}ms)")
        else:
            parts.append(f"{r} (?)")
    first_sender = _shorten_urn(hops[0].sender) if short_urns else hops[0].sender
    return first_sender + " -> " + " -> ".join(parts)


def extract_trace_ids(lines: Iterable[str]) -> list[str]:
    """Extract unique trace IDs from log lines (received/processed events only).

    Args:
        lines: Log lines (e.g. from file or stdin).

    Returns:
        Sorted list of unique trace_id values found in asap.request.received
        or asap.request.processed events.
    """
    seen: set[str] = set()
    for line in lines:
        if EVENT_RECEIVED not in line and EVENT_PROCESSED not in line:
            continue
        parsed = parse_log_line(line)
        if parsed is None:
            continue
        if parsed.get("event") not in (EVENT_RECEIVED, EVENT_PROCESSED):
            continue
        tid = parsed.get("trace_id")
        if isinstance(tid, str) and tid:
            seen.add(tid)
    return sorted(seen)


def parse_trace_from_lines(
    lines: Iterable[str], trace_id: str
) -> tuple[list[TraceHop], str]:
    """Parse logs and build ASCII diagram for a trace_id.

    Args:
        lines: Log lines (e.g. from file or stdin).
        trace_id: Trace ID to filter and visualize.

    Returns:
        Tuple of (list of TraceHop, ASCII diagram string). Diagram is empty
        if no matching records.
    """
    records = filter_records_by_trace_id(lines, trace_id)
    hops = build_hops(records)
    diagram = format_ascii_diagram(hops)
    return hops, diagram
