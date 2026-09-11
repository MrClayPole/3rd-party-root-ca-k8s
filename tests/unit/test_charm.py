import pytest
from ops import testing

from charm import RootCAValidationError, ThirdPartyRootCaCharm, validate_root_ca

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
META = {
    "name": "third-party-root-ca-k8s",
    "provides": {"send-ca-cert": {"interface": "certificate_transfer"}},
}
CONFIG = {"options": {"root-ca": {"type": "string", "default": ""}}}


def context() -> testing.Context:
    return testing.Context(ThirdPartyRootCaCharm, meta=META, config=CONFIG)


def test_validates_exactly_one_certificate():
    assert validate_root_ca(CERTIFICATE) == CERTIFICATE + "\n"


@pytest.mark.parametrize("invalid", ["", "garbage", CERTIFICATE + "\ntrailing", CERTIFICATE * 2])
def test_rejects_empty_bundle_and_trailing_data(invalid: str):
    with pytest.raises(RootCAValidationError):
        validate_root_ca(invalid)


def test_missing_configuration_is_blocked():
    ctx = context()
    state_out = ctx.run(ctx.on.config_changed(), testing.State(leader=True))

    assert state_out.unit_status == testing.BlockedStatus(
        "root-ca must contain exactly one PEM certificate"
    )


def test_publishes_certificate_to_related_consumer():
    ctx = context()
    relation = testing.Relation(
        "send-ca-cert",
        remote_app_name="consumer",
        interface="certificate_transfer",
        remote_app_data={"version": "1"},
    )
    state_out = ctx.run(
        ctx.on.config_changed(),
        testing.State(config={"root-ca": CERTIFICATE}, relations={relation}, leader=True),
    )

    assert state_out.unit_status == testing.ActiveStatus("root CA published")
    assert state_out.get_relation(relation.id).local_app_data["certificates"]


def test_non_leader_waits_for_leader():
    ctx = context()
    state_out = ctx.run(ctx.on.config_changed(), testing.State(config={"root-ca": CERTIFICATE}))

    assert state_out.unit_status == testing.WaitingStatus("waiting for leader to publish root CA")
