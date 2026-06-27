# CloudNativePG

CloudNativePG provides the PostgreSQL operator used by platform services in the k3s cluster.

The `k3s-01` overlay installs the upstream `cloudnative-pg` Helm chart through the k3s `HelmChart` controller. The chart is targeted at the existing `database` namespace; cluster wiring and namespace creation are owned by the cluster overlay.
