# Velero Backup and Restore Drill Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Prove Velero backup and PVC restore against TrueNAS S3, populate the daily schedule's last-backup status, and deliver failed/stale backup alerts through Alertmanager, Apprise, and ntfy.

**Architecture:** Use an ephemeral namespace for the destructive restore drill and keep only reusable monitoring configuration and operator instructions in Git. Enable the Velero chart's ServiceMonitor and PrometheusRule so metrics, alert rules, and the Velero release remain versioned together.

**Tech Stack:** Kubernetes/k3s, Velero 1.18.1, Velero Helm chart 12.1.0, Kopia filesystem backup, democratic-csi NFS (`storage-bulk`), Prometheus Operator, Alertmanager, Apprise/ntfy, PyYAML/pytest.

## Global Constraints

- Use `core@10.10.10.50` and `sudo k3s kubectl`; do not use the Ansible SSH user.
- Never expose OpenBao or S3 credential values in command output, logs, commits, or issue comments.
- Do not restore over production resources or add persistent state to `sample-app`.
- Keep drill resources in the disposable `velero-restore-drill` namespace.
- Preserve unrelated files in the original dirty checkout; work only in `/home/dev/repos/homelab-gitops-issue-116`.
- Do not change `config/metadata.yml`: this work adds no role, tag, command, or profile behavior.

---

### Task 1: Execute the backup and restore drill

**Files:**
- Create temporarily on cluster: namespace, Secret, PVC, Deployment, and Service in `velero-restore-drill`
- No repository files

**Interfaces:**
- Consumes: `storage-bulk`, `truenas-s3`, Velero Backup/Restore CRDs
- Produces: completed Backup and Restore resources plus captured object/PVC verification evidence

- [ ] **Step 1: Create the disposable workload**

From the issue worktree, generate a unique non-secret marker and apply the namespace, Secret, PVC, Deployment, and Service through SSH. The pod copies `/config/marker` to `/data/marker` only when the PVC is empty, which makes the restored value distinguishable from a fresh deployment.

```bash
DRILL_ID="velero-drill-$(date -u +%Y%m%dT%H%M%SZ)"
ssh core@10.10.10.50 "sudo k3s kubectl apply -f -" <<EOF
apiVersion: v1
kind: Namespace
metadata:
  name: velero-restore-drill
---
apiVersion: v1
kind: Secret
metadata:
  name: restore-drill-marker
  namespace: velero-restore-drill
type: Opaque
stringData:
  marker: ${DRILL_ID}
---
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: restore-drill-data
  namespace: velero-restore-drill
  annotations:
    backup.velero.io/backup-volumes: data
spec:
  accessModes: [ReadWriteOnce]
  storageClassName: storage-bulk
  resources:
    requests:
      storage: 1Gi
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: restore-drill
  namespace: velero-restore-drill
spec:
  replicas: 1
  selector:
    matchLabels:
      app: restore-drill
  template:
    metadata:
      labels:
        app: restore-drill
      annotations:
        backup.velero.io/backup-volumes: data
    spec:
      containers:
        - name: server
          image: nginxinc/nginx-unprivileged:1.27-alpine
          command: ["/bin/sh", "-c"]
          args:
            - test -f /data/marker || cp /config/marker /data/marker;
              cp /data/marker /usr/share/nginx/html/index.html;
              exec nginx -g 'daemon off;'
          ports:
            - name: http
              containerPort: 8080
          volumeMounts:
            - name: data
              mountPath: /data
            - name: marker
              mountPath: /config
              readOnly: true
      volumes:
        - name: data
          persistentVolumeClaim:
            claimName: restore-drill-data
        - name: marker
          secret:
            secretName: restore-drill-marker
---
apiVersion: v1
kind: Service
metadata:
  name: restore-drill
  namespace: velero-restore-drill
spec:
  selector:
    app: restore-drill
  ports:
    - name: http
      port: 80
      targetPort: http
EOF
```

Expected: all five resources are created.

- [ ] **Step 2: Verify initial readiness and marker data**

```bash
ssh core@10.10.10.50 'sudo k3s kubectl -n velero-restore-drill rollout status deploy/restore-drill --timeout=180s'
ssh core@10.10.10.50 'sudo k3s kubectl -n velero-restore-drill get deploy,svc,pvc,pod'
RESTORED_MARKER="$(ssh core@10.10.10.50 'sudo k3s kubectl -n velero-restore-drill exec deploy/restore-drill -- cat /data/marker')"
test "$RESTORED_MARKER" = "$DRILL_ID"
```

Expected: rollout succeeds, PVC is `Bound`, and `test` exits 0.

- [ ] **Step 3: Create and wait for the Velero backup**

Use a Backup CR so the drill does not depend on a locally installed `velero` CLI.

```bash
BACKUP_NAME="restore-drill-$(date -u +%Y%m%d%H%M%S)"
ssh core@10.10.10.50 "sudo k3s kubectl -n backup create -f -" <<EOF
apiVersion: velero.io/v1
kind: Backup
metadata:
  name: ${BACKUP_NAME}
spec:
  includedNamespaces:
    - velero-restore-drill
  storageLocation: truenas-s3
  snapshotVolumes: false
  defaultVolumesToFsBackup: true
  ttl: 168h0m0s
EOF
for _ in $(seq 1 60); do
  PHASE="$(ssh core@10.10.10.50 "sudo k3s kubectl -n backup get backup ${BACKUP_NAME} -o jsonpath='{.status.phase}'")"
  case "$PHASE" in Completed) break ;; Failed|PartiallyFailed|FailedValidation) exit 1 ;; esac
  sleep 5
done
test "$PHASE" = Completed
ssh core@10.10.10.50 "sudo k3s kubectl -n backup get backup ${BACKUP_NAME} -o wide"
ssh core@10.10.10.50 "sudo k3s kubectl -n backup get podvolumebackups -l velero.io/backup-name=${BACKUP_NAME}"
```

Expected: Backup phase is `Completed` and a PodVolumeBackup is `Completed`.

- [ ] **Step 4: Delete and restore the namespace**

```bash
ssh core@10.10.10.50 'sudo k3s kubectl delete namespace velero-restore-drill --wait=true --timeout=180s'
RESTORE_NAME="${BACKUP_NAME}-restore"
ssh core@10.10.10.50 "sudo k3s kubectl -n backup create -f -" <<EOF
apiVersion: velero.io/v1
kind: Restore
metadata:
  name: ${RESTORE_NAME}
spec:
  backupName: ${BACKUP_NAME}
  includedNamespaces:
    - velero-restore-drill
EOF
for _ in $(seq 1 60); do
  PHASE="$(ssh core@10.10.10.50 "sudo k3s kubectl -n backup get restore ${RESTORE_NAME} -o jsonpath='{.status.phase}'")"
  case "$PHASE" in Completed) break ;; Failed|PartiallyFailed|FailedValidation) exit 1 ;; esac
  sleep 5
done
test "$PHASE" = Completed
```

Expected: Restore phase is `Completed`.

- [ ] **Step 5: Verify every acceptance object and restored PVC data**

```bash
ssh core@10.10.10.50 'sudo k3s kubectl -n velero-restore-drill rollout status deploy/restore-drill --timeout=180s'
ssh core@10.10.10.50 'sudo k3s kubectl -n velero-restore-drill get deploy/restore-drill svc/restore-drill secret/restore-drill-marker pvc/restore-drill-data'
ssh core@10.10.10.50 'sudo k3s kubectl -n velero-restore-drill get deploy/restore-drill -o jsonpath="{.spec.template.spec.volumes[?(@.secret.secretName==\"restore-drill-marker\")].secret.secretName}{\"\\n\"}"'
RESTORED_MARKER="$(ssh core@10.10.10.50 'sudo k3s kubectl -n velero-restore-drill exec deploy/restore-drill -- cat /data/marker')"
test "$RESTORED_MARKER" = "$DRILL_ID"
ssh core@10.10.10.50 'sudo k3s kubectl delete namespace velero-restore-drill --wait=true --timeout=180s'
```

Expected: every `get` succeeds, the Secret reference prints `restore-drill-marker`, marker comparison exits 0, and cleanup completes.

### Task 2: Trigger and verify the daily schedule

**Files:**
- No repository files

**Interfaces:**
- Consumes: `backup/platform-namespace-daily`
- Produces: completed schedule-owned Backup and non-empty `status.lastBackup`

- [ ] **Step 1: Make the existing schedule immediately due**

```bash
OLD_BACKUPS="$(ssh core@10.10.10.50 "sudo k3s kubectl -n backup get backups -l velero.io/schedule-name=platform-namespace-daily -o jsonpath='{range .items[*]}{.metadata.name}{\"\\n\"}{end}'")"
DUE_AT="$(date -u -d '2 days ago' +%Y-%m-%dT%H:%M:%SZ)"
ssh core@10.10.10.50 "sudo k3s kubectl -n backup patch schedule platform-namespace-daily --subresource=status --type=merge -p '{\"status\":{\"lastBackup\":\"${DUE_AT}\"}}'"
```

Expected: only the Schedule status is changed. Its unchanged `03:17` cron is now
overdue, causing the Velero schedule controller to create the backup and replace
the artificial timestamp with the actual controller run time. Do not patch the
Schedule spec or suspend Argo CD.

- [ ] **Step 2: Require completion and populated schedule status**

```bash
SCHEDULE_BACKUP=""
for _ in $(seq 1 30); do
  CURRENT_BACKUPS="$(ssh core@10.10.10.50 "sudo k3s kubectl -n backup get backups -l velero.io/schedule-name=platform-namespace-daily -o jsonpath='{range .items[*]}{.metadata.name}{\"\\n\"}{end}'")"
  SCHEDULE_BACKUP="$(comm -13 <(printf '%s\n' "$OLD_BACKUPS" | sort) <(printf '%s\n' "$CURRENT_BACKUPS" | sort) | head -n1)"
  test -n "$SCHEDULE_BACKUP" && break
  sleep 5
done
test -n "$SCHEDULE_BACKUP"
for _ in $(seq 1 60); do
  PHASE="$(ssh core@10.10.10.50 "sudo k3s kubectl -n backup get backup ${SCHEDULE_BACKUP} -o jsonpath='{.status.phase}'")"
  case "$PHASE" in Completed) break ;; Failed|PartiallyFailed|FailedValidation) exit 1 ;; esac
  sleep 5
done
test "$PHASE" = Completed
LAST_BACKUP="$(ssh core@10.10.10.50 "sudo k3s kubectl -n backup get schedule platform-namespace-daily -o jsonpath='{.status.lastBackup}'")"
test -n "$LAST_BACKUP"
test "$LAST_BACKUP" != "$DUE_AT"
ssh core@10.10.10.50 'sudo k3s kubectl -n backup get schedules.velero.io,backups.velero.io -o wide'
```

Expected: phase is `Completed`, `LAST_BACKUP` contains the controller's new run
time rather than `DUE_AT`, and the schedule table displays a last backup time.

### Task 3: Add Velero monitoring and backup alerts test-first

**Files:**
- Modify: `tests/test_k3s_platform_readiness.py`
- Modify: `kubernetes/platform/velero/overlays/k3s-01/helmchart.yaml`
- Modify: `kubernetes/platform/velero/README.md`
- Modify: `kubernetes/platform/observability/README.md`

**Interfaces:**
- Consumes: Velero metrics Service on port 8085; Prometheus ServiceMonitor selector `release=kube-prometheus-stack`
- Produces: ServiceMonitor and PrometheusRule generated by Helm with alerts `VeleroBackupFailed` and `VeleroBackupStale`

- [ ] **Step 1: Write failing regression tests**

Append helpers/tests that parse the Velero Helm values and assert monitoring behavior:

```python
def velero_helm_values() -> dict:
    documents = load_yaml_documents(
        PLATFORM_ROOT / "velero" / "overlays" / "k3s-01" / "helmchart.yaml"
    )
    helmchart = next(document for document in documents if document.get("kind") == "HelmChart")
    return yaml.safe_load(helmchart["spec"]["valuesContent"])


def test_velero_metrics_are_scraped_by_platform_prometheus() -> None:
    metrics = velero_helm_values()["metrics"]

    assert metrics["serviceMonitor"]["enabled"] is True
    assert metrics["serviceMonitor"]["additionalLabels"]["release"] == "kube-prometheus-stack"


def test_velero_has_failure_and_stale_backup_alerts() -> None:
    prometheus_rule = velero_helm_values()["metrics"]["prometheusRule"]
    alerts = {rule["alert"]: rule for rule in prometheus_rule["spec"]}

    assert prometheus_rule["enabled"] is True
    assert prometheus_rule["additionalLabels"]["release"] == "kube-prometheus-stack"
    assert {"VeleroBackupFailed", "VeleroBackupStale"}.issubset(alerts)
    assert "velero_backup_failure_total" in alerts["VeleroBackupFailed"]["expr"]
    assert "velero_backup_last_successful_timestamp" in alerts["VeleroBackupStale"]["expr"]
    assert alerts["VeleroBackupStale"]["for"] == "1h"
```

- [ ] **Step 2: Run tests and confirm failure**

```bash
pytest -q tests/test_k3s_platform_readiness.py
```

Expected: the two new tests fail because `metrics` is absent.

- [ ] **Step 3: Configure ServiceMonitor and PrometheusRule in Helm values**

Add this block under `valuesContent`, at the same indentation as `credentials`:

```yaml
    metrics:
      enabled: true
      serviceMonitor:
        enabled: true
        additionalLabels:
          release: kube-prometheus-stack
      prometheusRule:
        enabled: true
        additionalLabels:
          release: kube-prometheus-stack
        spec:
          - alert: VeleroBackupFailed
            expr: |-
              increase(velero_backup_failure_total[15m]) > 0
              or increase(velero_backup_partial_failure_total[15m]) > 0
              or increase(velero_backup_validation_failure_total[15m]) > 0
            for: 1m
            labels:
              severity: critical
            annotations:
              summary: Velero backup failed
              description: Velero reported a failed, partially failed, or invalid backup in the last 15 minutes.
              runbook_url: https://github.com/echoares-lab/homelab-gitops/blob/master/docs/RUNBOOK.md#velero-backup-and-restore
          - alert: VeleroBackupStale
            expr: |-
              (time() - velero_backup_last_successful_timestamp{schedule="platform-namespace-daily"}) > 90000
              or absent(velero_backup_last_successful_timestamp{schedule="platform-namespace-daily"})
            for: 1h
            labels:
              severity: critical
            annotations:
              summary: Scheduled Velero backup is stale
              description: platform-namespace-daily has no successful backup newer than 25 hours.
              runbook_url: https://github.com/echoares-lab/homelab-gitops/blob/master/docs/RUNBOOK.md#velero-backup-and-restore
```

- [ ] **Step 4: Run focused tests and manifest validation**

```bash
pytest -q tests/test_k3s_platform_readiness.py
python3 scripts/validate_gitops_manifests.py
```

Expected: focused tests pass and GitOps validation reports no errors.

- [ ] **Step 5: Document monitoring ownership**

Update `kubernetes/platform/velero/README.md` to state that the chart creates a ServiceMonitor and failure/staleness PrometheusRule, and update `kubernetes/platform/observability/README.md` to state that backup alerts are sourced from the Velero release and routed through the common Apprise receiver.

- [ ] **Step 6: Commit monitoring**

```bash
git add tests/test_k3s_platform_readiness.py kubernetes/platform/velero/overlays/k3s-01/helmchart.yaml kubernetes/platform/velero/README.md kubernetes/platform/observability/README.md
git commit -m "feat(velero): alert on failed and stale backups"
```

### Task 4: Synchronize operator and release documentation

**Files:**
- Modify: `docs/RUNBOOK.md`
- Modify: `docs/DESIGN.md`
- Modify: `docs/ROADMAP.md`
- Modify: `docs/VERSIONS_AND_UPDATES.md`

**Interfaces:**
- Consumes: commands and alert names from Tasks 1-3
- Produces: operator procedure and synchronized feature status

- [ ] **Step 1: Add the Velero runbook procedure**

Add `### Velero backup and restore` under the platform readiness section. Include:

- health checks for Velero pods, ExternalSecret, BackupStorageLocation, Schedule, and Backup resources;
- Backup and Restore CR examples using `kubectl apply -f -` and explicit namespace scoping;
- checks for `Completed`, PodVolumeBackup/PodVolumeRestore completion, restored Secret reference, and PVC marker content;
- schedule status inspection with `kubectl -n backup get schedule platform-namespace-daily -o jsonpath='{.status.lastBackup}'`;
- alert inspection in Prometheus/Alertmanager and the synthetic webhook procedure;
- credential rotation that updates only `prod/platform/velero`, annotates `backup/velero-object-store` ExternalSecret with `force-sync=$(date +%s)`, waits for `Ready=True`, restarts Velero, and verifies `truenas-s3` is `Available` without printing the Secret.

- [ ] **Step 2: Synchronize design, roadmap, and version history**

Add a `v3.4.16 - Velero Backup And Restore Validation` entry describing the completed drill, schedule verification, and alerts. Update the roadmap's backup/DR item to explicitly include the Kubernetes Velero restore drill. Update the design's operational excellence section to state that backup readiness requires a completed restore drill and monitored schedule recency.

- [ ] **Step 3: Check documentation diff and commit**

```bash
git diff --check
git diff -- docs/RUNBOOK.md docs/DESIGN.md docs/ROADMAP.md docs/VERSIONS_AND_UPDATES.md
git add docs/RUNBOOK.md docs/DESIGN.md docs/ROADMAP.md docs/VERSIONS_AND_UPDATES.md
git commit -m "docs: record Velero disaster recovery procedure"
```

Expected: no whitespace errors and only #116 documentation changes are present.

### Task 5: Reconcile and verify alert delivery in production

**Execution ordering:** Run Task 6 Steps 1-3 (final repository verification,
scope review, and PR publication) before this task. After production
verification succeeds, finish with Task 6 Step 4. This split is required
because Argo CD cannot reconcile the alert configuration until the PR merges.

**Files:**
- No additional repository files

**Interfaces:**
- Consumes: merged/reconciled Helm values from Task 3
- Produces: loaded rules and end-to-end backup failure notification evidence

- [ ] **Step 1: Verify Argo CD has reconciled the commit**

After the branch is merged, wait until the k3s root Application reports the merged revision as `Synced` and `Healthy`. Do not manually apply the GitOps manifests.

```bash
ssh core@10.10.10.50 'sudo k3s kubectl -n argocd get applications.argoproj.io -o wide'
ssh core@10.10.10.50 'sudo k3s kubectl -n backup get servicemonitor,prometheusrule'
```

Expected: Velero ServiceMonitor and PrometheusRule exist and the application is healthy.

- [ ] **Step 2: Verify Prometheus loads both rules and scrapes Velero**

```bash
ssh core@10.10.10.50 'sudo k3s kubectl -n observability exec prometheus-kube-prometheus-stack-prometheus-0 -c prometheus -- wget -qO- "http://127.0.0.1:9090/api/v1/query?query=up%7Bjob%3D%22velero%22%7D"'
ssh core@10.10.10.50 'sudo k3s kubectl -n observability exec prometheus-kube-prometheus-stack-prometheus-0 -c prometheus -- wget -qO- "http://127.0.0.1:9090/api/v1/rules"' | grep -E 'VeleroBackupFailed|VeleroBackupStale'
```

Expected: Velero target value is 1 and both alert names appear.

- [ ] **Step 3: Create a safe invalid backup fixture**

```bash
FAILED_BACKUP="alert-drill-$(date -u +%Y%m%d%H%M%S)"
ssh core@10.10.10.50 "sudo k3s kubectl -n backup create -f -" <<EOF
apiVersion: velero.io/v1
kind: Backup
metadata:
  name: ${FAILED_BACKUP}
spec:
  includedNamespaces: [velero-alert-drill-does-not-exist]
  storageLocation: intentionally-invalid
  ttl: 1h0m0s
EOF
```

Expected: the fixture enters `FailedValidation` without touching production resources or the valid storage location.

- [ ] **Step 4: Verify firing alert and Apprise delivery**

Wait for one scrape interval plus the one-minute `for` duration, then inspect Alertmanager and webhook logs:

```bash
for _ in $(seq 1 18); do
  if ssh core@10.10.10.50 'sudo k3s kubectl -n observability exec alertmanager-kube-prometheus-stack-alertmanager-0 -c alertmanager -- wget -qO- http://127.0.0.1:9093/api/v2/alerts' | grep -q VeleroBackupFailed; then
    break
  fi
  sleep 10
done
ssh core@10.10.10.50 'sudo k3s kubectl -n observability exec alertmanager-kube-prometheus-stack-alertmanager-0 -c alertmanager -- wget -qO- http://127.0.0.1:9093/api/v2/alerts' | grep VeleroBackupFailed
ssh core@10.10.10.50 'sudo k3s kubectl -n notifications logs deploy/apprise-alertmanager-webhook --since=10m' | grep -E 'VeleroBackupFailed|apprise_status=2[0-9][0-9]'
```

Expected: Alertmanager returns `VeleroBackupFailed`, the webhook log contains that name and a 2xx Apprise status, and the operator confirms receipt in ntfy.

- [ ] **Step 5: Remove the failure fixture**

```bash
ssh core@10.10.10.50 "sudo k3s kubectl -n backup delete backup ${FAILED_BACKUP}"
```

Expected: temporary Backup is deleted.

### Task 6: Final verification and issue evidence

**Files:**
- Verify all changed repository files
- Update: GitHub issue #116 comment/state

**Interfaces:**
- Consumes: all prior task outputs
- Produces: verified branch/PR and auditable issue closure evidence

- [ ] **Step 1: Run repository verification**

```bash
pytest -q tests/test_k3s_platform_readiness.py
python3 scripts/validate_gitops_manifests.py
pytest -q
git diff --check origin/master...HEAD
git status -sb
```

Expected: all tests and validation pass; the worktree is clean. `scripts/matrix_test.py` is intentionally omitted because no manage.py parsing, OpenTofu, dynamic inventory, lifecycle phase, or generator helper changed.

- [ ] **Step 2: Review branch scope**

```bash
git log --oneline origin/master..HEAD
git diff --stat origin/master...HEAD
git diff --name-only origin/master...HEAD
```

Expected: only the design/plan, Velero monitoring, focused test, and synchronized documentation files are listed.

- [ ] **Step 3: Publish through the repository PR workflow**

Push the issue branch, open a PR that closes #116, wait for required checks, and enable auto-merge without weakening branch protection.

- [ ] **Step 4: Post concise evidence to issue #116**

Report names and final phases for the drill Backup/Restore, the verified restored object types and marker match (not the marker value), schedule `lastBackup`, loaded alert names, end-to-end 2xx delivery, validation commands, and PR number. Close #116 only after the PR is merged and production alert verification succeeds.
