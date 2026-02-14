"""Unit tests for mTLS (mutual TLS) support."""

from pathlib import Path

import pytest

from asap.models.entities import Capability, Endpoint, Manifest, Skill
from asap.transport.client import ASAPClient
from asap.transport.mtls import MTLSConfig, create_ssl_context, mtls_config_to_uvicorn_kwargs
from asap.transport.server import create_app


def _generate_test_cert_and_key(tmp_path: Path) -> tuple[Path, Path]:
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import rsa
    from cryptography.x509.oid import NameOID
    from cryptography import x509
    from datetime import datetime, timedelta, timezone

    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    subject = issuer = x509.Name(
        [
            x509.NameAttribute(NameOID.COMMON_NAME, "test.local"),
        ]
    )
    now = datetime.now(timezone.utc)
    cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now)
        .not_valid_after(now + timedelta(days=365))
        .sign(key, hashes.SHA256())
    )
    cert_path = tmp_path / "test.crt"
    key_path = tmp_path / "test.key"
    cert_path.write_bytes(cert.public_bytes(serialization.Encoding.PEM))
    key_path.write_bytes(
        key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.TraditionalOpenSSL,
            encryption_algorithm=serialization.NoEncryption(),
        )
    )
    return cert_path, key_path


def test_mtls_config_creation() -> None:
    config = MTLSConfig(cert_file="cert.pem", key_file="key.pem")
    assert config.cert_file == "cert.pem"
    assert config.key_file == "key.pem"
    assert config.ca_certs is None
    assert config.key_password is None


def test_mtls_config_with_ca() -> None:
    config = MTLSConfig(
        cert_file="cert.pem",
        key_file="key.pem",
        ca_certs="ca.pem",
        key_password="secret",
    )
    assert config.ca_certs == "ca.pem"
    assert config.key_password == "secret"


def test_create_ssl_context_client(tmp_path: Path) -> None:
    cert_path, key_path = _generate_test_cert_and_key(tmp_path)
    config = MTLSConfig(cert_file=cert_path, key_file=key_path)
    ctx = create_ssl_context(config, purpose="client")
    assert ctx is not None
    assert ctx.check_hostname is True
    assert ctx.verify_mode == 2  # CERT_REQUIRED


def test_create_ssl_context_client_with_ca(tmp_path: Path) -> None:
    cert_path, key_path = _generate_test_cert_and_key(tmp_path)
    config = MTLSConfig(cert_file=cert_path, key_file=key_path, ca_certs=cert_path)
    ctx = create_ssl_context(config, purpose="client")
    assert ctx is not None
    assert ctx.verify_mode == 2


def test_create_ssl_context_server(tmp_path: Path) -> None:
    cert_path, key_path = _generate_test_cert_and_key(tmp_path)
    config = MTLSConfig(cert_file=cert_path, key_file=key_path)
    ctx = create_ssl_context(config, purpose="server")
    assert ctx is not None
    assert ctx.verify_mode == 0  # CERT_NONE when no ca_certs


def test_create_ssl_context_missing_cert_raises(tmp_path: Path) -> None:
    key_path = tmp_path / "key.pem"
    key_path.write_bytes(b"")
    config = MTLSConfig(cert_file="/nonexistent/cert.pem", key_file=str(key_path))
    with pytest.raises(FileNotFoundError) as exc_info:
        create_ssl_context(config, purpose="client")
    assert "cert" in str(exc_info.value).lower() or "Certificate" in str(exc_info.value)


def test_create_ssl_context_missing_key_raises(tmp_path: Path) -> None:
    cert_path, _ = _generate_test_cert_and_key(tmp_path)
    config = MTLSConfig(cert_file=cert_path, key_file="/nonexistent/key.pem")
    with pytest.raises(FileNotFoundError) as exc_info:
        create_ssl_context(config, purpose="client")
    assert "key" in str(exc_info.value).lower() or "Key" in str(exc_info.value)


def test_mtls_config_to_uvicorn_kwargs(tmp_path: Path) -> None:
    cert_path, key_path = _generate_test_cert_and_key(tmp_path)
    config = MTLSConfig(cert_file=cert_path, key_file=key_path, ca_certs=cert_path)
    kwargs = mtls_config_to_uvicorn_kwargs(config)
    assert kwargs["ssl_keyfile"] == str(key_path)
    assert kwargs["ssl_certfile"] == str(cert_path)
    assert kwargs["ssl_ca_certs"] == str(cert_path)
    assert kwargs["ssl_cert_reqs"] == 2  # CERT_REQUIRED


def test_mtls_config_to_uvicorn_kwargs_without_ca(tmp_path: Path) -> None:
    cert_path, key_path = _generate_test_cert_and_key(tmp_path)
    config = MTLSConfig(cert_file=cert_path, key_file=key_path)
    kwargs = mtls_config_to_uvicorn_kwargs(config)
    assert "ssl_ca_certs" not in kwargs
    assert kwargs["ssl_cert_reqs"] == 0  # CERT_NONE


def test_create_app_with_mtls_config(tmp_path: Path) -> None:
    cert_path, key_path = _generate_test_cert_and_key(tmp_path)
    config = MTLSConfig(cert_file=cert_path, key_file=key_path)
    manifest = Manifest(
        id="urn:asap:agent:mtls-test",
        name="mTLS Test",
        version="1.0.0",
        description="Test",
        capabilities=Capability(
            asap_version="0.1",
            skills=[Skill(id="echo", description="Echo")],
            state_persistence=False,
        ),
        endpoints=Endpoint(asap="https://localhost:8443/asap"),
    )
    app = create_app(manifest, mtls_config=config)
    assert app.state.mtls_config is config


def test_create_app_without_mtls_config() -> None:
    manifest = Manifest(
        id="urn:asap:agent:plain-test",
        name="Plain Test",
        version="1.0.0",
        description="Test",
        capabilities=Capability(
            asap_version="0.1",
            skills=[Skill(id="echo", description="Echo")],
            state_persistence=False,
        ),
        endpoints=Endpoint(asap="http://localhost:8000/asap"),
    )
    app = create_app(manifest)
    assert not hasattr(app.state, "mtls_config") or app.state.mtls_config is None


def test_asap_client_with_mtls_config(tmp_path: Path) -> None:
    cert_path, key_path = _generate_test_cert_and_key(tmp_path)
    config = MTLSConfig(cert_file=cert_path, key_file=key_path)
    client = ASAPClient("https://localhost:8443", mtls_config=config)
    assert client._mtls_config is config


def test_asap_client_without_mtls_config() -> None:
    client = ASAPClient("http://localhost:8000")
    assert client._mtls_config is None
