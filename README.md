# Unified GitOps Template Pipeline

A Python-orchestrated automation framework for building, provisioning, and configuring
Ubuntu and VMware Photon OS nodes on vSphere, using Packer (golden images),
OpenTofu (virtual hardware), and Ansible (OS state).

## Documentation

All project documentation — architecture, design specs, runbooks, roadmap, plans, and
status notes — lives in the Obsidian vault, not in this repository
(per [Master-Policy §1.6](/home/dev/obsidian-vault/02%20Areas/Policies/Master-Policy.md),
Obsidian-First Documentation Minimalism):

**`/home/dev/obsidian-vault/01 Projects/Homelab-Gitops/`**

- `Runbooks/RUNBOOK.md` — installation, command usage, troubleshooting
- `Specs/DESIGN.md` — workflow diagrams and hardware standards
- `Specs/ROADMAP.md` — project status and milestones
- `Specs/ENGINEERING_STANDARDS.md` — naming, linting, and architecture rules
- `Specs/TOOLING.md` — tooling inventory and required versions

Agent directives are in [AGENTS.md](./AGENTS.md).

## Requirements

Python >= 3.10, plus Ansible, OpenTofu, and Packer on `PATH`. Dependencies are
managed with `uv`:

```bash
uv venv && uv sync
```

## Quick start

Configure credentials (secret references resolve from OpenBao/1Password; see the
secrets runbook in the vault):

```bash
cp config/vault.yml.example config/vault.yml
echo 'your_secure_password' > config/.vault_pass
ansible-vault encrypt config/vault.yml --vault-password-file config/.vault_pass
```

Deploy a node through the full lint → deploy → config → test pipeline:

```bash
python3 manage.py all photon-docker 02 esxi-01.mgmt.plexplease.com
```

Running `python3 manage.py` with no arguments launches an interactive command builder.

## Tests and linting

```bash
pytest -q
yamllint .
ansible-lint
```

## Repository layout

- `src/homelab_gitops/`, `manage.py` — orchestrator CLI
- `ansible/` — roles and dynamic inventory (each role's `README.md` documents its interface)
- `config/` — YAML node profiles and secret references
- `packer/` — golden image build definitions
- `tofu/` — declarative HCL for vSphere provisioning
- `scripts/` — operational helper scripts
- `tests/` — unit, integration, and Testinfra validation suites
