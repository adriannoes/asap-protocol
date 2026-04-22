"""`asap compliance-check` — Compliance Harness v2 over HTTP(S)."""

from __future__ import annotations

import asyncio
import json
from typing import Optional

import httpx
import typer
from jsonschema import Draft202012Validator

from asap.testing.compliance import ComplianceReport, run_compliance_harness_v2_from_url


def _render_text(report: ComplianceReport, url: str) -> str:
    lines = [
        f"Compliance Harness v2 — {url}",
        f"Score: {report.score:.4f} — {report.summary}",
        f"Categories: {', '.join(report.categories_run)}",
        "",
    ]
    for c in report.checks:
        status = "PASS" if c.passed else "FAIL"
        lines.append(f"  [{status}] {c.category}.{c.name} — {c.message}")
    return "\n".join(lines) + "\n"


def _transport_user_message(exc: BaseException) -> str:
    if isinstance(exc, httpx.ConnectError):
        return "Could not connect to the given --url (connection refused or unreachable)."
    if isinstance(exc, httpx.TimeoutException):
        return "Request timed out; try a larger --timeout."
    if isinstance(exc, httpx.RequestError):
        return f"HTTP transport error: {type(exc).__name__}"
    return f"Unexpected error: {type(exc).__name__}"


def register_compliance_check_command(root: typer.Typer) -> None:
    @root.command(
        "compliance-check",
        help="Run Compliance Harness v2 against an ASAP agent at an HTTP(S) base URL.",
    )
    def compliance_check(
        url: str = typer.Option(
            ...,
            "--url",
            help="Agent base URL (scheme + host[:port]), e.g. http://127.0.0.1:8000",
        ),
        output_format: str = typer.Option(
            "text",
            "--output",
            "--format",
            "-f",
            help="Report format: text or json (--format aliases --output).",
        ),
        exit_on_fail: bool = typer.Option(
            False,
            "--exit-on-fail",
            help="Exit with code 1 if any harness check fails (score < 1.0).",
        ),
        timeout: float = typer.Option(
            60.0,
            "--timeout",
            help="HTTP client timeout in seconds (per request / connect).",
        ),
        asap_version: Optional[str] = typer.Option(
            None,
            "--asap-version",
            help="If set, sent as default ASAP-Version header on requests.",
        ),
    ) -> None:
        out_fmt = output_format.strip().lower()
        if out_fmt not in ("text", "json"):
            raise typer.BadParameter("--output must be 'text' or 'json'")
        if timeout <= 0:
            raise typer.BadParameter("--timeout must be positive")

        headers: dict[str, str] | None = None
        if asap_version is not None and asap_version.strip() != "":
            headers = {"ASAP-Version": asap_version.strip()}

        async def _run() -> ComplianceReport:
            return await run_compliance_harness_v2_from_url(
                url,
                request_timeout=timeout,
                default_headers=headers,
            )

        try:
            report = asyncio.run(_run())
        except (httpx.ConnectError, httpx.TimeoutException, httpx.RequestError) as exc:
            typer.echo(_transport_user_message(exc), err=True)
            raise typer.Exit(2) from exc
        except OSError as exc:
            typer.echo(f"Transport error: {exc}", err=True)
            raise typer.Exit(2) from exc

        if out_fmt == "json":
            payload = report.model_dump(mode="json")
            schema = ComplianceReport.model_json_schema()
            Draft202012Validator(schema).validate(payload)
            typer.echo(json.dumps(payload, indent=2))
        else:
            typer.echo(_render_text(report, url), nl=False)

        if exit_on_fail and report.score < 1.0:
            raise typer.Exit(1)
