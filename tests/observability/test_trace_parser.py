"""Tests for ASAP trace parser (log parsing and ASCII diagram)."""

import json


from asap.observability.trace_parser import (
    EVENT_PROCESSED,
    EVENT_RECEIVED,
    TraceHop,
    build_hops,
    extract_trace_ids,
    filter_records_by_trace_id,
    format_ascii_diagram,
    parse_log_line,
    parse_trace_from_lines,
    trace_to_json_export,
)


class TestParseLogLine:
    """Tests for parse_log_line."""

    def test_valid_json_returns_dict(self) -> None:
        line = '{"event": "asap.request.received", "trace_id": "t1"}'
        assert parse_log_line(line) == {"event": "asap.request.received", "trace_id": "t1"}

    def test_invalid_json_returns_none(self) -> None:
        assert parse_log_line("not json") is None
        assert parse_log_line("{") is None

    def test_empty_line_returns_none(self) -> None:
        assert parse_log_line("") is None
        assert parse_log_line("   ") is None

    def test_non_dict_json_returns_none(self) -> None:
        assert parse_log_line("[1,2,3]") is None


class TestFilterRecordsByTraceId:
    """Tests for filter_records_by_trace_id."""

    def test_filters_by_trace_id(self) -> None:
        lines = [
            '{"event": "other", "trace_id": "t0"}',
            '{"event": "asap.request.received", "trace_id": "t1", "envelope_id": "e1", "sender": "urn:asap:agent:a", "recipient": "urn:asap:agent:b"}',
            '{"event": "asap.request.processed", "trace_id": "t1", "envelope_id": "e1", "duration_ms": 15}',
        ]
        records = filter_records_by_trace_id(lines, "t1")
        assert len(records) == 2
        assert records[0]["event"] == EVENT_RECEIVED
        assert records[1]["event"] == EVENT_PROCESSED

    def test_skips_lines_without_trace_id_match(self) -> None:
        lines = [
            '{"event": "asap.request.received", "trace_id": "t2"}',
        ]
        assert len(filter_records_by_trace_id(lines, "t1")) == 0
        assert len(filter_records_by_trace_id(lines, "t2")) == 1

    def test_skips_invalid_json_lines(self) -> None:
        lines = [
            '{"event": "asap.request.received", "trace_id": "t1"}',
            "not json but contains t1",
        ]
        records = filter_records_by_trace_id(lines, "t1")
        assert len(records) == 1


class TestBuildHops:
    """Tests for build_hops."""

    def test_pairs_received_with_processed(self) -> None:
        records = [
            {
                "event": EVENT_RECEIVED,
                "envelope_id": "e1",
                "trace_id": "t1",
                "sender": "urn:asap:agent:a",
                "recipient": "urn:asap:agent:b",
                "timestamp": "2026-01-31T12:00:00Z",
            },
            {
                "event": EVENT_PROCESSED,
                "envelope_id": "e1",
                "trace_id": "t1",
                "duration_ms": 15,
            },
        ]
        hops = build_hops(records)
        assert len(hops) == 1
        assert hops[0].sender == "urn:asap:agent:a"
        assert hops[0].recipient == "urn:asap:agent:b"
        assert hops[0].duration_ms == 15.0

    def test_multiple_hops_ordered_by_timestamp(self) -> None:
        records = [
            {
                "event": EVENT_RECEIVED,
                "envelope_id": "e2",
                "trace_id": "t1",
                "sender": "urn:asap:agent:b",
                "recipient": "urn:asap:agent:c",
                "timestamp": "2026-01-31T12:00:01Z",
            },
            {
                "event": EVENT_PROCESSED,
                "envelope_id": "e2",
                "trace_id": "t1",
                "duration_ms": 23,
            },
            {
                "event": EVENT_RECEIVED,
                "envelope_id": "e1",
                "trace_id": "t1",
                "sender": "urn:asap:agent:a",
                "recipient": "urn:asap:agent:b",
                "timestamp": "2026-01-31T12:00:00Z",
            },
            {
                "event": EVENT_PROCESSED,
                "envelope_id": "e1",
                "trace_id": "t1",
                "duration_ms": 15,
            },
        ]
        hops = build_hops(records)
        assert len(hops) == 2
        assert hops[0].sender == "urn:asap:agent:a" and hops[0].recipient == "urn:asap:agent:b"
        assert hops[0].duration_ms == 15.0
        assert hops[1].sender == "urn:asap:agent:b" and hops[1].recipient == "urn:asap:agent:c"
        assert hops[1].duration_ms == 23.0

    def test_received_without_processed_has_none_duration(self) -> None:
        records = [
            {
                "event": EVENT_RECEIVED,
                "envelope_id": "e1",
                "trace_id": "t1",
                "sender": "urn:asap:agent:a",
                "recipient": "urn:asap:agent:b",
            },
        ]
        hops = build_hops(records)
        assert len(hops) == 1
        assert hops[0].duration_ms is None


class TestFormatAsciiDiagram:
    """Tests for format_ascii_diagram."""

    def test_single_hop(self) -> None:
        hops = [TraceHop("urn:asap:agent:a", "urn:asap:agent:b", 15.0)]
        assert format_ascii_diagram(hops) == "a -> b (15ms)"

    def test_two_hops(self) -> None:
        hops = [
            TraceHop("urn:asap:agent:a", "urn:asap:agent:b", 15.0),
            TraceHop("urn:asap:agent:b", "urn:asap:agent:c", 23.0),
        ]
        assert format_ascii_diagram(hops) == "a -> b (15ms) -> c (23ms)"

    def test_empty_hops(self) -> None:
        assert format_ascii_diagram([]) == ""


class TestTraceToJsonExport:
    """Tests for trace_to_json_export (JSON output for external tools)."""

    def test_single_hop(self) -> None:
        hops = [TraceHop("urn:asap:agent:a", "urn:asap:agent:b", 15.0)]
        out = trace_to_json_export("trace-1", hops)
        assert out["trace_id"] == "trace-1"
        assert len(out["hops"]) == 1
        assert out["hops"][0]["sender"] == "urn:asap:agent:a"
        assert out["hops"][0]["recipient"] == "urn:asap:agent:b"
        assert out["hops"][0]["duration_ms"] == 15.0

    def test_multiple_hops_and_round_trip(self) -> None:
        hops = [
            TraceHop("urn:asap:agent:a", "urn:asap:agent:b", 10.0),
            TraceHop("urn:asap:agent:b", "urn:asap:agent:c", None),
        ]
        out = trace_to_json_export("t2", hops)
        assert out["trace_id"] == "t2"
        assert len(out["hops"]) == 2
        assert out["hops"][1]["duration_ms"] is None
        assert json.loads(json.dumps(out)) == out


class TestExtractTraceIds:
    """Tests for extract_trace_ids."""

    def test_extracts_unique_trace_ids(self) -> None:
        lines = [
            '{"event": "asap.request.received", "trace_id": "t1", "envelope_id": "e1"}',
            '{"event": "asap.request.processed", "trace_id": "t1", "envelope_id": "e1"}',
            '{"event": "asap.request.received", "trace_id": "t2", "envelope_id": "e2"}',
        ]
        assert extract_trace_ids(lines) == ["t1", "t2"]

    def test_returns_sorted(self) -> None:
        lines = [
            '{"event": "asap.request.received", "trace_id": "z"}',
            '{"event": "asap.request.received", "trace_id": "a"}',
        ]
        assert extract_trace_ids(lines) == ["a", "z"]

    def test_ignores_non_asap_events(self) -> None:
        lines = ['{"event": "other", "trace_id": "t1"}']
        assert extract_trace_ids(lines) == []


class TestParseTraceFromLines:
    """Tests for parse_trace_from_lines (integration)."""

    def test_full_flow(self) -> None:
        lines = [
            json.dumps(
                {
                    "event": EVENT_RECEIVED,
                    "envelope_id": "e1",
                    "trace_id": "trace-123",
                    "sender": "urn:asap:agent:client",
                    "recipient": "urn:asap:agent:echo",
                    "timestamp": "2026-01-31T12:00:00Z",
                }
            ),
            json.dumps(
                {
                    "event": EVENT_PROCESSED,
                    "envelope_id": "e1",
                    "trace_id": "trace-123",
                    "duration_ms": 12.5,
                }
            ),
        ]
        hops, diagram = parse_trace_from_lines(lines, "trace-123")
        assert len(hops) == 1
        assert diagram == "client -> echo (12ms)"

    def test_no_match_returns_empty(self) -> None:
        lines = ['{"event": "other", "trace_id": "other"}']
        hops, diagram = parse_trace_from_lines(lines, "missing")
        assert len(hops) == 0
        assert diagram == ""
