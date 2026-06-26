# Apprise Notifications Platform

The `k3s-01` overlay deploys Apprise in the existing `notifications` namespace
and exposes it through Traefik at `apprise.infra.plexplease.com` with
certificates issued by the `letsencrypt-cloudflare` ClusterIssuer.

Apprise configuration is sourced from OpenBao through External Secrets. The
`apprise-config` ExternalSecret reads key `prod/platform/notifications` property
`APPRISE_CONFIG` from the `openbao` ClusterSecretStore and writes it as
`apprise.yml` in the `apprise-config` Kubernetes Secret. Store ntfy as the first
backend in that OpenBao value; do not commit ntfy URLs or tokens to Git.

Alertmanager posts to the in-cluster Apprise Alertmanager webhook transformer,
which formats grouped alerts and forwards normalized notifications to Apprise
key `apprise`.
