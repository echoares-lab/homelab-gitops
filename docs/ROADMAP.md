# Deployment Process Roadmap

This roadmap outlines high-impact improvements to make the deployment process more robust, secure, and production-ready.

## Phase 1: Native Tooling & Idempotency
*   **Native Ansible vCenter Modules:** [DONE] Installed the `vSphere Automation SDK` and transitioned to native `vmware.vmware` modules.
*   **Idempotency and State Checks:** [DONE] Added pre-flight checks in `deploy.yml` and utilized OpenTofu for state-driven infrastructure management.
*   **Photon OS Golden Image (vmx-21):** [DONE] Upgraded to Hardware Version 21 and captured the stabilized system as the final `photon-5.0-golden` template.
*   **Custom MAC Addressing:** [DONE] Added support for specifying network MAC addresses during the OpenTofu deployment phase.

## Phase 2: Configuration & Secret Management
*   **Secret Management:** [DEFERRED] Integrate Ansible Vault or a CI/CD secret manager to encrypt sensitive data (e.g., `VCENTER_PASSWORD`, `SSH_ADMIN_PASSWORD`) rather than storing them in plain text `.env` files.
*   **Static IP Support:** [DEFERRED] Extend cloud-init configuration to support static IPs via `network-config` (v2), allowing variables like `DEPLOY_IP`, `DEPLOY_NETMASK`, and `DEPLOY_GATEWAY` to dictate networking.

## Phase 3: Initialization Refinement
*   **`guestinfo` Cloud-Init Injection:** [INVESTIGATED] Attempted native and `govc` injection; found to be incompatible with the standard Ubuntu cloud image without template modification. Reverted to reliable ISO method.
*   **Robust Cleanup and Error Handling:** [DONE] Implemented `block/always` in Ansible to guarantee the cleanup of temporary artifacts. Note: Datastore ISO removal may require manual unmounting if file locks persist.
