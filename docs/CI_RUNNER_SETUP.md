# CI Runner Setup (multi-repo)

Self-hosted GitHub Actions runners are provisioned by **homelab-gitops** Ansible.
Each application repo declares what it needs; homelab-gitops **aggregates** manifests and applies them to runner hosts.

Runner profiles allocate a 400 GB virtual disk. During runner baseline provisioning,
`github_runner_base` expands the root partition and filesystem so `/` can use the
full disk exposed by OpenTofu/vSphere instead of remaining at the golden template
size.

## Architecture

```
┌─────────────────────┐     ┌──────────────────────────────┐
│  ai-gateway         │     │  homelab-gitops              │
│  requirements/    │     │  config/ci-runner-repos.yaml  │
│  ci-runner.manifest │────▶│  scripts/sync_ci_runner_*.py  │
└─────────────────────┘     │  ansible/generated/ci_runner/ │
┌─────────────────────┐     │  ansible/roles/github_runner_ci│
│  other-repo       │────▶│  make sync-ci-runners        │
└─────────────────────┘     │  make apply-ci-runners       │
                          └──────────────────────────────┘
                                      │
                                      ▼
                          ┌──────────────────────────────┐
                          │  dev-01 / cf-runner VMs    │
                          │  apt + seed venv + cache    │
                          └──────────────────────────────┘
```

## Per-repo contract

Add to any repo that uses self-hosted CI:

**`requirements/ci-runner.manifest.yaml`**

```yaml
schema_version: 1
repo: my-repo

python:
  version: "3.12"                    # pin interpreter for seed venv
  venv_packages: requirements/ci-runner-venv.txt

system_packages_file: requirements/ci-runner-system-packages.txt   # optional

apt_packages:                          # optional extra apt names
  - some-package

pip_requirements_files:                  # optional extra pip files
  - path/to/extra-requirements.txt
```

Register the repo in **`config/ci-runner-repos.yaml`** (homelab-gitops).

## Operator workflow

### When you add a new repo

1. Add `requirements/ci-runner.manifest.yaml` (and pip/apt files) in the repo.
2. Add an entry to `homelab-gitops/config/ci-runner-repos.yaml`.
3. From homelab-gitops root:

```bash
make sync-ci-runners      # regenerate ansible/generated/ci_runner/*
make apply-ci-runners    # push to tag_git_test / tag_cf_runner hosts
```

`ansible/generated/ci_runner/apt-packages.txt`,
`ansible/generated/ci_runner/pip-requirements.txt`, and
`ansible/generated/ci_runner/vars.yaml` are generated locally and ignored by
git. They include local checkout paths and should be regenerated instead of
edited or committed.

### When an existing repo changes CI deps

1. Edit that repo's manifest or `requirements/ci-runner-venv.txt`.
2. `make sync-ci-runners && make apply-ci-runners`

### New runner VM (full provision)

Unchanged except `github_runner_ci` is now included:

```bash
ansible-playbook ansible/git-test-runner.yml \
  -i ansible/inventory/vmware_vms.yml \
  -l tag_git_test \
  -e runner_token=<org-token>
```

Or Cloudflare runner playbook for org-level runners.

### Existing runner maintenance

Use the token-free maintenance playbook when you need to repair storage or
baseline packages on already-registered runners. This does not re-register the
GitHub runner and does not require a GitHub runner token:

```bash
ansible-playbook ansible/runner-maintenance.yml \
  -i ansible/inventory/vmware_vms.yml
```

If vCenter tags are unavailable, limit by hostname pattern or inventory host
list instead of passing a runner token.

## What persists on the runner

| Layer | Persists? | Managed by |
|-------|-----------|------------|
| apt packages | Yes | Ansible (`github_runner_base` + `github_runner_ci`) |
| `/var/cache/ai-gateway/` | Yes | `github_runner_ci` |
| Seed venv `/var/cache/ai-gateway/venv-ci-seed` | Yes | `github_runner_ci` |
| `~/ci-runner-pip-requirements.txt` | Yes | copy of aggregated file |
| CI job `.venv-ci` in workspace | No (cache restores) | GitHub Actions cache |

## Roles

| Role | Purpose |
|------|---------|
| `log_retention` | Profile-owned log retention and journald size/time caps |
| `github_runner_base` | Grow root filesystem to the full runner disk, then install Go, Node, python3.12, direnv, base apt |
| `docker` | docker + compose |
| `github_runner` | Install/register actions-runner service |
| `github_runner_ci` | **Aggregated** multi-repo apt + pip seed venv |

## ai-gateway pointer

This repo ships `requirements/ci-runner.manifest.yaml` and is registered in `config/ci-runner-repos.yaml`.
Manual bootstrap script `scripts/ci-runner-bootstrap.sh` remains for ad-hoc repair without Ansible.
