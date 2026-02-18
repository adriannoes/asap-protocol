"""Command-line interface for ASAP Protocol utilities.

This module provides CLI commands for schema export, inspection, validation,
trace visualization, and an interactive REPL for testing payloads.

Example:
    >>> # From terminal:
    >>> # asap --version
    >>> # asap export-schemas --output-dir ./schemas
    >>> # asap list-schemas
    >>> # asap show-schema agent
    >>> # asap validate-schema message.json --schema-type envelope
    >>> # asap trace <trace-id> [--log-file asap.log] [--format ascii|json]
    >>> # asap repl  # Interactive REPL with ASAP models
"""

import asyncio
import code
import json
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Annotated, Optional

import typer
from pydantic import ValidationError

from asap import __version__
from asap.crypto.keys import (
    generate_keypair,
    load_private_key_from_file_sync,
    serialize_private_key,
)
from asap.crypto.models import SignedManifest
from asap.crypto.signing import sign_manifest, verify_manifest
from asap.economics.delegation import (
    DelegationConstraints,
    create_delegation_jwt,
)
from asap.economics.delegation_storage import SQLiteDelegationStorage
from asap.errors import SignatureVerificationError
from asap.models import Envelope, TaskRequest, generate_id
from asap.models.entities import Capability, Endpoint, Manifest, Skill

from asap.observability.trace_parser import parse_trace_from_lines, trace_to_json_export
from asap.schemas import SCHEMA_REGISTRY, export_all_schemas, get_schema_json, list_schema_entries

app = typer.Typer(help="ASAP Protocol CLI.")

# Nested Typer app for key management (Ed25519)
keys_app = typer.Typer(help="Ed25519 key generation and management.")
app.add_typer(keys_app, name="keys")

manifest_app = typer.Typer(help="Manifest operations (sign, verify).")
app.add_typer(manifest_app, name="manifest")

delegation_app = typer.Typer(help="Delegation token operations (create, revoke).")
app.add_typer(delegation_app, name="delegation")

# Restrict private key file to owner read/write only (security)
PRIVATE_KEY_FILE_MODE = 0o600

# Default directory for schema operations
DEFAULT_SCHEMAS_DIR = Path("schemas")


@keys_app.command("generate")
def keys_generate(
    out: Annotated[
        Path,
        typer.Option(..., "--out", "-o", help="Output path for the private key PEM file."),
    ],
) -> None:
    """Write new Ed25519 key pair to PEM file (mode 0600)."""
    if out.exists() and out.is_dir():
        raise typer.BadParameter(f"Output path is a directory: {out}")
    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    private_key, _ = generate_keypair()
    pem = serialize_private_key(private_key)
    out.write_bytes(pem)
    try:
        out.chmod(PRIVATE_KEY_FILE_MODE)
    except OSError as exc:
        typer.echo(
            f"Warning: could not set file permissions to 0600: {exc}. "
            "Ensure the key file is not readable by others.",
            err=True,
        )
    typer.echo(f"Private key written to {out}")


@manifest_app.command("sign")
def manifest_sign(
    key: Annotated[
        Path,
        typer.Option(..., "--key", "-k", help="Path to the Ed25519 private key PEM file."),
    ],
    manifest_file: Annotated[
        Path,
        typer.Argument(help="Path to the manifest JSON file."),
    ],
    out: Annotated[
        Optional[Path],
        typer.Option("--out", "-o", help="Output path for signed manifest JSON (default: stdout)."),
    ] = None,
) -> None:
    """Sign manifest JSON with Ed25519; output signed manifest (JCS canonicalized)."""
    if not key.exists():
        raise typer.BadParameter(f"Key file not found: {key}")
    if not manifest_file.exists():
        raise typer.BadParameter(f"Manifest file not found: {manifest_file}")
    try:
        manifest_data = json.loads(manifest_file.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise typer.BadParameter(f"Invalid JSON in manifest: {exc}") from exc
    try:
        manifest = Manifest.model_validate(manifest_data)
    except ValidationError as exc:
        raise typer.BadParameter(f"Invalid manifest: {exc}") from exc
    private_key = load_private_key_from_file_sync(key)
    signed = sign_manifest(manifest, private_key)
    output = json.dumps(signed.model_dump(), indent=2)
    if out is not None:
        Path(out).write_text(output, encoding="utf-8")
        typer.echo(f"Signed manifest written to {out}")
    else:
        typer.echo(output)


@manifest_app.command("info")
def manifest_info(
    signed_manifest_file: Annotated[
        Path,
        typer.Argument(help="Path to the signed manifest JSON file."),
    ],
) -> None:
    """Show manifest ID, name, trust level, ASAP version."""
    if not signed_manifest_file.exists():
        raise typer.BadParameter(f"File not found: {signed_manifest_file}")
    try:
        data = json.loads(signed_manifest_file.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise typer.BadParameter(f"Invalid JSON: {exc}") from exc
    try:
        signed = SignedManifest.model_validate(data)
    except ValidationError as exc:
        raise typer.BadParameter(f"Invalid signed manifest format: {exc}") from exc
    from asap.crypto.trust import detect_trust_level

    trust_level = detect_trust_level(signed)
    manifest = signed.manifest
    typer.echo(f"Manifest ID: {manifest.id}")
    typer.echo(f"Name: {manifest.name}")
    typer.echo(f"Trust level: {trust_level.value}")
    typer.echo(f"ASAP version: {manifest.capabilities.asap_version}")


@manifest_app.command("verify")
def manifest_verify(
    signed_manifest_file: Annotated[
        Path,
        typer.Argument(help="Path to the signed manifest JSON file."),
    ],
    public_key: Annotated[
        Optional[Path],
        typer.Option(
            "--public-key",
            "-k",
            help="Path to private key PEM (public key is used for verification). Optional if manifest includes public_key.",
        ),
    ] = None,
) -> None:
    """Verify Ed25519 signature; use --public-key if manifest has no embedded public_key."""
    if not signed_manifest_file.exists():
        raise typer.BadParameter(f"File not found: {signed_manifest_file}")
    try:
        data = json.loads(signed_manifest_file.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise typer.BadParameter(f"Invalid JSON: {exc}") from exc
    try:
        signed = SignedManifest.model_validate(data)
    except ValidationError as exc:
        raise typer.BadParameter(f"Invalid signed manifest format: {exc}") from exc
    pub_key = None
    if public_key is not None:
        if not public_key.exists():
            raise typer.BadParameter(f"Public key file not found: {public_key}")
        priv = load_private_key_from_file_sync(public_key)
        pub_key = priv.public_key()
    try:
        verify_manifest(signed, public_key=pub_key)
    except SignatureVerificationError as e:
        typer.echo(f"Verification failed: {e.message}", err=True)
        raise typer.Exit(1) from e
    from asap.crypto.trust import detect_trust_level

    trust_level = detect_trust_level(signed)
    typer.echo(f"Signature valid (trust: {trust_level.value}): {signed_manifest_file}")


@delegation_app.command("create")
def delegation_create(
    delegate: str = typer.Option(..., "--delegate", "-d", help="URN of the delegate."),
    scopes: str = typer.Option(..., "--scopes", "-s", help="Comma-separated scopes."),
    key_file: Path = typer.Option(..., "--key", "-k", help="Path to delegator Ed25519 key PEM."),
    delegator: str = typer.Option(..., "--delegator", help="URN of the delegator (issuer)."),
    expires_in: Optional[int] = typer.Option(86400, "--expires-in", help="Validity in seconds."),
    max_tasks: Optional[int] = typer.Option(None, "--max-tasks", help="Max tasks for delegate."),
) -> None:
    """Create a signed delegation token (JWT, EdDSA). Output: raw JWT string."""
    if not key_file.exists():
        raise typer.BadParameter(f"Key file not found: {key_file}")
    if not key_file.is_file():
        raise typer.BadParameter(f"Key path is not a file: {key_file}")
    try:
        mode = key_file.stat().st_mode & 0o777
        if mode & 0o077:
            typer.echo(
                f"Warning: key file {key_file} has open permissions ({oct(mode)}). "
                "Consider restricting to 0600.",
                err=True,
            )
    except OSError:
        pass
    scope_list = [s.strip() for s in scopes.split(",") if s.strip()]
    if not scope_list:
        raise typer.BadParameter("At least one scope is required.")
    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(seconds=expires_in or 86400)
    constraints = DelegationConstraints(
        max_tasks=max_tasks,
        max_cost_usd=None,
        expires_at=expires_at,
    )
    private_key = load_private_key_from_file_sync(key_file)
    token = create_delegation_jwt(
        delegator_urn=delegator,
        delegate_urn=delegate,
        scopes=scope_list,
        constraints=constraints,
        private_key=private_key,
    )
    typer.echo(token)


# Default DB path for delegation revoke (same as server when using asap_state.db).
DEFAULT_DELEGATION_DB = Path(os.environ.get("ASAP_STORAGE_PATH", "asap_state.db"))


@delegation_app.command("revoke")
def delegation_revoke(
    token_id: str = typer.Argument(..., help="Delegation token ID (jti) to revoke."),
    db: Annotated[
        Optional[Path],
        typer.Option("--db", "-d", help="Path to SQLite DB (revocations table)."),
    ] = None,
    reason: Annotated[
        Optional[str],
        typer.Option("--reason", "-r", help="Optional reason for revocation."),
    ] = None,
) -> None:
    """Revoke a delegation token by ID."""
    db_path = Path(db) if db is not None else DEFAULT_DELEGATION_DB
    storage = SQLiteDelegationStorage(db_path=db_path)
    asyncio.run(storage.revoke_cascade(token_id.strip(), reason=reason))
    typer.echo(f"Revoked delegation token: {token_id}")


# Global verbose flag
_verbose: bool = False


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

# Module-level singleton options to avoid B008 linting errors
OUTPUT_DIR_EXPORT_OPTION = typer.Option(
    DEFAULT_SCHEMAS_DIR,
    "--output-dir",
    help="Directory where JSON schemas will be written.",
)
OUTPUT_DIR_LIST_OPTION = typer.Option(
    DEFAULT_SCHEMAS_DIR,
    "--output-dir",
    help="Directory where JSON schemas are written.",
)


@app.callback()
def cli(
    version: bool = VERSION_OPTION,
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable verbose output."),
) -> None:
    """ASAP Protocol CLI entrypoint."""
    global _verbose
    _verbose = verbose


@app.command("export-schemas")
def export_schemas(
    output_dir: Path = OUTPUT_DIR_EXPORT_OPTION,
) -> None:
    """Export all ASAP JSON schemas to the output directory."""
    try:
        written_paths = export_all_schemas(output_dir)
        typer.echo(f"Exported {len(written_paths)} schemas to {output_dir}")
        if _verbose:
            for path in sorted(written_paths):
                typer.echo(f"  - {path.relative_to(output_dir)}")
    except PermissionError as exc:
        raise typer.BadParameter(f"Cannot write to directory: {output_dir}") from exc
    except OSError as exc:
        raise typer.BadParameter(f"Failed to export schemas: {exc}") from exc


@app.command("list-schemas")
def list_schemas(
    output_dir: Path = OUTPUT_DIR_LIST_OPTION,
) -> None:
    """List available schema names and output paths."""
    entries = list_schema_entries(output_dir)
    for name, path in entries:
        typer.echo(f"{name}\t{path.relative_to(output_dir)}")


@app.command("show-schema")
def show_schema(schema_name: str) -> None:
    """Print the JSON schema for a named model."""
    try:
        schema = get_schema_json(schema_name)
    except ValueError as exc:
        raise typer.BadParameter(str(exc)) from exc

    typer.echo(json.dumps(schema, indent=2))


def _detect_schema_type(data: dict[str, object]) -> str | None:
    """Attempt to auto-detect schema type from JSON data.

    Auto-detects envelope type if payload_type field is present.

    Args:
        data: Parsed JSON data.

    Returns:
        Detected schema type name or None if not detectable.
    """
    # Envelope detection: has payload_type field
    if "payload_type" in data and "asap_version" in data:
        return "envelope"
    return None


def _validate_against_schema(data: dict[str, object], schema_type: str) -> list[str]:
    """Validate JSON data against a registered schema.

    Args:
        data: Parsed JSON data to validate.
        schema_type: Schema type name from SCHEMA_REGISTRY.

    Returns:
        List of validation error messages (empty if valid).

    Raises:
        ValueError: If schema_type is not registered.
    """
    if schema_type not in SCHEMA_REGISTRY:
        raise ValueError(f"Unknown schema type: {schema_type}")

    model_class = SCHEMA_REGISTRY[schema_type]
    try:
        model_class.model_validate(data)
        return []
    except ValidationError as exc:
        errors: list[str] = []
        for error in exc.errors():
            loc = ".".join(str(part) for part in error["loc"])
            msg = error["msg"]
            errors.append(f"  - {loc}: {msg}")
        return errors


@app.command("validate-schema")
def validate_schema(
    file: Annotated[Path, typer.Argument(help="Path to JSON file to validate.")],
    schema_type: Annotated[
        Optional[str],
        typer.Option(
            "--schema-type",
            help="Schema type to validate against (e.g., agent, envelope, task_request).",
        ),
    ] = None,
) -> None:
    """Validate a JSON file against an ASAP schema.

    The schema type can be auto-detected for envelope files (those containing
    payload_type and asap_version fields). For other schema types, use the
    --schema-type option.

    Available schema types: agent, manifest, conversation, task, message,
    artifact, state_snapshot, text_part, data_part, file_part, resource_part,
    template_part, task_request, task_response, task_update, task_cancel,
    message_send, state_query, state_restore, artifact_notify, mcp_tool_call,
    mcp_tool_result, mcp_resource_fetch, mcp_resource_data, envelope.
    """
    if not file.exists():
        raise typer.BadParameter(f"File not found: {file}")

    # Parse JSON
    try:
        content = file.read_text(encoding="utf-8")
        data = json.loads(content)
    except json.JSONDecodeError as exc:
        raise typer.BadParameter(f"Invalid JSON: {exc}") from exc

    if not isinstance(data, dict):
        raise typer.BadParameter("JSON root must be an object")

    # Determine schema type
    effective_schema_type = schema_type
    if effective_schema_type is None:
        effective_schema_type = _detect_schema_type(data)
        if effective_schema_type is None:
            raise typer.BadParameter(
                "Cannot auto-detect schema type. Use --schema-type to specify."
            )

    # Validate
    try:
        errors = _validate_against_schema(data, effective_schema_type)
    except ValueError as exc:
        raise typer.BadParameter(str(exc)) from exc

    if errors:
        error_details = "\n".join(errors)
        raise typer.BadParameter(f"Validation error:\n{error_details}")

    typer.echo(f"Valid {effective_schema_type} schema: {file}")


# Environment variable for default trace log file
ENV_TRACE_LOG = "ASAP_TRACE_LOG"

# REPL banner and namespace
REPL_BANNER = (
    "ASAP Protocol REPL - test payloads interactively.\n"
    "  Envelope, TaskRequest, Manifest, generate_id, sample_envelope() available.\n"
    "  Type exit() or Ctrl-D to quit."
)


def _repl_namespace() -> dict[str, object]:
    """Build namespace for the ASAP REPL with models and a sample envelope helper."""

    def sample_envelope() -> Envelope:
        """Return a sample task.request envelope for quick testing."""
        return Envelope(
            asap_version="0.1",
            sender="urn:asap:agent:repl-sender",
            recipient="urn:asap:agent:repl-recipient",
            payload_type="task.request",
            payload=TaskRequest(
                conversation_id=f"conv-{generate_id()}",
                skill_id="echo",
                input={"message": "hello from REPL"},
            ).model_dump(),
        )

    return {
        "Envelope": Envelope,
        "TaskRequest": TaskRequest,
        "Manifest": Manifest,
        "Capability": Capability,
        "Endpoint": Endpoint,
        "Skill": Skill,
        "generate_id": generate_id,
        "sample_envelope": sample_envelope,
    }


@app.command("repl")
def repl() -> None:
    """Start an interactive REPL with ASAP models for testing payloads.

    Provides Envelope, TaskRequest, Manifest, generate_id, and sample_envelope()
    in the namespace. Use Python's code module for the interactive loop.
    """
    namespace = _repl_namespace()
    code.interact(banner=REPL_BANNER, local=namespace)


@app.command("trace")
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
            "Error: trace_id is required. Usage: asap trace <trace-id> [--log-file PATH]", err=True
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


def main() -> None:
    """Run the ASAP Protocol CLI."""
    app()


if __name__ == "__main__":
    main()
