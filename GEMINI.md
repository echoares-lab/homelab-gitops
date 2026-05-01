# Template Pipeline Project Instructions

## Engineering Standards
- **Golden Image:** Always use Ubuntu LTS (26.04+) with the `minimal` installation profile.
- **Build Stack:** Use local QEMU/virt-install for building images to ensure speed and robustness. Defer complex configuration to post-deployment Ansible.
- **Templates:** All golden images must be uploaded to the vCenter Content Library as OVF templates.
- **Ansible:** Follow official best practices. Use roles for reusable logic and keep playbooks focused on orchestration.
- **Testing:** Every major component (Build disk, Ansible roles) must have corresponding `pytest-testinfra` tests.
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
