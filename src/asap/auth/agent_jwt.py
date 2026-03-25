"""Host JWT and Agent JWT creation and verification for per-runtime-agent identity (v2.2).

JWTs use Ed25519 keys (RFC 8037) with ``alg: EdDSA`` in the JOSE header.
``iss`` for host tokens is the RFC 7638 JWK thumbprint (SHA-256) of the host
public key.
"""

from __future__ import annotations

import base64
import json
import time
from dataclasses import dataclass
from typing import Any, cast

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from joserfc import jwt as jose_jwt
from joserfc.errors import JoseError
from joserfc.jwk import OKPKey
from joserfc.jws import extract_compact as _jws_extract_compact

from asap.auth.identity import (
    AgentSession,
    AgentStore,
    HostIdentity,
    HostStore,
    jwk_thumbprint_sha256,
)
from asap.auth.lifecycle import check_agent_expiry, extend_session
from asap.models.ids import generate_id

# Encode/decode: EdDSA (RFC 8037 Ed25519); joserfc also accepts "Ed25519" alias.
JWT_ALGS_SIGN = "EdDSA"
JWT_ALGS_VERIFY: list[str] = ["EdDSA", "Ed25519"]

HOST_JWT_TYP = "host+jwt"
AGENT_JWT_TYP = "agent+jwt"
HOST_PUBLIC_KEY_CLAIM = "host_public_key"
AGENT_PUBLIC_KEY_CLAIM = "agent_public_key"
CAPABILITIES_CLAIM = "capabilities"

DEFAULT_HOST_JWT_TTL_SECONDS = 300
AGENT_JWT_TTL_SECONDS = 60

# Clock skew allowance for ``iat`` checks (seconds).
_IAT_MAX_FUTURE_SKEW_SECONDS = 60


@dataclass(frozen=True)
class JwtVerifyResult:
    """Outcome of :func:`verify_host_jwt` or :func:`verify_agent_jwt`."""

    ok: bool
    claims: dict[str, Any] | None = None
    host: HostIdentity | None = None
    agent: AgentSession | None = None
    error: str | None = None


class JtiReplayCache:
    """In-memory ``jti`` replay guard (default 90s window).

    Partition keys isolate tokens per host thumbprint or per agent id so
    unrelated identities do not share ``jti`` namespaces.

    ``max_size`` bounds memory: after pruning expired entries, if the map
    still exceeds ``max_size``, entries with the earliest expiry are removed
    first (may slightly weaken replay detection for those keys under extreme
    load; prefer Redis-backed limits in multi-instance production).
    """

    def __init__(self, ttl_seconds: float = 90.0, max_size: int = 10_000) -> None:
        self._ttl = ttl_seconds
        self._max_size = max_size
        self._expiry_by_key: dict[tuple[str, str], float] = {}

    def _prune_expired(self, now: float) -> None:
        dead = [k for k, exp in self._expiry_by_key.items() if exp <= now]
        for k in dead:
            del self._expiry_by_key[k]

    def _evict_to_max_size(self) -> None:
        while len(self._expiry_by_key) > self._max_size:
            oldest = min(self._expiry_by_key, key=lambda k: self._expiry_by_key[k])
            del self._expiry_by_key[oldest]

    def check_and_record(self, partition_key: str, jti: str) -> bool:
        """Record ``jti`` for ``partition_key``.

        Returns:
            True if this is the first use within the TTL window.

            False if the same ``(partition_key, jti)`` was seen within the TTL
            (replay).
        """
        if not jti or not str(jti).strip():
            return False
        now = time.time()
        self._prune_expired(now)
        key = (partition_key, jti)
        if key in self._expiry_by_key and self._expiry_by_key[key] > now:
            return False
        self._expiry_by_key[key] = now + self._ttl
        self._evict_to_max_size()
        return True


def _unverified_header_and_payload(token: str) -> tuple[dict[str, Any], dict[str, Any]]:
    """Parse JWT header and payload without verifying the signature.

    Uses :func:`joserfc.jws.extract_compact` to decode the compact
    serialisation, avoiding manual base64url padding.
    """
    obj = _jws_extract_compact(token.encode("utf-8"))
    header = dict(obj.headers())
    payload: dict[str, Any] = json.loads(obj.payload)
    return header, payload


def _okp_from_public_jwk(public_key: dict[str, Any]) -> OKPKey:
    return OKPKey.import_key(cast("dict[str, str | list[str]]", dict(public_key)))


def _claims_dict(token: Any) -> dict[str, Any]:
    return dict(token.claims)


def _iat_not_in_future(claims: dict[str, Any], *, now_ts: float) -> bool:
    iat = claims.get("iat")
    if iat is None:
        return True
    try:
        iat_ts = float(iat)
    except (TypeError, ValueError):
        return False
    return iat_ts <= now_ts + float(_IAT_MAX_FUTURE_SKEW_SECONDS)


def _exp_valid(claims: dict[str, Any], *, now_ts: float) -> bool:
    """Return True if ``exp`` exists and is strictly after ``now_ts``."""
    exp = claims.get("exp")
    if exp is None:
        return False
    try:
        exp_ts = float(exp)
    except (TypeError, ValueError):
        return False
    return now_ts < exp_ts


def _jti_present(claims: dict[str, Any]) -> bool:
    jti = claims.get("jti")
    return isinstance(jti, str) and bool(jti.strip())


def _audience_matches_expected(
    claims: dict[str, Any],
    expected_audience: str | list[str],
) -> bool:
    """Return True if ``aud`` intersects ``expected_audience`` (RFC 7519 §4.1.3)."""
    aud = claims.get("aud")
    expected = (
        [expected_audience] if isinstance(expected_audience, str) else list(expected_audience)
    )
    if isinstance(aud, str):
        token_auds = [aud]
    elif isinstance(aud, list):
        token_auds = [a for a in aud if isinstance(a, str)]
    else:
        return False
    return any(a in expected for a in token_auds)


async def verify_host_jwt(
    token: str,
    host_store: HostStore,
    *,
    expected_audience: str | list[str] | None = None,
    jti_replay_cache: JtiReplayCache | None = None,
) -> JwtVerifyResult:
    """Verify a Host JWT signature and resolve the host (or inline registration).

    Validates header ``typ``, signature against ``host_public_key`` claim,
    ``iss`` vs thumbprint, ``exp``/``iat``/``jti``, optional replay cache, and
    rejects stored hosts in ``revoked`` status.

    When ``expected_audience`` is set, the ``aud`` claim must match one of the
    expected values (RFC 7519 §4.1.3). Production callers should pass the
    server's manifest id (or equivalent) so tokens cannot be replayed across
    services.

    When no host row exists for ``iss``, verification still succeeds (dynamic
    registration) with ``host=None`` and valid ``claims``.
    """
    try:
        header, unverified_payload = _unverified_header_and_payload(token)
    except (json.JSONDecodeError, UnicodeDecodeError, ValueError, JoseError) as e:
        return JwtVerifyResult(ok=False, error=f"invalid JWT structure: {e!s}")

    if header.get("typ") != HOST_JWT_TYP:
        return JwtVerifyResult(ok=False, error="invalid typ for host JWT")

    try:
        host_pub_claim = unverified_payload.get(HOST_PUBLIC_KEY_CLAIM)
        if not isinstance(host_pub_claim, dict):
            return JwtVerifyResult(ok=False, error="missing or invalid host_public_key claim")
        okp = _okp_from_public_jwk(host_pub_claim)
        decoded = jose_jwt.decode(token, okp, algorithms=JWT_ALGS_VERIFY)
    except (JoseError, ValueError, TypeError) as e:
        return JwtVerifyResult(ok=False, error=f"invalid host JWT: {e!s}")

    claims = _claims_dict(decoded)
    now_ts = time.time()
    if not _exp_valid(claims, now_ts=now_ts):
        return JwtVerifyResult(ok=False, error="token expired or missing exp")
    if not _iat_not_in_future(claims, now_ts=now_ts):
        return JwtVerifyResult(ok=False, error="invalid iat (too far in the future)")
    if not _jti_present(claims):
        return JwtVerifyResult(ok=False, error="missing jti")
    if expected_audience is not None and not _audience_matches_expected(claims, expected_audience):
        return JwtVerifyResult(ok=False, error="audience mismatch")

    host_pub = claims.get(HOST_PUBLIC_KEY_CLAIM)
    if not isinstance(host_pub, dict):
        return JwtVerifyResult(ok=False, error="missing host_public_key in verified claims")
    expected_iss = jwk_thumbprint_sha256(host_pub)
    iss = claims.get("iss")
    if iss != expected_iss:
        return JwtVerifyResult(ok=False, error="iss does not match host_public_key thumbprint")

    if jti_replay_cache is not None:
        partition = str(iss)
        jti = str(claims["jti"])
        if not jti_replay_cache.check_and_record(partition, jti):
            return JwtVerifyResult(ok=False, error="jti replay detected")

    host = await host_store.get_by_public_key(str(iss))
    if host is not None and host.status == "revoked":
        return JwtVerifyResult(ok=False, error="host revoked")

    return JwtVerifyResult(ok=True, claims=claims, host=host)


async def verify_agent_jwt(
    token: str,
    host_store: HostStore,
    agent_store: AgentStore,
    *,
    expected_audience: str | list[str] | None = None,
    jti_replay_cache: JtiReplayCache | None = None,
    agent_store_writable: bool = True,
) -> JwtVerifyResult:
    """Verify an Agent JWT: typ, signatures, host/agent rows, exp/iat/jti, capabilities.

    When ``expected_audience`` is set, ``aud`` must match (RFC 7519 §4.1.3).
    When ``agent_store_writable`` is False, session extension after verification is not persisted.
    """
    try:
        header, unverified_payload = _unverified_header_and_payload(token)
    except (json.JSONDecodeError, UnicodeDecodeError, ValueError, JoseError) as e:
        return JwtVerifyResult(ok=False, error=f"invalid JWT structure: {e!s}")

    if header.get("typ") != AGENT_JWT_TYP:
        return JwtVerifyResult(ok=False, error="invalid typ for agent JWT")

    sub_raw = unverified_payload.get("sub")
    if not isinstance(sub_raw, str) or not sub_raw.strip():
        return JwtVerifyResult(ok=False, error="missing sub (agent id)")

    agent = await agent_store.get(sub_raw)
    if agent is None:
        return JwtVerifyResult(ok=False, error="unknown agent")

    if agent.status in ("revoked", "expired", "pending", "rejected"):
        return JwtVerifyResult(ok=False, error=f"agent session not usable: {agent.status}")

    try:
        okp = _okp_from_public_jwk(dict(agent.public_key))
        decoded = jose_jwt.decode(token, okp, algorithms=JWT_ALGS_VERIFY)
    except (JoseError, ValueError, TypeError) as e:
        return JwtVerifyResult(ok=False, error=f"invalid agent JWT: {e!s}")

    claims = _claims_dict(decoded)
    now_ts = time.time()
    if not _exp_valid(claims, now_ts=now_ts):
        return JwtVerifyResult(ok=False, error="token expired or missing exp")
    if not _iat_not_in_future(claims, now_ts=now_ts):
        return JwtVerifyResult(ok=False, error="invalid iat (too far in the future)")
    if not _jti_present(claims):
        return JwtVerifyResult(ok=False, error="missing jti")
    if expected_audience is not None and not _audience_matches_expected(claims, expected_audience):
        return JwtVerifyResult(ok=False, error="audience mismatch")

    if claims.get("sub") != agent.agent_id:
        return JwtVerifyResult(ok=False, error="sub does not match verified agent id")

    iss = claims.get("iss")
    if not isinstance(iss, str) or not iss.strip():
        return JwtVerifyResult(ok=False, error="missing iss (host thumbprint)")

    host = await host_store.get_by_public_key(iss)
    if host is None:
        return JwtVerifyResult(ok=False, error="unknown host for iss")
    if host.status == "revoked":
        return JwtVerifyResult(ok=False, error="host revoked")
    if host.host_id != agent.host_id:
        return JwtVerifyResult(ok=False, error="agent host_id does not match iss host")

    if jti_replay_cache is not None:
        jti = str(claims["jti"])
        if not jti_replay_cache.check_and_record(agent.agent_id, jti):
            return JwtVerifyResult(ok=False, error="jti replay detected")

    expiry_status = check_agent_expiry(agent)
    if expiry_status == "revoked":
        return JwtVerifyResult(ok=False, error="agent_revoked")
    if expiry_status == "expired":
        return JwtVerifyResult(ok=False, error="agent_expired")

    agent = extend_session(agent)
    if agent_store_writable:
        await agent_store.save(agent)

    return JwtVerifyResult(ok=True, claims=claims, host=host, agent=agent)


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("ascii").rstrip("=")


def _ed25519_private_key_to_okp_key(private_key: Ed25519PrivateKey) -> OKPKey:
    """Build joserfc OKP (Ed25519) JWK including private ``d`` for signing."""
    raw_private = private_key.private_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PrivateFormat.Raw,
        encryption_algorithm=serialization.NoEncryption(),
    )
    raw_public = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
    jwk_dict = {
        "kty": "OKP",
        "crv": "Ed25519",
        "d": _b64url(raw_private),
        "x": _b64url(raw_public),
    }
    return OKPKey.import_key(cast("dict[str, str | list[str]]", jwk_dict))


def create_host_jwt(
    host_keypair: Ed25519PrivateKey,
    aud: str | list[str],
    *,
    agent_public_key: dict[str, Any] | None = None,
    ttl_seconds: int = DEFAULT_HOST_JWT_TTL_SECONDS,
) -> str:
    """Sign a Host JWT (``typ: host+jwt``).

    Claims include ``iss`` (JWK thumbprint of the host public key),
    ``host_public_key`` (public JWK), and optional ``agent_public_key``.
    """
    okp = _ed25519_private_key_to_okp_key(host_keypair)
    host_pub = okp.as_dict(private=False)
    iss = jwk_thumbprint_sha256(dict(host_pub))
    now = int(time.time())
    claims: dict[str, Any] = {
        "iss": iss,
        "aud": aud,
        "iat": now,
        "exp": now + ttl_seconds,
        "jti": f"jwt_{generate_id()}",
        HOST_PUBLIC_KEY_CLAIM: dict(host_pub),
    }
    if agent_public_key is not None:
        claims[AGENT_PUBLIC_KEY_CLAIM] = agent_public_key

    header = {"alg": JWT_ALGS_SIGN, "typ": HOST_JWT_TYP}
    return jose_jwt.encode(
        header,
        claims,
        okp,
        algorithms=[JWT_ALGS_SIGN],
    )


def create_agent_jwt(
    agent_keypair: Ed25519PrivateKey,
    host_thumbprint: str,
    agent_id: str,
    aud: str | list[str],
    *,
    capabilities: list[str] | None = None,
) -> str:
    """Sign an Agent JWT (``typ: agent+jwt``).

    ``iss`` is the host JWK thumbprint; ``sub`` is ``agent_id``; lifetime is
    :data:`AGENT_JWT_TTL_SECONDS` (60s).
    """
    okp = _ed25519_private_key_to_okp_key(agent_keypair)
    now = int(time.time())
    claims: dict[str, Any] = {
        "iss": host_thumbprint,
        "sub": agent_id,
        "aud": aud,
        "iat": now,
        "exp": now + AGENT_JWT_TTL_SECONDS,
        "jti": f"jwt_{generate_id()}",
    }
    if capabilities is not None:
        claims[CAPABILITIES_CLAIM] = capabilities

    header = {"alg": JWT_ALGS_SIGN, "typ": AGENT_JWT_TYP}
    return jose_jwt.encode(
        header,
        claims,
        okp,
        algorithms=[JWT_ALGS_SIGN],
    )
