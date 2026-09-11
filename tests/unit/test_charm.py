import pytest
from ops import testing

from certificate_store import CertificateError, CertificateStoreError
from charm import ThirdPartyRootCaCharm

META = {
    "name": "third-party-root-ca",
    "subordinate": True,
    "requires": {"juju-info": {"interface": "juju-info", "scope": "container"}},
}
CONFIG = {"options": {"root-ca": {"type": "string", "default": ""}}}


def context() -> testing.Context:
    return testing.Context(ThirdPartyRootCaCharm, meta=META, config=CONFIG)


def test_missing_configuration_is_blocked(monkeypatch: pytest.MonkeyPatch):
    ctx = context()
    monkeypatch.setattr("charm.CertificateStore.sync", lambda *_: False)

    state_out = ctx.run(ctx.on.install(), testing.State())

    assert state_out.unit_status == testing.BlockedStatus("set root-ca with a PEM root certificate")


def test_valid_configuration_is_active(monkeypatch: pytest.MonkeyPatch):
    ctx = context()
    monkeypatch.setattr("charm.CertificateStore.sync", lambda *_: True)

    state_out = ctx.run(ctx.on.config_changed(), testing.State(config={"root-ca": "a certificate"}))

    assert state_out.unit_status == testing.ActiveStatus("third-party root CA trusted")


def test_invalid_configuration_is_blocked(monkeypatch: pytest.MonkeyPatch):
    ctx = context()
    monkeypatch.setattr(
        "charm.CertificateStore.sync", lambda *_: (_ for _ in ()).throw(CertificateError("bad PEM"))
    )

    state_out = ctx.run(ctx.on.config_changed(), testing.State(config={"root-ca": "bad"}))

    assert state_out.unit_status == testing.BlockedStatus("bad PEM")


def test_refresh_failure_is_blocked(monkeypatch: pytest.MonkeyPatch):
    ctx = context()
    monkeypatch.setattr(
        "charm.CertificateStore.sync", lambda *_: (_ for _ in ()).throw(CertificateStoreError("update failed"))
    )

    state_out = ctx.run(ctx.on.config_changed(), testing.State(config={"root-ca": "bad"}))

    assert state_out.unit_status == testing.BlockedStatus("update failed")
