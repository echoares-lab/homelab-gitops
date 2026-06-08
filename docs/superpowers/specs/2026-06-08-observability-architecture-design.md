---
title: Observability Architecture Design
date: 2026-06-08
status: draft
---

# Observability Architecture Design

## 1. System Overview

A three-tier observability system with **centralized collection and visualization**:

```
┌─────────────────────────────────────────────────────────────┐
│ Centralized Stack (10.10.10.30)                             │
│ ├─ Prometheus (metrics database)                            │
│ ├─ Loki (logs database)                                     │
│ ├─ Grafana (visualization & alerting)                       │
│ ├─ dockerhand (Docker management via TLS)                   │
│ ├─ uptime-kuma (synthetic monitoring via TLS)               │
│ └─ OPNsense CA certificates (issued)                        │
└─────────────────────────────────────────────────────────────┘
         ↑                    ↑
         │ metrics/logs       │ TLS requests
         │                    │
    ┌────┴────────────────────┴──────────────────┐
    │                                             │
[Node A]                                     [Node B]
├─ Alloy agent                              ├─ Alloy agent
│  ├─ Scrapes metrics                       │  ├─ Scrapes metrics
│  ├─ Collects logs                         │  ├─ Collects logs
│  └─ Pushes to 10.10.10.30                 │  └─ Pushes to 10.10.10.30
├─ Docker daemon                            ├─ Docker daemon
│  ├─ TLS socket (cert from OPNsense)       │  ├─ TLS socket (cert from OPNsense)
│  └─ Metrics exposed locally               │  └─ Metrics exposed locally
└────────────────────────────────────────────────────────────┘
```

## 2. Roles & Responsibilities

### `alloy` Role (New)

**Purpose:** Deploy Grafana Alloy agent on monitored nodes.

**Applies to:** All profiles by default except GitHub runners (opt-out via `skip_alloy: true` in profile)

**Responsibilities:**
- Install Grafana Alloy from official repos
- Configure Alloy to scrape:
  - Host metrics (CPU, memory, disk, network, systemd state)
  - Container metrics (if Docker present — cAdvisor-style via Docker socket)
  - Application logs (systemd journal, /var/log/*, custom paths)
  - Service-specific metrics (DNS, custom exporters, etc.)
- Push metrics to Prometheus on 10.10.10.30:9090
- Push logs to Loki on 10.10.10.30:3100
- Handle failures gracefully (backoff, retry, no blocking on upstream)

**Configuration Defaults** (`alloy/defaults/main.yml`):
```yaml
alloy_central_prometheus_url: "http://10.10.10.30:9090"
alloy_central_loki_url: "http://10.10.10.30:3100"
alloy_scrape_interval: "15s"
alloy_extra_scrape_targets: []  # Profiles can extend
```

Profiles can override or extend via vars if needed.

### `docker_metrics` Role (New)

**Purpose:** Configure Docker daemon for secure remote access and metrics exposure.

**Applies to:** Nodes tagged `tag_docker` (runs after `docker` role)

**Responsibilities:**
- Retrieve/distribute OPNsense CA-issued TLS certificate for this node's Docker daemon
- Configure Docker daemon to:
  - Expose metrics endpoint (via `-metrics-addr` flag or equivalent)
  - Bind TLS socket at a known port (e.g., 2376)
  - Load certificate and key from Ansible-distributed files
- Ensure Alloy can access Docker socket locally (no TLS, `/var/run/docker.sock`)
- Ensure dockerhand and uptime-kuma can access Docker daemon remotely via TLS

**Configuration** (`docker_metrics/defaults/main.yml`):
```yaml
docker_metrics_enabled: true
docker_tls_port: 2376
docker_cert_path: /etc/docker/certs.d
```

**Certificate Flow:**
- Pre-requisite: OPNsense CA has already issued certs for each node (manual or scripted)
- Ansible copies `ca.crt`, `server.crt`, `server.key` from `files/` or fetches from OPNsense
- Docker daemon loads them at startup
- Alloy accesses Docker locally via socket (no TLS)

### Central Tools (Not Roles)

These run on 10.10.10.30 and are managed outside this pipeline (assumed to exist):

- **Prometheus** — scrapes metrics from Alloy agents
- **Loki** — receives logs from Alloy agents
- **Grafana** — visualizes Prometheus + Loki data
- **dockerhand** — Connects to remote Docker daemons via TLS to manage containers
- **uptime-kuma** — Probes endpoints/services via TLS for availability alerting

## 3. Application via Tags & Metadata

### New Tags in `config/metadata.yml`

```yaml
tags:
  alloy: "Deploy Grafana Alloy monitoring agent (metrics + logs)."
  # (existing tags remain unchanged)

roles:
  alloy: "Grafana Alloy agent for metrics and logs collection."
  docker_metrics: "Configure Docker daemon for TLS and metrics exposure."
  # (existing roles remain)
```

### Updated `ansible/site.yml`

```yaml
- name: Deploy monitoring agents
  hosts: tag_alloy
  become: true
  roles:
    - alloy

- name: Configure Docker with metrics and TLS
  hosts: tag_docker
  become: true
  roles:
    - docker
    - docker_metrics
```

### Profile Examples

**Docker host (observability enabled):**
```yaml
name: docker-web-01
tags:
  - ubuntu
  - docker
  - alloy          # Included, so Alloy runs
```

**GitHub runner (observability disabled):**
```yaml
name: github-runner-01
tags:
  - ubuntu
  - github_runner
# No `alloy` tag → Alloy won't run
```

**DNS server (observability enabled):**
```yaml
name: dns-primary
tags:
  - ubuntu
  - dns
  - alloy          # Monitoring enabled
```

## 4. TLS Certificate Strategy

### Generation (Manual Process, Pre-Automation)

1. OPNsense CA issues a certificate for each node (or shared wildcard cert)
   - Subject: `docker-web-01.mgmt.plexplease.com` (or internal FQDN)
   - Validity: 1+ year for simplicity
2. Certs stored in repository (encrypted via Ansible Vault/age) or OPNsense secrets

### Distribution (Ansible)

The `docker_metrics` role:
- Copies `ca.crt` (CA public cert) → all nodes in `/etc/docker/certs.d/ca.crt`
- Copies node-specific `server.crt` → `/etc/docker/certs.d/server.crt`
- Copies node-specific `server.key` → `/etc/docker/certs.d/server.key` (sensitive, permissions 0600)

### Central Usage

- **dockerhand** loads `ca.crt` to verify Docker daemon certs
- **uptime-kuma** same approach
- Both configured with node FQDNs and TLS port (2376)

### Renewal

- If cert expires, OPNsense reissues → Ansible re-runs `docker_metrics` to distribute
- No downtime if automated (Docker reloads certs on config change)

## 5. Data & Metric Flow

### Alloy → Central (Push)

```
Node (Alloy) ──prometheus_sd──> 10.10.10.30:9090 (Prometheus)
Node (Alloy) ──loki_log_push──> 10.10.10.30:3100 (Loki)
```

### Central → Remote Docker (Pull via TLS)

```
10.10.10.30 (dockerhand) ──docker_api_tls──> Node:2376 (Docker daemon)
10.10.10.30 (uptime-kuma) ──tcp_check_tls──> Node:2376 (Docker daemon)
```

### Alloy → Local Docker (No TLS)

```
Node (Alloy) ──docker_socket──> /var/run/docker.sock (local, no TLS)
```

## 6. Integration with Existing Pipeline

### No Changes to

- `manage.py` orchestrator
- Existing roles (`base`, `security`, `docker`, etc.)
- Packer golden images
- OpenTofu provisioning

### Changes to

- `ansible/roles/` — add `alloy/` and `docker_metrics/` directories
- `ansible/site.yml` — add plays for new roles (2 new plays)
- `config/metadata.yml` — add new tags and role descriptions
- Profiles — include `tag_alloy` (or explicitly skip it for runners via `skip_alloy: true`)

### Certificate Storage Options

- **Option A (Recommended):** Commit encrypted certs to `ansible/roles/docker_metrics/files/` (via Ansible Vault or age)
- **Option B:** Fetch from OPNsense at runtime (requires OPNsense API access from control node)
- **Option C:** Manual SCP before running playbooks (simple for homelab, not automated)

## 7. What Gets Monitored (Out of Box)

### Host Metrics (Alloy)

- CPU, memory, disk usage, network I/O
- System load, uptime
- Process state (systemd unit health)

### Container Metrics (Alloy via Docker socket)

- Per-container CPU, memory, network I/O
- Container restart count
- Image/volume usage

### Logs (Alloy)

- Systemd journal (all units)
- Docker container logs (if Docker present)
- Application logs (configurable per role)

### Availability (uptime-kuma)

- TCP/HTTP probes to key services (DNS, Docker API, custom endpoints)
- Response time trends

### Management (dockerhand)

- Remote container start/stop/restart
- Image management
- Network inspection

## 8. Future Extensibility

Each profile can customize:
- Extra Alloy scrape targets (Prometheus exporters, custom services)
- Extra log paths
- Custom alerting rules (via Grafana)

Example (Docker host with custom app metrics):
```yaml
name: docker-app-01
tags:
  - ubuntu
  - docker
  - alloy
alloy_extra_scrape_targets:
  - job_name: app_metrics
    static_configs:
      - targets: ['localhost:9999']
```

## 9. Implementation Phases

### Phase 1: Core Alloy Role
- Create `ansible/roles/alloy/` with base structure
- Configure agent to ship metrics/logs to 10.10.10.30
- Test with a single node (Docker host or DNS)
- Tag a profile with `tag_alloy` and validate

### Phase 2: Docker Metrics & TLS
- Create `ansible/roles/docker_metrics/` 
- Configure Docker daemon TLS socket
- Distribute OPNsense certs via Ansible
- Test dockerhand and uptime-kuma can connect

### Phase 3: Rollout & Integration
- Add `tag_alloy` to all production profiles (except runners)
- Update metadata.yml with new tags
- Update site.yml with new plays
- Document in RUNBOOK.md

### Phase 4: Validation
- Verify metrics flow to Prometheus
- Verify logs flow to Loki
- Test Grafana dashboards
- Test dockerhand and uptime-kuma connections

## 10. Success Criteria

- [ ] All non-runner nodes have Alloy agent running
- [ ] Metrics appear in Prometheus (via 10.10.10.30:9090)
- [ ] Logs appear in Loki (via 10.10.10.30:3100)
- [ ] Grafana dashboards display host/container metrics
- [ ] dockerhand can remotely manage Docker via TLS
- [ ] uptime-kuma can probe services via TLS
- [ ] Cert renewal is documented and tested
- [ ] Runners can opt-out of Alloy (skip_alloy: true)
