"""WebAuthn credential storage and verification (optional ``asap-protocol[webauthn]`` extra)."""

from __future__ import annotations

import asyncio
import secrets
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol, runtime_checkable

import aiosqlite

from asap.observability import get_logger

logger = get_logger(__name__)


@dataclass(frozen=True, slots=True)
class WebAuthnCredentialRecord:
    """Stored credential material for a WebAuthn public key credential."""

    credential_id: bytes
    public_key: bytes
    sign_count: int


class WebAuthnCeremonyError(Exception):
    """Ceremony failure; ``detail`` is a stable code (safe for logs)."""

    def __init__(self, detail: str) -> None:
        super().__init__(detail)
        self.detail = detail


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
        """Return credential ids for ``host_id``."""


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
            """
            CREATE TABLE IF NOT EXISTS webauthn_credentials (
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
                """
                INSERT OR REPLACE INTO webauthn_credentials
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
                """
                SELECT credential_id, public_key, sign_count
                FROM webauthn_credentials
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
                """
                UPDATE webauthn_credentials
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
                """
                SELECT credential_id FROM webauthn_credentials
                WHERE host_id = ?
                """,
                (host_id,),
            )
            rows = await cur.fetchall()
            return [r[0] for r in rows]


class WebAuthnVerifierImpl:
    """WebAuthn registration/assertion (lazy-imports ``webauthn``; needs ``[webauthn]`` extra)."""

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

    async def start_webauthn_registration(self, host_id: str) -> dict[str, Any]:
        """Start registration; returns browser JSON dict and stores the challenge for ``host_id``."""
        self._ensure_webauthn_installed()
        from webauthn import generate_registration_options
        from webauthn.helpers import options_to_json_dict

        challenge = (
            self._fixed_registration_challenge
            if self._fixed_registration_challenge is not None
            else secrets.token_bytes(32)
        )
        options = generate_registration_options(
            rp_id=self._rp_id,
            rp_name=self._rp_name,
            user_name=host_id,
            user_id=host_id.encode("utf-8"),
            challenge=challenge,
        )
        async with self._lock:
            self._pending_registration[host_id] = challenge
        return options_to_json_dict(options)

    async def finish_webauthn_registration(self, host_id: str, attestation: dict[str, Any]) -> str:
        """Verify attestation, persist credential, return credential id (base64url)."""
        self._ensure_webauthn_installed()
        from webauthn import verify_registration_response
        from webauthn.helpers import bytes_to_base64url
        from webauthn.helpers.exceptions import InvalidRegistrationResponse

        async with self._lock:
            if host_id not in self._pending_registration:
                logger.warning(
                    "asap.webauthn.registration.no_pending_ceremony",
                    host_id=host_id,
                )
                raise WebAuthnCeremonyError("webauthn_registration_state_missing")
            expected_challenge = self._pending_registration[host_id]

        try:
            verified = verify_registration_response(
                credential=attestation,
                expected_challenge=expected_challenge,
                expected_rp_id=self._rp_id,
                expected_origin=self._origin,
            )
        except InvalidRegistrationResponse as exc:
            logger.warning(
                "asap.webauthn.registration.invalid",
                host_id=host_id,
                reason=str(exc),
            )
            raise WebAuthnCeremonyError("webauthn_registration_verification_failed") from exc

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
    ) -> dict[str, Any]:
        """Start assertion; returns browser JSON dict and stores the challenge for ``host_id``."""
        self._ensure_webauthn_installed()
        from webauthn import generate_authentication_options
        from webauthn.helpers import options_to_json_dict
        from webauthn.helpers.structs import (
            PublicKeyCredentialDescriptor,
            UserVerificationRequirement,
        )

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
        options = generate_authentication_options(
            rp_id=self._rp_id,
            challenge=challenge,
            allow_credentials=allow_credentials,
            user_verification=uv,
        )
        async with self._lock:
            self._pending_authentication[host_id] = challenge
        return options_to_json_dict(options)

    async def finish_webauthn_assertion(
        self,
        host_id: str,
        assertion: dict[str, Any],
        *,
        claimed_challenge_b64url: str | None = None,
        require_user_verification: bool = False,
    ) -> bool:
        """Verify assertion; optional ``claimed_challenge_b64url`` must match pending challenge."""
        self._ensure_webauthn_installed()
        from webauthn import verify_authentication_response
        from webauthn.helpers import base64url_to_bytes
        from webauthn.helpers.exceptions import InvalidAuthenticationResponse

        async with self._lock:
            if host_id not in self._pending_authentication:
                logger.warning(
                    "asap.webauthn.assertion.no_pending_ceremony",
                    host_id=host_id,
                )
                return False
            expected_challenge = self._pending_authentication[host_id]
            if claimed_challenge_b64url is not None:
                try:
                    claimed = base64url_to_bytes(claimed_challenge_b64url.strip())
                except (ValueError, TypeError) as exc:
                    logger.warning(
                        "asap.webauthn.assertion.malformed_challenge",
                        host_id=host_id,
                        error_class=type(exc).__name__,
                    )
                    return False
                if claimed != expected_challenge:
                    logger.warning(
                        "asap.webauthn.assertion.challenge_mismatch",
                        host_id=host_id,
                    )
                    return False

        raw_id = assertion.get("rawId", assertion.get("id"))
        if not isinstance(raw_id, str):
            logger.warning(
                "asap.webauthn.assertion.missing_raw_id",
                host_id=host_id,
            )
            return False
        try:
            credential_id = base64url_to_bytes(raw_id)
        except (ValueError, TypeError) as exc:
            logger.warning(
                "asap.webauthn.assertion.malformed_raw_id",
                host_id=host_id,
                error_class=type(exc).__name__,
            )
            return False

        row = await self._store.get_credential(host_id, credential_id)
        if row is None:
            logger.warning(
                "asap.webauthn.assertion.unknown_credential",
                host_id=host_id,
            )
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
        except InvalidAuthenticationResponse as exc:
            logger.warning(
                "asap.webauthn.assertion.invalid",
                host_id=host_id,
                reason=str(exc),
            )
            return False

        async with self._lock:
            self._pending_authentication.pop(host_id, None)

        await self._store.update_sign_count(host_id, credential_id, verified.new_sign_count)
        return True


class WebAuthnSelfAuthVerifier:
    """Wraps :class:`WebAuthnVerifierImpl` for :class:`WebAuthnVerifier`."""

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
