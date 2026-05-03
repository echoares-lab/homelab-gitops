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

| Command | Arguments | Description |
| :--- | :--- | :--- |
| `lint` | `<profile>` | Validates YAML schema and vCenter object existence. |
| `deploy` | `<profile> <id> [host]` | Provisions virtual hardware and waits for SSH. |
| `config` | `<profile>` | Applies Ansible roles via dynamic inventory. |
| `test` | `<profile> <id>` | Executes Pytest-Testinfra OS validation. |
| `destroy` | `<profile> <id>` | Deletes the VM and its isolated Tofu workspace. |
| `all` | `<profile> <id> [host]` | Runs Lint -> Deploy -> Config -> Test. |

**Example:**
```bash
./manage.sh all ubuntu-base 01 esxi-01.mgmt.plexplease.com
```

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
