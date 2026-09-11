#!/usr/bin/env python3
"""Subordinate charm for Ubuntu third-party root CA management."""

from __future__ import annotations

import logging

import ops

from certificate_store import CertificateError, CertificateStore, CertificateStoreError

logger = logging.getLogger(__name__)


class ThirdPartyRootCaCharm(ops.CharmBase):
    """Synchronise the configured CA with the associated Ubuntu trust store."""

    def __init__(self, framework: ops.Framework) -> None:
        super().__init__(framework)
        self.store = CertificateStore()
        framework.observe(self.on.install, self._on_reconcile)
        framework.observe(self.on.config_changed, self._on_reconcile)
        framework.observe(self.on.juju_info_relation_joined, self._on_reconcile)

    def _on_reconcile(self, event: ops.EventBase) -> None:
        """Apply the current configuration, reporting actionable Juju status."""
        certificate = self.config["root-ca"]
        if not certificate.strip():
            try:
                self.store.sync("")
            except CertificateStoreError as error:
                logger.exception("Unable to remove managed root CA")
                self.unit.status = ops.BlockedStatus(str(error))
                return
            self.unit.status = ops.BlockedStatus("set root-ca with a PEM root certificate")
            return

        try:
            self.store.sync(certificate)
        except CertificateError as error:
            self.unit.status = ops.BlockedStatus(str(error))
        except CertificateStoreError as error:
            logger.exception("Unable to refresh Ubuntu trust store")
            self.unit.status = ops.BlockedStatus(str(error))
        else:
            self.unit.status = ops.ActiveStatus("third-party root CA trusted")


if __name__ == "__main__":  # pragma: nocover
    ops.main(ThirdPartyRootCaCharm)
