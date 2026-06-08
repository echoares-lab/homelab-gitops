# Observability Architecture Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement Grafana Alloy agent role and Docker TLS metrics exposure to enable centralized observability across all nodes.

**Architecture:** Two independent Ansible roles — `alloy` (agent deployment) and `docker_metrics` (TLS + metrics exposure) — with integration into existing `site.yml` and metadata. TLS certs distributed from OPNsense CA via Ansible. All non-runner nodes get Alloy by default.

**Tech Stack:** Grafana Alloy, Ansible, OpenTofu profiles, OPNsense CA certificates, Prometheus/Loki remote endpoints

---

## File Structure

### New Roles
```
ansible/roles/alloy/
├── tasks/main.yml              # Install Alloy, deploy config, start service
├── defaults/main.yml           # Default vars (Prometheus URL, scrape interval, etc.)
├── handlers/main.yml           # Handler to restart Alloy service
├── templates/alloy-config.river  # Alloy config (Prometheus + Loki targets)
└── meta/main.yml               # Role metadata (dependencies)

ansible/roles/docker_metrics/
├── tasks/main.yml              # Distribute TLS certs, update Docker daemon config
├── defaults/main.yml           # Default vars (TLS port, cert path, etc.)
├── handlers/main.yml           # Handler to restart Docker daemon
├── files/                       # TLS certificates (ca.crt, server.crt, server.key)
│   ├── ca.crt                  # CA public cert
│   ├── server.crt              # Server cert
│   └── server.key              # Server key (sensitive)
└── meta/main.yml               # Role metadata
```

### Modified Files
```
ansible/site.yml                # Add 2 plays for alloy and docker_metrics
config/metadata.yml             # Add alloy tag and role descriptions
```

### Tests (Unit)
```
tests/test_alloy_role.py        # Test Alloy role logic (config generation, vars)
tests/test_docker_metrics_role.py  # Test Docker metrics role logic (cert handling)
```

---

## Task Breakdown

### Task 1: Create Alloy Role Structure

**Files:**
- Create: `ansible/roles/alloy/tasks/main.yml`
- Create: `ansible/roles/alloy/defaults/main.yml`
- Create: `ansible/roles/alloy/handlers/main.yml`
- Create: `ansible/roles/alloy/templates/alloy-config.river`
- Create: `ansible/roles/alloy/meta/main.yml`

- [ ] **Step 1: Create Alloy role directory structure**

```bash
mkdir -p ansible/roles/alloy/{tasks,defaults,handlers,templates}
touch ansible/roles/alloy/meta/main.yml
```

- [ ] **Step 2: Write role metadata**

Create `ansible/roles/alloy/meta/main.yml`:
```yaml
---
galaxy_info:
  author: HomeLabGitOps
  description: Deploy Grafana Alloy monitoring agent
  license: MIT
  platforms:
    - name: Ubuntu
      versions:
        - "24.04"
        - "26.04"
    - name: VMware Photon OS
      versions:
        - "5.0"

dependencies: []
```

- [ ] **Step 3: Write default variables**

Create `ansible/roles/alloy/defaults/main.yml`:
```yaml
---
alloy_version: "latest"
alloy_user: "alloy"
alloy_group: "alloy"
alloy_home: "/etc/alloy"
alloy_config_dir: "/etc/alloy"
alloy_config_file: "/etc/alloy/config.river"
alloy_log_level: "info"

alloy_central_prometheus_url: "http://10.10.10.30:9090"
alloy_central_loki_url: "http://10.10.10.30:3100"

alloy_scrape_interval: "15s"
alloy_evaluation_interval: "15s"

alloy_enable_docker_metrics: "{{ 'tag_docker' in group_names }}"
alloy_docker_socket_path: "/var/run/docker.sock"

alloy_extra_scrape_targets: []
alloy_extra_log_paths: []

skip_alloy: false
```

- [ ] **Step 4: Write Alloy config template**

Create `ansible/roles/alloy/templates/alloy-config.river`:
```
// Prometheus scrape configs
prometheus.scrape "node" {
  targets = [
    {"__address__" = "localhost:9100"},
  ]
  scrape_interval = "{{ alloy_scrape_interval }}"
  scrape_timeout  = "10s"

  forward_to = [prometheus.remote_write.default.receiver]
}

{% if alloy_enable_docker_metrics %}
prometheus.scrape "docker" {
  targets = [
    {"__address__" = "localhost:2375"},
  ]
  scrape_interval = "{{ alloy_scrape_interval }}"
  scrape_timeout  = "10s"

  forward_to = [prometheus.remote_write.default.receiver]
}
{% endif %}

prometheus.remote_write "default" {
  endpoint {
    url = "{{ alloy_central_prometheus_url }}/api/v1/write"
  }
}

// Loki log targets
loki.source.syslog "default" {
  listen_address = "0.0.0.0:1514"
  forward_to     = [loki.write.default.receiver]
}

loki.source.file "varlog" {
  targets    = [
    {__path__ = "/var/log/*.log", job = "varlog"},
  ]
  forward_to = [loki.write.default.receiver]
}

{% if alloy_enable_docker_metrics %}
loki.source.docker "containers" {
  host             = "unix://{{ alloy_docker_socket_path }}"
  targets          = []
  forward_to       = [loki.write.default.receiver]
  relabel_rules    = discovery.relabel.docker.rules
}
{% endif %}

loki.write "default" {
  clients = [{
    url = "{{ alloy_central_loki_url }}/loki/api/v1/push"
  }]
}
```

- [ ] **Step 5: Write handlers**

Create `ansible/roles/alloy/handlers/main.yml`:
```yaml
---
- name: Restart Alloy service
  ansible.builtin.systemd:
    name: alloy
    state: restarted
    daemon_reload: true
```

- [ ] **Step 6: Write tasks/main.yml (stub)**

Create `ansible/roles/alloy/tasks/main.yml`:
```yaml
---
- name: Check if Alloy should be skipped
  ansible.builtin.set_fact:
    skip_alloy: true
  when: skip_alloy | bool

- name: Skip Alloy installation
  ansible.builtin.debug:
    msg: "Alloy monitoring disabled for this node"
  when: skip_alloy | bool

- name: Install Alloy
  block:
    - name: Add Alloy package repository (Ubuntu)
      ansible.builtin.apt_key:
        url: https://apt.grafana.com/gpg.key
        state: present
      when: ansible_facts['distribution'] == 'Ubuntu'

    - name: Add Alloy APT repository (Ubuntu)
      ansible.builtin.apt_repository:
        repo: "deb https://apt.grafana.com stable main"
        state: present
      when: ansible_facts['distribution'] == 'Ubuntu'

    - name: Install Alloy package (Ubuntu)
      ansible.builtin.apt:
        name: alloy
        state: present
        update_cache: true
      when: ansible_facts['distribution'] == 'Ubuntu'

    - name: Install Alloy (Photon)
      ansible.builtin.command: tdnf install -y alloy
      register: photon_alloy_install
      changed_when: "'Nothing to do' not in photon_alloy_install.stdout"
      when: ansible_facts['distribution'] == 'VMware Photon OS'

    - name: Deploy Alloy config
      ansible.builtin.template:
        src: alloy-config.river
        dest: "{{ alloy_config_file }}"
        owner: "{{ alloy_user }}"
        group: "{{ alloy_group }}"
        mode: "0644"
      notify: Restart Alloy service

    - name: Enable and start Alloy service
      ansible.builtin.systemd:
        name: alloy
        enabled: true
        state: started

  when: not skip_alloy | bool
```

- [ ] **Step 7: Commit**

```bash
git add ansible/roles/alloy/
git commit -m "feat: add alloy monitoring agent role

Add Grafana Alloy role for metrics and logs collection. Includes:
- Prometheus scrape config with node and Docker targets
- Loki log forwarding config
- Support for Ubuntu and Photon OS
- Configurable central Prometheus/Loki endpoints
- Skip capability for opt-out profiles

Co-Authored-By: Claude Haiku 4.5 <noreply@anthropic.com>"
```

---

### Task 2: Create Docker Metrics Role Structure

**Files:**
- Create: `ansible/roles/docker_metrics/tasks/main.yml`
- Create: `ansible/roles/docker_metrics/defaults/main.yml`
- Create: `ansible/roles/docker_metrics/handlers/main.yml`
- Create: `ansible/roles/docker_metrics/files/{ca,server.crt,server.key}`
- Create: `ansible/roles/docker_metrics/meta/main.yml`

- [ ] **Step 1: Create Docker metrics role directory structure**

```bash
mkdir -p ansible/roles/docker_metrics/{tasks,defaults,handlers,files}
touch ansible/roles/docker_metrics/meta/main.yml
```

- [ ] **Step 2: Write role metadata**

Create `ansible/roles/docker_metrics/meta/main.yml`:
```yaml
---
galaxy_info:
  author: HomeLabGitOps
  description: Configure Docker daemon for TLS and metrics exposure
  license: MIT
  platforms:
    - name: Ubuntu
      versions:
        - "24.04"
        - "26.04"
    - name: VMware Photon OS
      versions:
        - "5.0"

dependencies:
  - role: docker
```

- [ ] **Step 3: Write default variables**

Create `ansible/roles/docker_metrics/defaults/main.yml`:
```yaml
---
docker_metrics_enabled: true
docker_tls_port: 2376
docker_cert_path: /etc/docker/certs.d
docker_daemon_config_file: /etc/docker/daemon.json
```

- [ ] **Step 4: Create placeholder TLS cert files**

Create `ansible/roles/docker_metrics/files/ca.crt`:
```
-----BEGIN CERTIFICATE-----
PLACEHOLDER_CA_CERT_CONTENT_FROM_OPNSENSE
-----END CERTIFICATE-----
```

Create `ansible/roles/docker_metrics/files/server.crt`:
```
-----BEGIN CERTIFICATE-----
PLACEHOLDER_SERVER_CERT_CONTENT_FROM_OPNSENSE
-----END CERTIFICATE-----
```

Create `ansible/roles/docker_metrics/files/server.key`:
```
-----BEGIN PRIVATE KEY-----
PLACEHOLDER_SERVER_KEY_CONTENT_FROM_OPNSENSE
-----END PRIVATE KEY-----
```

- [ ] **Step 5: Write handlers**

Create `ansible/roles/docker_metrics/handlers/main.yml`:
```yaml
---
- name: Restart Docker daemon
  ansible.builtin.systemd:
    name: docker
    state: restarted
    daemon_reload: true
```

- [ ] **Step 6: Write tasks/main.yml**

Create `ansible/roles/docker_metrics/tasks/main.yml`:
```yaml
---
- name: Create Docker certs directory
  ansible.builtin.file:
    path: "{{ docker_cert_path }}"
    state: directory
    mode: "0700"

- name: Distribute CA certificate
  ansible.builtin.copy:
    src: ca.crt
    dest: "{{ docker_cert_path }}/ca.crt"
    owner: root
    group: root
    mode: "0644"
  notify: Restart Docker daemon

- name: Distribute server certificate
  ansible.builtin.copy:
    src: server.crt
    dest: "{{ docker_cert_path }}/server.crt"
    owner: root
    group: root
    mode: "0644"
  notify: Restart Docker daemon

- name: Distribute server key
  ansible.builtin.copy:
    src: server.key
    dest: "{{ docker_cert_path }}/server.key"
    owner: root
    group: root
    mode: "0600"
  notify: Restart Docker daemon

- name: Read current Docker daemon config
  ansible.builtin.slurp:
    src: "{{ docker_daemon_config_file }}"
  register: docker_config_b64
  ignore_errors: true

- name: Parse Docker daemon config
  ansible.builtin.set_fact:
    docker_config: "{{ (docker_config_b64.content | b64decode | from_json) if docker_config_b64.stat is defined else {} }}"

- name: Update Docker daemon config for TLS and metrics
  ansible.builtin.copy:
    content: |
      {
        "tlscert": "{{ docker_cert_path }}/server.crt",
        "tlskey": "{{ docker_cert_path }}/server.key",
        "tlscacert": "{{ docker_cert_path }}/ca.crt",
        "tls": true,
        "hosts": [
          "unix:///var/run/docker.sock",
          "tcp://0.0.0.0:{{ docker_tls_port }}"
        ],
        "metrics-addr": "0.0.0.0:9323",
        "experimental": true
      }
    dest: "{{ docker_daemon_config_file }}"
    owner: root
    group: root
    mode: "0644"
  notify: Restart Docker daemon
  when: docker_metrics_enabled | bool
```

- [ ] **Step 7: Commit**

```bash
git add ansible/roles/docker_metrics/
git commit -m "feat: add docker_metrics role for TLS and metrics exposure

Configure Docker daemon with TLS socket on port 2376 and metrics endpoint.
Distribute OPNsense CA certificates for secure remote access via dockerhand
and uptime-kuma.

Note: TLS cert files are placeholders. Replace with actual certs from OPNsense CA
before running playbooks.

Co-Authored-By: Claude Haiku 4.5 <noreply@anthropic.com>"
```

---

### Task 3: Update site.yml with New Plays

**Files:**
- Modify: `ansible/site.yml`

- [ ] **Step 1: Add Alloy play to site.yml**

Read the current `site.yml` to understand structure, then add this play after the fact-gathering play and before the existing Ubuntu/Photon plays:

```yaml
- name: Deploy monitoring agents
  hosts: tag_alloy
  become: true
  roles:
    - alloy
```

Insert after line 4 (after `serial: 0`).

- [ ] **Step 2: Add Docker metrics play to site.yml**

Add this play after the `tag_docker` play (or create if not present):

```yaml
- name: Configure Docker nodes with metrics and TLS
  hosts: tag_docker
  become: true
  roles:
    - docker
    - docker_metrics
```

If a `tag_docker` play already exists that applies the `docker` role, replace it with the above. If not, add this as a new play.

- [ ] **Step 3: Verify site.yml syntax**

```bash
ansible-playbook ansible/site.yml --syntax-check
```

Expected: No errors.

- [ ] **Step 4: Commit**

```bash
git add ansible/site.yml
git commit -m "feat: add observability plays to site.yml

Add plays for:
- tag_alloy: Deploy Grafana Alloy agent
- tag_docker: Docker daemon with metrics and TLS (via docker_metrics role)

Co-Authored-By: Claude Haiku 4.5 <noreply@anthropic.com>"
```

---

### Task 4: Update config/metadata.yml

**Files:**
- Modify: `config/metadata.yml`

- [ ] **Step 1: Add alloy tag to metadata**

In `config/metadata.yml`, under the `tags:` section, add:

```yaml
  alloy: "Deploy Grafana Alloy monitoring agent (metrics + logs)."
```

- [ ] **Step 2: Add docker_metrics role to metadata**

Under the `roles:` section, add:

```yaml
  docker_metrics: "Configure Docker daemon for TLS socket and metrics exposure."
```

- [ ] **Step 3: Verify YAML syntax**

```bash
yamllint config/metadata.yml
```

Expected: No errors.

- [ ] **Step 4: Commit**

```bash
git add config/metadata.yml
git commit -m "docs: add alloy and docker_metrics to metadata

Add tag and role descriptions for observability setup in metadata.yml
for use in interactive CLI prompts.

Co-Authored-By: Claude Haiku 4.5 <noreply@anthropic.com>"
```

---

### Task 5: Write Unit Tests for Alloy Role

**Files:**
- Create: `tests/test_alloy_role.py`

- [ ] **Step 1: Write test file with imports and fixtures**

Create `tests/test_alloy_role.py`:
```python
import pytest
import yaml
from pathlib import Path


@pytest.fixture
def alloy_defaults():
    """Load Alloy role defaults."""
    defaults_file = Path("ansible/roles/alloy/defaults/main.yml")
    with open(defaults_file) as f:
        return yaml.safe_load(f)


@pytest.fixture
def alloy_config_template():
    """Load Alloy config template."""
    template_file = Path("ansible/roles/alloy/templates/alloy-config.river")
    with open(template_file) as f:
        return f.read()


def test_alloy_defaults_has_prometheus_url(alloy_defaults):
    """Alloy defaults should specify central Prometheus URL."""
    assert "alloy_central_prometheus_url" in alloy_defaults
    assert alloy_defaults["alloy_central_prometheus_url"] == "http://10.10.10.30:9090"


def test_alloy_defaults_has_loki_url(alloy_defaults):
    """Alloy defaults should specify central Loki URL."""
    assert "alloy_central_loki_url" in alloy_defaults
    assert alloy_defaults["alloy_central_loki_url"] == "http://10.10.10.30:3100"


def test_alloy_defaults_has_scrape_interval(alloy_defaults):
    """Alloy defaults should specify scrape interval."""
    assert "alloy_scrape_interval" in alloy_defaults
    assert alloy_defaults["alloy_scrape_interval"] == "15s"


def test_alloy_defaults_skip_alloy_flag(alloy_defaults):
    """Alloy defaults should have skip_alloy flag for opt-out."""
    assert "skip_alloy" in alloy_defaults
    assert alloy_defaults["skip_alloy"] is False


def test_alloy_config_has_prometheus_scrape(alloy_config_template):
    """Alloy config template should include Prometheus scrape config."""
    assert "prometheus.scrape" in alloy_config_template
    assert "prometheus.remote_write" in alloy_config_template


def test_alloy_config_has_loki_write(alloy_config_template):
    """Alloy config template should include Loki write config."""
    assert "loki.write" in alloy_config_template


def test_alloy_config_conditional_docker_metrics(alloy_config_template):
    """Alloy config should conditionally include Docker metrics when enabled."""
    assert "alloy_enable_docker_metrics" in alloy_config_template
    assert "prometheus.scrape \"docker\"" in alloy_config_template


def test_alloy_tasks_has_main_file():
    """Alloy role tasks/main.yml should exist."""
    tasks_file = Path("ansible/roles/alloy/tasks/main.yml")
    assert tasks_file.exists()


def test_alloy_handlers_has_restart():
    """Alloy handlers should include restart Alloy service handler."""
    handlers_file = Path("ansible/roles/alloy/handlers/main.yml")
    with open(handlers_file) as f:
        handlers = yaml.safe_load(f)
    
    handler_names = [h.get("name") for h in handlers]
    assert "Restart Alloy service" in handler_names
```

- [ ] **Step 2: Run tests to verify they pass**

```bash
pytest tests/test_alloy_role.py -v
```

Expected: All tests pass.

- [ ] **Step 3: Commit**

```bash
git add tests/test_alloy_role.py
git commit -m "test: add unit tests for alloy role

Test Alloy role defaults, config template, and file existence.
Verify Prometheus/Loki URLs, scrape intervals, and skip capability.

Co-Authored-By: Claude Haiku 4.5 <noreply@anthropic.com>"
```

---

### Task 6: Write Unit Tests for Docker Metrics Role

**Files:**
- Create: `tests/test_docker_metrics_role.py`

- [ ] **Step 1: Write test file**

Create `tests/test_docker_metrics_role.py`:
```python
import pytest
import yaml
import json
from pathlib import Path


@pytest.fixture
def docker_metrics_defaults():
    """Load Docker metrics role defaults."""
    defaults_file = Path("ansible/roles/docker_metrics/defaults/main.yml")
    with open(defaults_file) as f:
        return yaml.safe_load(f)


@pytest.fixture
def docker_metrics_certs():
    """Check that TLS cert files exist."""
    cert_files = [
        Path("ansible/roles/docker_metrics/files/ca.crt"),
        Path("ansible/roles/docker_metrics/files/server.crt"),
        Path("ansible/roles/docker_metrics/files/server.key"),
    ]
    return cert_files


def test_docker_metrics_defaults_enabled(docker_metrics_defaults):
    """Docker metrics should be enabled by default."""
    assert "docker_metrics_enabled" in docker_metrics_defaults
    assert docker_metrics_defaults["docker_metrics_enabled"] is True


def test_docker_metrics_tls_port(docker_metrics_defaults):
    """Docker metrics should specify TLS port."""
    assert "docker_tls_port" in docker_metrics_defaults
    assert docker_metrics_defaults["docker_tls_port"] == 2376


def test_docker_metrics_cert_path(docker_metrics_defaults):
    """Docker metrics should specify cert directory path."""
    assert "docker_cert_path" in docker_metrics_defaults
    assert docker_metrics_defaults["docker_cert_path"] == "/etc/docker/certs.d"


def test_docker_metrics_tasks_exist():
    """Docker metrics role tasks/main.yml should exist."""
    tasks_file = Path("ansible/roles/docker_metrics/tasks/main.yml")
    assert tasks_file.exists()


def test_docker_metrics_tasks_create_cert_dir():
    """Docker metrics tasks should create cert directory."""
    tasks_file = Path("ansible/roles/docker_metrics/tasks/main.yml")
    with open(tasks_file) as f:
        tasks = yaml.safe_load(f)
    
    task_names = [t.get("name") for t in tasks if isinstance(t, dict)]
    assert "Create Docker certs directory" in task_names


def test_docker_metrics_tasks_distribute_certs():
    """Docker metrics tasks should distribute TLS certificates."""
    tasks_file = Path("ansible/roles/docker_metrics/tasks/main.yml")
    with open(tasks_file) as f:
        tasks = yaml.safe_load(f)
    
    task_names = [t.get("name") for t in tasks if isinstance(t, dict)]
    assert "Distribute CA certificate" in task_names
    assert "Distribute server certificate" in task_names
    assert "Distribute server key" in task_names


def test_docker_metrics_tasks_update_daemon_config():
    """Docker metrics tasks should update Docker daemon config."""
    tasks_file = Path("ansible/roles/docker_metrics/tasks/main.yml")
    with open(tasks_file) as f:
        tasks = yaml.safe_load(f)
    
    task_names = [t.get("name") for t in tasks if isinstance(t, dict)]
    assert "Update Docker daemon config for TLS and metrics" in task_names


def test_docker_metrics_handlers_restart():
    """Docker metrics handlers should include restart Docker daemon."""
    handlers_file = Path("ansible/roles/docker_metrics/handlers/main.yml")
    with open(handlers_file) as f:
        handlers = yaml.safe_load(f)
    
    handler_names = [h.get("name") for h in handlers]
    assert "Restart Docker daemon" in handler_names


def test_docker_metrics_cert_files_exist(docker_metrics_certs):
    """TLS certificate files should exist (as placeholders)."""
    for cert_file in docker_metrics_certs:
        assert cert_file.exists(), f"Certificate file {cert_file} not found"


def test_docker_metrics_cert_files_have_content(docker_metrics_certs):
    """TLS certificate files should have placeholder content."""
    for cert_file in docker_metrics_certs:
        with open(cert_file) as f:
            content = f.read()
        assert len(content) > 0, f"Certificate file {cert_file} is empty"
        assert "PLACEHOLDER" in content, f"Certificate file {cert_file} should contain PLACEHOLDER"
```

- [ ] **Step 2: Run tests to verify they pass**

```bash
pytest tests/test_docker_metrics_role.py -v
```

Expected: All tests pass.

- [ ] **Step 3: Commit**

```bash
git add tests/test_docker_metrics_role.py
git commit -m "test: add unit tests for docker_metrics role

Test Docker metrics role defaults, tasks, handlers, and TLS cert files.
Verify cert directory creation, certificate distribution, and daemon config
updates.

Co-Authored-By: Claude Haiku 4.5 <noreply@anthropic.com>"
```

---

### Task 7: Integration Test - Verify site.yml Applies Roles Correctly

**Files:**
- Modify: `tests/test_manage.py` (or create integration test)

- [ ] **Step 1: Verify site.yml plays target correct hosts**

```bash
ansible-playbook ansible/site.yml --list-tasks | grep -E "alloy|docker_metrics"
```

Expected output should show:
```
Deploy monitoring agents
Configure Docker nodes with metrics and TLS
```

- [ ] **Step 2: Validate playbook against test profile**

Create a test profile to verify Alloy is included:

```bash
cat > /tmp/test-alloy-profile.yml << 'EOF'
name: test-alloy-node
tags:
  - ubuntu
  - alloy
EOF
```

Verify the profile would trigger Alloy role by checking metadata:

```bash
grep -A 5 "tag_alloy" config/metadata.yml
```

Expected: Tag definition shows Alloy will be applied.

- [ ] **Step 3: Verify GitHub runner profile skips Alloy**

Check that runners do NOT have `tag_alloy`:

```bash
grep -r "tag_alloy" config/profiles/ || echo "No runner profiles with tag_alloy found (correct)"
```

Expected: No runner profiles should have the Alloy tag.

- [ ] **Step 4: Commit**

```bash
git add tests/
git commit -m "test: verify site.yml integration with alloy and docker_metrics

Validate that site.yml correctly targets alloy and docker_metrics roles
to appropriate hosts via tags. Confirm runners opt-out of monitoring.

Co-Authored-By: Claude Haiku 4.5 <noreply@anthropic.com>"
```

---

### Task 8: Documentation - Update RUNBOOK.md

**Files:**
- Modify: `docs/RUNBOOK.md`

- [ ] **Step 1: Add Observability section to RUNBOOK**

At the end of `docs/RUNBOOK.md`, add:

```markdown
## Observability Setup

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
```

- [ ] **Step 2: Commit**

```bash
git add docs/RUNBOOK.md
git commit -m "docs: add observability setup section to RUNBOOK

Document Alloy agent setup, Docker TLS/metrics configuration, and
instructions for OPNsense cert distribution and renewal.

Co-Authored-By: Claude Haiku 4.5 <noreply@anthropic.com>"
```

---

### Task 9: Documentation - Create TLS Certificate Instructions

**Files:**
- Create: `docs/OBSERVABILITY_TLS_SETUP.md`

- [ ] **Step 1: Write TLS cert setup guide**

Create `docs/OBSERVABILITY_TLS_SETUP.md`:

```markdown
# Observability TLS Certificate Setup

This guide covers how to generate and distribute TLS certificates for Docker daemon TLS sockets used by dockerhand and uptime-kuma.

## Prerequisites

- OPNsense router with CA configured
- Access to OPNsense WebUI or API
- Ansible control node with access to playbooks

## Step 1: Generate Certificates on OPNsense

### Via OPNsense WebUI:

1. Go to **System > Trust > Certificates**
2. Click **Add** to create a new certificate
3. Fill in:
   - **Name:** `docker-web-01` (node name)
   - **Type:** Server Certificate
   - **CA:** Select your internal CA
   - **Common Name:** `docker-web-01.mgmt.plexplease.com` (node FQDN)
4. Save
5. Export as PEM:
   - Certificate (`.crt`)
   - Key (`.key`) — keep private!
   - CA cert (if not already have)

### Naming Convention:

- `ca.crt` — CA public certificate (same for all nodes)
- `server.crt` — Node-specific server certificate
- `server.key` — Node-specific server key (sensitive)

## Step 2: Distribute Certificates via Ansible

1. Place certificates in role files:
   ```bash
   cp opnsense/ca.crt ansible/roles/docker_metrics/files/
   cp opnsense/docker-web-01.crt ansible/roles/docker_metrics/files/server.crt
   cp opnsense/docker-web-01.key ansible/roles/docker_metrics/files/server.key
   ```

2. Run site.yml to apply docker_metrics role:
   ```bash
   python3 manage.py config PROFILE INDEX
   ```

3. Verify on node:
   ```bash
   ssh user@docker-web-01 ls -la /etc/docker/certs.d/
   # Should show: ca.crt, server.crt, server.key
   ```

## Step 3: Test TLS Connection

From 10.10.10.30 or any node with Docker client:

```bash
docker -H tcp://docker-web-01.mgmt.plexplease.com:2376 \
  --tlscacert=/etc/docker/certs.d/ca.crt \
  --tlscert=/etc/docker/certs.d/client.crt \
  --tlskey=/etc/docker/certs.d/client.key \
  ps
```

Expected: List of running containers on docker-web-01.

## Certificate Renewal

1. OPNsense: Re-issue certificate (extend validity or regenerate)
2. Export new cert/key
3. Update `ansible/roles/docker_metrics/files/{server.crt,server.key}`
4. Run site.yml to distribute
5. Docker daemon auto-reloads on config change

## Troubleshooting

**Connection refused:**
- Check Docker daemon is running: `systemctl status docker`
- Check TLS port is listening: `netstat -tuln | grep 2376`

**Certificate verification failed:**
- Verify CA cert matches: Compare fingerprints between node and central
- Check cert expiry: `openssl x509 -in server.crt -noout -dates`

**Alloy can't scrape Docker metrics:**
- Verify `/var/run/docker.sock` exists: `ls -la /var/run/docker.sock`
- Check Alloy logs: `journalctl -u alloy -f`
```

- [ ] **Step 2: Commit**

```bash
git add docs/OBSERVABILITY_TLS_SETUP.md
git commit -m "docs: add TLS certificate setup guide for Docker observability

Document OPNsense CA cert generation, Ansible distribution, testing,
and renewal procedures for docker_metrics role.

Co-Authored-By: Claude Haiku 4.5 <noreply@anthropic.com>"
```

---

### Task 10: Final Validation & Matrix Test

**Files:**
- Run existing: `scripts/matrix_test.py`

- [ ] **Step 1: Run linting on new roles**

```bash
ansible-lint ansible/roles/alloy/ ansible/roles/docker_metrics/
```

Expected: No errors (warnings are OK if advisory).

- [ ] **Step 2: Validate YAML syntax**

```bash
yamllint ansible/roles/alloy/ ansible/roles/docker_metrics/ config/metadata.yml
```

Expected: All YAML is valid.

- [ ] **Step 3: Run all existing tests to verify no regressions**

```bash
pytest tests/ -v
```

Expected: All tests pass (including new alloy and docker_metrics tests).

- [ ] **Step 4: Test site.yml syntax**

```bash
ansible-playbook ansible/site.yml --syntax-check
```

Expected: No syntax errors.

- [ ] **Step 5: Verify metadata consistency**

```bash
python3 scripts/lint_config.py
```

Expected: No validation errors.

- [ ] **Step 6: Commit validation results**

```bash
git add -A && git commit -m "test: validation pass for observability implementation

All linting, syntax checks, and tests pass:
- ansible-lint: OK
- yamllint: OK
- pytest: OK
- site.yml syntax: OK
- metadata validation: OK

Ready for integration testing.

Co-Authored-By: Claude Haiku 4.5 <noreply@anthropic.com>"
```

---

## Verification Checklist

- [ ] `ansible/roles/alloy/` exists with all subdirectories and files
- [ ] `ansible/roles/docker_metrics/` exists with all subdirectories and files
- [ ] `ansible/site.yml` includes plays for `tag_alloy` and `tag_docker`
- [ ] `config/metadata.yml` includes `alloy` tag and `docker_metrics` role
- [ ] All tests pass: `pytest tests/test_alloy_role.py tests/test_docker_metrics_role.py -v`
- [ ] No ansible-lint errors: `ansible-lint ansible/roles/alloy ansible/roles/docker_metrics`
- [ ] YAML valid: `yamllint ansible/roles/alloy ansible/roles/docker_metrics config/metadata.yml`
- [ ] Playbook syntax valid: `ansible-playbook ansible/site.yml --syntax-check`
- [ ] TLS cert placeholder files exist in `ansible/roles/docker_metrics/files/`
- [ ] Documentation added to `docs/RUNBOOK.md` and `docs/OBSERVABILITY_TLS_SETUP.md`
