# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Unified GitOps Template Pipeline** is a professional automation framework for building, provisioning, and configuring high-performance Ubuntu and Photon OS nodes on vSphere. It uses a unified orchestrator (`manage.py`) to manage the complete lifecycle: Build, Deploy, Config, Test, and Destroy.

The core pipeline follows a **Build-Provision-Configure-Test** workflow:
1. **Build:** Packer creates golden OVF images with standardized hardware (PVSCSI, VMXNET3, vmx-21)
2. **Deploy:** OpenTofu provisions VMs with Workspace-based state isolation
3. **Config:** Ansible applies dynamic configuration via vCenter tag-based discovery
4. **Test:** Pytest-Testinfra validates OS hardening and service state

## Quick Start Commands

### Development Environment
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Interactive Orchestrator
```bash
python3 manage.py          # Launches Rich-styled command builder wizard
```

### Core Orchestration Commands
```bash
python3 manage.py lint PROFILE [INDEX]           # Validate YAML and vCenter infrastructure
python3 manage.py deploy PROFILE INDEX --host HOST  # Provision VM via OpenTofu
python3 manage.py config PROFILE [INDEX]         # Apply Ansible configuration
python3 manage.py test PROFILE [INDEX]           # Run Pytest-Testinfra validation
python3 manage.py build TARGET                   # Packer build (targets: ubuntu-2404, ubuntu-2604, photon-docker)
python3 manage.py destroy IDENTIFIER             # Remove VM (by name, IP, or MAC)
python3 manage.py status                         # Read-only fleet visibility
```

### Matrix Testing
```bash
python3 scripts/matrix_test.py                   # End-to-end logic validation across OS/networking scenarios
```

### Linting & Validation
```bash
python3 scripts/lint_config.py                   # Validate all YAML profiles against schema
python3 scripts/test_connectivity.py IP          # Test SSH connectivity to a target VM
```

### Schema Management
```bash
yamllint config/profiles/*.yml                   # Lint YAML syntax
ansible-lint ansible/                            # Lint Ansible playbooks and roles
flake8 manage.py scripts/ tests/                 # Lint Python code (PEP 8)
shellcheck scripts/*.sh                          # Lint shell scripts
```

### Testing with Testinfra
```bash
# Unit tests (no VM required)
pytest tests/test_manage.py -v
pytest tests/test_connectivity_optimized.py -v

# Integration tests (requires target VM)
pytest --hosts='ansible@10.10.10.50' \
       --ssh-extra-args='-o StrictHostKeyChecking=no -o IdentityFile=~/.ssh/id_ed25519' \
       --sudo tests/test_os.py -v
```

## Repository Structure

```
├── manage.py                # Unified orchestrator (typer CLI + Rich UI)
├── ansible/
│   ├── roles/               # Task-based roles (docker, security, github_runner, etc.)
│   ├── site.yml             # Master playbook with tag-based routing
│   └── inventory/
├── config/
│   ├── profiles/            # YAML node blueprints (hardware + tags)
│   ├── metadata.yml         # Runtime metadata (commands, tags, roles)
│   ├── secrets.env          # 1Password references (safe to commit)
│   └── dns_records.csv      # DNS entries
├── tofu/                    # OpenTofu HCL (one workspace per VM)
│   └── main.tf              # vSphere provisioning
├── tests/
│   ├── conftest.py          # Pytest configuration (auto-skips testinfra without --hosts)
│   ├── test_manage.py       # Orchestrator validation
│   ├── test_os.py           # OS hardening & security
│   ├── test_common.py       # Common testinfra assertions
│   └── test_*.py            # Role-specific integration tests
├── scripts/
│   ├── matrix_test.py       # E2E logic validation
│   ├── lint_config.py       # Profile schema validation
│   ├── profile_manager.py   # Create/edit profile wizards
│   ├── op-vault-setup.sh    # 1Password integration setup
│   └── setup.sh             # Environment initialization
├── packer/
│   ├── ubuntu2404.pkr.hcl   # Ubuntu 24.04 LTS golden image
│   ├── ubuntu2604.pkr.hcl   # Ubuntu 26.04 LTS golden image
│   └── photon.pkr.hcl       # Photon OS 5.0 golden image
├── docs/
│   ├── DESIGN.md            # Architecture & technical decisions
│   ├── RUNBOOK.md           # Operational procedures
│   ├── ROADMAP.md           # Project milestones & status
│   └── VERSIONS_AND_UPDATES.md  # Release notes
├── GEMINI.md                # Engineering standards & policies
└── README.md                # Quick reference
```

## Key Architecture Concepts

### Profile-Driven Deployment
Each node is defined by a YAML profile in `config/profiles/` containing:
- vCenter infrastructure (datacenter, cluster, datastore, network)
- VM specifications (CPU, RAM, disk)
- vSphere Tags (for Ansible group discovery)
- Post-deployment roles (mapped from tags)

### Dynamic Ansible Inventory
Ansible queries vCenter in real-time using vSphere tags rather than static inventory files. The master playbook (`ansible/site.yml`) automatically applies roles based on discovered tags (e.g., `tag_docker` triggers docker role).

### Workspace-Based State Isolation
Each VM gets a dedicated OpenTofu workspace named after its FQDN. This allows independent destroy/update operations without affecting other VMs.

### Testinfra Validation Strategy
- **Unit tests** (no VM): Run `pytest tests/test_*.py` locally to validate orchestrator logic
- **Integration tests** (requires VM): Use `--hosts='ansible@<ip>'` to target a real VM and verify OS hardening, SSH keys, user presence, etc.
- The `conftest.py` auto-skips testinfra tests when `--hosts` is omitted to prevent false failures on localhost

## Naming Conventions (From GEMINI.md)

- **Profiles:** Lowercase alphanumeric + hyphens only (e.g., `ubuntu-2404-base`, `photon-docker`)
- **Roles:** Lowercase alphanumeric + underscores only (e.g., `harden_os`, `install_docker`)
- **Tags:** Lowercase alphanumeric + underscores only (e.g., `primary_dns`, `docker_host`)

## Standards & Enforcement

### Hardware Standardization
- **SCSI Controller:** VMware Paravirtual (PVSCSI)
- **Network Adapter:** VMXNET3
- **Hardware Version:** 21 (vmx-21) for modern vSphere 8.x features

### Code Quality
All changes must pass:
- `yamllint` (YAML syntax)
- `ansible-lint` (Ansible best practices)
- `flake8` (Python PEP 8)
- `shellcheck` (shell scripts)

### Testing & Quality Gate
- All logic changes must be validated through `scripts/matrix_test.py`
- Golden image hardening is immutable; post-deployment changes are Ansible-driven
- Every major feature must include corresponding testinfra validation

### Documentation Requirements
Significant features or architectural changes must be documented in:
- `docs/ROADMAP.md` (milestones)
- `docs/VERSIONS_AND_UPDATES.md` (release notes)
- `docs/RUNBOOK.md` (operational procedures)
- `docs/DESIGN.md` (technical architecture)

## Common Development Tasks

### Adding a New Ansible Role
```bash
python3 manage.py create-role  # Interactive wizard
# OR manually:
mkdir -p ansible/roles/my_role/{tasks,handlers,templates,defaults}
echo "---\n- name: My role\n  debug: msg='hello'" > ansible/roles/my_role/tasks/main.yml
```

### Creating a New Profile
```bash
python3 manage.py create-profile  # Interactive wizard
# Files generated: config/profiles/my-profile.yml
```

### Deploying a Node
```bash
# Full pipeline (lint → deploy → config → test)
python3 manage.py all ubuntu-2404-base 01 --host esxi-01.mgmt.plexplease.com

# Individual steps
python3 manage.py lint ubuntu-2404-base 01
python3 manage.py deploy ubuntu-2404-base 01 --host esxi-01.mgmt.plexplease.com
python3 manage.py config ubuntu-2404-base 01
python3 manage.py test ubuntu-2404-base 01
```

### Running the Full Test Suite
```bash
# Orchestrator & unit tests (no infrastructure required)
pytest tests/ -v -k "not (host in getattr"

# With matrix validation
python3 scripts/matrix_test.py
```

### Secrets Management

Secrets are stored in 1Password vaults and accessed via 1Password Connect server (10.10.10.30:8200).

#### Setup

1. Ensure `OP_CONNECT_TOKEN` environment variable is set:
   ```bash
   export OP_CONNECT_TOKEN=$(cat /etc/op-connect/token)
   ```

2. Run commands with `op run` wrapper:
   ```bash
   op run --server https://{connect-hostname}:8200 -- python3 manage.py config ubuntu-base 01
   ```

#### Vault Structure

- Vault: `op://homelab-gitops/`
  - `prod/` — Production secrets (vCenter, SSH, API keys)
  - `dev/` — Development/test secrets
  - `ci/` — CI/CD automation secrets

#### 1Password Connect Server

- **Location:** 10.10.10.30:8200
- **Token:** `/etc/op-connect/token` (restricted: 0600)
- **Access:** Central authentication broker for all projects

For more details, see:
- `docs/1PASSWORD_VAULTS.md` — Vault structure and roles
- `docs/DOCKER_SECRETS_INTEGRATION.md` — Docker usage
- `docs/GITHUB_ACTIONS_SECRETS.md` — CI/CD usage

## Emergency Procedures

### Token Compromise

1. Notify ops team immediately
2. Do NOT commit exposed token
3. Follow "Rotating Connect Token" in docs/SECRETS_RUNBOOK.md
4. Audit access logs: `grep compromised /var/log/op-connect/access.log`

### Service Down

If 1Password Connect is unavailable:
1. Check health: `curl https://{connect-hostname}:8200/health`
2. Restart: `docker restart op-connect-api op-connect-sync`
3. Verify: `curl https://{connect-hostname}:8200/health`
4. If still down, check 1Password cloud status: https://status.1password.com

### Secret Rotation

See docs/SECRETS_RUNBOOK.md → "Rotating Connect Token" section

## Critical Files to Understand

- **manage.py:** Core orchestrator; all CLI commands start here
- **ansible/site.yml:** Master playbook with tag-based role routing
- **tofu/main.tf:** vSphere provisioning logic; creates/updates VMs
- **config/metadata.yml:** Runtime metadata mapping tags to roles and playbooks
- **scripts/matrix_test.py:** E2E validation; tests all command aliases and profile/playbook relationships
- **GEMINI.md:** Engineering standards and policies (reference before changing conventions)

## Debugging Tips

1. **Lint failures:** Run `python3 scripts/lint_config.py` to catch YAML/schema issues before deployment
2. **vCenter connectivity:** Use `govc` (in `build/` or system PATH) to inspect vCenter objects
3. **Testinfra failures:** Add `--hosts='ansible@<ip>'` and `--sudo` to target the actual VM
4. **Ansible issues:** Increase verbosity: `ansible-playbook -vvv` (available through manage.py)
5. **OpenTofu drift:** Run `python3 manage.py status` to compare workspace state with vCenter reality
6. **1Password access:** Verify `op` CLI installed and `OP_SERVICE_ACCOUNT_TOKEN` exported

## Key Dependencies

- **typer & rich:** CLI framework and formatting
- **pyyaml:** Profile/metadata parsing
- **pytest-testinfra:** VM validation
- **pexpect & paramiko:** SSH automation
- **OpenTofu:** IaC provisioning
- **Ansible:** Post-deployment configuration
- **Packer:** Golden image building
