"""Command-line interface for ASAP Protocol utilities.

Wires the Typer app and delegates command groups to dedicated modules
(``schemas``, ``keys``, ``manifest``, ``delegation``, ``trace``, ``repl``
plus the existing ``compliance_check`` and ``audit_export`` registrations).

Example:
    >>> # asap --version
    >>> # asap export-schemas --output-dir ./schemas
    >>> # asap keys generate -o key.pem
    >>> # asap manifest sign -k key.pem manifest.json
    >>> # asap delegation create -d <urn> -s scope -k key.pem --delegator <urn>
    >>> # asap trace <trace-id> [--log-file asap.log] [--format ascii|json]
    >>> # asap repl  # Interactive REPL with ASAP models
"""

from __future__ import annotations

import typer

from asap import __version__
from asap.cli import schemas as schemas_module
from asap.cli.audit_export import register_audit_export_commands
from asap.cli.compliance_check import register_compliance_check_command
from asap.cli.delegation import register_delegation_commands
from asap.cli.keys import register_keys_commands
from asap.cli.manifest import register_manifest_commands
from asap.cli.repl import _repl_namespace
from asap.cli.repl import register_repl_command
from asap.cli.schemas import DEFAULT_SCHEMAS_DIR
from asap.cli.schemas import register_schemas_commands
from asap.cli.trace import register_trace_command

# Re-exported so legacy `patch("asap.cli.export_all_schemas")` and
# `from asap.cli import DEFAULT_SCHEMAS_DIR, export_all_schemas, _repl_namespace`
# keep resolving after the v2.5.1 S3 cli split (behavior-preserving surface).
from asap.schemas import export_all_schemas

__all__ = [
    "DEFAULT_SCHEMAS_DIR",
    "app",
    "export_all_schemas",
    "main",
    "_repl_namespace",
]

app = typer.Typer(help="ASAP Protocol CLI.")


def _version_callback(value: bool) -> None:
    """Print the version and exit when requested."""
    if value:
        typer.echo(__version__)
        raise typer.Exit()


VERSION_OPTION = typer.Option(
    False,
    "--version",
    help="Show ASAP Protocol version and exit.",
    callback=_version_callback,
    is_eager=True,
)


@app.callback()
def cli(
    version: bool = VERSION_OPTION,
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable verbose output."),
) -> None:
    """ASAP Protocol CLI entrypoint."""
    schemas_module._verbose = verbose


register_schemas_commands(app)
register_keys_commands(app)
register_manifest_commands(app)
register_delegation_commands(app)
register_trace_command(app)
register_repl_command(app)
register_compliance_check_command(app)
register_audit_export_commands(app)


def main() -> None:
    """Run the ASAP Protocol CLI."""
    app()


if __name__ == "__main__":
    main()
