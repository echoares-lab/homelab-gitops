# Tooling inventory: homelab-gitops

## 1. Repository identity and status

- **Repository:** homelab-gitops
- **Status:** active infrastructure automation
- **Git root:** `.`
- **Nested applications:** Python package, Ansible roles, Packer images, and OpenTofu modules are documented here.

## 2. Runtime tools

| Tool | Version | Category | Required | Source | Purpose | Installation | Verification |
|---|---|---|---|---|---|---|---|
| Python | >=3.10 | Runtime | Required | `pyproject.toml` | Run automation CLI/tests | Create venv; install requirements | `python --version` |
| Ansible | unversioned | Runtime | Required | `requirements.txt` | Configure hosts | Install requirements | `ansible --version` |
| OpenTofu | unversioned | Runtime | Required for provisioning | `tofu/main.tf` | Provision vSphere resources | Install OpenTofu | `tofu version` |
| Packer | unversioned | Runtime | Required for images | `packer/ubuntu2404.pkr.hcl` | Build golden images | Install Packer | `packer version` |

## 3. Project/build tools

| Tool | Version | Category | Required | Source | Purpose | Installation | Verification |
|---|---|---|---|---|---|---|---|
| setuptools | pyproject.toml | Project | Required | `pyproject.toml` | Package CLI | `pip install -e .` | `homelab-gitops --help` |
| Make | unversioned | Project | Optional | `Makefile` | Runner sync/deployment tasks | Install make | `make help-ci-runners` |
| Ansible Vault | unversioned | Project | Operator-only | `README.md` | Encrypt configuration | Included with Ansible | `ansible-vault --version` |

## 4. Developer tools

| Tool | Version | Category | Required | Source | Purpose | Installation | Verification |
|---|---|---|---|---|---|---|---|
| pytest | 8.4.2 | Dev | Required | `requirements.txt` | Unit/integration tests | `pip install -r requirements.txt` | `pytest -q` |
| ansible-lint | 26.4.0 | Dev | Required | `requirements.txt` | Lint Ansible | Install requirements | `ansible-lint --version` |
| yamllint | 1.38.0 | Dev | Required | `requirements.txt` | Lint YAML | Install requirements | `yamllint --version` |

## 5. CI tools

| Tool | Version | Category | Required | Source | Purpose | Installation | Verification |
|---|---|---|---|---|---|---|---|
| GitHub Actions | unversioned | CI | CI-only | `.github/workflows/lint-and-unit-tests.yml` | Run lint/tests | GitHub-hosted | Workflow run |
| CycloneDX Python generator | unversioned | CI | CI-only | `.github/workflows/sbom.yml` | Generate Python dependency SBOM | Installed by workflow | `test -s homelab-gitops-python.cdx.json` |

## 6. Operations/deployment tools

| Tool | Version | Category | Required | Source | Purpose | Installation | Verification |
|---|---|---|---|---|---|---|---|
| vSphere/vCenter | unknown | Ops | Operator-only | `tofu/main.tf` | Host virtual machines | Operator-managed | OpenTofu plan |
| Docker | unversioned | Ops | Operator-only | `docker/op-connect/docker-compose.yml` | Run secret connector | Install Docker Compose | `docker compose config` |
| 1Password CLI | unversioned | Ops | Operator-only | `scripts/op-setup.sh` | Retrieve protected values | Install `op` | `op --version` |

## 7. Native source manifests

- `pyproject.toml` and `requirements.txt` define Python dependencies.
- Ansible YAML, Packer HCL, and OpenTofu HCL define infrastructure.
- CI workflows and Makefile define automation tasks.

## 8. Standard commands

- `pytest -q` — tests (source: `pytest.ini`).
- `make sync-ci-runners` — aggregate runner requirements (source: `Makefile`).
- `ansible-playbook ansible/site.yml` — configure nodes (source: `Makefile`).

## 9. Missing or unpinned tooling

- Ansible, OpenTofu, Packer, Docker, and 1Password CLI versions are not fully pinned.
- vSphere endpoint and credentials are intentionally excluded.

## 10. Future adoption notes

Evaluate `mise.toml` for Python, infrastructure CLIs, and task aliases; keep Ansible/OpenTofu/Packer files authoritative.

## SBOM artifact

`.github/workflows/sbom.yml` uploads `homelab-gitops-python.cdx.json` as `homelab-gitops-sbom`.
