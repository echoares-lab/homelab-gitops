# github_runner_ci

Applies **aggregated** CI dependencies from all registered repos onto self-hosted
GitHub Actions runners.

## Repo contract

Each repo that uses self-hosted CI ships:

```
requirements/ci-runner.manifest.yaml
```

Optional companion files referenced by the manifest (`system_packages_file`, `venv_packages`).

Register the repo in `config/ci-runner-repos.yaml`.

## Workflow

```bash
# 1) After changing any repo manifest or adding a repo to the registry:
make sync-ci-runners

# 2) Push updated packages/venv to runner hosts:
make apply-ci-runners

# Full runner provision (new VM) still uses:
#   ansible-playbook ansible/git-test-runner.yml -l tag_git_test -e runner_token=...
# which includes github_runner_base + github_runner + github_runner_ci
```

## Generated artifacts (do not edit)

- `ansible/generated/ci_runner/apt-packages.txt`
- `ansible/generated/ci_runner/pip-requirements.txt`
- `ansible/generated/ci_runner/vars.yaml`

Regenerate with `make sync-ci-runners`.
