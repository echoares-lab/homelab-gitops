# Version Control & Update Strategy

## Versioning Policy
This project uses [Semantic Versioning 2.0.0](https://semver.org/).
- **MAJOR:** Incompatible API changes (e.g., changing the base OS or Packer builder type).
- **MINOR:** Functionality added in a backwards-compatible manner (e.g., adding a new Ansible role or updating the minor version of a base OS).
- **PATCH:** Backwards-compatible bug fixes or security patches.

## Update Strategy
- **Base Image:** The golden image is rebuilt monthly or when critical security patches are released for Ubuntu.
- **Ansible Roles:** Roles are updated as needed. Changes must be tested against the latest golden image before being merged.
- **Rollback:** In case of a failed deployment, vCenter snapshots or previous versions of the Packer template can be used for rapid rollback.

## Version History

### v3.4.5 - GitOps Directory Standard
- Documented the target Kubernetes GitOps layout for cluster directories, platform apps, workloads, and bootstrap/root apps.
- Added naming and ownership rules for GitOps directories, Argo CD apps, secret references, and cross-directory reviews.
- Confirmed the existing `kubernetes/clusters/k3s-01/` manifests can map to the standard without moving manifests in this change.

### v3.4.4 - K3s ExternalDNS RFC-2136 DNS Registration
- Switched external-dns deployment on k3s-01 from webhook sidecar to native RFC-2136 provider.
- Configured external-dns to target the 'infra.plexplease.com' zone on Technitium DNS to support the cluster's hostnames.
- Configured Technitium DNS zone 'infra.plexplease.com' updateSecurityPolicies to allow TSIG key 'externaldns-k3s-01' updates for both parent and wildcard subdomains.
- Fixed `helm-install-argocd` crashlooping by correcting the pinned Argo CD chart version from `7.9.4` to `9.7.0` to match the version running on the live cluster.

### v3.4.3 - OpenBao Runtime Secrets Migration
- Migrated committed runtime secret references in `config/secrets.env` from `op://` to `bao://` KV v2 paths.
- Added native `bao://` resolution to `SecretsDriver` for single secret reads and env-file bootstrap.
- Migrated existing 1Password values and local `.env` values into OpenBao without committing secret material.

### v3.4.2 - Driver Maturity & Edge Case Hardening
- **Ansible Driver:** Added native support for `--limit` and `--tags` CLI overrides in `AnsibleDriver`.
- **Ansible Driver:** Hardened command construction to filter redundant variables from `extra_vars` when CLI flags are used.
- **Migration Driver:** Fixed a critical bug in `rollback` where sub-driver tasks were missing required profile context.
- **Test Coverage:** Achieved 100% unit test coverage for `AnsibleDriver` and `MigrationDriver` with exhaustive edge case validation (SSH failures, state corruption, timeout handling).

### v3.4.1 - Runner Storage and Profile Log Retention
- Ensured GitHub runner baseline provisioning expands the root partition and filesystem to use the full 400GB virtual disk allocated by runner profiles.
- Added `ansible/runner-maintenance.yml` for token-free maintenance of existing self-hosted runners.
- Added a reusable `log_retention` role with profile-owned logrotate file policies and a 14-day/512MB journald vacuum timer.
- Added a Technitium DNS profile policy for `/var/log/technitium/dns/*.log` with daily rotation, 14 retained rotations, 100MB max size, compression, and copytruncate.

### v3.4.0 - GitHub Runner for Testing & CI
- Added `ubuntu-2404-git-test` profile for high-performance GitHub runners (20 cores, 20GB RAM, 400GB Disk).
- Implemented `ansible/git-test-runner.yml` dedicated playbook for automated runner registration.
- **Automated Runner Tokens:** Integrated GitHub API support into `manage.py` to automatically fetch registration tokens using a PAT (resolved via 1Password).
- Hardened the `git-test` runner with passwordless sudo for the `github-runner` user to support CI/CD workloads.
- Integrated `git_test` tag into `manage.py` orchestrator for automated playbook selection.

### v3.3.0 - Fleet Observability & 1Password Runtime Alignment
- Added the read-only `manage.py status` fleet dashboard for managed OpenTofu workspaces and vCenter VM state.
- Hardened orchestrator command execution for Ansible, Tofu, Packer, Pytest, and helper invocations by preferring explicit argv lists.
- Aligned documentation with the active 1Password `config/secrets.env` runtime path and marked Ansible Vault as legacy migration reference.
- Deferred automated golden image refresh and first-class CAA runner/dev lifecycle work pending separate design and ownership.

### v3.2.0 - Security & Secrets Management
- **1Password Runtime Integration:** Transitioned from local plaintext secrets to `config/secrets.env` references resolved through the Homelab-GitOps 1Password vault.
- Refactored `manage.py` orchestrator to bootstrap secret-dependent commands through `op run` when `OP_SERVICE_ACCOUNT_TOKEN` is available.

### v3.1.0 - Usability & Lifecycle Enhancements
- **Interactive Builder:** Added a guided CLI wizard (triggered by running `python3 manage.py` with no arguments).
- **Generator Helpers:** Implemented `create-profile`, `edit-profile`, `create-role`, and `create-play` to automate GitOps boilerplate.
- **Simplified Destruction:** Refactored `destroy` to support single-identifier targeting (IP/MAC/Name) with safety confirmation.
- **Implied Limits:** Automated Ansible targeting logic; the script now automatically limits runs based on provided Profile/ID.
- **Inventory Cleanup:** Migrated to modern `vmware.vmware.vms` plugin and resolved all dot-notation variable deprecations.

### v3.0.0 - Pipeline Synthesis & Remediation
- **MAJOR CHANGE:** Implemented `manage.sh` unified lifecycle orchestrator (Lint, Deploy, Config, Test, Destroy).
- **Architecture:** Switched to **OpenTofu Workspaces** for granular, per-VM state isolation.
- **Hardware Standardization:** Upgraded all templates to **Hardware Version 21**, **PVSCSI**, and **VMXNET3**.
- **Security:** Verified and remediated Ubuntu 26.04 golden image to resolve vCenter OVF deployment conflicts.
- **Testing:** Integrated `pytest-testinfra` for automated end-to-end OS validation.
- **Flexibility:** Added runtime CLI overrides for target ESXi hosts and network MAC addresses.

### v2.0.0 - Ubuntu 26.04 LTS (Resolute Raccoon) Update
- **MAJOR CHANGE:** Updated base OS from Ubuntu 24.04 LTS to Ubuntu 26.04 LTS.
- Updated all build scripts, cloud-init configurations, and OVF templates to support 26.04.
- Verified SHA256 checksums for the 26.04 Live Server ISO and Cloud Images.
- Updated Ansible deployment defaults to target 26.04 templates.

### v1.2.0 - Folder Standardization & Lifecycle
- Standardized vCenter folder hierarchy:
    - `Builds/Linux/Ubuntu/Templates/` (Golden Images)
    - `Builds/Linux/Ubuntu/Test/` (Temporary Builds)
    - `Deploy/Linux/Ubuntu/Prod/` (Production Deployments)
    - `Deploy/Linux/Ubuntu/Test/` (Test Deployments)
- Added `-k` / `--keep` flag to `build.sh` and `deploy.sh` to prevent automated cleanup of test artifacts.
- Introduced `cleanup.sh` helper script for lifecycle management.

### v1.0.0 - Initial Release
- Automated pipeline for Golden Image creation via Packer and Ansible.
- Standardized configuration via `defaults.env` and `inputs.env`.
nv`.
