# Deployment Process Roadmap

This roadmap outlines high-impact improvements to make the deployment process more robust, secure, and production-ready.

## Phase 1: Native Tooling & Idempotency
*   **Native Ansible vCenter Modules:** Install the `vSphere Automation SDK` in the environment to replace `govc` shell commands with native `community.vmware` modules (e.g., `vmware_content_deploy_ovf_template`). This ensures a cleaner and more idempotent workflow.
*   **Idempotency and State Checks:** [DONE] Added pre-flight checks in `deploy.yml` to verify if a VM already exists before attempting deployment, allowing the playbook to skip deployment and proceed to configuration.

## Phase 2: Configuration & Secret Management
*   **Secret Management:** [DEFERRED] Integrate Ansible Vault or a CI/CD secret manager to encrypt sensitive data (e.g., `VCENTER_PASSWORD`, `SSH_ADMIN_PASSWORD`) rather than storing them in plain text `.env` files.
*   **Static IP Support:** [DEFERRED] Extend cloud-init configuration to support static IPs via `network-config` (v2), allowing variables like `DEPLOY_IP`, `DEPLOY_NETMASK`, and `DEPLOY_GATEWAY` to dictate networking.

## Phase 3: Initialization Refinement
*   **`guestinfo` Cloud-Init Injection:** [INVESTIGATED] Attempted native and `govc` injection; found to be incompatible with the standard Ubuntu cloud image without template modification. Reverted to reliable ISO method.
*   **Robust Cleanup and Error Handling:** [DONE] Implemented `block/always` in Ansible to guarantee the cleanup of temporary artifacts. Note: Datastore ISO removal may require manual unmounting if file locks persist.
