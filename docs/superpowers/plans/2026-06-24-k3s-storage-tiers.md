# K3s Storage Profiling & Tier Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build an automated two-phase storage benchmark suite that profiles ESXi NVMe and TrueNAS (NFS v4 + iSCSI) under Kubernetes-realistic I/O patterns, then deliver named StorageClasses for k3s based on the results.

**Architecture:** An Ansible role (`storage_benchmark`) runs against a dedicated benchmark VM. Phase 1 mounts each backend and runs fio directly; Phase 2 delegates kubectl to k3s-01 to run fio pods through the CSI path. A Python report script aggregates per-backend JSON results into a markdown comparison table and tier recommendations. democratic-csi provides NFS v4 and iSCSI CSI drivers via k3s HelmChart CRDs; k3s's built-in `local-path` provisioner covers NVMe.

**Tech Stack:** Ansible, fio, Python 3.10+, pytest, kubectl, democratic-csi (k3s HelmChart CRD), OpenBao KV v2, 1Password Connect, typer (manage.py)

---

## File Map

| File | Action | Responsibility |
|------|--------|---------------|
| `config/profiles/benchmark-storage.yml` | Create | Benchmark VM profile (4 CPU / 8 GB / 50 GB on NVMe datastore) |
| `ansible/roles/storage_benchmark/defaults/main.yml` | Create | All tunables: run_id, fio settings, backend list, paths |
| `ansible/roles/storage_benchmark/tasks/main.yml` | Create | Role orchestrator: init → secrets → phase1 → phase2 → final report |
| `ansible/roles/storage_benchmark/tasks/resolve_secrets.yml` | Create | OpenBao probe → 1Password Connect fallback |
| `ansible/roles/storage_benchmark/tasks/phase1_vm.yml` | Create | NVMe baseline + NFS v4 + iSCSI raw protocol benchmarks on VM |
| `ansible/roles/storage_benchmark/tasks/phase2_k3s.yml` | Create | CSI path benchmarks via fio pods in k3s (delegated to k3s-01) |
| `ansible/roles/storage_benchmark/tasks/report.yml` | Create | Call report script after each backend (interim) and at end (final) |
| `ansible/roles/storage_benchmark/templates/fio-jobs.ini.j2` | Create | Parameterised fio job file (5 profiles, configurable runtime) |
| `ansible/roles/storage_benchmark/templates/fio-pod.yaml.j2` | Create | k3s fio pod + PVC manifest for Phase 2 |
| `ansible/roles/storage_benchmark/templates/storageclass-temp.yaml.j2` | Create | Temporary StorageClass for Phase 2 benchmarks (cleaned up after) |
| `scripts/storage_benchmark_report.py` | Create | JSON → markdown table + tier recommendations + summary.txt |
| `tests/unit/test_storage_benchmark_report.py` | Create | Unit tests for all report script pure functions |
| `ansible/site.yml` | Modify | Add `tag_benchmark` play routing to `storage_benchmark` role |
| `config/metadata.yml` | Modify | Add `storage_benchmark` role + `storage_benchmark` tag descriptions |
| `src/homelab_gitops/cli/core_commands/config.py` | Modify | Add `--background` flag (tmux wrapper, nohup fallback) |
| `kubernetes/platform/democratic-csi/overlays/k3s-01/nfs-helmchart.yaml` | Create | democratic-csi NFS HelmChart |
| `kubernetes/platform/democratic-csi/overlays/k3s-01/iscsi-helmchart.yaml` | Create | democratic-csi iSCSI HelmChart |
| `kubernetes/platform/democratic-csi/overlays/k3s-01/kustomization.yaml` | Create | Kustomization for democratic-csi overlay |
| `kubernetes/platform/storage/overlays/k3s-01/storageclass-fast.yaml` | Create | Skeleton StorageClass for fast tier (fill from benchmark results) |
| `kubernetes/platform/storage/overlays/k3s-01/storageclass-standard.yaml` | Create | Skeleton StorageClass for standard tier |
| `kubernetes/platform/storage/overlays/k3s-01/storageclass-bulk.yaml` | Create | Skeleton StorageClass for bulk tier |
| `kubernetes/platform/storage/overlays/k3s-01/kustomization.yaml` | Create | Kustomization for storage overlay |
| `kubernetes/clusters/k3s-01/kustomization.yaml` | Modify | Add democratic-csi and storage platform references |

---

## Task 1: Benchmark VM Profile

**Files:**
- Create: `config/profiles/benchmark-storage.yml`

- [ ] **Step 1: Write the profile**

```yaml
# config/profiles/benchmark-storage.yml
---
vcenter:
  datacenter: "HOMELAB"
  cluster: "Primary"
  host: "10.10.10.11"
  datastore: "NVME_2TB_970_SAMSUNG_EVO_M.2"
  network: "VM Network"

content_library:
  name: "GOLDEN"
  template: "ubuntu-24.04-lts-golden"

vm_specs:
  cpu: 4
  memory: 8192
  disk: 50

deployment:
  tags:
    - "ubuntu"
    - "ubuntu-2404"
    - "benchmark"
  vm_name_prefix: "bench-storage"
  vm_name_domain: "mgmt.plexplease.com"

network:
  ipv4_address: "10.10.10.101"
  ipv4_netmask: 24
  ipv4_gateway: "10.10.10.1"
  dns_servers:
    - "10.10.10.2"
    - "1.1.1.1"
```

- [ ] **Step 2: Validate profile syntax**

```bash
python3 manage.py lint benchmark-storage
```

Expected: No schema errors.

- [ ] **Step 3: Commit**

```bash
git add config/profiles/benchmark-storage.yml
git commit -m "feat(storage): add benchmark-storage VM profile"
```

---

## Task 2: Ansible Role Skeleton + Defaults

**Files:**
- Create: `ansible/roles/storage_benchmark/defaults/main.yml`
- Create: `ansible/roles/storage_benchmark/tasks/main.yml`

- [ ] **Step 1: Create role directory structure**

```bash
mkdir -p ansible/roles/storage_benchmark/{defaults,tasks,templates}
```

- [ ] **Step 2: Write defaults**

```yaml
# ansible/roles/storage_benchmark/defaults/main.yml
---
benchmark_run_id: "{{ lookup('pipe', 'date +%Y-%m-%dT%H%M') }}"
benchmark_results_base: "results/storage-benchmark"
benchmark_run_dir: "{{ benchmark_results_base }}/{{ benchmark_run_id }}"

fio_runtime_sec: 60
fio_ramp_sec: 10
fio_file_size: "4g"

truenas_host: "10.10.10.20"
k3s_node_ip: "10.10.10.50"
k3s_kubeconfig: "/etc/rancher/k3s/k3s.yaml"

truenas_datasets:
  - name: "K3S_HDD"
    nfs_path: "/mnt/K3S_HDD"
  - name: "vmstore"
    nfs_path: "/mnt/vmstore"
  - name: "WHITEBOX"
    nfs_path: "/mnt/WHITEBOX"

nvme_fio_dir: "/tmp/fio-nvme-bench"
nfs_mount_base: "/mnt/bench-nfs"
iscsi_mount_base: "/mnt/bench-iscsi"

completed_backends: []
```

- [ ] **Step 3: Write role orchestrator**

```yaml
# ansible/roles/storage_benchmark/tasks/main.yml
---
- name: Ensure local results directory exists
  ansible.builtin.file:
    path: "{{ benchmark_run_dir }}"
    state: directory
    mode: "0755"
  delegate_to: localhost

- name: Load completed backends from state file (resume support)
  ansible.builtin.set_fact:
    completed_backends: "{{ (lookup('file', benchmark_run_dir + '/state.json') | from_json).completed | default([]) }}"
  failed_when: false
  delegate_to: localhost

- name: Resolve storage credentials
  ansible.builtin.include_tasks: resolve_secrets.yml

- name: Install benchmark prerequisites on VM
  ansible.builtin.apt:
    name:
      - fio
      - nfs-common
      - open-iscsi
      - jq
    state: present
    update_cache: true
  become: true

- name: Run Phase 1 — raw protocol benchmarks on VM
  ansible.builtin.include_tasks: phase1_vm.yml

- name: Run Phase 2 — CSI path benchmarks via k3s pods
  ansible.builtin.include_tasks: phase2_k3s.yml

- name: Generate final report
  ansible.builtin.include_tasks: report.yml
  vars:
    report_mode: "final"
```

- [ ] **Step 4: Commit**

```bash
git add ansible/roles/storage_benchmark/
git commit -m "feat(storage): scaffold storage_benchmark role with defaults and orchestrator"
```

---

## Task 3: Secrets Resolution Task

**Files:**
- Create: `ansible/roles/storage_benchmark/tasks/resolve_secrets.yml`

- [ ] **Step 1: Write resolve_secrets.yml**

```yaml
# ansible/roles/storage_benchmark/tasks/resolve_secrets.yml
---
- name: Probe OpenBao health
  ansible.builtin.uri:
    url: "http://10.10.10.30:8201/v1/sys/health"
    method: GET
    status_code: [200, 429, 472, 473, 501, 503]
    timeout: 5
  register: openbao_health
  failed_when: false
  delegate_to: localhost

- name: Attempt OpenBao secret fetch
  ansible.builtin.uri:
    url: "http://10.10.10.30:8201/v1/kv/data/storage/truenas"
    method: GET
    headers:
      X-Vault-Token: "{{ lookup('env', 'VAULT_TOKEN') }}"
    status_code: [200, 403, 404]
    timeout: 5
  register: openbao_secret
  failed_when: false
  delegate_to: localhost
  when: openbao_health.status is defined and openbao_health.status in [200, 429]

- name: Set credentials from OpenBao
  ansible.builtin.set_fact:
    truenas_api_key: "{{ openbao_secret.json.data.data.api_key }}"
    iscsi_chap_user: "{{ openbao_secret.json.data.data.iscsi_chap_user | default('') }}"
    iscsi_chap_secret: "{{ openbao_secret.json.data.data.iscsi_chap_secret | default('') }}"
    secrets_source: "openbao"
  no_log: true
  when:
    - openbao_secret is defined
    - openbao_secret.status is defined
    - openbao_secret.status == 200

- name: Fetch credentials from 1Password Connect (fallback)
  community.general.onepassword_info:
    item_name: "truenas-api"
    vault: "homelab-gitops"
    connect_host: "http://10.10.10.30:8200"
    connect_token: "{{ lookup('env', 'OP_CONNECT_TOKEN') }}"
  register: op_secret
  delegate_to: localhost
  no_log: true
  when: truenas_api_key is not defined

- name: Set credentials from 1Password Connect
  ansible.builtin.set_fact:
    truenas_api_key: "{{ op_secret.onepassword['truenas-api']['api_key'] }}"
    iscsi_chap_user: "{{ op_secret.onepassword['truenas-api']['iscsi_chap_user'] | default('') }}"
    iscsi_chap_secret: "{{ op_secret.onepassword['truenas-api']['iscsi_chap_secret'] | default('') }}"
    secrets_source: "1password"
  no_log: true
  when: truenas_api_key is not defined

- name: Fail if no credentials resolved
  ansible.builtin.fail:
    msg: "Could not resolve TrueNAS credentials from OpenBao or 1Password Connect. Check VAULT_TOKEN or OP_CONNECT_TOKEN."
  when: truenas_api_key is not defined

- name: Persist secrets source to state
  ansible.builtin.copy:
    dest: "{{ benchmark_run_dir }}/state.json"
    content: "{{ {'run_id': benchmark_run_id, 'secrets_source': secrets_source, 'completed': completed_backends} | to_json(indent=2) }}"
    mode: "0600"
  delegate_to: localhost
```

- [ ] **Step 2: Commit**

```bash
git add ansible/roles/storage_benchmark/tasks/resolve_secrets.yml
git commit -m "feat(storage): add OpenBao → 1Password fallback secrets resolution"
```

---

## Task 4: fio Job Template

**Files:**
- Create: `ansible/roles/storage_benchmark/templates/fio-jobs.ini.j2`

- [ ] **Step 1: Write fio template**

```ini
; ansible/roles/storage_benchmark/templates/fio-jobs.ini.j2
[global]
ioengine=libaio
direct=1
runtime={{ fio_runtime_sec }}
ramp_time={{ fio_ramp_sec }}
time_based=1
group_reporting=1
output-format=json
size={{ fio_file_size }}
filename={{ fio_target_path }}/fio-testfile

[rand-read-4k]
rw=randread
bs=4k
iodepth=32
name=rand-read-4k

[rand-write-4k]
rw=randwrite
bs=4k
iodepth=32
name=rand-write-4k

[seq-read-1m]
rw=read
bs=1m
iodepth=8
name=seq-read-1m

[mixed-7030-4k]
rw=randrw
rwmixread=70
bs=4k
iodepth=32
name=mixed-7030-4k

[db-pattern-8k]
rw=randrw
rwmixread=75
bs=8k
iodepth=1
fsync=1
name=db-pattern-8k
```

- [ ] **Step 2: Commit**

```bash
git add ansible/roles/storage_benchmark/templates/fio-jobs.ini.j2
git commit -m "feat(storage): add parameterised fio job template (5 profiles)"
```

---

## Task 5: Phase 1 VM Benchmarks — NVMe + NFS

**Files:**
- Create: `ansible/roles/storage_benchmark/tasks/phase1_vm.yml`

- [ ] **Step 1: Write phase1_vm.yml**

```yaml
# ansible/roles/storage_benchmark/tasks/phase1_vm.yml
---
# ── NVMe baseline ────────────────────────────────────────────────────────────

- name: "Phase1 NVMe | Skip if already complete"
  ansible.builtin.meta: end_play
  when: "'nvme-local-phase1' in completed_backends"

- name: "Phase1 NVMe | Create fio directory"
  ansible.builtin.file:
    path: "{{ nvme_fio_dir }}"
    state: directory
    mode: "0755"
  become: true
  when: "'nvme-local-phase1' not in completed_backends"

- name: "Phase1 NVMe | Write fio job file"
  ansible.builtin.template:
    src: fio-jobs.ini.j2
    dest: /tmp/fio-nvme.ini
    mode: "0644"
  vars:
    fio_target_path: "{{ nvme_fio_dir }}"
  when: "'nvme-local-phase1' not in completed_backends"

- name: "Phase1 NVMe | Run fio (async)"
  ansible.builtin.command: fio /tmp/fio-nvme.ini --output-format=json
  register: fio_nvme
  become: true
  async: 900
  poll: 30
  when: "'nvme-local-phase1' not in completed_backends"

- name: "Phase1 NVMe | Save result"
  ansible.builtin.copy:
    dest: "{{ benchmark_run_dir }}/nvme-local-phase1.json"
    content: "{{ {'backend': 'nvme-local', 'protocol': 'local', 'phase': 'phase1', 'run_id': benchmark_run_id, 'secrets_source': secrets_source, 'fio': fio_nvme.stdout | from_json} | to_json(indent=2) }}"
    mode: "0644"
  delegate_to: localhost
  when: "'nvme-local-phase1' not in completed_backends"

- name: "Phase1 NVMe | Update state"
  ansible.builtin.copy:
    dest: "{{ benchmark_run_dir }}/state.json"
    content: "{{ (lookup('file', benchmark_run_dir + '/state.json') | from_json) | combine({'completed': completed_backends + ['nvme-local-phase1']}) | to_json(indent=2) }}"
    mode: "0600"
  delegate_to: localhost
  when: "'nvme-local-phase1' not in completed_backends"

- name: "Phase1 NVMe | Set completed"
  ansible.builtin.set_fact:
    completed_backends: "{{ completed_backends + ['nvme-local-phase1'] }}"
  when: "'nvme-local-phase1' not in completed_backends"

- name: "Phase1 NVMe | Interim report"
  ansible.builtin.include_tasks: report.yml
  vars:
    report_mode: "interim"

- name: "Phase1 NVMe | Cleanup test file"
  ansible.builtin.file:
    path: "{{ nvme_fio_dir }}/fio-testfile"
    state: absent
  become: true
  failed_when: false

# ── NFS v4 backends ──────────────────────────────────────────────────────────

- name: "Phase1 NFS | Process each dataset"
  ansible.builtin.include_tasks: phase1_nfs_backend.yml
  loop: "{{ truenas_datasets }}"
  loop_control:
    loop_var: dataset
```

- [ ] **Step 2: Write phase1_nfs_backend.yml**

```yaml
# ansible/roles/storage_benchmark/tasks/phase1_nfs_backend.yml
---
- name: "Phase1 NFS {{ dataset.name }} | Skip if complete"
  ansible.builtin.set_fact:
    _skip_nfs: "{{ dataset.name + '-nfs4-phase1' in completed_backends }}"

- name: "Phase1 NFS {{ dataset.name }} | Create mount point"
  ansible.builtin.file:
    path: "{{ nfs_mount_base }}/{{ dataset.name }}"
    state: directory
    mode: "0755"
  become: true
  when: not _skip_nfs

- name: "Phase1 NFS {{ dataset.name }} | Mount NFS v4 share"
  ansible.posix.mount:
    path: "{{ nfs_mount_base }}/{{ dataset.name }}"
    src: "{{ truenas_host }}:{{ dataset.nfs_path }}"
    fstype: nfs4
    opts: "rw,hard,intr,timeo=600,retrans=2,_netdev"
    state: mounted
  become: true
  when: not _skip_nfs

- name: "Phase1 NFS {{ dataset.name }} | Write fio job file"
  ansible.builtin.template:
    src: fio-jobs.ini.j2
    dest: "/tmp/fio-nfs-{{ dataset.name }}.ini"
    mode: "0644"
  vars:
    fio_target_path: "{{ nfs_mount_base }}/{{ dataset.name }}"
  when: not _skip_nfs

- name: "Phase1 NFS {{ dataset.name }} | Run fio (async)"
  ansible.builtin.command: "fio /tmp/fio-nfs-{{ dataset.name }}.ini --output-format=json"
  register: fio_nfs_result
  become: true
  async: 900
  poll: 30
  when: not _skip_nfs

- name: "Phase1 NFS {{ dataset.name }} | Save result"
  ansible.builtin.copy:
    dest: "{{ benchmark_run_dir }}/{{ dataset.name }}-nfs4-phase1.json"
    content: "{{ {'backend': dataset.name, 'protocol': 'nfs4', 'phase': 'phase1', 'run_id': benchmark_run_id, 'secrets_source': secrets_source, 'fio': fio_nfs_result.stdout | from_json} | to_json(indent=2) }}"
    mode: "0644"
  delegate_to: localhost
  when: not _skip_nfs

- name: "Phase1 NFS {{ dataset.name }} | Update state"
  ansible.builtin.copy:
    dest: "{{ benchmark_run_dir }}/state.json"
    content: "{{ (lookup('file', benchmark_run_dir + '/state.json') | from_json) | combine({'completed': completed_backends + [dataset.name + '-nfs4-phase1']}) | to_json(indent=2) }}"
    mode: "0600"
  delegate_to: localhost
  when: not _skip_nfs

- name: "Phase1 NFS {{ dataset.name }} | Set completed"
  ansible.builtin.set_fact:
    completed_backends: "{{ completed_backends + [dataset.name + '-nfs4-phase1'] }}"
  when: not _skip_nfs

- name: "Phase1 NFS {{ dataset.name }} | Interim report"
  ansible.builtin.include_tasks: report.yml
  vars:
    report_mode: "interim"
  when: not _skip_nfs

- name: "Phase1 NFS {{ dataset.name }} | Unmount"
  ansible.posix.mount:
    path: "{{ nfs_mount_base }}/{{ dataset.name }}"
    state: unmounted
  become: true
  when: not _skip_nfs
```

- [ ] **Step 3: Commit**

```bash
git add ansible/roles/storage_benchmark/tasks/phase1_vm.yml \
        ansible/roles/storage_benchmark/tasks/phase1_nfs_backend.yml
git commit -m "feat(storage): phase1 NVMe baseline and NFS v4 benchmark tasks"
```

---

## Task 6: Phase 1 — iSCSI Backends

**Files:**
- Create: `ansible/roles/storage_benchmark/tasks/phase1_iscsi_backend.yml`
- Modify: `ansible/roles/storage_benchmark/tasks/phase1_vm.yml` (add iSCSI loop)

- [ ] **Step 1: Write phase1_iscsi_backend.yml**

```yaml
# ansible/roles/storage_benchmark/tasks/phase1_iscsi_backend.yml
---
- name: "Phase1 iSCSI {{ dataset.name }} | Skip if complete"
  ansible.builtin.set_fact:
    _skip_iscsi: "{{ dataset.name + '-iscsi-phase1' in completed_backends }}"

- name: "Phase1 iSCSI {{ dataset.name }} | Discover targets"
  ansible.builtin.command: "iscsiadm -m discovery -t sendtargets -p {{ truenas_host }}"
  register: iscsi_discovery
  become: true
  changed_when: false
  when: not _skip_iscsi

- name: "Phase1 iSCSI {{ dataset.name }} | Extract target IQN for dataset"
  ansible.builtin.set_fact:
    iscsi_target_iqn: "{{ iscsi_discovery.stdout_lines | select('search', dataset.name | lower) | first | regex_replace('^.*\\s+', '') }}"
  when: not _skip_iscsi and iscsi_discovery is defined

- name: "Phase1 iSCSI {{ dataset.name }} | Fail if IQN not found"
  ansible.builtin.fail:
    msg: "Could not find iSCSI target IQN for dataset {{ dataset.name }} in discovery output:\n{{ iscsi_discovery.stdout }}"
  when: not _skip_iscsi and (iscsi_target_iqn is not defined or iscsi_target_iqn == '')

- name: "Phase1 iSCSI {{ dataset.name }} | Login to target"
  ansible.builtin.command: "iscsiadm -m node -T {{ iscsi_target_iqn }} -p {{ truenas_host }} --login"
  become: true
  changed_when: true
  when: not _skip_iscsi

- name: "Phase1 iSCSI {{ dataset.name }} | Wait for block device"
  ansible.builtin.shell: "ls /dev/disk/by-path/*{{ iscsi_target_iqn | regex_replace(':', '.') }}* 2>/dev/null | head -1"
  register: iscsi_dev_path
  retries: 10
  delay: 3
  until: iscsi_dev_path.stdout != ''
  become: true
  changed_when: false
  when: not _skip_iscsi

- name: "Phase1 iSCSI {{ dataset.name }} | Write fio job file (block device)"
  ansible.builtin.template:
    src: fio-jobs.ini.j2
    dest: "/tmp/fio-iscsi-{{ dataset.name }}.ini"
    mode: "0644"
  vars:
    fio_target_path: "{{ iscsi_dev_path.stdout | trim }}"
  when: not _skip_iscsi

- name: "Phase1 iSCSI {{ dataset.name }} | Run fio on block device (async)"
  ansible.builtin.command: "fio /tmp/fio-iscsi-{{ dataset.name }}.ini --output-format=json"
  register: fio_iscsi_result
  become: true
  async: 900
  poll: 30
  when: not _skip_iscsi

- name: "Phase1 iSCSI {{ dataset.name }} | Save result"
  ansible.builtin.copy:
    dest: "{{ benchmark_run_dir }}/{{ dataset.name }}-iscsi-phase1.json"
    content: "{{ {'backend': dataset.name, 'protocol': 'iscsi', 'phase': 'phase1', 'run_id': benchmark_run_id, 'secrets_source': secrets_source, 'fio': fio_iscsi_result.stdout | from_json} | to_json(indent=2) }}"
    mode: "0644"
  delegate_to: localhost
  when: not _skip_iscsi

- name: "Phase1 iSCSI {{ dataset.name }} | Update state"
  ansible.builtin.copy:
    dest: "{{ benchmark_run_dir }}/state.json"
    content: "{{ (lookup('file', benchmark_run_dir + '/state.json') | from_json) | combine({'completed': completed_backends + [dataset.name + '-iscsi-phase1']}) | to_json(indent=2) }}"
    mode: "0600"
  delegate_to: localhost
  when: not _skip_iscsi

- name: "Phase1 iSCSI {{ dataset.name }} | Set completed"
  ansible.builtin.set_fact:
    completed_backends: "{{ completed_backends + [dataset.name + '-iscsi-phase1'] }}"
  when: not _skip_iscsi

- name: "Phase1 iSCSI {{ dataset.name }} | Interim report"
  ansible.builtin.include_tasks: report.yml
  vars:
    report_mode: "interim"
  when: not _skip_iscsi

- name: "Phase1 iSCSI {{ dataset.name }} | Logout from target"
  ansible.builtin.command: "iscsiadm -m node -T {{ iscsi_target_iqn }} -p {{ truenas_host }} --logout"
  become: true
  changed_when: true
  when: not _skip_iscsi
  failed_when: false
```

- [ ] **Step 2: Add iSCSI loop to phase1_vm.yml**

Append to the end of `ansible/roles/storage_benchmark/tasks/phase1_vm.yml`:

```yaml
# ── iSCSI backends ───────────────────────────────────────────────────────────

- name: "Phase1 iSCSI | Ensure iscsid is running"
  ansible.builtin.systemd:
    name: iscsid
    state: started
    enabled: true
  become: true

- name: "Phase1 iSCSI | Process each dataset"
  ansible.builtin.include_tasks: phase1_iscsi_backend.yml
  loop: "{{ truenas_datasets }}"
  loop_control:
    loop_var: dataset
```

- [ ] **Step 3: Commit**

```bash
git add ansible/roles/storage_benchmark/tasks/phase1_iscsi_backend.yml \
        ansible/roles/storage_benchmark/tasks/phase1_vm.yml
git commit -m "feat(storage): phase1 iSCSI benchmark tasks with async fio and resume"
```

---

## Task 7: Phase 2 Templates + k3s Pod Benchmarks

**Files:**
- Create: `ansible/roles/storage_benchmark/templates/fio-pod.yaml.j2`
- Create: `ansible/roles/storage_benchmark/templates/storageclass-temp.yaml.j2`
- Create: `ansible/roles/storage_benchmark/tasks/phase2_k3s.yml`
- Create: `ansible/roles/storage_benchmark/tasks/phase2_backend.yml`

- [ ] **Step 1: Write fio pod template**

```yaml
# ansible/roles/storage_benchmark/templates/fio-pod.yaml.j2
---
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: bench-pvc-{{ backend_key }}
  namespace: default
spec:
  storageClassName: bench-sc-{{ backend_key }}
  accessModes:
    - ReadWriteOnce
  resources:
    requests:
      storage: 10Gi
---
apiVersion: v1
kind: Pod
metadata:
  name: bench-fio-{{ backend_key }}
  namespace: default
spec:
  restartPolicy: Never
  containers:
    - name: fio
      image: nixery.dev/fio
      command:
        - fio
        - /jobs/fio-jobs.ini
        - --output-format=json
        - --output=/results/fio-output.json
      volumeMounts:
        - name: bench-volume
          mountPath: /mnt/bench
        - name: jobs
          mountPath: /jobs
        - name: results
          mountPath: /results
      securityContext:
        runAsUser: 0
  volumes:
    - name: bench-volume
      persistentVolumeClaim:
        claimName: bench-pvc-{{ backend_key }}
    - name: jobs
      configMap:
        name: bench-fio-jobs-{{ backend_key }}
    - name: results
      emptyDir: {}
```

- [ ] **Step 2: Write temporary StorageClass template**

```yaml
# ansible/roles/storage_benchmark/templates/storageclass-temp.yaml.j2
---
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: bench-sc-{{ backend_key }}
provisioner: "{{ sc_provisioner }}"
parameters:
{% for key, value in sc_parameters.items() %}
  {{ key }}: "{{ value }}"
{% endfor %}
reclaimPolicy: Delete
volumeBindingMode: Immediate
```

- [ ] **Step 3: Write phase2_k3s.yml**

```yaml
# ansible/roles/storage_benchmark/tasks/phase2_k3s.yml
---
- name: "Phase2 | Process NVMe local-path"
  ansible.builtin.include_tasks: phase2_backend.yml
  vars:
    backend_key: "nvme-local"
    backend_name: "nvme-local"
    protocol: "local"
    sc_provisioner: "rancher.io/local-path"
    sc_parameters: {}
  when: "'nvme-local-phase2' not in completed_backends"

- name: "Phase2 | Process NFS backends"
  ansible.builtin.include_tasks: phase2_backend.yml
  loop: "{{ truenas_datasets }}"
  loop_control:
    loop_var: dataset
  vars:
    backend_key: "{{ dataset.name | lower }}-nfs4"
    backend_name: "{{ dataset.name }}"
    protocol: "nfs4"
    sc_provisioner: "org.democratic-csi.nfs"
    sc_parameters:
      fsType: "nfs"
  when: "dataset.name + '-nfs4-phase2' not in completed_backends"

- name: "Phase2 | Process iSCSI backends"
  ansible.builtin.include_tasks: phase2_backend.yml
  loop: "{{ truenas_datasets }}"
  loop_control:
    loop_var: dataset
  vars:
    backend_key: "{{ dataset.name | lower }}-iscsi"
    backend_name: "{{ dataset.name }}"
    protocol: "iscsi"
    sc_provisioner: "org.democratic-csi.iscsi"
    sc_parameters:
      fsType: "ext4"
  when: "dataset.name + '-iscsi-phase2' not in completed_backends"
```

- [ ] **Step 4: Write phase2_backend.yml**

```yaml
# ansible/roles/storage_benchmark/tasks/phase2_backend.yml
---
- name: "Phase2 {{ backend_key }} | Template StorageClass"
  ansible.builtin.template:
    src: storageclass-temp.yaml.j2
    dest: "/tmp/bench-sc-{{ backend_key }}.yaml"
    mode: "0644"
  delegate_to: "{{ k3s_node_ip }}"

- name: "Phase2 {{ backend_key }} | Apply StorageClass and PVC"
  ansible.builtin.command: "kubectl apply -f /tmp/bench-sc-{{ backend_key }}.yaml --kubeconfig {{ k3s_kubeconfig }}"
  delegate_to: "{{ k3s_node_ip }}"
  become: true

- name: "Phase2 {{ backend_key }} | Write fio jobs ConfigMap"
  ansible.builtin.template:
    src: fio-jobs.ini.j2
    dest: "/tmp/fio-jobs-{{ backend_key }}.ini"
    mode: "0644"
  vars:
    fio_target_path: "/mnt/bench"
  delegate_to: "{{ k3s_node_ip }}"

- name: "Phase2 {{ backend_key }} | Create fio jobs ConfigMap"
  ansible.builtin.shell: >
    kubectl create configmap bench-fio-jobs-{{ backend_key }}
    --from-file=fio-jobs.ini=/tmp/fio-jobs-{{ backend_key }}.ini
    --kubeconfig {{ k3s_kubeconfig }}
    --dry-run=client -o yaml | kubectl apply -f - --kubeconfig {{ k3s_kubeconfig }}
  delegate_to: "{{ k3s_node_ip }}"
  become: true

- name: "Phase2 {{ backend_key }} | Apply fio Pod and PVC"
  ansible.builtin.template:
    src: fio-pod.yaml.j2
    dest: "/tmp/bench-pod-{{ backend_key }}.yaml"
    mode: "0644"
  delegate_to: "{{ k3s_node_ip }}"

- name: "Phase2 {{ backend_key }} | Create Pod and PVC"
  ansible.builtin.command: "kubectl apply -f /tmp/bench-pod-{{ backend_key }}.yaml --kubeconfig {{ k3s_kubeconfig }}"
  delegate_to: "{{ k3s_node_ip }}"
  become: true

- name: "Phase2 {{ backend_key }} | Wait for Pod to complete"
  ansible.builtin.command: >
    kubectl wait pod/bench-fio-{{ backend_key }}
    --for=condition=Ready=False
    --timeout=1200s
    --kubeconfig {{ k3s_kubeconfig }}
    -n default
  delegate_to: "{{ k3s_node_ip }}"
  become: true
  changed_when: false

- name: "Phase2 {{ backend_key }} | Collect fio results from Pod logs"
  ansible.builtin.command: "kubectl logs bench-fio-{{ backend_key }} -n default --kubeconfig {{ k3s_kubeconfig }}"
  register: pod_logs
  delegate_to: "{{ k3s_node_ip }}"
  become: true
  changed_when: false

- name: "Phase2 {{ backend_key }} | Save result"
  ansible.builtin.copy:
    dest: "{{ benchmark_run_dir }}/{{ backend_key }}-phase2.json"
    content: "{{ {'backend': backend_name, 'protocol': protocol, 'phase': 'phase2', 'run_id': benchmark_run_id, 'secrets_source': secrets_source, 'fio': pod_logs.stdout | from_json} | to_json(indent=2) }}"
    mode: "0644"
  delegate_to: localhost

- name: "Phase2 {{ backend_key }} | Update state"
  ansible.builtin.copy:
    dest: "{{ benchmark_run_dir }}/state.json"
    content: "{{ (lookup('file', benchmark_run_dir + '/state.json') | from_json) | combine({'completed': completed_backends + [backend_key + '-phase2']}) | to_json(indent=2) }}"
    mode: "0600"
  delegate_to: localhost

- name: "Phase2 {{ backend_key }} | Set completed"
  ansible.builtin.set_fact:
    completed_backends: "{{ completed_backends + [backend_key + '-phase2'] }}"

- name: "Phase2 {{ backend_key }} | Interim report"
  ansible.builtin.include_tasks: report.yml
  vars:
    report_mode: "interim"

- name: "Phase2 {{ backend_key }} | Cleanup Pod, PVC, ConfigMap, StorageClass"
  ansible.builtin.command: >
    kubectl delete pod/bench-fio-{{ backend_key }}
    pvc/bench-pvc-{{ backend_key }}
    configmap/bench-fio-jobs-{{ backend_key }}
    storageclass/bench-sc-{{ backend_key }}
    -n default
    --ignore-not-found
    --kubeconfig {{ k3s_kubeconfig }}
  delegate_to: "{{ k3s_node_ip }}"
  become: true
  failed_when: false
```

- [ ] **Step 5: Commit**

```bash
git add ansible/roles/storage_benchmark/templates/ \
        ansible/roles/storage_benchmark/tasks/phase2_k3s.yml \
        ansible/roles/storage_benchmark/tasks/phase2_backend.yml
git commit -m "feat(storage): phase2 k3s CSI pod benchmarks with per-backend cleanup"
```

---

## Task 8: Report Ansible Task

**Files:**
- Create: `ansible/roles/storage_benchmark/tasks/report.yml`

- [ ] **Step 1: Write report.yml**

```yaml
# ansible/roles/storage_benchmark/tasks/report.yml
---
- name: "Report | Run {{ report_mode }} report"
  ansible.builtin.command: >
    python3 scripts/storage_benchmark_report.py
    --run-dir {{ benchmark_run_dir }}
    --mode {{ report_mode }}
  args:
    chdir: "{{ playbook_dir | dirname }}"
  delegate_to: localhost
  changed_when: true
  register: report_output

- name: "Report | Show summary tail"
  ansible.builtin.debug:
    msg: "{{ report_output.stdout_lines[-10:] }}"
  when: report_output.stdout_lines | length > 0
```

- [ ] **Step 2: Commit**

```bash
git add ansible/roles/storage_benchmark/tasks/report.yml
git commit -m "feat(storage): add interim and final report Ansible task"
```

---

## Task 9: Benchmark Report Script (TDD)

**Files:**
- Create: `tests/unit/test_storage_benchmark_report.py`
- Create: `scripts/storage_benchmark_report.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/unit/test_storage_benchmark_report.py
import json
import textwrap
import pytest
from pathlib import Path
from scripts.storage_benchmark_report import (
    parse_job_metrics,
    generate_summary_line,
    generate_markdown_table,
    assign_tiers,
)


def make_fio_job(name, read_iops=0, write_iops=0, read_bw_kb=0, read_lat_p99_ns=0, write_lat_p99_ns=0):
    return {
        "jobname": name,
        "read": {
            "iops": read_iops,
            "bw": read_bw_kb,
            "lat_ns": {"percentile": {"99.000000": read_lat_p99_ns}},
        },
        "write": {
            "iops": write_iops,
            "bw": 0,
            "lat_ns": {"percentile": {"99.000000": write_lat_p99_ns}},
        },
    }


def make_result(backend, protocol, phase, jobs):
    return {
        "backend": backend,
        "protocol": protocol,
        "phase": phase,
        "run_id": "2026-06-24T1430",
        "fio": {
            "jobs": jobs,
        },
    }


def test_parse_job_metrics_extracts_rand_read_iops():
    jobs = [
        make_fio_job("rand-read-4k", read_iops=145000),
        make_fio_job("rand-write-4k", write_iops=92000),
        make_fio_job("seq-read-1m", read_bw_kb=2150000),
        make_fio_job("mixed-7030-4k", read_lat_p99_ns=210000, write_lat_p99_ns=310000),
        make_fio_job("db-pattern-8k", read_lat_p99_ns=195000, write_lat_p99_ns=290000),
    ]
    result = make_result("nvme-local", "local", "phase1", jobs)
    metrics = parse_job_metrics(result)
    assert metrics["rand_read_iops"] == 145000


def test_parse_job_metrics_extracts_rand_write_iops():
    jobs = [
        make_fio_job("rand-read-4k", read_iops=12000),
        make_fio_job("rand-write-4k", write_iops=8000),
        make_fio_job("seq-read-1m", read_bw_kb=870000),
        make_fio_job("mixed-7030-4k", read_lat_p99_ns=1200000, write_lat_p99_ns=1800000),
        make_fio_job("db-pattern-8k", read_lat_p99_ns=980000, write_lat_p99_ns=1500000),
    ]
    result = make_result("K3S_HDD", "nfs4", "phase1", jobs)
    metrics = parse_job_metrics(result)
    assert metrics["rand_write_iops"] == 8000


def test_parse_job_metrics_converts_seq_read_to_mb():
    jobs = [
        make_fio_job("rand-read-4k"),
        make_fio_job("rand-write-4k"),
        make_fio_job("seq-read-1m", read_bw_kb=2150000),
        make_fio_job("mixed-7030-4k"),
        make_fio_job("db-pattern-8k"),
    ]
    result = make_result("nvme-local", "local", "phase1", jobs)
    metrics = parse_job_metrics(result)
    assert metrics["seq_read_mb"] == pytest.approx(2099.6, rel=0.01)


def test_parse_job_metrics_extracts_mixed_p99_us():
    jobs = [
        make_fio_job("rand-read-4k"),
        make_fio_job("rand-write-4k"),
        make_fio_job("seq-read-1m"),
        make_fio_job("mixed-7030-4k", read_lat_p99_ns=1200000, write_lat_p99_ns=1800000),
        make_fio_job("db-pattern-8k"),
    ]
    result = make_result("K3S_HDD", "nfs4", "phase1", jobs)
    metrics = parse_job_metrics(result)
    assert metrics["mixed_p99_us"] == pytest.approx(1500.0)  # avg of read+write


def test_parse_job_metrics_extracts_db_p99_us():
    jobs = [
        make_fio_job("rand-read-4k"),
        make_fio_job("rand-write-4k"),
        make_fio_job("seq-read-1m"),
        make_fio_job("mixed-7030-4k"),
        make_fio_job("db-pattern-8k", read_lat_p99_ns=980000, write_lat_p99_ns=1500000),
    ]
    result = make_result("K3S_HDD", "iscsi", "phase1", jobs)
    metrics = parse_job_metrics(result)
    assert metrics["db_p99_us"] == pytest.approx(1240.0)  # avg of read+write


def test_generate_summary_line_done():
    metrics = {
        "rand_read_iops": 12000,
        "rand_write_iops": 8000,
        "seq_read_mb": 870.0,
        "mixed_p99_us": 1500.0,
        "db_p99_us": 1240.0,
    }
    line = generate_summary_line("K3S_HDD", "nfs4", "phase1", metrics)
    assert "[DONE]" in line
    assert "K3S_HDD" in line
    assert "nfs4" in line
    assert "12000" in line
    assert "8000" in line


def test_generate_summary_line_pending():
    line = generate_summary_line("WHITEBOX", "iscsi", "phase1", None)
    assert "[WAIT]" in line
    assert "WHITEBOX" in line
    assert "pending" in line


def test_generate_markdown_table_has_headers():
    rows = [
        {
            "backend": "nvme-local", "protocol": "local", "phase": "phase1",
            "metrics": {"rand_read_iops": 145000, "rand_write_iops": 92000,
                        "seq_read_mb": 2100.0, "mixed_p99_us": 210.0, "db_p99_us": 195.0},
        },
        {
            "backend": "K3S_HDD", "protocol": "nfs4", "phase": "phase1",
            "metrics": None,
        },
    ]
    table = generate_markdown_table(rows)
    assert "| Backend |" in table
    assert "| Protocol |" in table
    assert "nvme-local" in table
    assert "145000" in table
    assert "K3S_HDD" in table
    assert "pending" in table


def test_assign_tiers_fast_is_best_db_p99():
    candidates = [
        {"backend": "nvme-local", "protocol": "local", "db_p99_us": 195.0, "rand_write_iops": 92000},
        {"backend": "K3S_HDD", "protocol": "iscsi", "db_p99_us": 980.0, "rand_write_iops": 45000},
        {"backend": "K3S_HDD", "protocol": "nfs4", "db_p99_us": 1240.0, "rand_write_iops": 8000},
    ]
    tiers = assign_tiers(candidates)
    assert tiers["fast"]["backend"] == "nvme-local"
    assert tiers["standard"]["backend"] == "K3S_HDD"
    assert tiers["bulk"]["backend"] == "K3S_HDD"
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
pytest tests/unit/test_storage_benchmark_report.py -v
```

Expected: `ModuleNotFoundError: No module named 'scripts.storage_benchmark_report'`

- [ ] **Step 3: Write the report script**

```python
#!/usr/bin/env python3
"""Storage benchmark report generator.

Reads per-backend fio JSON results and produces:
  - report-live.md  (updated after each backend — interim)
  - report-final.md (full comparison + tier recommendations)
  - summary.txt     (one-liner per backend for `watch`)
"""
import argparse
import json
from pathlib import Path
from typing import Optional


ALL_BACKENDS = [
    ("nvme-local", "local", "phase1"),
    ("nvme-local", "local", "phase2"),
    ("K3S_HDD", "nfs4", "phase1"),
    ("K3S_HDD", "nfs4", "phase2"),
    ("vmstore", "nfs4", "phase1"),
    ("vmstore", "nfs4", "phase2"),
    ("WHITEBOX", "nfs4", "phase1"),
    ("WHITEBOX", "nfs4", "phase2"),
    ("K3S_HDD", "iscsi", "phase1"),
    ("K3S_HDD", "iscsi", "phase2"),
    ("vmstore", "iscsi", "phase1"),
    ("vmstore", "iscsi", "phase2"),
    ("WHITEBOX", "iscsi", "phase1"),
    ("WHITEBOX", "iscsi", "phase2"),
]


def parse_job_metrics(result: dict) -> dict:
    """Extract key performance metrics from a fio result dict."""
    jobs = {j["jobname"]: j for j in result["fio"]["jobs"]}

    def lat_avg_us(job_name: str) -> float:
        j = jobs.get(job_name, {})
        r_ns = j.get("read", {}).get("lat_ns", {}).get("percentile", {}).get("99.000000", 0)
        w_ns = j.get("write", {}).get("lat_ns", {}).get("percentile", {}).get("99.000000", 0)
        return ((r_ns + w_ns) / 2) / 1000

    return {
        "rand_read_iops": int(jobs.get("rand-read-4k", {}).get("read", {}).get("iops", 0)),
        "rand_write_iops": int(jobs.get("rand-write-4k", {}).get("write", {}).get("iops", 0)),
        "seq_read_mb": jobs.get("seq-read-1m", {}).get("read", {}).get("bw", 0) / 1024,
        "mixed_p99_us": lat_avg_us("mixed-7030-4k"),
        "db_p99_us": lat_avg_us("db-pattern-8k"),
    }


def generate_summary_line(backend: str, protocol: str, phase: str, metrics: Optional[dict]) -> str:
    """Return a one-liner status string for summary.txt."""
    label = f"{backend} {protocol} {phase}"
    if metrics is None:
        return f"[WAIT] {label:<40} pending"
    return (
        f"[DONE] {label:<40} "
        f"r={metrics['rand_read_iops']:>6} w={metrics['rand_write_iops']:>6} iops | "
        f"seq={metrics['seq_read_mb']:>6.0f}MB/s | "
        f"p99={metrics['mixed_p99_us']:>7.0f}µs | "
        f"db_p99={metrics['db_p99_us']:>7.0f}µs"
    )


def generate_markdown_table(rows: list) -> str:
    """Render results as a GitHub-flavoured markdown table."""
    header = (
        "| Backend | Protocol | Phase | Rand R IOPS | Rand W IOPS | "
        "Seq R MB/s | Mixed p99 µs | DB p99 µs |\n"
        "|---------|----------|-------|-------------|-------------|"
        "-----------|-------------|----------|\n"
    )
    lines = [header]
    for row in rows:
        m = row.get("metrics")
        if m:
            lines.append(
                f"| {row['backend']} | {row['protocol']} | {row['phase']} | "
                f"{m['rand_read_iops']} | {m['rand_write_iops']} | "
                f"{m['seq_read_mb']:.0f} | {m['mixed_p99_us']:.0f} | {m['db_p99_us']:.0f} |\n"
            )
        else:
            lines.append(
                f"| {row['backend']} | {row['protocol']} | {row['phase']} | "
                "pending | pending | pending | pending | pending |\n"
            )
    return "".join(lines)


def assign_tiers(candidates: list) -> dict:
    """Assign fast/standard/bulk tiers from phase1 results.

    fast    = lowest db_p99_us (best for stateful DBs)
    standard = second-lowest db_p99_us or best non-fast balance
    bulk    = remaining (highest capacity assumption)
    """
    sorted_by_db = sorted(candidates, key=lambda c: c["db_p99_us"])
    fast = sorted_by_db[0] if len(sorted_by_db) > 0 else {}
    standard = sorted_by_db[1] if len(sorted_by_db) > 1 else {}
    bulk = sorted_by_db[2] if len(sorted_by_db) > 2 else sorted_by_db[-1] if sorted_by_db else {}
    return {"fast": fast, "standard": standard, "bulk": bulk}


def run_report(run_dir: Path, mode: str) -> None:
    result_files = sorted(run_dir.glob("*-phase*.json"))
    loaded = {}
    for f in result_files:
        try:
            data = json.loads(f.read_text())
            key = f.stem
            loaded[key] = data
        except (json.JSONDecodeError, KeyError):
            continue

    rows = []
    summary_lines = []
    for backend, protocol, phase in ALL_BACKENDS:
        key = f"{backend}-{protocol}-{phase}"
        result = loaded.get(key)
        metrics = parse_job_metrics(result) if result else None
        rows.append({"backend": backend, "protocol": protocol, "phase": phase, "metrics": metrics})
        summary_lines.append(generate_summary_line(backend, protocol, phase, metrics))

    table = generate_markdown_table(rows)

    # Write live report
    live_path = run_dir / "report-live.md"
    live_path.write_text(f"# Storage Benchmark — Live Results\n\n{table}\n")

    # Write summary
    summary_path = run_dir / "summary.txt"
    summary_path.write_text("\n".join(summary_lines) + "\n")

    if mode == "final":
        # Tier assignment from phase1 results only
        phase1_metrics = [
            {**{"backend": r["backend"], "protocol": r["protocol"]}, **r["metrics"]}
            for r in rows
            if r["phase"] == "phase1" and r["metrics"] is not None
        ]
        tiers = assign_tiers(phase1_metrics)

        tier_section = (
            "\n## Tier Recommendations\n\n"
            f"| Tier | StorageClass | Backend | Protocol | DB p99 µs |\n"
            f"|------|-------------|---------|----------|-----------|\n"
            f"| Fast | storage-fast | {tiers.get('fast', {}).get('backend', 'TBD')} | "
            f"{tiers.get('fast', {}).get('protocol', 'TBD')} | "
            f"{tiers.get('fast', {}).get('db_p99_us', 'N/A')} |\n"
            f"| Standard | storage-standard | {tiers.get('standard', {}).get('backend', 'TBD')} | "
            f"{tiers.get('standard', {}).get('protocol', 'TBD')} | "
            f"{tiers.get('standard', {}).get('db_p99_us', 'N/A')} |\n"
            f"| Bulk | storage-bulk | {tiers.get('bulk', {}).get('backend', 'TBD')} | "
            f"{tiers.get('bulk', {}).get('protocol', 'TBD')} | "
            f"{tiers.get('bulk', {}).get('db_p99_us', 'N/A')} |\n"
        )

        final_path = run_dir / "report-final.md"
        final_path.write_text(f"# Storage Benchmark — Final Results\n\n{table}{tier_section}\n")
        print(f"Final report written to {final_path}")
        print(tier_section)

    print("\n".join(summary_lines))


def main() -> None:
    parser = argparse.ArgumentParser(description="Storage benchmark report generator")
    parser.add_argument("--run-dir", required=True, type=Path)
    parser.add_argument("--mode", choices=["interim", "final"], default="interim")
    args = parser.parse_args()
    run_report(args.run_dir, args.mode)


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run tests to confirm they pass**

```bash
pytest tests/unit/test_storage_benchmark_report.py -v
```

Expected: 9 tests pass.

- [ ] **Step 5: Commit**

```bash
git add scripts/storage_benchmark_report.py tests/unit/test_storage_benchmark_report.py
git commit -m "feat(storage): add benchmark report script with tier assignment (TDD)"
```

---

## Task 10: --background Flag in manage.py

**Files:**
- Modify: `src/homelab_gitops/cli/core_commands/config.py`

- [ ] **Step 1: Update config_command to accept --background**

Replace the `config_command` function in `src/homelab_gitops/cli/core_commands/config.py`:

```python
"""Config command - apply post-deployment OS configuration via Ansible."""

import os
import shutil
import subprocess
import sys
import time
import typer
import yaml
from typing import Optional
from homelab_gitops.domain.models import NodeProfile
from homelab_gitops.domain.workflows import Workflow
from homelab_gitops.drivers.ansible_driver import AnsibleDriver
from homelab_gitops.drivers.secrets_driver import SecretsDriver
from homelab_gitops.domain.exceptions import DomainError
from homelab_gitops.cli.utils import print_success, print_error, print_info


def _run_in_background(args: list[str]) -> None:
    """Wrap command in tmux session or nohup if tmux not available."""
    run_id = time.strftime("%Y-%m-%dT%H%M")
    session_name = f"bench-{run_id}"
    log_path = f"results/storage-benchmark/{run_id}/ansible.log"
    os.makedirs(f"results/storage-benchmark/{run_id}", exist_ok=True)

    if shutil.which("tmux"):
        cmd = ["tmux", "new-session", "-d", "-s", session_name, " ".join(args)]
        subprocess.run(cmd, check=True)
        print_info(f"Benchmark running in tmux session '{session_name}'")
        print_info(f"  Attach:  tmux attach -t {session_name}")
        print_info(f"  Monitor: watch cat results/storage-benchmark/{run_id}/summary.txt")
    else:
        with open(log_path, "w") as log:
            subprocess.Popen(args, stdout=log, stderr=log, start_new_session=True)
        print_info(f"Benchmark running in background (tmux not found)")
        print_info(f"  Log:     {log_path}")
        print_info(f"  Monitor: watch cat results/storage-benchmark/{run_id}/summary.txt")


def config_command(
    profile: str,
    index: Optional[str] = typer.Argument(None, help="Instance index (01, 02, etc.)"),
    background: bool = typer.Option(False, "--background", help="Run in tmux session (nohup fallback)"),
):
    """Apply post-deployment OS configuration via Ansible.

    Example:
        $ manage config ubuntu-base 01
        $ manage config benchmark-storage --background
    """
    if background:
        args = [sys.executable, "manage.py", "config", profile]
        if index:
            args.append(index)
        _run_in_background(args)
        return

    try:
        profile_path = f"config/profiles/{profile}.yml"
        if not os.path.exists(profile_path):
            raise FileNotFoundError(f"Profile not found: {profile_path}")

        with open(profile_path) as f:
            profile_dict = yaml.safe_load(f)

        profile_dict["name"] = profile
        profile_obj = NodeProfile(**profile_dict)

        drivers = {
            "config": AnsibleDriver(),
        }

        workflow = Workflow(profile_obj, drivers=drivers, secrets_driver=SecretsDriver())

        print_info(f"Configuring {profile} {index or 'all instances'} ...")
        state = workflow.execute(["config"])

        print_success(f"Configuration applied to {state.vm_name}")

    except Exception as e:
        print_error(f"Configuration failed: {e}")
        raise typer.Exit(code=1)


command_metadata = {
    "name": "config",
    "aliases": ["cfg"],
    "help": "Apply Ansible configuration to nodes",
}
```

- [ ] **Step 2: Verify manage.py help shows --background**

```bash
python3 manage.py config --help
```

Expected output includes: `--background  Run in tmux session (nohup fallback)`

- [ ] **Step 3: Commit**

```bash
git add src/homelab_gitops/cli/core_commands/config.py
git commit -m "feat(storage): add --background flag to config command (tmux/nohup)"
```

---

## Task 11: Wire Role into site.yml and metadata.yml

**Files:**
- Modify: `ansible/site.yml`
- Modify: `config/metadata.yml`

- [ ] **Step 1: Add benchmark play to site.yml**

Append to `ansible/site.yml`:

```yaml
- name: Run storage benchmarks
  hosts: tag_benchmark
  become: true
  roles:
    - storage_benchmark
```

- [ ] **Step 2: Add entries to metadata.yml**

In `config/metadata.yml`, under `tags:`, add:

```yaml
  storage_benchmark: "Run the two-phase storage benchmark suite (Phase 1 VM + Phase 2 k3s pods)."
```

Under `roles:`, add:

```yaml
  storage_benchmark: "Two-phase storage benchmarking: raw protocol fio on VM and CSI-path fio pods in k3s."
```

- [ ] **Step 3: Run existing unit tests to confirm no regressions**

```bash
pytest tests/unit/ -v -x
```

Expected: All existing tests pass.

- [ ] **Step 4: Commit**

```bash
git add ansible/site.yml config/metadata.yml
git commit -m "feat(storage): wire storage_benchmark role into site.yml and metadata"
```

---

## Task 12: democratic-csi + StorageClass Manifests + Kustomize Wiring

**Files:**
- Create: `kubernetes/platform/democratic-csi/overlays/k3s-01/nfs-helmchart.yaml`
- Create: `kubernetes/platform/democratic-csi/overlays/k3s-01/iscsi-helmchart.yaml`
- Create: `kubernetes/platform/democratic-csi/overlays/k3s-01/kustomization.yaml`
- Create: `kubernetes/platform/storage/overlays/k3s-01/storageclass-fast.yaml`
- Create: `kubernetes/platform/storage/overlays/k3s-01/storageclass-standard.yaml`
- Create: `kubernetes/platform/storage/overlays/k3s-01/storageclass-bulk.yaml`
- Create: `kubernetes/platform/storage/overlays/k3s-01/kustomization.yaml`
- Modify: `kubernetes/clusters/k3s-01/kustomization.yaml`

- [ ] **Step 1: Create directory structure**

```bash
mkdir -p kubernetes/platform/democratic-csi/overlays/k3s-01
mkdir -p kubernetes/platform/storage/overlays/k3s-01
```

- [ ] **Step 2: Write democratic-csi NFS HelmChart**

```yaml
# kubernetes/platform/democratic-csi/overlays/k3s-01/nfs-helmchart.yaml
apiVersion: helm.cattle.io/v1
kind: HelmChart
metadata:
  name: democratic-csi-nfs
  namespace: kube-system
  annotations:
    argocd.argoproj.io/sync-wave: "3"
spec:
  repo: https://democratic-csi.github.io/charts
  chart: democratic-csi
  version: 0.14.6
  targetNamespace: democratic-csi
  createNamespace: true
  valuesContent: |-
    csiDriver:
      name: "org.democratic-csi.nfs"
    controller:
      driver:
        image: democraticcsi/democratic-csi:v1.9.3
    node:
      driver:
        image: democraticcsi/democratic-csi:v1.9.3
    driver:
      config:
        driver: freenas-api-nfs
        httpConnection:
          protocol: http
          host: 10.10.10.20
          port: 80
          apiVersion: 2
          apiKey: "${TRUENAS_API_KEY}"
        zfs:
          datasetParentName: K3S_HDD/k3s-nfs
          detachedSnapshotsDatasetParentName: K3S_HDD/k3s-nfs-snapshots
          datasetEnableQuotas: true
          datasetEnableReservation: false
        nfs:
          shareHost: 10.10.10.20
          shareAlldirs: false
          shareMaprootUser: root
          shareMaprootGroup: root
```

> **Note:** `TRUENAS_API_KEY` must be available to the controller pod as an environment variable via a Secret named `truenas-credentials` in the `democratic-csi` namespace. Create this ExternalSecret after benchmark results confirm which dataset to use; update `datasetParentName` to match the winning backend.

- [ ] **Step 3: Write democratic-csi iSCSI HelmChart**

```yaml
# kubernetes/platform/democratic-csi/overlays/k3s-01/iscsi-helmchart.yaml
apiVersion: helm.cattle.io/v1
kind: HelmChart
metadata:
  name: democratic-csi-iscsi
  namespace: kube-system
  annotations:
    argocd.argoproj.io/sync-wave: "3"
spec:
  repo: https://democratic-csi.github.io/charts
  chart: democratic-csi
  version: 0.14.6
  targetNamespace: democratic-csi
  createNamespace: true
  valuesContent: |-
    csiDriver:
      name: "org.democratic-csi.iscsi"
    controller:
      driver:
        image: democraticcsi/democratic-csi:v1.9.3
    node:
      driver:
        image: democraticcsi/democratic-csi:v1.9.3
    driver:
      config:
        driver: freenas-api-iscsi
        httpConnection:
          protocol: http
          host: 10.10.10.20
          port: 80
          apiVersion: 2
          apiKey: "${TRUENAS_API_KEY}"
        zfs:
          datasetParentName: K3S_HDD/k3s-iscsi
          detachedSnapshotsDatasetParentName: K3S_HDD/k3s-iscsi-snapshots
        iscsi:
          targetPortal: "10.10.10.20:3260"
          interface: ""
          namePrefix: "k3s-"
          nameSuffix: ""
          targetGroups:
            - targetGroupPortalGroup: 1
              targetGroupInitiatorGroup: 1
              targetGroupAuthType: None
          extentInsecureTpc: true
          extentXenCompat: false
          extentDisablePhysicalBlocksize: true
          extentBlocksize: 512
          extentRpm: "SSD"
          extentAvailThreshold: 0
```

> **Note:** Update `datasetParentName` and `iscsi.targetPortal` after benchmark results confirm the winning iSCSI backend.

- [ ] **Step 4: Write democratic-csi kustomization**

```yaml
# kubernetes/platform/democratic-csi/overlays/k3s-01/kustomization.yaml
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization
resources:
  - nfs-helmchart.yaml
  - iscsi-helmchart.yaml
```

- [ ] **Step 5: Write StorageClass skeleton manifests**

```yaml
# kubernetes/platform/storage/overlays/k3s-01/storageclass-fast.yaml
# FAST TIER — update provisioner and parameters after reviewing benchmark report-final.md
# Expected winner: backend with lowest db_p99_us from phase1/phase2 results
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: storage-fast
  annotations:
    # Set to true once this is confirmed as the primary fast tier
    storageclass.kubernetes.io/is-default-class: "false"
# UPDATE: set provisioner to the winning backend after benchmarks:
#   NVMe local:  rancher.io/local-path
#   iSCSI:       org.democratic-csi.iscsi
#   NFS v4:      org.democratic-csi.nfs
provisioner: org.democratic-csi.iscsi
parameters:
  fsType: ext4
reclaimPolicy: Retain
volumeBindingMode: Immediate
allowVolumeExpansion: true
```

```yaml
# kubernetes/platform/storage/overlays/k3s-01/storageclass-standard.yaml
# STANDARD TIER — platform services (monitoring, logging, ArgoCD state)
# UPDATE: set provisioner to second-best db_p99_us backend from report-final.md
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: storage-standard
provisioner: org.democratic-csi.nfs
parameters:
  fsType: nfs
reclaimPolicy: Retain
volumeBindingMode: Immediate
allowVolumeExpansion: true
```

```yaml
# kubernetes/platform/storage/overlays/k3s-01/storageclass-bulk.yaml
# BULK TIER — backups, large media artifacts, infrequent access
# UPDATE: set provisioner to highest-capacity backend from report-final.md
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: storage-bulk
provisioner: org.democratic-csi.nfs
parameters:
  fsType: nfs
reclaimPolicy: Retain
volumeBindingMode: WaitForFirstConsumer
allowVolumeExpansion: true
```

- [ ] **Step 6: Write storage kustomization**

```yaml
# kubernetes/platform/storage/overlays/k3s-01/kustomization.yaml
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization
resources:
  - storageclass-fast.yaml
  - storageclass-standard.yaml
  - storageclass-bulk.yaml
```

- [ ] **Step 7: Add storage and democratic-csi to cluster kustomization**

In `kubernetes/clusters/k3s-01/kustomization.yaml`, add two lines to the `resources:` list:

```yaml
  - ../../platform/democratic-csi/overlays/k3s-01
  - ../../platform/storage/overlays/k3s-01
```

- [ ] **Step 8: Validate kustomize renders cleanly**

```bash
kubectl kustomize kubernetes/clusters/k3s-01/ --enable-helm 2>&1 | head -40
```

Expected: YAML output with no errors. StorageClass manifests appear in output.

- [ ] **Step 9: Commit**

```bash
git add kubernetes/platform/democratic-csi/ \
        kubernetes/platform/storage/ \
        kubernetes/clusters/k3s-01/kustomization.yaml
git commit -m "feat(storage): add democratic-csi HelmCharts and StorageClass tier skeletons"
```

---

## Post-Benchmark Steps (not automated — do after running the suite)

Once `report-final.md` is generated:

1. Read the tier recommendation table in the report.
2. Update `storageclass-fast.yaml`, `storageclass-standard.yaml`, `storageclass-bulk.yaml` with the winning backend's provisioner and parameters.
3. Update `datasetParentName` in the relevant democratic-csi HelmChart to match the winning dataset.
4. Create a `truenas-credentials` ExternalSecret in the `democratic-csi` namespace referencing OpenBao `kv/storage/truenas`.
5. Commit, push, and let ArgoCD apply.

---

## Running the Full Suite

```bash
# 1. Provision benchmark VM
python3 manage.py deploy benchmark-storage 01 --host 10.10.10.11

# 2. Run full benchmark in background
python3 manage.py config benchmark-storage --background

# 3. Monitor progress
watch cat results/storage-benchmark/<run-id>/summary.txt

# 4. Resume if interrupted
python3 manage.py config benchmark-storage -e benchmark_run_id=<run-id>

# 5. Destroy VM when done
python3 manage.py destroy bench-storage-01
```
