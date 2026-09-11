#!/usr/bin/env python3
"""Kubernetes charm providing a configured CA through certificate_transfer."""

from __future__ import annotations

import re
import ssl

import ops
from charmlibs.interfaces.certificate_transfer import CertificateTransferProvides

_PEM_CERTIFICATE = re.compile(
    r"\A-----BEGIN CERTIFICATE-----\r?\n"
    r"(?:[A-Za-z0-9+/=]+\r?\n)+"
    r"-----END CERTIFICATE-----\Z"
)


class RootCAValidationError(ValueError):
    """The configured root CA is not exactly one valid PEM certificate."""


def validate_root_ca(certificate: str) -> str:
    """Return a canonical PEM CA, rejecting bundles and trailing data."""
    certificate = certificate.strip()
    if not _PEM_CERTIFICATE.fullmatch(certificate):
        raise RootCAValidationError("root-ca must contain exactly one PEM certificate")
    try:
        ssl.PEM_cert_to_DER_cert(certificate)
    except ValueError as error:
        raise RootCAValidationError("root-ca is not a valid PEM certificate") from error
    return certificate + "\n"


class ThirdPartyRootCaCharm(ops.CharmBase):
    """Publish the configured root CA to certificate_transfer requirers."""

    def __init__(self, framework: ops.Framework) -> None:
        super().__init__(framework)
        self.certificate_transfer = CertificateTransferProvides(self, "send-ca-cert")
        framework.observe(self.on.config_changed, self._reconcile)
        framework.observe(self.on.send_ca_cert_relation_joined, self._reconcile)

    def _reconcile(self, _: ops.EventBase) -> None:
        """Validate and publish the CA to every related consumer."""
        if not self.unit.is_leader():
            self.unit.status = ops.WaitingStatus("waiting for leader to publish root CA")
            return
        try:
            certificate = validate_root_ca(self.config["root-ca"])
        except RootCAValidationError as error:
            self.unit.status = ops.BlockedStatus(str(error))
            return

        self.certificate_transfer.add_certificates({certificate})
        self.unit.status = ops.ActiveStatus("root CA published")


if __name__ == "__main__":  # pragma: nocover
    ops.main(ThirdPartyRootCaCharm)
