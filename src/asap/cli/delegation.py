"""`asap delegation` — delegation token creation and revocation."""

from __future__ import annotations

import asyncio
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Annotated, Optional

import typer

from asap.crypto.keys import load_private_key_from_file_sync
from asap.economics.delegation import DelegationConstraints, create_delegation_jwt
from asap.economics.delegation_storage import SQLiteDelegationStorage

# Default DB path for delegation revoke (same as server when using asap_state.db).
DEFAULT_DELEGATION_DB = Path(os.environ.get("ASAP_STORAGE_PATH", "asap_state.db"))


def register_delegation_commands(root: typer.Typer) -> None:
    """Register the ``delegation`` command group (create, revoke) on *root*."""
    delegation_app = typer.Typer(help="Delegation token operations (create, revoke).")
    root.add_typer(delegation_app, name="delegation")

    @delegation_app.command("create")
    def delegation_create(
        delegate: Annotated[
            str, typer.Option(..., "--delegate", "-d", help="URN of the delegate.")
        ],
        scopes: Annotated[str, typer.Option(..., "--scopes", "-s", help="Comma-separated scopes.")],
        key_file: Annotated[
            Path, typer.Option(..., "--key", "-k", help="Path to delegator Ed25519 key PEM.")
        ],
        delegator: Annotated[
            str, typer.Option(..., "--delegator", help="URN of the delegator (issuer).")
        ],
        expires_in: Annotated[
            Optional[int], typer.Option("--expires-in", help="Validity in seconds.")
        ] = 86400,
        max_tasks: Annotated[
            Optional[int], typer.Option("--max-tasks", help="Max tasks for delegate.")
        ] = None,
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

    @delegation_app.command("revoke")
    def delegation_revoke(
        token_id: Annotated[str, typer.Argument(..., help="Delegation token ID (jti) to revoke.")],
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
