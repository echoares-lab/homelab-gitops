# Deployment Process Roadmap

This roadmap outlines high-impact improvements to make the deployment process more robust, secure, and production-ready.

## Phase 1: Native Tooling & Idempotency
*   **Native Ansible vCenter Modules:** Install the `vSphere Automation SDK` in the environment to replace `govc` shell commands with native `community.vmware` modules (e.g., `vmware_content_deploy_ovf_template`). This ensures a cleaner and more idempotent workflow.
*   **Idempotency and State Checks:** Add pre-flight checks in `deploy.yml` to verify if a VM already exists before attempting deployment, allowing the playbook to skip deployment or halt gracefully.

## Phase 2: Configuration & Secret Management
*   **Secret Management:** Integrate Ansible Vault or a CI/CD secret manager to encrypt sensitive data (e.g., `VCENTER_PASSWORD`, `SSH_ADMIN_PASSWORD`) rather than storing them in plain text `.env` files.
*   **Static IP Support:** Extend cloud-init configuration to support static IPs via `network-config` (v2), allowing variables like `DEPLOY_IP`, `DEPLOY_NETMASK`, and `DEPLOY_GATEWAY` to dictate networking.

## Phase 3: Initialization Refinement
*   **`guestinfo` Cloud-Init Injection:** Revisit injecting cloud-init via `guestinfo.userdata` advanced properties. This eliminates the need to build, upload, attach, and clean up temporary ISO files on the datastore.
*   **Robust Cleanup and Error Handling:** Implement `always` blocks in Ansible to guarantee the cleanup of temporary artifacts (like `cidata.iso`) even if a deployment fails midway.
