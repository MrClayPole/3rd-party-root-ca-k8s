# Third-party root CA charm

A Juju subordinate charm that installs a configured PEM root CA into Ubuntu's
standard trust store. It is intended for Juju machine units and LXD system
containers running Ubuntu 20.04, 22.04, 24.04, or 26.04.

## What it changes

The charm manages exactly one file:

`/usr/local/share/ca-certificates/third-party-root-ca.crt`

After a successful configuration change it invokes `update-ca-certificates`.
Clearing `root-ca` removes only that managed file and refreshes the store.

## Deploy and integrate

```bash
juju deploy ./third-party-root-ca_*.charm third-party-root-ca
juju integrate third-party-root-ca:juju-info <principal>:juju-info
juju config third-party-root-ca root-ca="$(base64 -w0 root-ca.pem)"
```

The `root-ca` configuration expects the literal PEM value. For multiline-safe
configuration use a YAML config file:

```yaml
third-party-root-ca:
  root-ca: |
    -----BEGIN CERTIFICATE-----
    ...
    -----END CERTIFICATE-----
```

Then apply it with `juju config third-party-root-ca --file ca-config.yaml`.

## Kubernetes scope

This is a subordinate configurator and does not modify Kubernetes nodes.
However, Kubernetes containers within one pod have separate filesystems. Juju
cannot grant this charm write access to an arbitrary principal workload
container merely through a subordinate `juju-info` relation. For Kubernetes,
the principal charm must deliberately provide an integration or shared writable
volume; without that workload-specific cooperation, updating its CA store is
not technically possible or safe. The charm will not attempt to bypass the
container isolation boundary.

## Development

```bash
tox -e unit
charmcraft pack
```

The source unit tests cover PEM validation, atomic file writes, idempotency,
removal, command failures, and Juju unit statuses.
