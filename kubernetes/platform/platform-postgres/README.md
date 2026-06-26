# Platform PostgreSQL

Platform PostgreSQL is the shared CloudNativePG database cluster for k3s platform services.

The `k3s-01` overlay creates a small `platform-postgres` cluster in the existing `database` namespace, stores data on the `storage-fast` storage class, and configures Barman object-store backups to the TrueNAS S3/MinIO endpoint.

Required OpenBao KV entries:

- `prod/platform/truenas-s3` with `AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY`
- `prod/platform/authentik` with `AUTHENTIK_POSTGRESQL_PASSWORD`

CloudNativePG uses the `platform-postgres-authentik` basic-auth secret to bootstrap the `authentik` database and owner role. Authentik consumes the same password from its identity namespace ExternalSecret.
