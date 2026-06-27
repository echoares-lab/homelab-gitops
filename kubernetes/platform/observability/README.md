# Observability Platform

The `k3s-01` overlay installs the observability stack with the K3s `HelmChart`
controller into the existing `observability` namespace. `kube-prometheus-stack`
provides Prometheus, Alertmanager, and Grafana. Loki stores Kubernetes logs, and
Grafana Alloy collects pod logs plus Kubernetes events and forwards them to
Loki.

Grafana is exposed through Traefik at `grafana.infra.plexplease.com` with
certificates issued by the `letsencrypt-cloudflare` ClusterIssuer. Grafana has
both Prometheus and Loki datasources so metrics and logs can be queried from the
same UI.

Loki runs in monolithic mode for the k3s-01 homelab footprint. It uses a
`storage-standard` 20Gi PVC and keeps logs for 7 days. Object storage is left for
a later migration if log volume or retention requirements grow.

Alertmanager is configured to send alert webhooks to the Apprise Alertmanager
webhook service in the `notifications` namespace. That service transforms the
Alertmanager payload and posts into Apprise, so Apprise remains the notification
fanout layer.
