"""`asap trace` — visualize request flow and timing for a trace ID from ASAP JSON logs."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Annotated, Optional

import typer

from asap.observability.trace_parser import parse_trace_from_lines, trace_to_json_export

# Environment variable for default trace log file
ENV_TRACE_LOG = "ASAP_TRACE_LOG"


def register_trace_command(root: typer.Typer) -> None:
    """Register the ``trace`` command on *root*."""

    @root.command("trace")
    def trace(
        trace_id: Annotated[
            Optional[str],
            typer.Argument(help="Trace ID to search for in logs (e.g. from envelope.trace_id)."),
        ] = None,
        log_file: Annotated[
            Optional[Path],
            typer.Option(
                "--log-file",
                "-f",
                help="Log file to search (JSON lines). Default: ASAP_TRACE_LOG env or stdin.",
            ),
        ] = None,
        output_format: Annotated[
            str,
            typer.Option(
                "--format",
                "-o",
                help="Output format: ascii (diagram) or json (for external tools).",
            ),
        ] = "ascii",
    ) -> None:
        """Show request flow and timing for a trace ID from ASAP JSON logs.

        Searches log lines for asap.request.received and asap.request.processed
        events with the given trace_id and prints an ASCII diagram of the flow
        with latency per hop (e.g. agent_a -> agent_b (15ms) -> agent_c (23ms)).

        Use --format json to output structured JSON for piping to jq, CI, or
        observability platforms.

        Logs must be JSON lines (ASAP_LOG_FORMAT=json). Use --log-file to pass
        a file, or set ASAP_TRACE_LOG; otherwise reads from stdin.
        """
        effective_log_file = log_file
        if effective_log_file is None and os.environ.get(ENV_TRACE_LOG):
            effective_log_file = Path(os.environ[ENV_TRACE_LOG])

        if trace_id is None or trace_id.strip() == "":
            typer.echo(
                "Error: trace_id is required. Usage: asap trace <trace-id> [--log-file PATH]",
                err=True,
            )
            raise typer.Exit(1)

        trace_id = trace_id.strip()
        fmt = output_format.strip().lower() if output_format else "ascii"
        if fmt not in ("ascii", "json"):
            typer.echo("Error: --format must be 'ascii' or 'json'", err=True)
            raise typer.Exit(1)

        def _lines() -> list[str]:
            if effective_log_file is None:
                return sys.stdin.readlines()
            if not effective_log_file.exists():
                raise typer.BadParameter(f"Log file not found: {effective_log_file}")
            return effective_log_file.read_text(encoding="utf-8").splitlines()

        try:
            lines = _lines()
        except typer.BadParameter:
            raise
        except OSError as exc:
            raise typer.BadParameter(f"Cannot read log file: {exc}") from exc

        hops, diagram = parse_trace_from_lines(lines, trace_id)
        if not hops:
            typer.echo(f"No trace found for: {trace_id}")
            raise typer.Exit(1)
        if fmt == "json":
            typer.echo(json.dumps(trace_to_json_export(trace_id, hops), indent=2))
        else:
            typer.echo(diagram)
