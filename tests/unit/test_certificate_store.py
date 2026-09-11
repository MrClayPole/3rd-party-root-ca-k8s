import subprocess
from pathlib import Path

import pytest

from certificate_store import CertificateError, CertificateStore, CertificateStoreError

CERTIFICATE = """-----BEGIN CERTIFICATE-----
MIIBszCCAVmgAwIBAgIUKd2Znjw/+HHgH+N/DpZVIjfaVVkwCgYIKoZIzj0EAwIw
EjEQMA4GA1UEAwwHdGVzdC1jYTAeFw0yNjAxMDEwMDAwMDBaFw0zNjAxMDEwMDAw
MDBaMBIxEDAOBgNVBAMMB3Rlc3QtY2EwWTATBgcqhkjOPQIBBggqhkjOPQMBBwNC
AASXqP8B1KfV9qI3IIKtpzlLiNgvO1hQ63Ih8J/OP8jSuPjKJwVFQuFdDsR9Y2W0
xfZq6OMGGNpMAozW8ZqYI5QPo1MwUTAdBgNVHQ4EFgQU9Jf4rLNvKf0qNQY0YF2y
kD0d0BIwHwYDVR0jBBgwFoAU9Jf4rLNvKf0qNQY0YF2ykD0d0BIwDwYDVR0TAQH/
BAUwAwEB/zAKBggqhkjOPQQDAgNHADBEAiA+TEOh27x3RMVF3jAUNr2v6AQuARmu
xOBr8zYo1lABDwIgY21V1VqFPYGsLKxNAA8JtOHUj0XWF4QUqCRzaJcLPE4=
-----END CERTIFICATE-----"""


def test_sync_installs_and_refreshes(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    commands = []
    store = CertificateStore(tmp_path / "third-party-root-ca.crt")
    monkeypatch.setattr(subprocess, "run", lambda command, **_: commands.append(command))

    assert store.sync(CERTIFICATE) is True
    assert store.certificate_path.read_text() == CERTIFICATE + "\n"
    assert store.certificate_path.stat().st_mode & 0o777 == 0o644
    assert commands == [("update-ca-certificates",)]


def test_sync_is_idempotent(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    store = CertificateStore(tmp_path / "third-party-root-ca.crt")
    monkeypatch.setattr(subprocess, "run", lambda *_, **__: None)
    store.sync(CERTIFICATE)

    assert store.sync(CERTIFICATE) is False


def test_sync_rejects_invalid_pem(tmp_path: Path):
    with pytest.raises(CertificateError, match="exactly one PEM"):
        CertificateStore(tmp_path / "third-party-root-ca.crt").sync("not a certificate")


def test_sync_removes_certificate(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    certificate_path = tmp_path / "third-party-root-ca.crt"
    certificate_path.write_text(CERTIFICATE + "\n")
    commands = []
    monkeypatch.setattr(subprocess, "run", lambda command, **_: commands.append(command))

    assert CertificateStore(certificate_path).sync("") is True
    assert not certificate_path.exists()
    assert commands == [("update-ca-certificates",)]


def test_refresh_failure_is_reported(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    def fail(*_, **__):
        raise subprocess.CalledProcessError(1, "update-ca-certificates")

    monkeypatch.setattr(subprocess, "run", fail)
    with pytest.raises(CertificateStoreError, match="failed to run"):
        CertificateStore(tmp_path / "third-party-root-ca.crt").sync(CERTIFICATE)
