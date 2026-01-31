"""Tests for ASAP Trace Web UI (FastAPI app)."""

from fastapi.testclient import TestClient

from asap.observability.trace_ui import app

client = TestClient(app)


def test_index_returns_html() -> None:
    """GET / returns HTML page."""
    response = client.get("/")
    assert response.status_code == 200
    assert "text/html" in response.headers.get("content-type", "")
    assert "ASAP Trace UI" in response.text


def test_list_traces_returns_trace_ids() -> None:
    """POST /api/traces/list returns unique trace IDs from log lines."""
    log_lines = "\n".join([
        '{"event": "asap.request.received", "trace_id": "t1", "envelope_id": "e1"}',
        '{"event": "asap.request.processed", "trace_id": "t1", "envelope_id": "e1"}',
        '{"event": "asap.request.received", "trace_id": "t2", "envelope_id": "e2"}',
    ])
    response = client.post("/api/traces/list", json={"log_lines": log_lines})
    assert response.status_code == 200
    data = response.json()
    assert data["trace_ids"] == ["t1", "t2"]


def test_list_traces_empty_returns_empty_list() -> None:
    """POST /api/traces/list with no ASAP events returns empty list."""
    response = client.post("/api/traces/list", json={"log_lines": "{}"})
    assert response.status_code == 200
    assert response.json()["trace_ids"] == []


def test_visualize_returns_diagram() -> None:
    """POST /api/traces/visualize returns hops and ASCII diagram."""
    log_lines = "\n".join([
        '{"event": "asap.request.received", "envelope_id": "e1", "trace_id": "viz-1", '
        '"sender": "urn:asap:agent:a", "recipient": "urn:asap:agent:b", "timestamp": "2026-01-31T12:00:00Z"}',
        '{"event": "asap.request.processed", "envelope_id": "e1", "trace_id": "viz-1", "duration_ms": 10}',
    ])
    response = client.post(
        "/api/traces/visualize",
        json={"log_lines": log_lines, "trace_id": "viz-1"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["trace_id"] == "viz-1"
    assert data["diagram"] == "a -> b (10ms)"
    assert len(data["hops"]) == 1
    assert data["hops"][0]["sender"] == "urn:asap:agent:a"
    assert data["hops"][0]["recipient"] == "urn:asap:agent:b"
    assert data["hops"][0]["duration_ms"] == 10.0


def test_visualize_not_found_returns_404() -> None:
    """POST /api/traces/visualize with missing trace_id returns 404."""
    response = client.post(
        "/api/traces/visualize",
        json={"log_lines": "{}", "trace_id": "nonexistent"},
    )
    assert response.status_code == 404
    assert "No trace found" in response.json()["detail"]
