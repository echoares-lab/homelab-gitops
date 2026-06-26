# Velero Backup and Restore Drill Design

## Scope

Issue #116 will prove that the live k3s cluster can back up Kubernetes API
objects and PVC data to the configured TrueNAS S3/MinIO target, restore those
objects and data, expose schedule recency, and alert through the existing
Alertmanager to Apprise/ntfy notification path.

The drill will not restore over production resources or add persistent state to
the sample workload. It will use disposable resources whose names clearly mark
them as recovery-test data.

## Live Drill

Create a temporary `velero-restore-drill` namespace containing:

- a Secret with a non-sensitive drill value;
- a PVC on `storage-bulk`;
- a Deployment that references the Secret, mounts the PVC, writes a unique
  marker if it is absent, and serves the stored marker;
- a ClusterIP Service selecting the Deployment.

Wait for the pod and PVC to become ready, then verify the marker through the
running pod. Create an on-demand Velero backup scoped to the drill namespace
and require a `Completed` phase in the `truenas-s3` backup storage location.

Delete the drill namespace, restore the backup, and require the restored
namespace, Deployment, Service, Secret reference, bound PVC, ready pod, and
exact marker value. Preserve command output as the issue's operational
evidence, then remove the restored namespace. The backup may remain until its
normal TTL expires so operators can inspect it.

## Schedule Verification

Create a backup from the `platform-namespace-daily` Schedule rather than
waiting for the next 03:17 UTC run. Require the resulting backup to complete
and verify that the Schedule's `status.lastBackup` field is populated. This
tests the schedule template and updates the same status field used by recency
monitoring.

## Alerting

Configure the Velero Helm release to generate a GitOps-managed
`PrometheusRule` in the backup namespace. The platform Prometheus instance
will discover the rule through its release label. The rule will alert on:

- a Velero backup reporting a failed or partially failed phase; and
- absence of a successful backup created by `platform-namespace-daily` within
  a threshold safely longer than its daily interval.

Rules will use Velero's exported Prometheus metrics and labels as observed on
the deployed chart. Alerts will carry actionable summaries and runbook links.
After Argo CD reconciliation, verify the rules are loaded and exercise the
failure rule without corrupting the successful backup path. Confirm the firing
alert reaches the existing Alertmanager to Apprise/ntfy receiver; clean up any
temporary failure fixture afterward.

## Repository Changes

Keep reusable desired state in Git and operational drill fixtures ephemeral.
Expected repository changes are limited to:

- the observability `PrometheusRule` and overlay wiring;
- focused manifest regression tests;
- Velero and observability component documentation;
- `RUNBOOK.md` backup, restore, alert test, and OpenBao credential rotation
  procedures;
- synchronized `ROADMAP.md`, `VERSIONS_AND_UPDATES.md`, and `DESIGN.md` status
  or architecture notes required by repository policy.

No new role, tag, command, or profile behavior is planned, so
`config/metadata.yml` does not require a change.

## Validation and Completion

Render and validate every changed Kustomize overlay, run the focused tests and
the repository's full applicable test suite, and run
`scripts/validate_gitops_manifests.py`. The matrix test is not required because
the change does not touch orchestrator parsing, OpenTofu, dynamic inventory, a
lifecycle phase, or a generator helper.

Completion requires captured live evidence for the successful on-demand
backup, successful schedule-created backup and populated `lastBackup`, complete
restore of all required resource types and PVC marker data, and end-to-end
delivery of the backup alert. Post a concise evidence summary to issue #116.
