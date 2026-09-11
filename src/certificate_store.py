"""Ubuntu CA trust-store management."""

from __future__ import annotations

import os
import ssl
import subprocess
import tempfile
from pathlib import Path


class CertificateError(ValueError):
    """A configured certificate is not a valid PEM certificate."""


class CertificateStoreError(RuntimeError):
    """The operating system trust store could not be refreshed."""


class CertificateStore:
    """Install one managed root CA in Ubuntu's update-ca-certificates store."""

    def __init__(
        self,
        certificate_path: Path = Path("/usr/local/share/ca-certificates/third-party-root-ca.crt"),
        update_command: tuple[str, ...] = ("update-ca-certificates",),
    ) -> None:
        self.certificate_path = certificate_path
        self.update_command = update_command

    def sync(self, certificate: str) -> bool:
        """Install, replace, or remove the managed certificate and refresh the store.

        Returns whether the managed certificate changed. The trust-store command
        is run only after a change, keeping config/relation hook retries idempotent.
        """
        certificate = certificate.strip()
        if certificate:
            self._validate_pem(certificate)
            desired = f"{certificate}\n"
            if self.certificate_path.exists() and self.certificate_path.read_text() == desired:
                return False
            self._atomic_write(desired)
        elif not self.certificate_path.exists():
            return False
        else:
            self.certificate_path.unlink()

        self._refresh()
        return True

    @staticmethod
    def _validate_pem(certificate: str) -> None:
        """Validate that exactly one PEM X.509 certificate was supplied."""
        try:
            ssl.PEM_cert_to_DER_cert(certificate)
        except ValueError as error:
            raise CertificateError(
                "root-ca must contain exactly one PEM X.509 certificate"
            ) from error

    def _atomic_write(self, contents: str) -> None:
        """Write the certificate atomically with world-readable certificate permissions."""
        self.certificate_path.parent.mkdir(parents=True, exist_ok=True)
        descriptor, temporary_name = tempfile.mkstemp(
            dir=self.certificate_path.parent, prefix=f".{self.certificate_path.name}."
        )
        try:
            with os.fdopen(descriptor, "w", encoding="utf-8") as temporary_file:
                temporary_file.write(contents)
                temporary_file.flush()
                os.fsync(temporary_file.fileno())
            os.chmod(temporary_name, 0o644)
            os.replace(temporary_name, self.certificate_path)
        except Exception:
            Path(temporary_name).unlink(missing_ok=True)
            raise

    def _refresh(self) -> None:
        """Regenerate Ubuntu's consolidated CA bundle."""
        try:
            subprocess.run(self.update_command, check=True, capture_output=True, text=True)
        except (OSError, subprocess.CalledProcessError) as error:
            message = f"failed to run {' '.join(self.update_command)}: {error}"
            raise CertificateStoreError(message) from error
