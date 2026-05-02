# Pipeline Operations Runbook

This runbook provides detailed operational procedures for the unified GitOps pipeline managing Ubuntu and Photon OS environments via OpenTofu, Packer, and Ansible.

## Table of Contents
1. [Prerequisites & Setup](#1-prerequisites--setup)
2. [Configuration Management](#2-configuration-management)
3. [Building Golden Images (Packer)](#3-building-golden-images-packer)
4. [Deploying Infrastructure (OpenTofu)](#4-deploying-infrastructure-opentofu)
5. [Configuring Nodes (Ansible)](#5-configuring-nodes-ansible)
6. [Troubleshooting & Common Issues](#6-troubleshooting--common-issues)

---

## 1. Prerequisites & Setup

Ensure the following tools are installed on your orchestration machine:
*   **OpenTofu** (`>= 1.6.0`)
*   **Packer** (`>= 1.9.0`)
*   **Ansible** (`>= 2.14`)
*   **govc** (vSphere CLI)
*   **Python 3** with `pyyaml`
*   **vSphere Automation SDK** (`vmware-vcenter`, `vmware-vapi-runtime`, `vmware-vapi-common-client`)

### Initializing the Environment
1.  Copy `config/secrets.env.example` to `config/secrets.env` (if applicable) or ensure `config/secrets.env` exists.
2.  Populate `VCENTER_SERVER`, `VCENTER_USERNAME`, `VCENTER_PASSWORD`, and `SSH_ADMIN_PASSWORD`.

---

## 2. Configuration Management

All deployments are driven by YAML profiles located in `config/profiles/`. 

### Creating a New Node Profile
To create a new type of node (e.g., a Photon OS database node):
1.  Duplicate an existing profile: `cp config/profiles/photon-docker.yml config/profiles/photon-db.yml`
2.  Edit the profile to match your requirements:
    *   **`content_library.template`**: Ensure it points to the correct golden image.
    *   **`vm_specs`**: Adjust CPU and RAM (`ram_gb`).
    *   **`deployment.tags`**: Add relevant tags (e.g., `photon`, `db`, `postgres`). *These tags dictate which Ansible roles are applied.*

---

## 3. Building Golden Images (Packer)

Golden images are pre-hardened OS templates stored in the vCenter Content Library.

**Command:**
```bash
./manage.sh build <profile_name>
```
*(Note: Currently, the build script defaults to the Photon configuration in `packer/photon.pkr.hcl`.)*

**Workflow:**
1.  Packer imports the base OVA.
2.  Applies initial OS updates and hardening.
3.  Exports the result as a new golden OVF (e.g., `photon-5.0-golden`).

---

## 4. Deploying Infrastructure (OpenTofu)

The deployment phase translates the YAML profile into virtual hardware in vCenter.

**Command:**
```bash
./manage.sh deploy <profile_name> <instance_id>
```
*Example: `./manage.sh deploy photon-docker 02`*

**Workflow:**
1.  **Linting:** The pipeline verifies that the Datacenter, Cluster, Datastore, and Network specified in the YAML actually exist in vCenter.
2.  **Workspace Isolation:** OpenTofu selects (or creates) a dedicated workspace named after the VM (e.g., `docker-02.infa.plexplease.com`).
3.  **Provisioning:** Tofu clones the golden template, assigns the specified RAM, CPU, and custom MAC address (if defined), and attaches the designated vSphere tags.

---

## 5. Configuring Nodes (Ansible)

Configuration is applied automatically based on the vSphere tags attached to the VM during deployment.

**Command:**
```bash
./manage.sh config
```

**Workflow:**
1.  Ansible uses the `community.vmware.vmware_vm_inventory` plugin to query vCenter.
2.  VMs are grouped dynamically (e.g., `tag_photon`, `tag_docker`, `tag_ubuntu`).
3.  The `ansible/site.yml` playbook maps these tags to specific roles. For example, any VM with the `tag_docker` receives the Docker CE installation.

---

## 6. Troubleshooting & Common Issues

### Issue: OpenTofu fails with "Network not found"
*   **Cause:** The network name in the YAML profile does not match exactly with what is in vCenter.
*   **Resolution:** Check vCenter for the exact name. Note that nested folders in vCenter networks must be respected in some cases.

### Issue: Ansible cannot connect via SSH ("Permission denied" or "No route to host")
*   **Cause:** 
    1.  The VM has not finished acquiring an IP address from DHCP.
    2.  The SSH keys inside the Golden Image do not match your local `~/.ssh/id_rsa` or `~/.ssh/id_ed25519`.
*   **Resolution:** 
    *   Verify the IP in vCenter. 
    *   Ensure your public key is accurately reflected in `config/secrets.env` during the Packer build phase.

### Issue: Ansible dynamic inventory returns empty
*   **Cause:** The `VMWARE_` environment variables are not correctly exported, or the inventory plugin is misconfigured.
*   **Resolution:** Ensure you are running Ansible through `./manage.sh config` which automatically exports the required authentication variables from `secrets.env`. Check tag assignments in vCenter.
