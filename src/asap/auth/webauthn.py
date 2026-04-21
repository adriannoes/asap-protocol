"""WebAuthn credential storage and verification (optional ``asap-protocol[webauthn]``).

This module defines the persistence contract for verified passkeys. Callers that do not
install the ``webauthn`` extra should not import verification helpers that depend on it;
the Protocol and record types here have no third-party imports.

Stores use ``aiosqlite`` for SQLite; that dependency is already part of the core package.
"""

from __future__ import annotations

import asyncio
import secrets
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol, runtime_checkable

import aiosqlite


@dataclass(frozen=True, slots=True)
class WebAuthnCredentialRecord:
    """Stored credential material for a WebAuthn public key credential."""

    credential_id: bytes
    public_key: bytes
    sign_count: int


class WebAuthnCeremonyError(Exception):
    """Raised when a WebAuthn registration or assertion ceremony cannot be completed."""


@runtime_checkable
class WebAuthnCredentialStore(Protocol):
    """Persist WebAuthn credentials keyed by host and credential id."""

    async def save_credential(
        self,
        host_id: str,
        credential_id: bytes,
        public_key: bytes,
        sign_count: int,
    ) -> None:
        """Insert or replace a credential for ``host_id``."""

    async def get_credential(
        self,
        host_id: str,
        credential_id: bytes,
    ) -> WebAuthnCredentialRecord | None:
        """Return the stored row, or ``None`` if missing."""

    async def update_sign_count(
        self,
        host_id: str,
        credential_id: bytes,
        new_count: int,
    ) -> None:
        """Persist the authenticator sign counter after a successful assertion."""

    async def list_credentials(self, host_id: str) -> list[bytes]:
        """Return credential ids registered for ``host_id`` (order is implementation-defined)."""


_WEBAUTHN_CREDENTIALS_TABLE = "webauthn_credentials"


class InMemoryWebAuthnCredentialStore:
    """In-memory :class:`WebAuthnCredentialStore` (asyncio.Lock, per-process only)."""

    def __init__(self) -> None:
        self._lock = asyncio.Lock()
        self._rows: dict[tuple[str, bytes], WebAuthnCredentialRecord] = {}

    async def save_credential(
        self,
        host_id: str,
        credential_id: bytes,
        public_key: bytes,
        sign_count: int,
    ) -> None:
        async with self._lock:
            self._rows[(host_id, credential_id)] = WebAuthnCredentialRecord(
                credential_id=credential_id,
                public_key=public_key,
                sign_count=sign_count,
            )

    async def get_credential(
        self,
        host_id: str,
        credential_id: bytes,
    ) -> WebAuthnCredentialRecord | None:
        async with self._lock:
            return self._rows.get((host_id, credential_id))

    async def update_sign_count(
        self,
        host_id: str,
        credential_id: bytes,
        new_count: int,
    ) -> None:
        async with self._lock:
            key = (host_id, credential_id)
            row = self._rows.get(key)
            if row is None:
                msg = f"no credential for host_id={host_id!r} credential_id={credential_id!r}"
                raise KeyError(msg)
            self._rows[key] = WebAuthnCredentialRecord(
                credential_id=row.credential_id,
                public_key=row.public_key,
                sign_count=new_count,
            )

    async def list_credentials(self, host_id: str) -> list[bytes]:
        async with self._lock:
            return [cid for (hid, cid) in self._rows if hid == host_id]


class SQLiteWebAuthnCredentialStore:
    """File-backed :class:`WebAuthnCredentialStore` using SQLite (``aiosqlite``)."""

    def __init__(self, db_path: str | Path) -> None:
        self._db_path = str(Path(db_path))

    async def _ensure_schema(self, conn: aiosqlite.Connection) -> None:
        await conn.execute(
            f"""
            CREATE TABLE IF NOT EXISTS {_WEBAUTHN_CREDENTIALS_TABLE} (
                host_id TEXT NOT NULL,
                credential_id BLOB NOT NULL,
                public_key BLOB NOT NULL,
                sign_count INTEGER NOT NULL,
                PRIMARY KEY (host_id, credential_id)
            )
            """
        )

    async def save_credential(
        self,
        host_id: str,
        credential_id: bytes,
        public_key: bytes,
        sign_count: int,
    ) -> None:
        async with aiosqlite.connect(self._db_path) as conn:
            await self._ensure_schema(conn)
            await conn.execute(
                f"""
                INSERT OR REPLACE INTO {_WEBAUTHN_CREDENTIALS_TABLE}
                    (host_id, credential_id, public_key, sign_count)
                VALUES (?, ?, ?, ?)
                """,
                (host_id, credential_id, public_key, sign_count),
            )
            await conn.commit()

    async def get_credential(
        self,
        host_id: str,
        credential_id: bytes,
    ) -> WebAuthnCredentialRecord | None:
        async with aiosqlite.connect(self._db_path) as conn:
            await self._ensure_schema(conn)
            conn.row_factory = aiosqlite.Row
            cur = await conn.execute(
                f"""
                SELECT credential_id, public_key, sign_count
                FROM {_WEBAUTHN_CREDENTIALS_TABLE}
                WHERE host_id = ? AND credential_id = ?
                """,
                (host_id, credential_id),
            )
            row = await cur.fetchone()
            if row is None:
                return None
            return WebAuthnCredentialRecord(
                credential_id=row["credential_id"],
                public_key=row["public_key"],
                sign_count=int(row["sign_count"]),
            )

    async def update_sign_count(
        self,
        host_id: str,
        credential_id: bytes,
        new_count: int,
    ) -> None:
        async with aiosqlite.connect(self._db_path) as conn:
            await self._ensure_schema(conn)
            cur = await conn.execute(
                f"""
                UPDATE {_WEBAUTHN_CREDENTIALS_TABLE}
                SET sign_count = ?
                WHERE host_id = ? AND credential_id = ?
                """,
                (new_count, host_id, credential_id),
            )
            await conn.commit()
            if cur.rowcount != 1:
                msg = f"no credential for host_id={host_id!r} credential_id={credential_id!r}"
                raise KeyError(msg)

    async def list_credentials(self, host_id: str) -> list[bytes]:
        async with aiosqlite.connect(self._db_path) as conn:
            await self._ensure_schema(conn)
            cur = await conn.execute(
                f"""
                SELECT credential_id FROM {_WEBAUTHN_CREDENTIALS_TABLE}
                WHERE host_id = ?
                """,
                (host_id,),
            )
            rows = await cur.fetchall()
            return [r[0] for r in rows]


class WebAuthnVerifierImpl:
    """Registration and assertion ceremonies using the optional ``webauthn`` package.

    Requires ``pip install 'asap-protocol[webauthn]'``. Imports from ``webauthn`` are lazy so
    modules that only need :class:`WebAuthnCredentialStore` stay usable without the extra.

    For tests with pre-baked attestation/assertion vectors, pass fixed ``registration_challenge``
    and ``authentication_challenge`` (raw challenge bytes). Production callers should omit them so
    each ``start_*`` call issues a fresh random challenge.
    """

    def __init__(
        self,
        store: WebAuthnCredentialStore,
        *,
        rp_id: str,
        origin: str,
        rp_name: str = "ASAP",
        registration_challenge: bytes | None = None,
        authentication_challenge: bytes | None = None,
    ) -> None:
        self._store = store
        self._rp_id = rp_id
        self._origin = origin
        self._rp_name = rp_name
        self._fixed_registration_challenge = registration_challenge
        self._fixed_authentication_challenge = authentication_challenge
        self._lock = asyncio.Lock()
        self._pending_registration: dict[str, bytes] = {}
        self._pending_authentication: dict[str, bytes] = {}

    def _ensure_webauthn_installed(self) -> None:
        try:
            import webauthn  # noqa: F401
        except ImportError as exc:
            msg = "WebAuthnVerifierImpl requires the optional extra: pip install 'asap-protocol[webauthn]'"
            raise ImportError(msg) from exc

    async def start_webauthn_registration(self, host_id: str) -> str:
        """Begin registration: return base64url challenge and remember it for ``host_id``."""
        self._ensure_webauthn_installed()
        from webauthn import generate_registration_options
        from webauthn.helpers import bytes_to_base64url

        challenge = (
            self._fixed_registration_challenge
            if self._fixed_registration_challenge is not None
            else secrets.token_bytes(32)
        )
        generate_registration_options(
            rp_id=self._rp_id,
            rp_name=self._rp_name,
            user_name=host_id,
            user_id=host_id.encode("utf-8"),
            challenge=challenge,
        )
        async with self._lock:
            self._pending_registration[host_id] = challenge
        return bytes_to_base64url(challenge)

    async def finish_webauthn_registration(self, host_id: str, attestation: dict[str, Any]) -> str:
        """Verify attestation, persist the credential, return base64url credential id."""
        self._ensure_webauthn_installed()
        from webauthn import verify_registration_response
        from webauthn.helpers import bytes_to_base64url
        from webauthn.helpers.exceptions import InvalidRegistrationResponse

        async with self._lock:
            if host_id not in self._pending_registration:
                raise WebAuthnCeremonyError(
                    f"no pending WebAuthn registration ceremony for host_id={host_id!r}"
                )
            expected_challenge = self._pending_registration[host_id]

        try:
            verified = verify_registration_response(
                credential=attestation,
                expected_challenge=expected_challenge,
                expected_rp_id=self._rp_id,
                expected_origin=self._origin,
            )
        except InvalidRegistrationResponse as exc:
            raise WebAuthnCeremonyError(str(exc)) from exc

        async with self._lock:
            self._pending_registration.pop(host_id, None)

        await self._store.save_credential(
            host_id,
            verified.credential_id,
            verified.credential_public_key,
            verified.sign_count,
        )
        return bytes_to_base64url(verified.credential_id)

    async def start_webauthn_assertion(
        self,
        host_id: str,
        *,
        user_verification_required: bool = False,
    ) -> str:
        """Begin assertion: return base64url challenge for an existing credential on ``host_id``."""
        self._ensure_webauthn_installed()
        from webauthn import generate_authentication_options
        from webauthn.helpers import bytes_to_base64url
        from webauthn.helpers.structs import PublicKeyCredentialDescriptor, UserVerificationRequirement

        challenge = (
            self._fixed_authentication_challenge
            if self._fixed_authentication_challenge is not None
            else secrets.token_bytes(32)
        )
        cred_ids = await self._store.list_credentials(host_id)
        allow_credentials = [PublicKeyCredentialDescriptor(id=cid) for cid in cred_ids] or None
        uv = (
            UserVerificationRequirement.REQUIRED
            if user_verification_required
            else UserVerificationRequirement.PREFERRED
        )
        generate_authentication_options(
            rp_id=self._rp_id,
            challenge=challenge,
            allow_credentials=allow_credentials,
            user_verification=uv,
        )
        async with self._lock:
            self._pending_authentication[host_id] = challenge
        return bytes_to_base64url(challenge)

    async def finish_webauthn_assertion(
        self,
        host_id: str,
        assertion: dict[str, Any],
        *,
        claimed_challenge_b64url: str | None = None,
        require_user_verification: bool = False,
    ) -> bool:
        """Verify assertion, advance sign count on success; return False if verification fails.

        When ``claimed_challenge_b64url`` is set (HTTP body ``webauthn.challenge``), it must
        match the pending server-issued challenge for ``host_id`` before cryptographic verification.

        When ``require_user_verification`` is True, the authenticator must have performed user
        verification (browser-controlled agent / high-assurance paths).
        """
        self._ensure_webauthn_installed()
        from webauthn import verify_authentication_response
        from webauthn.helpers import base64url_to_bytes

        async with self._lock:
            if host_id not in self._pending_authentication:
                return False
            expected_challenge = self._pending_authentication[host_id]
            if claimed_challenge_b64url is not None:
                try:
                    claimed = base64url_to_bytes(claimed_challenge_b64url.strip())
                except Exception:
                    return False
                if claimed != expected_challenge:
                    return False

        raw_id = assertion.get("rawId", assertion.get("id"))
        if not isinstance(raw_id, str):
            return False
        credential_id = base64url_to_bytes(raw_id)

        row = await self._store.get_credential(host_id, credential_id)
        if row is None:
            return False

        try:
            verified = verify_authentication_response(
                credential=assertion,
                expected_challenge=expected_challenge,
                expected_rp_id=self._rp_id,
                expected_origin=self._origin,
                credential_public_key=row.public_key,
                credential_current_sign_count=row.sign_count,
                require_user_verification=require_user_verification,
            )
        except Exception:
            return False

        async with self._lock:
            self._pending_authentication.pop(host_id, None)

        await self._store.update_sign_count(host_id, credential_id, verified.new_sign_count)
        return True


class WebAuthnSelfAuthVerifier:
    """Adapts :class:`WebAuthnVerifierImpl` to the ``WebAuthnVerifier`` protocol in ``asap.auth.self_auth``."""

    __asap_performs_real_webauthn__ = True

    def __init__(self, impl: WebAuthnVerifierImpl) -> None:
        self._impl = impl

    async def verify(
        self,
        challenge: str,
        response: Any,
        *,
        host_id: str | None = None,
        require_user_verification: bool = False,
    ) -> bool:
        if host_id is None:
            return False
        if not isinstance(response, dict):
            return False
        return await self._impl.finish_webauthn_assertion(
            host_id,
            response,
            claimed_challenge_b64url=challenge,
            require_user_verification=require_user_verification,
        )


__all__ = [
    "InMemoryWebAuthnCredentialStore",
    "SQLiteWebAuthnCredentialStore",
    "WebAuthnCeremonyError",
    "WebAuthnCredentialRecord",
    "WebAuthnCredentialStore",
    "WebAuthnSelfAuthVerifier",
    "WebAuthnVerifierImpl",
]
