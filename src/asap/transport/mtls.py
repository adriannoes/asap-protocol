"""Optional mTLS (mutual TLS) support for ASAP transport (SD-6).

Provides configuration and SSL context creation for enterprise deployments
where both client and server authenticate via X.509 certificates.
mTLS is optional and never required.
"""

from __future__ import annotations

import ssl
from dataclasses import dataclass
from pathlib import Path


@dataclass
class MTLSConfig:
    cert_file: str | Path
    key_file: str | Path
    ca_certs: str | Path | None = None
    key_password: str | None = None


def create_ssl_context(config: MTLSConfig, *, purpose: str = "client") -> ssl.SSLContext:
    cert_path = Path(config.cert_file)
    key_path = Path(config.key_file)
    if not cert_path.exists():
        raise FileNotFoundError(f"Certificate file not found: {cert_path}")
    if not key_path.exists():
        raise FileNotFoundError(f"Key file not found: {key_path}")

    if purpose == "server":
        ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        ctx.load_cert_chain(
            certfile=str(cert_path),
            keyfile=str(key_path),
            password=config.key_password,
        )
        if config.ca_certs:
            ca_path = Path(config.ca_certs)
            if not ca_path.exists():
                raise FileNotFoundError(f"CA certs file not found: {ca_path}")
            ctx.load_verify_locations(cafile=str(ca_path))
            ctx.verify_mode = ssl.CERT_REQUIRED
        else:
            ctx.verify_mode = ssl.CERT_NONE
    else:
        ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        ctx.load_cert_chain(
            certfile=str(cert_path),
            keyfile=str(key_path),
            password=config.key_password,
        )
        if config.ca_certs:
            ca_path = Path(config.ca_certs)
            if not ca_path.exists():
                raise FileNotFoundError(f"CA certs file not found: {ca_path}")
            ctx.load_verify_locations(cafile=str(ca_path))
        ctx.check_hostname = True
        ctx.verify_mode = ssl.CERT_REQUIRED

    return ctx


def mtls_config_to_uvicorn_kwargs(config: MTLSConfig) -> dict[str, str | int]:
    cert_path = Path(config.cert_file)
    key_path = Path(config.key_file)
    kwargs: dict[str, str | int] = {
        "ssl_keyfile": str(key_path),
        "ssl_certfile": str(cert_path),
        "ssl_cert_reqs": ssl.CERT_REQUIRED if config.ca_certs else ssl.CERT_NONE,
    }
    if config.key_password:
        kwargs["ssl_keyfile_password"] = config.key_password
    if config.ca_certs:
        kwargs["ssl_ca_certs"] = str(Path(config.ca_certs))
    return kwargs
