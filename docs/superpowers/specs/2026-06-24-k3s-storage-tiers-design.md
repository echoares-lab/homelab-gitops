# K3s Storage Profiling & Tier Design

**Date:** 2026-06-24
**Branch:** codex/inventory-artifact-state-hygiene
**Status:** Approved — pending implementation plan

---

## Goal

Profile ESXi local NVMe storage and TrueNAS network storage (NFS v4 and iSCSI) under realistic Kubernetes I/O patterns. Use benchmark results to assign backends to named StorageClass tiers, then deliver those tiers as ready-to-apply manifests in the cluster's GitOps tree.

---

## Infrastructure Targets

| Host | Role | Address |
|------|------|---------|
| ESXi | Hypervisor / NVMe host | 10.10.10.11 |
| TrueNAS | Network storage | 10.10.10.20 |
| k3s-01 | Target cluster (Fedora CoreOS) | 10.10.10.50 |
| OpenBao | Primary secret store (KV v2) | 10.10.10.30:8201 |
| 1Password Connect | Secret fallback | 10.10.10.30:8200 |

**ESXi datastore:** `NVME_2TB_970_SAMSUNG_EVO_M.2`

**TrueNAS datasets:** `K3S_HDD`, `vmstore`, `WHITEBOX`

---

## Secrets Resolution

The benchmark role resolves credentials at runtime using a two-step probe:

1. **OpenBao (primary):** HTTP health check against `http://10.10.10.30:8201/v1/sys/health`. If healthy and token valid, pull from KV v2 path `kv/storage/truenas`.
2. **1Password Connect (fallback):** If OpenBao is unreachable or returns 401/403, resolve via `community.general.onepassword_info` against `http://10.10.10.30:8200`.

Secrets resolved:
- TrueNAS API key
- iSCSI CHAP username and password (if configured)
- NFS export paths per dataset

Credentials are registered as Ansible vars and never written to disk. The source used (`openbao` or `1password`) is recorded in every result JSON file for auditability.

---

## Benchmark Matrix

### Backends (7 total)

| # | Backend | Protocol | Notes |
|---|---------|----------|-------|
| 1 | ESXi NVMe | local-path | Baseline — no network path |
| 2 | TrueNAS `K3S_HDD` | NFS v4 | |
| 3 | TrueNAS `vmstore` | NFS v4 | |
| 4 | TrueNAS `WHITEBOX` | NFS v4 | |
| 5 | TrueNAS `K3S_HDD` | iSCSI | |
| 6 | TrueNAS `vmstore` | iSCSI | |
| 7 | TrueNAS `WHITEBOX` | iSCSI | |

### fio Job Profiles (5 per backend)

| Job | Block size | Pattern | Queue depth | fsync | Primary metric |
|-----|-----------|---------|------------|-------|---------------|
| rand-read | 4K | 100% read | 32 | no | IOPS |
| rand-write | 4K | 100% write | 32 | no | IOPS |
| seq-read | 1M | 100% read | 8 | no | Throughput MB/s |
| mixed-7030 | 4K | 70% read / 30% write | 32 | no | p99 latency µs |
| db-pattern | 8K | 75% read / 25% write | 1 | yes | p99 latency µs |

Runtime: **60 seconds per job** + 10s ramp-up. Total estimated runtime: **~2 hours**.

---

## Execution Phases

### Phase 1 — Raw Protocol (Benchmark VM)

A single Ubuntu 24.04 VM (`benchmark-storage` profile, 4 CPU / 8 GB RAM / 50 GB disk) is provisioned on ESXi 10.10.10.11 via the existing pipeline.

For each backend:
1. Mount the target (NFS v4 mount or iSCSI initiator connect)
2. Run all 5 fio jobs sequentially
3. Write results to `results/storage-benchmark/<run-id>/<backend>-<protocol>-phase1.json`
4. Update `state.json` to mark backend complete
5. Unmount / disconnect

NVMe baseline runs fio against a local directory on the VM's disk (no mount step).

### Phase 2 — CSI Path (k3s Pods)

For each backend (including NVMe via `local-path`):
1. Apply temporary StorageClass and PVC manifest
2. Deploy `fio` pod with PVC mounted at `/mnt/benchmark`
3. Run all 5 fio jobs via `kubectl exec`
4. Write results to `results/storage-benchmark/<run-id>/<backend>-<protocol>-phase2.json`
5. Update `state.json`
6. Delete pod, PVC, and StorageClass

CSI drivers required:
- **local-path:** k3s built-in (no install needed)
- **NFS v4:** `democratic-csi` with NFS transport (Helm)
- **iSCSI:** `democratic-csi` with iSCSI transport (Helm)

---

## Resilience & Resume

### SSH Disconnect Protection

**Local side:** `--background` flag on `manage.py config` wraps the invocation in a named tmux session:

```
Benchmark running in: tmux attach -t storage-bench-<run-id>
Monitor progress:     watch cat results/storage-benchmark/<run-id>/summary.txt
```

Falls back to `nohup` with output to `results/storage-benchmark/<run-id>/ansible.log` if tmux is unavailable.

**Remote side:** All fio tasks use Ansible `async: 900, poll: 30`. The fio process runs detached from the SSH session; Ansible reconnects every 30 seconds to check status. An SSH disconnect loses at most the current poll interval, not the running job.

k3s pod phase is inherently resilient — pods are managed by k3s and unaffected by control-plane SSH state.

### Resume Logic

Each run is identified by a `run-id` (e.g., `2026-06-24T1430`). A `state.json` file tracks completion per backend:

```json
{
  "run_id": "2026-06-24T1430",
  "completed": ["nvme-local-phase1", "K3S_HDD-nfs4-phase1"],
  "secrets_source": "openbao"
}
```

Resume a specific run:
```bash
python3 manage.py config benchmark-storage --tags storage_benchmark -e benchmark_run_id=2026-06-24T1430
```

Completed backends are skipped. Partially-completed backends re-run from scratch.

---

## Interim Reporting

After each backend completes, `scripts/storage_benchmark_report.py --interim` updates two files:

- `results/storage-benchmark/<run-id>/report-live.md` — full markdown table with `pending` for incomplete backends
- `results/storage-benchmark/<run-id>/summary.txt` — one line per backend, designed for `watch`:

```
[DONE] nvme-local        phase1: r=145k w=92k iops | seq=2100MB/s | p99=210µs
[DONE] K3S_HDD nfs4      phase1: r=12k  w=8k  iops | seq=850MB/s  | p99=1.2ms
[RUN ] vmstore nfs4       phase1: running rand-write (3/5)...
[WAIT] WHITEBOX nfs4      phase1: pending
```

---

## Final Outputs

### 1. Comparison Report

`results/storage-benchmark/<run-id>/report-final.md` — full 7-backend × 5-job table for both phases, plus tier recommendation section.

### 2. Tier Assignments

Based on results, three tiers are assigned:

| Tier | StorageClass name | Target workloads | Selection criteria |
|------|------------------|------------------|--------------------|
| Fast | `storage-fast` | Postgres, Redis, stateful DBs | Highest rand-write IOPS + lowest db-pattern p99 |
| Standard | `storage-standard` | ArgoCD, monitoring, logging | Best IOPS/capacity balance |
| Bulk | `storage-bulk` | Backups, large artifacts | Highest capacity, protocol stability |

### 3. StorageClass Manifests

Written to `kubernetes/clusters/k3s-01/storage/` and wired into the existing kustomization:

```
kubernetes/clusters/k3s-01/storage/
├── kustomization.yaml
├── storageclass-fast.yaml
├── storageclass-standard.yaml
├── storageclass-bulk.yaml
└── democratic-csi/
    ├── nfs-helmrelease.yaml
    └── iscsi-helmrelease.yaml
```

---

## New Files Summary

| Path | Purpose |
|------|---------|
| `ansible/roles/storage_benchmark/` | Full benchmark role |
| `ansible/roles/storage_benchmark/tasks/main.yml` | Orchestrates all phases |
| `ansible/roles/storage_benchmark/tasks/resolve_secrets.yml` | OpenBao → 1Password fallback |
| `ansible/roles/storage_benchmark/tasks/phase1_vm.yml` | VM-side fio execution |
| `ansible/roles/storage_benchmark/tasks/phase2_k3s.yml` | k3s pod fio execution |
| `ansible/roles/storage_benchmark/tasks/report.yml` | Calls report script after each backend |
| `ansible/roles/storage_benchmark/templates/fio-jobs.ini.j2` | Parameterized fio job file |
| `ansible/roles/storage_benchmark/templates/fio-pod.yaml.j2` | k3s fio pod + PVC manifest |
| `ansible/roles/storage_benchmark/defaults/main.yml` | fio runtime, paths, backend list |
| `config/profiles/benchmark-storage.yml` | Benchmark VM profile |
| `scripts/storage_benchmark_report.py` | JSON → markdown + tier recommendations |
| `kubernetes/clusters/k3s-01/storage/` | StorageClass manifests (generated post-benchmark) |

---

## Invocation

```bash
# Deploy benchmark VM
python3 manage.py deploy benchmark-storage 01 --host 10.10.10.11

# Run full benchmark suite in background (tmux)
python3 manage.py config benchmark-storage --tags storage_benchmark --background

# Resume an interrupted run
python3 manage.py config benchmark-storage --tags storage_benchmark -e benchmark_run_id=2026-06-24T1430

# Monitor live
watch cat results/storage-benchmark/2026-06-24T1430/summary.txt

# Tear down benchmark VM when done
python3 manage.py destroy benchmark-storage-01
```
