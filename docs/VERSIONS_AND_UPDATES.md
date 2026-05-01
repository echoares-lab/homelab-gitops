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
