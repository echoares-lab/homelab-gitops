# Sample App Workload Template

This workload is a non-critical example for onboarding home applications onto the
k3s GitOps platform. Copy the overlay shape, then replace the image, host name,
labels, probes, and operational decisions with values for the real service.

## Required Decisions

Before adding a production workload, record these decisions in the workload
README or the service runbook:

| Decision | Required answer |
| --- | --- |
| Owner | Name the person or team responsible for lifecycle, upgrades, and incident response. |
| DNS | Choose the public or internal host name and confirm the record is managed by the platform DNS path. |
| SSO mode | State whether access is public, local-network only, protected by SSO, or handled by the app itself. |
| Storage class | Choose `storage-fast`, `storage-standard`, `storage-bulk`, or no persistent storage. |
| Secrets | List every required secret and where it is sourced from; do not commit secret values. |
| Backup | State whether the app needs backups and which data paths or PVCs are in scope. |
| Alerts | Define the minimum alerts for availability, certificate expiry, backup failures, and app-specific health. |
| Restore expectation | Define the expected restore target, such as redeploy only, restore from latest backup, or point-in-time restore. |

## Sample Contract

The `overlays/k3s-01` sample demonstrates the baseline platform contract:

- namespace-scoped workload resources owned by Argo CD
- a public container image with modest CPU and memory requests and limits
- HTTP health probes on the application endpoint
- ClusterIP service fronting the workload
- HTTPS ingress through Traefik
- TLS certificate issued by cert-manager using the `letsencrypt-cloudflare`
  ClusterIssuer

The sample intentionally does not include secrets, persistent storage, backups,
or SSO configuration. Real workloads must make those decisions explicitly before
being wired into a cluster kustomization.
