# 1Password Secrets Inventory

This repo uses `repo-homelab-gitops` for repo-local build and host values, plus shared platform vaults for vCenter, OPNsense, Technitium, and GitHub runner credentials. `config/secrets.env` is the committed reference file; it must contain only `op://` references or plain non-secret defaults.

## Vaults and items

| Scope | Vault | Item | Notes |
| --- | --- | --- | --- |
| Repo infra | `repo-homelab-gitops` | `prod`, `ci`, `test`, `local-dev` | Build defaults, SSH admin material, ISO/build metadata |
| Shared vCenter | `platform-vcenter` | `vcenter`, `opnsense`, `technitium` | vSphere and network services reused across homelab automation |
| Shared runners | `platform-github-runners` | `github-runners` | Runner registration and test VM SSH material |

## Inventory

| Variable | Classification | Required | Target reference |
| --- | --- | --- | --- |
| `VCENTER_SERVER`, `VCENTER_USERNAME`, `VCENTER_PASSWORD` | secret/sensitive config | OpenTofu/Packer/Ansible | `op://platform-vcenter/vcenter/<FIELD>` |
| `VCENTER_DATACENTER`, `VCENTER_CLUSTER`, `VCENTER_DATASTORE`, `VCENTER_NETWORK`, `VCENTER_*_FOLDER` | sensitive config | infra workflows | `op://platform-vcenter/vcenter/<FIELD>` |
| `CONTENT_LIBRARY_NAME`, `CONTENT_LIBRARY_ITEM_NAME` | sensitive config | template build/deploy | `op://platform-vcenter/vcenter/<FIELD>` |
| `SSH_ADMIN_USERNAME`, `SSH_ADMIN_PASSWORD`, `SSH_ADMIN_SSH_PUBKEY`, `SSH_PRIVATE_KEY_PATH` | secret/sensitive config | Ansible/Packer | `op://repo-homelab-gitops/prod/<FIELD>` |
| `UBUNTU_*_ISO_URL`, `UBUNTU_*_ISO_CHECKSUM`, `PHOTON_ISO_URL`, `PHOTON_ISO_CHECKSUM` | sensitive config | image builds | `op://repo-homelab-gitops/prod/<FIELD>` |
| `PACKER_FIRMWARE`, `TEMPLATE_CPU_COUNT`, `TEMPLATE_MEMORY_MB`, `TEMPLATE_DISK_SIZE_MB` | sensitive config | image builds | `op://repo-homelab-gitops/prod/<FIELD>` |
| `OPNSENSE_URL`, `OPNSENSE_KEY`, `OPNSENSE_SECRET` | secret/sensitive config | network automation | `op://platform-vcenter/opnsense/<FIELD>` |
| `TECHNITIUM_HOST`, `TECHNITIUM_TOKEN` | secret/sensitive config | DNS automation | `op://platform-vcenter/technitium/<FIELD>` |
| `GITHUB_PERSONAL_ACCESS_TOKEN` | secret | GitHub automation | `op://platform-github-runners/github-runners/GITHUB_PERSONAL_ACCESS_TOKEN` |
| `TEST_VM_HOST`, `TEST_VM_SSH_KEY` | secret/sensitive config | runner/test VM CI | Add to `op://platform-github-runners/github-runners/<FIELD>` before enabling live CI test VM jobs |
| `DEPLOY_VM_NAME`, `DEPLOY_CPU_COUNT`, `DEPLOY_MEMORY_MB`, `NODE_HOSTNAME`, `NODE_FQDN`, `SSH_ADMIN_GROUP`, `SSH_ADMIN_CIDRS`, `NTP_SERVERS`, `DEPLOY_ESXI_HOST` | plain/sensitive config | per deployment | Keep in profile/config files unless environment-specific secrecy is required |

## Usage

```bash
op run --env-file config/secrets.env -- python3 manage.py <command>
```

CI should use `OP_SERVICE_ACCOUNT_TOKEN` scoped to `repo-homelab-gitops`, `platform-vcenter`, and `platform-github-runners` only. Production infra jobs should use protected GitHub environments and should not write resolved env files to disk.

`OP_SERVICE_ACCOUNT_TOKEN` is the bootstrap credential for reading `config/secrets.env`; keep it as a GitHub environment/repo secret, not as an `op://` field in this file.

## Maintenance

When adding a new secret-backed variable, update `config/secrets.env`, this inventory, and the relevant tests or workflow smoke checks. Rotate by updating 1Password first, restarting or redeploying consumers, then running the protected validation workflow.
