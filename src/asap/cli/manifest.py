"""`asap manifest` — Ed25519 manifest signing and verification."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated, Optional

import typer
from pydantic import ValidationError

from asap.crypto.keys import load_private_key_from_file_sync
from asap.crypto.models import SignedManifest
from asap.crypto.signing import sign_manifest, verify_manifest
from asap.crypto.trust import detect_trust_level
from asap.errors import SignatureVerificationError
from asap.models.entities import Manifest


def register_manifest_commands(root: typer.Typer) -> None:
    """Register the ``manifest`` command group (sign, info, verify) on *root*."""
    manifest_app = typer.Typer(help="Manifest operations (sign, verify).")
    root.add_typer(manifest_app, name="manifest")

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
            typer.Option(
                "--out", "-o", help="Output path for signed manifest JSON (default: stdout)."
            ),
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
                help="Path to Ed25519 private key PEM (public key is derived for verification). Optional if manifest includes embedded public_key.",
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
        trust_level = detect_trust_level(signed)
        typer.echo(f"Signature valid (trust: {trust_level.value}): {signed_manifest_file}")
