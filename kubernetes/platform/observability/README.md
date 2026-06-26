# Observability Platform

The `k3s-01` overlay installs `kube-prometheus-stack` with the K3s `HelmChart`
controller into the existing `observability` namespace. Grafana is exposed
through Traefik at `grafana.infra.plexplease.com` with certificates issued by
the `letsencrypt-cloudflare` ClusterIssuer.

Alertmanager is configured to send alert webhooks to the Apprise Alertmanager
webhook service in the `notifications` namespace. That service transforms the
Alertmanager payload and posts into Apprise, so Apprise remains the notification
fanout layer.
