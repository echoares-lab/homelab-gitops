# Pipeline Operations Runbook

Detailed operational procedures for the unified GitOps pipeline managing high-performance Ubuntu and Photon OS environments.

## Table of Contents
1. [Prerequisites](#1-prerequisites)
2. [Command Reference (`manage.sh`)](#2-command-reference-managesh)
3. [Configuration System](#3-configuration-system)
4. [Deployment Workflow](#4-deployment-workflow)
5. [Automated Testing](#5-automated-testing)
6. [Troubleshooting](#6-troubleshooting)

---

## 1. Prerequisites
Ensure the orchestration host has the following:
*   **OpenTofu** (`>= 1.6`)
*   **Packer** (`>= 1.9`)
*   **Ansible** (`>= 2.14`) with `vSphere Automation SDK`
*   **Pytest & Testinfra**
*   **govc** (installed in `build/`)

---

## 2. Command Reference (`manage.sh`)

The `./manage.sh` orchestrator provides a unified interface for the entire lifecycle.

### `lint`
Validates the YAML profile schema and checks if all vCenter objects (Datacenter, Cluster, Host, Network) actually exist.
*   **Usage:** `./manage.sh lint <profile> [id] [host]`
*   **Example:** `./manage.sh lint photon-docker 02 esxi-01.mgmt.plexplease.com`

### `deploy`
Provisions the virtual hardware using OpenTofu. It creates a dedicated workspace for the VM state and performs an intermediate SSH connectivity test.
*   **Usage:** `./manage.sh deploy <profile> <id> [host] [mac_address]`
*   **Example:** `./manage.sh deploy ubuntu-base 01 esxi-02.mgmt.plexplease.com 00:50:56:af:00:01`
*   *Note: Providing a MAC address at runtime overrides any MAC defined in the YAML profile.*

### `config`
Applies the post-deployment OS configuration using Ansible. It uses dynamic discovery to target the VM by its vCenter tags.
*   **Usage:** `./manage.sh config <profile>`
*   **Example:** `./manage.sh config photon-docker`

### `test`
Executes the `pytest-testinfra` suite to verify that the node complies with security hardening and service standards.
*   **Usage:** `./manage.sh test <profile> <id>`
*   **Example:** `./manage.sh test ubuntu-base 01`

### `destroy`
Safely removes the virtual machine from vCenter and deletes its isolated OpenTofu workspace.
*   **Usage:** `./manage.sh destroy <profile> <id>`
*   **Example:** `./manage.sh destroy photon-docker 02`

### `all`
The recommended command for end-to-end deployments. It sequentially executes `lint` -> `deploy` -> `config` -> `test`.
*   **Usage:** `./manage.sh all <profile> <id> [host] [mac_address]`
*   **Example:** `./manage.sh all photon-docker 05 esxi-01.mgmt.plexplease.com 00:50:56:af:00:05`

---

## 3. Configuration System

### Global Secrets
Populate `config/secrets.env` with vCenter credentials and standard admin passwords. This file is ignored by Git.

### Node Profiles (`config/profiles/`)
Each profile dictates the hardware and personality of the node:
```yaml
vcenter:
  host: "esxi-01.mgmt.plexplease.com" # Default target host
  network: "VM Network"
content_library:
  template: "ubuntu-26.04-golden" # Remediated vmx-21 template
vm_specs:
  cpu: 4
  ram_gb: 8
deployment:
  tags: ["ubuntu"] # Dictates Ansible roles
```

---

## 4. Deployment Workflow

1.  **State Isolation:** Every node gets a dedicated **OpenTofu Workspace** named after its FQDN.
2.  **Hardware Alignment:** The pipeline enforces **PVSCSI** and **VMXNET3** for performance.
3.  **Connectivity:** After provisioning, the pipeline waits for port 22 to become reachable before handing off to Ansible.

---

## 5. Automated Testing

The pipeline uses `pytest-testinfra` to verify the "Final State":
*   **Common:** SSH hardening (root/password disabled), user presence.
*   **Ubuntu:** UFW status, package integrity.
*   **Photon:** Docker service status, locally running stacks.

To run tests manually:
```bash
./manage.sh test photon-docker 03
```

---

## 6. Troubleshooting

### vCenter REST API 500 Error
*   **Cause:** Mismatch between the OVF template's hardware (e.g., `lsilogic`) and the Tofu config (`pvscsi`).
*   **Fix:** Ensure the template in the `GOLDEN` library was remediated using `scripts/remediate_ubuntu.py` or equivalent hardware version 21 standards.

### Ansible "Unreachable"
*   **Cause:** Incorrect SSH password or VM not fully booted.
*   **Fix:** Verify `SSH_ADMIN_PASSWORD` in `config/secrets.env` matches the password in the golden image. The pipeline includes an intermediate connectivity test to wait for boot.
