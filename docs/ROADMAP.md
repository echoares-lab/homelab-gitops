# Project Roadmap: HomeLab GitOps

This document outlines the strategic vision for the unified GitOps pipeline, detailing upcoming features, deferred items, and a history of completed milestones.

---

## 🎯 Pending Features (Next Up)

These high-impact features are prioritized for near-term development to further mature the pipeline's operational capabilities.

### Phase 3: Usability & Advanced Orchestration
*   **Profile, Role & Play Generator Helpers:** [DONE] Implemented interactive wizards (`create-profile`, `create-role`, `create-play`) with strict naming standards.
*   **Implied Limits:** [DONE] Refactored orchestrator to automatically calculate Ansible targeting scope.
*   **Simplified Destruction:** [DONE] Enabled targeting via single identifier (IP/MAC/Name) with safety confirmation.
*   **Static IP Injection:** [DONE] Implemented native guest customization via OpenTofu for both Ubuntu and Photon OS.
*   **CLI Refactor:** [DONE] Transitioned to clean, named CLI flags for all runtime overrides.
*   **Inventory Migration:** [DONE] Migrated to modern `vmware.vmware.vms` plugin and resolved all deprecation warnings.
*   **Ansible Vault Integration:** [DONE] Transitioned from plain-text `.env` infrastructure secrets to encrypted Ansible Vault files, allowing application-level secrets (DB passwords, API keys) to be securely committed to the Git repository.
*   **Fleet Status Dashboard:** Add a read-only orchestrator command (`python3 manage.py status`) that queries vCenter and Tofu Workspaces to print a formatted terminal table detailing VM IP, power state, assigned tags, and drift status.
*   **Automated Golden Image Refresh:** Develop a scheduled automation script that deploys a temporary VM from the existing golden image, runs OS-level package updates (`apt-get upgrade` / `tdnf update`), and automatically captures and versions a new, patched golden image.

---

## ⏸️ Deferred Features (Backlog)

These items are recognized as valuable but are currently pending further architectural review or are superseded by existing robust solutions.

*   **Static IP Injection via `guestinfo`:** Pass IP configuration directly through vApp properties to cloud-init, bypassing DHCP entirely. *Currently deferred as the existing MAC-reservation + DHCP architecture provides sufficient stability.*
*   **Native `guestinfo` Metadata Injection:** Removing the reliance on ISO attachments for cloud-init. *Previously investigated; found incompatible with standard Ubuntu cloud images without significant template modification. The ISO method remains the active standard.*

---

## ✅ Completed Milestones

A record of significant architectural achievements and technical debt remediation.

### Phase 2: Pipeline Synthesis & Security
*   **Security Remediation:** Scrubbed leaked credentials from Git history and transitioned to a private repository structure.
*   **Unified Orchestrator:** Implemented `manage.sh` to handle the full lifecycle (Build, Lint, Deploy, Config, Test, Destroy).
*   **Tofu Workspaces:** Adopted OpenTofu workspaces for granular, per-VM state isolation and idempotency.
*   **End-to-End Testing:** Integrated `pytest-testinfra` for automated post-deployment validation of OS hardening and services.
*   **Runtime Flexibility:** Added CLI support for specifying target ESXi hosts and network MAC addresses during deployment.
*   **Hardware Remediation:** Fixed OVF metadata corruption; all templates now actively utilize **PVSCSI**, **VMXNET3**, and **Hardware Version 21**.

### Phase 1: Foundation
*   **Native Ansible Integration:** Transitioned to native `vmware.vmware` modules using the vSphere Automation SDK.
*   **Tag-Based Routing:** Ansible configuration targets VMs dynamically via vCenter tags instead of static inventories.
*   **Robust Cleanup:** Implemented `block/always` logic in Ansible to guarantee the cleanup of temporary build artifacts.
