# Template Pipeline

Automated pipeline for creating Ubuntu golden images and deploying them to ESXi/vCenter with host-specific configuration.

## Features
- **Golden Image Creation:** Local QEMU/virt-install with cloud-init (autoinstall) for minimal Ubuntu 26.04 LTS images.
- **vCenter Integration:** Automated upload to vCenter Content Library as OVF templates.
- **Automated Deployment:** Ansible playbook to deploy VMs directly from the Content Library.
- **Dynamic Configuration:** Ansible roles for base OS setup and security hardening.
- **Verification:** Integrated testing with `pytest-testinfra`.
- **Policies:** Codified standards in `GEMINI.md` for AI-driven enforcement.

## Prerequisites
- QEMU / KVM / virt-install
- genisoimage
- govc
- Ansible
- Python 3 with `pytest-testinfra`

## Quick Start

### 1. Build the Golden Image
```bash
./build.sh
```
This script downloads the Ubuntu 26.04 ISO, builds a minimal image locally using QEMU, packages it as an OVA, and uploads it to your vCenter Content Library.

### 2. Deploy a New VM
```bash
cd ansible
# Update variables in deploy.yml or use environment variables
ansible-playbook deploy.yml
```

### 3. Run Verification Tests
```bash
pytest --hosts='ansible@<vm-ip>' tests/test_golden_image.py
```

## Project Structure
- `build/`: Local build orchestration scripts and Subiquity configs.
- `ansible/`: Playbooks and roles for deployment and post-install configuration.
- `tests/`: Pytest-testinfra verification scripts.
- `docs/`: Documentation for versioning and updates.

## Policies & Standards
See [GEMINI.md](./GEMINI.md) for detailed coding standards, linting requirements, and architectural rules.
