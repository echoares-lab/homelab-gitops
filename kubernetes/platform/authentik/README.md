# authentik

authentik provides the identity platform for the k3s cluster.

The `k3s-01` overlay installs authentik into the existing `identity` namespace with the bundled PostgreSQL chart disabled. It connects to the CloudNativePG `platform-postgres` backend in the `database` namespace and exposes `https://authentik.infra.plexplease.com` through Traefik with the `letsencrypt-cloudflare` cert-manager issuer.

Required OpenBao KV entry:

- `prod/platform/authentik` with `AUTHENTIK_SECRET_KEY`, `AUTHENTIK_BOOTSTRAP_EMAIL`, `AUTHENTIK_BOOTSTRAP_PASSWORD_HASH`, `AUTHENTIK_BOOTSTRAP_TOKEN`, and `AUTHENTIK_POSTGRESQL_PASSWORD`

`AUTHENTIK_BOOTSTRAP_PASSWORD_HASH` is read only on first startup for the `akadmin` account. Generate it with authentik's `hash_password` command before writing it to OpenBao.
