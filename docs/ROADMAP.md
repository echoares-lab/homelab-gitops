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
*   **OpenBao Runtime Secrets:** [DONE] Runtime secrets resolve through `config/secrets.env` and OpenBao KV v2; 1Password and Ansible Vault remain legacy migration references.
*   **Fleet Status Dashboard:** [DONE] Added a read-only orchestrator command (`python3 manage.py status`) that queries vCenter and Tofu Workspaces to print a formatted terminal table detailing VM IP, power state, assigned tags, and drift status.
*   **GitHub Runner for CI/Testing:** [DONE] Added high-performance runner profile (20 cores, 20GB RAM, 400GB disk), automated registration token retrieval, passwordless sudo support, token-free maintenance, and Ansible root filesystem expansion to consume the full runner disk.
*   **Profile-Owned Log Retention:** [DONE] Added reusable `log_retention` role plus profile-level log policies for bounded logrotate and journald retention.
*   **GitOps Directory Standard:** [DONE] Documented the target Kubernetes layout for bootstrap/root apps, cluster composition, platform apps, workloads, naming, and ownership.
*   **k3s-01 GitOps Layout Migration:** [DONE] Moved k3s-01 manifests into the standard bootstrap, cluster config, and platform overlay directories while preserving the cluster root sync path.
*   **GitOps Manifest Validation:** [DONE] Added a local validation command that renders Kubernetes kustomizations and checks YAML plus basic Kubernetes object schema before manifests are applied.
*   **Image Build Asset Layout:** [DONE] Moved generated FCOS installer payloads out of Packer source paths and updated Packer to serve generated HTTP content from `build/http/fcos`.
*   **Image Build Smoke Validation:** [DONE] Added no-deploy Packer and Butane validation for image build inputs.
*   **Ansible Structure Validation:** [DONE] Added local validation for playbook role paths, profile playbook references, and role/tag metadata consistency.
*   **ARC/Nexus CI/CD Stack Design:** [DONE] Documented the preferred ARC-first CI/CD model with Nexus Repository OSS on k3s, layered cache ownership, two runner pools, GitOps-only promotion, and release version gates.

### Phase 4: Production Maturity & AI Integration
*   **85% Unit Test Coverage:** [DONE] Exhaustive driver edge-case testing, Pydantic model validation, and 92% project-wide coverage.
*   **Automated Backup & DR Service:** [DONE] Orchestrated config export for OPNsense and Technitium with secure storage in 1Password.
*   **Model Context Protocol (MCP) Server:** [DONE] Exposed homelab capabilities as AI tools.

---

## ⏸️ Deferred Features (Backlog)

These items are recognized as valuable but are currently pending further architectural review or are superseded by existing robust solutions.

*   **Static IP Injection via `guestinfo`:** Pass IP configuration directly through vApp properties to cloud-init, bypassing DHCP entirely. *Currently deferred as the existing MAC-reservation + DHCP architecture provides sufficient stability.*
*   **Native `guestinfo` Metadata Injection:** Removing the reliance on ISO attachments for cloud-init. *Previously investigated; found incompatible with standard Ubuntu cloud images without significant template modification. The ISO method remains the active standard.*
*   **Automated Golden Image Refresh:** Deferred pending a separate design for template replacement policy, validation gates, rollback, and versioning of patched golden images.
*   **First-Class CAA Runner/Dev Lifecycle:** Deferred until cross-repo ownership is resumed; current profiles remain available, but no new cloudflare_access_automation project work is in scope.

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
