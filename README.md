# Third-party root CA for Kubernetes

A Kubernetes Juju charm that provides one third-party root CA through the
standard `certificate_transfer` relation interface. It does not modify cluster
nodes or workload containers. Each related consumer receives the CA and updates
its own trust store.

## Configuration

`root-ca` must contain **exactly one literal PEM certificate**. Certificate
bundles, text before or after the PEM block, and malformed certificates are
rejected.

Use a YAML configuration file to preserve the PEM line breaks:

```yaml
third-party-root-ca-k8s:
  root-ca: |
    -----BEGIN CERTIFICATE-----
    ...
    -----END CERTIFICATE-----
```

```bash
juju config third-party-root-ca-k8s --file ca-config.yaml
```

## Integrate

The charm provides `send-ca-cert` with the canonical `certificate_transfer`
interface. Integrate it with any charm that requires `receive-ca-cert`:

```bash
juju deploy ./third-party-root-ca-k8s_*.charm third-party-root-ca-k8s
juju integrate third-party-root-ca-k8s:send-ca-cert <consumer>:receive-ca-cert
```

When the CA configuration changes, the charm republishes it to every related
consumer. A consumer controls where and how it trusts the received CA.

## Development

```bash
PYTHONPATH=src uv run --group unit pytest -v tests/unit
charmcraft pack
```
