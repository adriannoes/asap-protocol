"""Ed25519 key generation, serialization, and loading for ASAP agent identity."""

from __future__ import annotations

import base64
import os
from datetime import datetime, timezone
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)
from cryptography.hazmat.primitives.serialization import load_pem_private_key
from pydantic import BaseModel

from asap.observability import get_logger

logger = get_logger(__name__)

# Age in days after which to log a key rotation warning (e.g. recommend key renewal).
KEY_ROTATION_WARNING_DAYS = 365
# Recommended mode for private key files (owner read/write only).
KEY_FILE_RECOMMENDED_MODE = 0o600


class KeyMetadata(BaseModel):
    """Key creation time (or file mtime); used for rotation/audit."""

    created_at: datetime


def generate_keypair() -> tuple[Ed25519PrivateKey, Ed25519PublicKey]:
    private_key = Ed25519PrivateKey.generate()
    public_key = private_key.public_key()
    return (private_key, public_key)


def serialize_private_key(key: Ed25519PrivateKey) -> bytes:
    """PEM (PKCS#8, unencrypted)."""
    pem: bytes = key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    return pem


def public_key_to_base64(key: Ed25519PublicKey) -> str:
    raw = key.public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
    return base64.b64encode(raw).decode("ascii")


def load_public_key_from_base64(b64: str) -> Ed25519PublicKey:
    """From base64 raw 32 bytes. Raises ValueError if not 32 bytes."""
    raw = base64.b64decode(b64)
    if len(raw) != 32:
        raise ValueError(f"Ed25519 public key must be 32 bytes, got {len(raw)}")
    return Ed25519PublicKey.from_public_bytes(raw)


def load_private_key_from_pem(pem: bytes) -> Ed25519PrivateKey:
    """From PEM. Raises ValueError if invalid or not Ed25519."""
    key = load_pem_private_key(pem, password=None)
    if not isinstance(key, Ed25519PrivateKey):
        raise ValueError("Key is not an Ed25519 private key")
    return key


def get_key_metadata_from_file(path: str | Path) -> KeyMetadata:
    """KeyMetadata from file mtime (UTC)."""
    path = Path(path)
    mtime = path.stat().st_mtime
    created_at = datetime.fromtimestamp(mtime, tz=timezone.utc)
    return KeyMetadata(created_at=created_at)


def warn_if_key_old(
    metadata: KeyMetadata,
    max_age_days: int = KEY_ROTATION_WARNING_DAYS,
) -> None:
    now = datetime.now(timezone.utc)
    age_days = (now - metadata.created_at).days
    if age_days >= max_age_days:
        logger.warning(
            "key_rotation_recommended",
            age_days=age_days,
            max_age_days=max_age_days,
            created_at=metadata.created_at.isoformat(),
        )


def warn_if_key_file_permissions_loose(path: Path) -> None:
    """Warn when key file is group/other readable (recommend chmod 0600)."""
    try:
        mode = path.stat().st_mode
    except OSError:
        return
    if (mode & 0o77) != 0:
        logger.warning(
            "key_file_permissions_loose",
            path=str(path),
            mode=oct(mode),
            recommended=oct(KEY_FILE_RECOMMENDED_MODE),
            message="Private key file is readable by group or others; consider chmod 0600.",
        )


def load_private_key_from_file_sync(path: str | Path) -> Ed25519PrivateKey:
    """Load Ed25519 private key from PEM file (synchronous, blocking I/O).

    **WARNING:** This function performs blocking disk I/O. Do NOT call it from
    async server or transport code (e.g. request handlers); it would block the
    event loop. Use only from CLI, scripts, or after loading in a thread.
    Logs rotation warning if the key file is older than KEY_ROTATION_WARNING_DAYS.
    Logs a security warning if the file is readable by group or others (recommend chmod 0600).
    """
    path = Path(path)
    warn_if_key_file_permissions_loose(path)
    pem = path.read_bytes()
    key = load_private_key_from_pem(pem)
    metadata = get_key_metadata_from_file(path)
    warn_if_key_old(metadata)
    return key


def load_private_key_from_env(var_name: str) -> Ed25519PrivateKey:
    """From env var (PEM string). Raises ValueError if unset or invalid."""
    value = os.environ.get(var_name)
    if not value:
        raise ValueError(f"Environment variable {var_name!r} is not set or empty")
    pem = value.encode("utf-8")
    return load_private_key_from_pem(pem)
