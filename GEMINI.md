# Template Pipeline Project Instructions

## Engineering Standards
- **Golden Image:** Always use Ubuntu LTS (26.04+) or Photon OS 5.0 with the `minimal` installation profile.
- **Build Stack:** Utilize vCenter-native capture workflows. Provision a source VM via ISO/Cloud-Init, standardize hardware to **PVSCSI** and **VMXNET3**, and capture as an OVF template in the `GOLDEN` Content Library.
- **Hardware Version:** Standardize on **Hardware Version 21** (vmx-21) for all templates to leverage modern vSphere 8.x features.
- **Provisioning:** Use declarative OpenTofu with Workspace-based state isolation (one workspace per VM).
- **Testing & Quality:** Every major component must pass `pytest-testinfra` validation. All code changes must be validated through appropriate linters (`yamllint`, `ansible-lint`, `flake8`, `shellcheck`).
- **Documentation Maintenance:** Every significant feature or architectural change MUST be documented across the following files: `ROADMAP.md`, `VERSIONS_AND_UPDATES.md`, `RUNBOOK.md`, and `DESIGN.md`.
- **Version Control:** Follow semantic versioning. All changes must be made via feature branches and validated through linting.

## Linting & Formatting
- **YAML:** Must pass `yamllint`.
- **Ansible:** Must pass `ansible-lint`.
- **Python:** Must follow PEP 8 and pass `flake8`.
- **Shell:** Scripts should be linted with `shellcheck`.

## Architecture
- **Immutable Infrastructure:** Treat the golden image as immutable. All post-deployment changes should be handled by Ansible in a reproducible manner.
- **Dynamic Configuration:** Use Ansible variables and host-specific data for runtime configuration, avoiding hardcoded values in roles.
- **Content Library:** Use Content Libraries for template management to ensure consistent deployment across clusters.

## Automated Enforcement
- **AGENTS.ME Integration:** All AI agents must adhere to these policies. If a requested change violates these standards, the agent must notify the user and suggest an alternative.
