# Pipeline Operations Runbook

Detailed operational procedures for the unified GitOps pipeline managing high-performance Ubuntu and Photon OS environments.

## Table of Contents
1. [Prerequisites](#1-prerequisites)
2. [Command Reference (`manage.sh`)](#2-command-reference-managesh)
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

## 2. Command Reference (`manage.sh`)

The `./manage.sh` orchestrator provides a unified interface for the entire lifecycle.

### `Interactive Mode`
Running `./manage.sh` with no arguments launches the **Command Builder**. This guided wizard helps you construct and execute the correct CLI syntax.

### `lint`
Validates the YAML profile schema and checks if all vCenter objects actually exist.
*   **Example:** `./manage.sh lint photon-docker 02 --host esxi-01.mgmt.plexplease.com`

### `deploy`
Provisions the virtual hardware via OpenTofu. Supports runtime overrides for IP, Hostname, and MAC.
*   **Example:** `./manage.sh deploy ubuntu-base 01 --ip 10.10.10.50 --gateway 10.10.10.1`

### `config` (Implied Limits)
Applies post-deployment OS configuration. Targeting is **Automatic**:
*   **Specific VM:** `./manage.sh config ubuntu-base 04` (Targets only the 04 node).
*   **Whole Group:** `./manage.sh config ubuntu-base` (Targets all VMs with the `ubuntu` tag).

### `test`
Executes Pytest-Testinfra validation.
*   **Example:** `./manage.sh test ubuntu-base 01`

### `destroy` (Safety First)
Removes a VM using a **single identifier** (Name, IP, or MAC).
*   **Example:** `./manage.sh destroy 10.10.10.50`
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
All credentials and defaults are stored in `config/secrets.env`.
*   **Template:** Use `config/secrets.env.example` to set up a new environment.
*   **Security:** This file is ignored by Git.

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
*   **Fix:** Check `SSH_PRIVATE_KEY_PATH` in `secrets.env`. The pipeline uses ED25519 by default.
