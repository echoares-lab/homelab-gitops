# Unified GitOps Infrastructure (Legacy Monolith)

> [!NOTE]
> **Repository Decomposition Notice (2026-09-03):**
> This monolithic infrastructure repository has been decomposed into modular, lifecycle-isolated repositories:
> - **[`compute-infra`](../compute-infra)**: Owns VM lifecycle, Packer golden images, OpenTofu vSphere/Proxmox definitions, and Ansible node configuration.
> - **[`network-infra`](../network-infra)**: Owns SONiC Dell PowerSwitch N3224T-ON NOS configuration, Technitium DNS/DHCP schemas, and EnGenius EPC controller containers.
> - **[`k8s`](../k8s)**: Owns Kubernetes GitOps, ArgoCD applications, and Authentik service access configurations.

## Documentation

Project documentation lives directly in-repo under `docs/`:
- `docs/architecture.md` — system architecture overview and repository boundaries
- `docs/runbooks/` — operational runbooks and troubleshooting guides

Agent directives are defined in [AGENTS.md](./AGENTS.md).

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
