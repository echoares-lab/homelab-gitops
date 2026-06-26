# Pipeline Operations Runbook

Detailed operational procedures for the unified GitOps pipeline managing high-performance Ubuntu and Photon OS environments.

## Table of Contents
1. [Prerequisites](#1-prerequisites)
2. [Command Reference (`manage.py`)](#2-command-reference-managesh)
3. [Generator Helpers](#3-generator-helpers)
4. [Configuration System](#4-configuration-system)
5. [Deployment Workflow](#5-deployment-workflow)
6. [Automated Testing](#6-automated-testing)
7. [Agent Workflow Hygiene](#7-agent-workflow-hygiene)
8. [Post-Deployment: Technitium DNS](#8-post-deployment-technitium-dns)
9. [Troubleshooting](#9-troubleshooting)
10. [Observability Setup](#10-observability-setup)

---

## 1. Prerequisites
Ensure the orchestration host has the following:
*   **OpenTofu** (`>= 1.6`)
*   **Ansible** (`>= 2.14`) with `vSphere Automation SDK`
*   **Pytest & Testinfra**
*   **govc** (installed in `build/`)
*   **OpenBao CLI** (`bao`) with `VAULT_ADDR` and an appropriate token for runtime secret resolution
*   **1Password CLI** only for legacy migration reads
*   **curl** — HTTP client for API testing
*   **jq** — JSON query tool for parsing responses
*   **docker-compose** or **docker compose** — Container orchestration

---

## 2. Command Reference (`manage.py`)

The `python3 manage.py` orchestrator provides a unified interface for the entire lifecycle.

### `Interactive Mode`
Running `python3 manage.py` with no arguments launches the **Command Builder**. This guided wizard helps you construct and execute the correct CLI syntax.

### `lint`
Validates the YAML profile schema and checks if all vCenter objects actually exist.
*   **Example:** `python3 manage.py lint photon-docker 02 --host esxi-01.mgmt.plexplease.com`

### `deploy`
Provisions the virtual hardware via OpenTofu. Supports runtime overrides for IP, Hostname, and MAC.
*   **Example:** `python3 manage.py deploy ubuntu-base 01 --ip 10.10.10.50 --gateway 10.10.10.1`

### `config` (Implied Limits)
Applies post-deployment OS configuration. Targeting is **Automatic**:
*   **Specific VM:** `python3 manage.py config ubuntu-base 04` (Targets only the 04 node).
*   **Whole Group:** `python3 manage.py config ubuntu-base` (Targets all VMs with the `ubuntu` tag).
*   **Long-running background run:** `python3 manage.py config benchmark-storage --background` (Runs in tmux when available, otherwise writes an Ansible log under `results/storage-benchmark/<run-id>/`.)

### `test`
Executes Pytest-Testinfra validation.
*   **Example:** `python3 manage.py test ubuntu-base 01`

### `destroy` (Safety First)
Removes a VM using a **single identifier** (Name, IP, or MAC).
*   **Example:** `python3 manage.py destroy 10.10.10.50`
*   **Safety:** Always requires an interactive `(y/N)` confirmation before proceeding.

### `status`
Prints a read-only Rich table of managed OpenTofu workspaces and matching vCenter VMs.
*   **Example:** `python3 manage.py status`
*   **Alias:** `python3 manage.py st`
*   **Use case:** Quickly spot missing VMs, missing IPs, power state, host placement, profile tags, and workspace drift before making changes.

### `cert`
Manages ACME certificates using DNS-01 challenges via Technitium.
*   **Issue:** `python3 manage.py cert issue --domain "app.mgmt.plexplease.com" --email "admin@plexplease.com"`
*   **Workflow:** Generates a local key, creates a TXT record in Technitium, validates via Let's Encrypt, and stores the resulting cert chain in 1Password.
*   **Security:** Certificates are stored in 1Password as `cert-<domain>-chain` and `cert-<domain>-key`.

### `doctor`
Runs comprehensive system diagnostics across all core infrastructure drivers.
*   **Example:** `python3 manage.py doctor`
*   **Use case:** Proactively check API connectivity to vCenter, OPNsense, Technitium, and Tofu, while verifying DNS resolution health.

### `monitor`
Manages the observability stack (Grafana Alloy, Docker Metrics) across the fleet.
*   **Setup:** `python3 manage.py monitor setup <profile>` - Deploys the monitoring agent to the target node via Ansible.
*   **Health:** `python3 manage.py monitor health <profile>` - Retrieves real-time health metrics summary from the node.

---

## 3. Generator Helpers

Wizards to automate the "Logic -> Play -> Blueprint" GitOps chain.

| Helper | Description |
| :--- | :--- |
| `create-role` | Scaffolds an Ansible role folder and attaches it to `site.yml`. |
| `create-play` | Creates a new targeting "bucket" in `site.yml` for specific tags. |
| `create-profile` | Generates a new hardware blueprint in `config/profiles/`. |
| `edit-profile` | Updates specs (CPU, RAM, Tags) for an existing profile. |

---

## 4. Configuration System

### Consolidated Secrets
Runtime secrets are resolved through OpenBao KV v2 using `config/secrets.env`.
*   **Endpoint:** `VAULT_ADDR=http://openbao.plexplease.com:8201`
*   **Runtime:** Export `VAULT_ADDR` and a token with read access, then run `python3 manage.py <command>`.
*   **Reference format:** `bao://kv/prod/<scope>/<field>`, for example `bao://kv/prod/platform/vcenter/VCENTER_PASSWORD`.
*   **Security:** `config/secrets.env` contains only `bao://` references and is safe to commit. Real secret values remain in OpenBao.
*   **Legacy:** 1Password and `config/vault.yml.example` remain migration references only; Ansible Vault is not the primary runtime path.

---

## 5. Deployment Workflow

1.  **State Isolation:** Every node gets a dedicated **OpenTofu Workspace** named after its FQDN.
2.  **Hardware Alignment:** The pipeline enforces **PVSCSI** and **VMXNET3** for performance.
3.  **Connectivity:** The pipeline automatically detects Static IPs or DHCP assignments and waits for SSH before configuration.

### Kubernetes GitOps layout

Use the [GitOps Layout Standard](./GITOPS_LAYOUT.md) when adding Kubernetes
platform or workload manifests. The `k3s-01` root Application syncs
`kubernetes/clusters/k3s-01/`, which composes cluster config from `config/` and
platform overlays from `kubernetes/platform/*/overlays/k3s-01/`.

For tracked and local generated-file inventory, including OpenTofu state,
generated Ignition, coverage, scratch, local env, and generated Ansible
artifacts, see [Artifact and State Hygiene Inventory](./ARTIFACT_STATE_HYGIENE.md).
For image build source paths and generated output paths, see
[Image Build Source And Artifact Layout](./IMAGE_BUILD_LAYOUT.md). FCOS Packer
builds serve generated installer Ignition from `build/http/fcos/installed.ign`;
regenerate that file locally before building and do not commit it.
Agents working in this repository should also follow
[Agent Working-Tree and PR Hygiene](./AGENT_WORKFLOW_HYGIENE.md) for claim
comments, dirty worktrees, generated artifacts, one-issue/one-PR flow, and
auto-merge expectations.

Validate GitOps manifests locally before opening a PR:

```bash
python3 scripts/validate_gitops_manifests.py
```

The validator renders every `kustomization.yaml` under `kubernetes/`, follows
referenced resource paths, parses rendered YAML, and checks that each Kubernetes
object has `apiVersion`, `kind`, and `metadata.name`.

### K3s platform readiness baseline

The `k3s-01` cluster composition includes the platform services required before
routine workloads are added:

- `velero` in `backup`, using OpenBao-managed TrueNAS S3/MinIO credentials.
- `kube-prometheus-stack` in `observability`, with Prometheus using
  `storage-standard`.
- `apprise` in `notifications`, with Alertmanager forwarding to Apprise and
  `ntfy` configured inside the OpenBao `APPRISE_CONFIG` value.
- `cloudnative-pg` and `platform-postgres` in `database`, using
  `storage-fast` and S3 backups.
- `authentik` in `identity`, backed by `platform-postgres` and exposed through
  Traefik/cert-manager ingress.
- `workloads/home/sample-app`, which documents the minimum workload onboarding
  contract for future services.

Required OpenBao paths:

- `prod/platform/velero`: `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`
- `prod/platform/truenas-s3`: `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`
- `prod/platform/notifications`: `APPRISE_CONFIG`
- `prod/platform/authentik`: `AUTHENTIK_SECRET_KEY`,
  `AUTHENTIK_BOOTSTRAP_EMAIL`, `AUTHENTIK_BOOTSTRAP_PASSWORD_HASH`,
  `AUTHENTIK_BOOTSTRAP_TOKEN`, `AUTHENTIK_POSTGRESQL_PASSWORD`

After Argo CD syncs the baseline, verify the platform with:

```bash
kubectl -n backup get pods
kubectl -n observability get pods
kubectl -n notifications get pods
kubectl -n database get clusters.postgresql.cnpg.io
kubectl -n identity get pods
```

Send a synthetic Alertmanager alert to confirm the path:

```bash
kubectl -n notifications port-forward svc/apprise-alertmanager-webhook 3000:3000
curl -X POST http://127.0.0.1:3000 \
  -H 'Content-Type: application/json' \
  -d '{"status":"firing","alerts":[{"status":"firing","labels":{"alertname":"SyntheticTest","severity":"info"},"annotations":{"summary":"Apprise ntfy path test"}}]}'
```

Expected result: the webhook returns `apprise_status=<2xx or 3xx>` and Apprise
forwards the message to the configured `ntfy` topic.

### K3s storage benchmark workflow

Use the `benchmark-storage` profile to provision a dedicated VM for storage
profiling, then run the storage benchmark role through the normal config
workflow. The role runs fio directly against VM-mounted backends and then runs
fio pods through k3s StorageClasses.

```bash
python3 manage.py deploy benchmark-storage 01 --host 10.10.10.11
python3 manage.py config benchmark-storage --background
watch cat results/storage-benchmark/<run-id>/summary.txt
python3 manage.py config benchmark-storage -e benchmark_run_id=<run-id>
python3 manage.py destroy bench-storage-01
```

After `report-final.md` is generated, update the `storage-fast`,
`storage-standard`, and `storage-bulk` manifests under
`kubernetes/platform/storage/overlays/k3s-01/` with the measured winners. Also
update the relevant democratic-csi dataset settings under
`kubernetes/platform/democratic-csi/overlays/k3s-01/`.

Validate image build inputs locally after changing Packer templates, Packer
HTTP fixtures, or Butane transpilation logic:

```bash
python3 scripts/validate_image_build_inputs.py
```

The image validator runs Packer syntax validation and Butane transpilation only.
It does not build templates, contact vCenter, or deploy infrastructure. The same
command is suitable for CI runners that have `packer` and `butane` installed.

---

## 6. Automated Testing

The pipeline uses `pytest-testinfra` to verify the "Final State":
*   **Common:** SSH hardening (root/password disabled), user presence, MAC alignment.
*   **Ubuntu:** UFW status, package integrity.
*   **Photon:** Docker service status.

### Ansible Structure Validation

Run the structure validator before changing playbooks, roles, profile
playbook references, or `config/metadata.yml`:

```bash
python3 scripts/validate_ansible_structure.py
```

The validator checks that playbook role references resolve to directories under
`ansible/roles/`, profile `deployment.playbooks` entries resolve under
`ansible/`, profile `deployment.roles` entries have matching role directories,
and role/profile tag metadata stays consistent. It is safe to run locally and
can be used as a CI gate if Ansible structure changes become part of the CI
workflow.

---

## 7. Agent Workflow Hygiene

Agents should follow the mandatory standards in [`AGENTS.md`](../AGENTS.md) and
the focused [Agent Working-Tree and PR Hygiene](./AGENT_WORKFLOW_HYGIENE.md)
runbook before opening a PR. In short: claim the issue, isolate dirty
worktrees, avoid committing generated local state, keep one issue per PR, and
enable auto-merge when branch protection allows it.

### Production Branch Governance

The protected live GitOps branch is `production`. Argo CD should reconcile
k3s-01 from `targetRevision: production`, not from an implicit `HEAD` value.
During migration, `master` can remain available for compatibility, but live
cluster promotion should happen by merging or fast-forwarding reviewed changes
into `production`.

Before switching GitHub's repository default branch to `production`, verify:

- the `production` branch exists and is protected with required CI checks;
- workflow push triggers include `production`;
- the k3s-01 root Application points at `targetRevision: production`;
- open PRs target the intended base branch;
- local clones update their default upstream after the GitHub setting changes.

---

## 8. Post-Deployment: Technitium DNS
Once your DNS server is deployed, you can manage its zones, records, and DHCP settings using the specialized **Technitium Manager**.

See the [DNS & DHCP Management Runbook](./DNS_DHCP_MANAGEMENT.md) for detailed instructions on using the interactive wizard and Universal CSV.

## 9. Troubleshooting

### vCenter REST API 500 Error
*   **Cause:** Hardware mismatch in the OVF template.
*   **Fix:** Ensure the template is remediated with vmx-21/PVSCSI standards.

### Ansible "Unreachable"
*   **Cause:** Incorrect SSH key or path.
*   **Fix:** Check the `SSH_PRIVATE_KEY_PATH` and SSH admin fields in OpenBao under `kv/prod/repo/homelab-gitops`. The pipeline uses ED25519 by default.

---

## 10. Observability Setup

### Monitoring Agents (Alloy)

All nodes receive a Grafana Alloy agent by default to collect metrics and logs.

**Skip Alloy for a profile:**
```yaml
tags:
  - ubuntu
  - github_runner
skip_alloy: true  # Opt-out for ephemeral runners
```

**Central metrics/logs destination:** `10.10.10.30`
- Prometheus metrics: `http://10.10.10.30:9090`
- Loki logs: `http://10.10.10.30:3100`
- Grafana UI: `http://10.10.10.30:3000`

**Agent configuration:** Modify `ansible/roles/alloy/defaults/main.yml` to change:
- `alloy_scrape_interval` — how often to scrape metrics
- `alloy_central_prometheus_url` / `alloy_central_loki_url` — where to send data
- Per-profile: `alloy_extra_scrape_targets` to add custom exporters

### Profile Log Retention

Every profile playbook includes the `log_retention` role. By default it keeps
journald bounded with a daily vacuum retaining up to 14 days or 512MB,
whichever limit is hit first.

Profiles can add application log policies under `logging.files`. Example from
`photon-dns`:

```yaml
logging:
  files:
  - path: /var/log/technitium/dns/*.log
    owner: dns-server
    group: dns-server
    mode: "0640"
    rotate_count: 14
    max_size: 100M
  journald:
    vacuum_enabled: true
    vacuum_time: 14d
    vacuum_size: 512M
```

This renders `/etc/logrotate.d/homelab-profile` and uses compression plus
copytruncate for app logs that stay open.

### Runner disk expansion

GitHub runner profiles allocate a 400 GB virtual disk. The `github_runner_base`
role expands the root partition and filesystem during configuration so the OS can
use the full disk.

Token-free repair for existing runners:

```bash
ansible-playbook ansible/runner-maintenance.yml \
  -i ansible/inventory/vmware_vms.yml
```

Verify a runner after config:

```bash
df -h /
```

### Docker Metrics & TLS

Docker hosts receive the `docker_metrics` role (applied after `docker` role).

**What it does:**
- Distributes OPNsense CA certificates to `/etc/docker/certs.d/`
- Configures Docker daemon with TLS socket on port 2376
- Exposes Docker metrics endpoint on port 9323
- Allows dockerhand and uptime-kuma to securely manage/monitor Docker

**TLS Certificate Setup:**

1. Generate/obtain certs from OPNsense CA for each Docker node:
   - Subject: `docker-web-01.mgmt.plexplease.com` (node FQDN)
   - Include: `ca.crt`, `server.crt`, `server.key`

2. Place certs in `ansible/roles/docker_metrics/files/`:
   ```bash
   cp /path/to/opnsense/ca.crt ansible/roles/docker_metrics/files/
   cp /path/to/opnsense/server-docker-web-01.crt ansible/roles/docker_metrics/files/server.crt
   cp /path/to/opnsense/server-docker-web-01.key ansible/roles/docker_metrics/files/server.key
   ```

3. Run site.yml — role distributes certs and configures Docker daemon.

4. Verify TLS socket is accessible:
   ```bash
   # From 10.10.10.30 or any node with Docker client certs:
   docker -H tcp://docker-web-01.mgmt.plexplease.com:2376 \
     --tlscacert=/path/to/ca.crt \
     --tlscert=/path/to/client.crt \
     --tlskey=/path/to/client.key \
     ps
   ```

**Renewal:** When OPNsense certs expire, re-generate and place in `files/`, then re-run site.yml.

### Remote Tools

**dockerhand** — Runs on 10.10.10.30, connects to Docker nodes via TLS
- Configuration: See dockerhand docs for adding Docker hosts
- Point to: `tcp://NODE_FQDN:2376` with CA/client certs

**uptime-kuma** — Runs on 10.10.10.30, probes services
- Configure TCP checks to `NODE:2376` with TLS enabled
- Optional: Use Prometheus integration to scrape custom metrics

## 10. 1Password Connect Server

The 1Password Connect service provides a secure REST API for programmatic secret retrieval. It runs on the main Docker host (`10.10.10.30`) and is used by the orchestrator and Ansible playbooks to resolve secrets from 1Password.

### Architecture

The Connect stack consists of two containers:
- **connect-api** — REST API endpoint (port 8200)
- **connect-sync** — Vault synchronization with 1Password cloud
- **connect-data** — Persistent volume for cached vault data

### Setup Instructions

**Step 1: Generate 1Password API Token (Manual)**

In 1Password web vault (https://my.1password.com):
1. Navigate to **Settings → Developer → API Tokens**
2. Click **Create New Token**
3. Select **1Password Connect** service account
4. Copy the token (format: `ops_...`)
5. Securely store this token — it will be used in Step 3

**Step 2: Create directories and permissions**

On the main Docker host (`10.10.10.30`):
```bash
sudo mkdir -p /etc/op-connect
sudo mkdir -p /var/log/op-connect
sudo chown root:root /etc/op-connect /var/log/op-connect
sudo chmod 700 /etc/op-connect /var/log/op-connect
```

**Step 3: Store API token with restricted permissions**

Paste the token from Step 1:
```bash
echo "ops_YOUR_TOKEN_HERE" | sudo tee /etc/op-connect/token > /dev/null
sudo chmod 644 /etc/op-connect/token
```

Verify permissions are correct:
```bash
ls -la /etc/op-connect/token
# Expected output: -rw-r--r-- 1 root root 50 Jun  8 12:00 /etc/op-connect/token
```

**Step 4: Deploy Connect containers**

Copy `docker/op-connect/docker-compose.yml` from this repository to the Docker host:
```bash
scp docker/op-connect/docker-compose.yml root@10.10.10.30:/home/docker-host/op-connect/
```

Start the services:
```bash
cd /home/docker-host/op-connect
docker-compose up -d
```

Verify containers are running:
```bash
docker ps | grep op-connect
# Expected: op-connect-api and op-connect-sync running
```

**Step 5: Health check and API validation**

Wait for both services to become healthy (30-60 seconds):
```bash
docker-compose logs -f
# Expected: "Server running" or similar
```

Test the health endpoint:
```bash
curl -s http://10.10.10.30:8200/health | jq .
# Expected: {"status":"ok"} or {"status":"running"}
```

Test API authentication with the token:
```bash
export OP_CONNECT_TOKEN=$(sudo cat /etc/op-connect/token)
curl -s -H "Authorization: Bearer ${OP_CONNECT_TOKEN}" \
  http://10.10.10.30:8200/v1/vaults | jq .
# Expected: Empty array [] or list of vaults
```

**Step 6: Configure orchestrator access**

Once Connect is running, update `config/secrets.env` to reference the Connect server:
```env
OP_CONNECT_HOST=http://10.10.10.30:8200
OP_CONNECT_TOKEN=op://Homelab-GitOps/op-connect-token
```

Or, set environment variable before running orchestrator commands:
```bash
export OP_CONNECT_HOST=http://10.10.10.30:8200
export OP_CONNECT_TOKEN=$(sudo cat /etc/op-connect/token)
python3 manage.py config ubuntu-base 01
```

### Logging and Monitoring

Logs are written to `/var/log/op-connect/` on the Docker host. View them:
```bash
docker logs op-connect-api
docker logs op-connect-sync
```

For persistent troubleshooting, configure Docker to send logs to syslog:
```bash
docker logs op-connect-api | tail -50
```

### Token Rotation

To rotate the 1Password API token:

1. Generate a new token in 1Password web vault (Settings → Developer → API Tokens)

2. Update the token file securely (without exposing token in shell history):
   ```bash
   read -rs OP_TOKEN < <(cat <<'EOF'
   ops_NEW_TOKEN_HERE
   EOF
   )
   echo "$OP_TOKEN" | sudo tee /etc/op-connect/token > /dev/null
   unset OP_TOKEN
   ```
   
   Or interactively (recommended for security):
   ```bash
   read -rs -p "Enter new 1Password Connect API token: " OP_TOKEN
   echo "$OP_TOKEN" | sudo tee /etc/op-connect/token > /dev/null
   unset OP_TOKEN
   ```

3. Restart the containers:
   ```bash
   cd /home/docker-host/op-connect
   docker-compose restart op-connect-api op-connect-sync
   ```

4. Verify health:
   ```bash
   curl -s http://10.10.10.30:8200/health | jq .
   ```

5. **Revoke old token in 1Password**:
   - Go to 1Password web vault: https://my.1password.com/
   - Navigate to Settings → Developer → API Tokens
   - Find the old token ID in the list
   - Click "Revoke" next to the old token
   - Verify the new token is marked as "Active"
   - Note: Old token will become invalid immediately after revocation

### Troubleshooting

**Connection Refused (10.10.10.30:8200)**
- Verify docker-compose is running: `docker-compose ps`
- Check firewall: `sudo ufw status` or `sudo firewall-cmd --list-all`
- Verify network: `docker network ls` and `docker inspect op-connect_op-connect`

**Authentication Failed (Bearer token)**
- Verify token format: `cat /etc/op-connect/token` should start with `ops_`
- Check token has correct permissions in 1Password (must be "1Password Connect" service account)
- Ensure token file is readable: `sudo cat /etc/op-connect/token`

**Permission Denied or "Cannot read token"**
- **Error:** Container exits immediately or logs show permission denied
- **Check token file permissions:**
  ```bash
  ls -la /etc/op-connect/token
  # Expected: -rw-r--r-- 1 root root (644 permissions, not 600)
  ```
- **Important:** Containers run as `opuser` (UID 9999), which requires read permissions
- **Fix:**
  ```bash
  sudo chmod 644 /etc/op-connect/token
  docker-compose restart op-connect-api op-connect-sync
  ```
- **Verify:** `docker logs op-connect-api` and `docker logs op-connect-sync` should show no permission errors

**Sync container unhealthy**
- Verify 1Password connectivity: `docker logs op-connect-sync | grep -i "error\|fail"`
- Check token validity: validate in 1Password web vault
- Restart sync container: `docker-compose restart op-connect-sync`

**Persistent storage issues**
- Verify volume exists: `docker volume ls | grep op-connect`
- Check disk space: `df -h /var/lib/docker/volumes/`
- Recreate volume if needed: `docker volume rm op-connect_op-connect-data && docker-compose up -d`
