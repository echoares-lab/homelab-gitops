# CI Runner Generated Files

This directory is populated by `make sync-ci-runners`, which runs
`scripts/sync_ci_runner_requirements.py` and writes the files consumed by the
`github_runner_ci` role:

- `apt-packages.txt`
- `pip-requirements.txt`
- `vars.yaml`

Those files are intentionally ignored because they include local checkout paths
and are regenerated immediately before `make apply-ci-runners`.
