"""`asap keys generate` — Ed25519 key generation and management."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

from asap.crypto.keys import generate_keypair, serialize_private_key

# Restrict private key file to owner read/write only (security)
PRIVATE_KEY_FILE_MODE = 0o600


def register_keys_commands(root: typer.Typer) -> None:
    """Register the ``keys`` command group (Ed25519 key management) on *root*."""
    keys_app = typer.Typer(help="Ed25519 key generation and management.")
    root.add_typer(keys_app, name="keys")

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
