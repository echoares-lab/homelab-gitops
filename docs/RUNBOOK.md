# Pipeline Operations Runbook

Detailed operational procedures for the unified GitOps pipeline managing high-performance Ubuntu and Photon OS environments.

## Table of Contents
1. [Prerequisites](#1-prerequisites)
2. [Command Reference (`manage.py`)](#2-command-reference-managesh)
3. [Generator Helpers](#3-generator-helpers)
4. [Configuration System](#4-configuration-system)
5. [Deployment Workflow](#5-deployment-workflow)
6. [Automated Testing](#6-automated-testing)
7. [Troubleshooting](#7-troubleshooting)

---

## 1. Prerequisites
Ensure the orchestration host has the following:
*   **OpenTofu** (`>= 1.6`)
*   **Ansible** (`>= 2.14`) with `vSphere Automation SDK`
*   **Pytest & Testinfra**
*   **govc** (installed in `build/`)

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

### `test`
Executes Pytest-Testinfra validation.
*   **Example:** `python3 manage.py test ubuntu-base 01`

### `destroy` (Safety First)
Removes a VM using a **single identifier** (Name, IP, or MAC).
*   **Example:** `python3 manage.py destroy 10.10.10.50`
*   **Safety:** Always requires an interactive `(y/N)` confirmation before proceeding.

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
All credentials and defaults are stored in an encrypted Ansible Vault file at `config/vault.yml`.
*   **Template:** Use `config/vault.yml.example` to set up a new environment. Copy it to `config/vault.yml`.
*   **Vault Password:** Create a file at `config/.vault_pass` containing your password.
*   **Encryption:** Encrypt the file using `ansible-vault encrypt config/vault.yml --vault-password-file config/.vault_pass`.
*   **Security:** `vault.yml` CAN be securely committed to Git if fully encrypted. `.vault_pass` MUST NOT be committed and is ignored by Git.

---

## 5. Deployment Workflow

1.  **State Isolation:** Every node gets a dedicated **OpenTofu Workspace** named after its FQDN.
2.  **Hardware Alignment:** The pipeline enforces **PVSCSI** and **VMXNET3** for performance.
3.  **Connectivity:** The pipeline automatically detects Static IPs or DHCP assignments and waits for SSH before configuration.

---

## 6. Automated Testing

The pipeline uses `pytest-testinfra` to verify the "Final State":
*   **Common:** SSH hardening (root/password disabled), user presence, MAC alignment.
*   **Ubuntu:** UFW status, package integrity.
*   **Photon:** Docker service status.

---

## 7. Troubleshooting

### vCenter REST API 500 Error
*   **Cause:** Hardware mismatch in the OVF template.
*   **Fix:** Ensure the template is remediated with vmx-21/PVSCSI standards.

### Ansible "Unreachable"
*   **Cause:** Incorrect SSH key or path.
*   **Fix:** Check `ssh_private_key_path` in `config/vault.yml`. The pipeline uses ED25519 by default.
