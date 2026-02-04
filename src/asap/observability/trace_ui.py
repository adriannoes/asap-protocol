"""Optional Web UI for ASAP trace visualization.

Serves a simple FastAPI app to browse traces, search by trace_id, and visualize
request flow from pasted JSON log lines (ASAP_LOG_FORMAT=json).

Run with: uvicorn asap.observability.trace_ui:app --reload
Then open http://localhost:8000
"""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from asap.observability.trace_parser import (
    TraceHop,
    extract_trace_ids,
    parse_trace_from_lines,
)

MAX_LOG_LINES_LENGTH = 2 * 1024 * 1024


def _parse_log_lines(raw: str, max_length: int = MAX_LOG_LINES_LENGTH) -> list[str]:
    """Parse raw log lines into non-empty stripped lines; raise 413 if over max_length."""
    if len(raw) > max_length:
        raise HTTPException(
            status_code=413,
            detail=f"Log lines payload too large (max {max_length} bytes)",
        )
    return [s.strip() for s in raw.strip().splitlines() if s.strip()]


app = FastAPI(
    title="ASAP Trace UI",
    description="Browse and visualize ASAP request traces from JSON log lines.",
    version="0.1.0",
)


class LogLinesBody(BaseModel):
    """Request body with newline-separated log lines."""

    log_lines: str


class VisualizeBody(BaseModel):
    """Request body for trace visualization."""

    log_lines: str
    trace_id: str


def _hops_to_dict(hops: list[TraceHop]) -> list[dict[str, Any]]:
    """Convert TraceHop list to JSON-serializable dicts."""
    return [
        {"sender": h.sender, "recipient": h.recipient, "duration_ms": h.duration_ms} for h in hops
    ]


@app.get("/", response_class=HTMLResponse)
def index() -> HTMLResponse:
    """Serve the trace browser UI (paste logs, list trace IDs, visualize)."""
    html = _INDEX_HTML
    return HTMLResponse(html)


@app.post("/api/traces/list")
def list_traces(body: LogLinesBody) -> dict[str, Any]:
    """Extract unique trace IDs from pasted log lines."""
    lines = _parse_log_lines(body.log_lines)
    trace_ids = extract_trace_ids(lines)
    return {"trace_ids": trace_ids}


@app.post("/api/traces/visualize")
def visualize_trace(body: VisualizeBody) -> dict[str, Any]:
    """Parse logs and return hops + ASCII diagram for the given trace_id."""
    lines = _parse_log_lines(body.log_lines)
    hops, diagram = parse_trace_from_lines(lines, body.trace_id.strip())
    if not diagram:
        raise HTTPException(status_code=404, detail=f"No trace found for: {body.trace_id}")
    return {
        "trace_id": body.trace_id,
        "hops": _hops_to_dict(hops),
        "diagram": diagram,
    }


_INDEX_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>ASAP Trace UI</title>
  <style>
    * { box-sizing: border-box; }
    body { font-family: system-ui, sans-serif; max-width: 900px; margin: 1rem auto; padding: 0 1rem; }
    h1 { font-size: 1.25rem; }
    label { display: block; margin-top: 0.75rem; font-weight: 600; }
    textarea { width: 100%; min-height: 120px; font-family: monospace; font-size: 0.8rem; padding: 0.5rem; }
    input[type="text"] { width: 100%; max-width: 320px; padding: 0.4rem; }
    button { margin-top: 0.5rem; padding: 0.4rem 0.8rem; cursor: pointer; }
    .result { margin-top: 1rem; padding: 0.75rem; background: #f5f5f5; border-radius: 4px; white-space: pre-wrap; font-family: monospace; font-size: 0.9rem; }
    .error { background: #fee; color: #c00; }
    ul { margin: 0.25rem 0; padding-left: 1.25rem; }
    ul li { cursor: pointer; margin: 0.2rem 0; }
    ul li:hover { text-decoration: underline; }
  </style>
</head>
<body>
  <h1>ASAP Trace UI</h1>
  <p>Paste ASAP JSON log lines below (one event per line, <code>ASAP_LOG_FORMAT=json</code>), then list trace IDs or visualize one.</p>

  <label for="logs">Log lines</label>
  <textarea id="logs" placeholder='{"event":"asap.request.received","trace_id":"t1",...}
{"event":"asap.request.processed","trace_id":"t1","duration_ms":15,...}'></textarea>

  <button id="btnList">List trace IDs</button>
  <div id="listResult" class="result" style="display:none;"></div>

  <label for="traceId">Trace ID (or click one above)</label>
  <input type="text" id="traceId" placeholder="e.g. trace-abc">

  <button id="btnViz">Visualize</button>
  <div id="vizResult" class="result" style="display:none;"></div>

  <script>
    function escapeHtml(s) {
      if (typeof s !== 'string') return '';
      const m = { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' };
      return s.replace(/[&<>"']/g, function(c) { return m[c] || c; });
    }
    function errorMessage(e) {
      return e instanceof Error ? e.message : String(e);
    }
    function showError(el, msg) {
      el.textContent = 'Error: ' + msg;
      el.classList.add('error');
      el.style.display = 'block';
    }
    function renderTraceList(data, listResult, traceIdEl) {
      if (data.trace_ids && data.trace_ids.length) {
        const safe = data.trace_ids.map(function(t) {
          return '<li data-trace="' + escapeHtml(t) + '">' + escapeHtml(t) + '</li>';
        });
        listResult.innerHTML = 'Trace IDs: <ul>' + safe.join('') + '</ul>';
        listResult.querySelectorAll('li').forEach(function(li) {
          li.onclick = function() { traceIdEl.value = li.dataset.trace || ''; };
        });
      } else {
        listResult.textContent = 'No trace IDs found in log lines.';
      }
      listResult.classList.remove('error');
      listResult.style.display = 'block';
    }

    const logsEl = document.getElementById('logs');
    const traceIdEl = document.getElementById('traceId');
    const listResult = document.getElementById('listResult');
    const vizResult = document.getElementById('vizResult');

    document.getElementById('btnList').onclick = async function() {
      listResult.style.display = 'none';
      const logLines = logsEl.value.trim();
      if (!logLines) {
        listResult.textContent = 'Paste log lines first.';
        listResult.style.display = 'block';
        return;
      }
      try {
        const r = await fetch('/api/traces/list', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ log_lines: logLines }),
        });
        const data = await r.json();
        renderTraceList(data, listResult, traceIdEl);
      } catch (e) {
        showError(listResult, errorMessage(e));
      }
    };

    document.getElementById('btnViz').onclick = async function() {
      vizResult.style.display = 'none';
      const logLines = logsEl.value.trim();
      const traceId = traceIdEl.value.trim();
      if (!logLines || !traceId) {
        vizResult.textContent = 'Paste log lines and enter a trace ID.';
        vizResult.style.display = 'block';
        return;
      }
      try {
        const r = await fetch('/api/traces/visualize', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ log_lines: logLines, trace_id: traceId }),
        });
        if (!r.ok) {
          const err = await r.json();
          throw new Error(err.detail || r.statusText);
        }
        const data = await r.json();
        vizResult.textContent = data.diagram || JSON.stringify(data, null, 2);
        vizResult.classList.remove('error');
        vizResult.style.display = 'block';
      } catch (e) {
        showError(vizResult, errorMessage(e));
      }
    };
  </script>
</body>
</html>
"""
