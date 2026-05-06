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

### v3.1.0 - Usability & Lifecycle Enhancements
- **Interactive Builder:** Added a guided CLI wizard (triggered by running `./manage.sh` with no arguments).
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
