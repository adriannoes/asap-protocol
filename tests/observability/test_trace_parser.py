"""Tests for ASAP trace parser (log parsing and ASCII diagram)."""

from __future__ import annotations

import json

import pytest

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

    def test_skips_parsed_record_when_trace_id_mismatch(self) -> None:
        """Lines that contain trace_id in body but parsed trace_id differs are skipped."""
        lines = [
            '{"event": "asap.request.received", "trace_id": "t2", "envelope_id": "e1"}',
        ]
        records = filter_records_by_trace_id(lines, "t1")
        assert len(records) == 0

    def test_skips_line_when_trace_id_in_body_but_parsed_trace_id_differs(self) -> None:
        """When line contains filter trace_id as substring but parsed trace_id differs, skip."""
        lines = [
            '{"event": "asap.request.received", "trace_id": "t2", "comment": "t1"}',
            '{"event": "asap.request.received", "trace_id": "t1", "envelope_id": "e1"}',
        ]
        records = filter_records_by_trace_id(lines, "t1")
        assert len(records) == 1
        assert records[0]["trace_id"] == "t1"


class TestTraceHopFormatHop:
    """Tests for TraceHop.format_hop."""

    def test_format_hop_short_urns(self) -> None:
        """format_hop with short_urns=True shortens URNs to last segment."""
        hop = TraceHop("urn:asap:agent:a", "urn:asap:agent:b", 10.0)
        assert hop.format_hop(short_urns=True) == "a -> b (10ms)"

    def test_format_hop_full_urns(self) -> None:
        """format_hop with short_urns=False keeps full URNs."""
        hop = TraceHop("urn:asap:agent:a", "urn:asap:agent:b", None)
        assert hop.format_hop(short_urns=False) == "urn:asap:agent:a -> urn:asap:agent:b (?)"


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

    def test_skips_record_with_non_string_envelope_id(self) -> None:
        """Records with non-string envelope_id are skipped in build_hops."""
        records = [
            {
                "event": EVENT_RECEIVED,
                "envelope_id": 123,
                "trace_id": "t1",
                "sender": "a",
                "recipient": "b",
            },
        ]
        assert build_hops(records) == []

    def test_skips_record_without_sender_or_recipient(self) -> None:
        """Records missing sender or recipient are skipped."""
        records = [
            {"event": EVENT_RECEIVED, "envelope_id": "e1", "trace_id": "t1", "recipient": "b"},
            {"event": EVENT_RECEIVED, "envelope_id": "e2", "trace_id": "t1", "sender": "a"},
        ]
        assert build_hops(records) == []

    def test_skips_record_with_non_string_sender_or_recipient(self) -> None:
        """Records with non-string sender or recipient are skipped in build_hops."""
        records = [
            {
                "event": EVENT_RECEIVED,
                "envelope_id": "e1",
                "trace_id": "t1",
                "sender": 123,
                "recipient": "b",
            },
            {
                "event": EVENT_RECEIVED,
                "envelope_id": "e2",
                "trace_id": "t1",
                "sender": "a",
                "recipient": None,
            },
        ]
        assert build_hops(records) == []

    def test_skips_record_with_other_event_type(self) -> None:
        """Records with event other than received/processed are skipped."""
        records = [
            {
                "event": "asap.request.sent",
                "envelope_id": "e1",
                "trace_id": "t1",
                "sender": "a",
                "recipient": "b",
            },
        ]
        assert build_hops(records) == []


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

    def test_two_hops_short_urns_false(self) -> None:
        """format_ascii_diagram with short_urns=False keeps full URNs."""
        hops = [
            TraceHop("urn:asap:agent:a", "urn:asap:agent:b", 15.0),
            TraceHop("urn:asap:agent:b", "urn:asap:agent:c", 23.0),
        ]
        out = format_ascii_diagram(hops, short_urns=False)
        assert "urn:asap:agent:a" in out
        assert "urn:asap:agent:b" in out
        assert "urn:asap:agent:c" in out

    def test_hop_without_duration_shows_question_mark(self) -> None:
        """format_ascii_diagram shows (?) when duration_ms is None."""
        hops = [TraceHop("urn:asap:agent:a", "urn:asap:agent:b", None)]
        assert format_ascii_diagram(hops) == "a -> b (?)"

    def test_multiple_hops_one_without_duration(self) -> None:
        """format_ascii_diagram mixes hops with and without duration."""
        hops = [
            TraceHop("urn:asap:agent:a", "urn:asap:agent:b", 10.0),
            TraceHop("urn:asap:agent:b", "urn:asap:agent:c", None),
        ]
        out = format_ascii_diagram(hops)
        assert "a -> b (10ms)" in out
        assert "c (?)" in out


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


class TestTraceParserEdgeCases:
    """Edge cases for trace parser helpers and extract_trace_ids."""

    def test_shorten_urn_without_colon(self) -> None:
        """_shorten_urn returns urn unchanged when no colon present."""
        from asap.observability.trace_parser import _shorten_urn

        assert _shorten_urn("nocolon") == "nocolon"

    def test_timestamp_to_sort_key_invalid(self) -> None:
        """_timestamp_to_sort_key returns 0.0 on invalid timestamp."""
        from asap.observability.trace_parser import _timestamp_to_sort_key

        assert _timestamp_to_sort_key("invalid") == 0.0
        assert _timestamp_to_sort_key("") == 0.0

    def test_timestamp_to_sort_key_bad_format_returns_zero(self) -> None:
        """_timestamp_to_sort_key returns 0.0 for bad date format (ValueError path)."""
        from asap.observability.trace_parser import _timestamp_to_sort_key

        assert _timestamp_to_sort_key("not-a-date") == 0.0
        assert _timestamp_to_sort_key("2020-13-45") == 0.0

    def test_format_ascii_diagram_long_urns(self) -> None:
        """format_ascii_diagram with short_urns=False uses full URNs."""
        hops = [
            TraceHop(
                sender="urn:asap:agent:client",
                recipient="urn:asap:agent:echo",
                duration_ms=15.0,
            )
        ]
        diagram = format_ascii_diagram(hops, short_urns=False)
        assert "urn:asap:agent:client" in diagram
        assert "urn:asap:agent:echo" in diagram
        assert "15ms" in diagram

    def test_extract_trace_ids_with_invalid_json(self) -> None:
        """extract_trace_ids skips invalid JSON lines."""
        lines = [
            "not valid json",
            '{"event": "asap.request.received", "trace_id": "t1"}',
        ]
        result = extract_trace_ids(lines)
        assert result == ["t1"]

    def test_extract_trace_ids_with_wrong_event(self) -> None:
        """extract_trace_ids skips non-asap events."""
        lines = [
            '{"event": "wrong.event", "trace_id": "t1"}',
            '{"event": "asap.request.received", "trace_id": "t2"}',
        ]
        result = extract_trace_ids(lines)
        assert result == ["t2"]

    def test_extract_trace_ids_with_empty_trace_id(self) -> None:
        """extract_trace_ids skips empty trace_id."""
        lines = [
            '{"event": "asap.request.received", "trace_id": ""}',
            '{"event": "asap.request.received", "trace_id": "valid"}',
        ]
        result = extract_trace_ids(lines)
        assert result == ["valid"]

    def test_extract_trace_ids_with_non_string_trace_id(self) -> None:
        """extract_trace_ids skips non-string trace_id."""
        lines = [
            '{"event": "asap.request.received", "trace_id": 123}',
            '{"event": "asap.request.received", "trace_id": "valid"}',
        ]
        result = extract_trace_ids(lines)
        assert result == ["valid"]

    def test_extract_trace_ids_skips_other_event_types(self) -> None:
        """extract_trace_ids skips lines whose parsed event is not received/processed."""
        lines = [
            '{"event": "asap.request.received", "trace_id": "t1"}',
            '{"event": "asap.request.received.extra", "trace_id": "t2"}',
            '{"event": "asap.request.processed", "trace_id": "t1"}',
        ]
        result = extract_trace_ids(lines)
        assert result == ["t1"]


class TestTraceParserStructuredLogIntegration:
    @pytest.mark.asyncio
    async def test_asgi_request_produces_parseable_trace_hops(self) -> None:
        import io
        import logging

        from asap.models.entities import Capability, Endpoint, Manifest, Skill
        from asap.models.envelope import Envelope
        from asap.models.payloads import TaskRequest
        from asap.observability.logging import configure_logging
        from asap.transport.handlers import HandlerRegistry, create_echo_handler
        from asap.transport.jsonrpc import ASAP_METHOD
        from asap.transport.rate_limit import create_test_limiter
        from asap.transport.server import create_app
        from httpx import ASGITransport, AsyncClient

        manifest = Manifest(
            id="urn:asap:agent:trace-log-test",
            name="Trace Log Test",
            version="1.0.0",
            description="trace integration",
            capabilities=Capability(
                asap_version="0.1",
                skills=[Skill(id="echo", description="Echo")],
                state_persistence=False,
            ),
            endpoints=Endpoint(asap="http://test/asap"),
        )
        reg = HandlerRegistry()
        reg.register("task.request", create_echo_handler())
        app = create_app(manifest, reg)
        app.state.limiter = create_test_limiter()

        log_buffer = io.StringIO()
        configure_logging(log_format="json", log_level="INFO", force=True)
        handler = logging.StreamHandler(log_buffer)
        handler.setLevel(logging.INFO)
        root_logger = logging.getLogger()
        if root_logger.handlers:
            handler.setFormatter(root_logger.handlers[0].formatter)
        root_logger.addHandler(handler)

        trace_id = "trace-integration-001"
        env = Envelope(
            asap_version="0.1",
            sender="urn:asap:agent:client",
            recipient=manifest.id,
            payload_type="task.request",
            payload=TaskRequest(
                conversation_id="c1",
                skill_id="echo",
                input={"message": "trace"},
            ).model_dump(),
            trace_id=trace_id,
            correlation_id="corr-trace-1",
        )
        rpc = {
            "jsonrpc": "2.0",
            "method": ASAP_METHOD,
            "params": {"envelope": env.model_dump(mode="json")},
            "id": "trace-req-1",
        }

        try:
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                response = await client.post("/asap", json=rpc)
            assert response.status_code == 200

            lines = log_buffer.getvalue().splitlines()
            hops, _diagram = parse_trace_from_lines(lines, trace_id)
            assert len(hops) >= 1
            assert hops[0].sender == env.sender
            assert hops[0].recipient == env.recipient
        finally:
            root_logger.removeHandler(handler)
