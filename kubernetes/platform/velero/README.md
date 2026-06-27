# Velero Backup Platform

The `overlays/k3s-01` slice deploys Velero into the existing `backup` namespace with the k3s `HelmChart` CRD.

Object-store credentials are resolved by External Secrets from the `openbao` `ClusterSecretStore` at `prod/platform/velero`. The OpenBao entry must expose `AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY`; the resulting Kubernetes Secret is `backup/velero-object-store` with a Velero-compatible `cloud` credentials file.

The default `BackupStorageLocation` is configured through Helm values for a TrueNAS S3/MinIO endpoint:

- endpoint: `http://10.10.10.20:30000`
- bucket: `velero`
- prefix: `k3s-01`
- region: `us-east-1`

No `VolumeSnapshotLocation` is configured because the S3 target is object storage, not a volume snapshot provider. Persistent volume contents are handled by Velero node-agent filesystem backups with Kopia.

The overlay also defines `platform-namespace-daily`, a Velero `Schedule` that backs up the `platform` namespace daily at `03:17` and retains backups for seven days.
