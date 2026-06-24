# Testing and CI Policy

This document establishes testing standards, CI configuration best practices, and procedures for maintaining test quality and reliability across the Unified GitOps Template Pipeline.

## Testing Hierarchy (4 Tiers)

### Tier 1: Unit Tests (Fast, No Infrastructure)
- **Purpose:** Validate business logic, orchestrator functions, service classes
- **Location:** `tests/unit/` and `tests/cli/`
- **Run Time:** < 30 seconds
- **Dependencies:** No external services, VMs, or infrastructure
- **Coverage Goal:** 85% minimum (enforced in CI)
- **Trigger:** Every push/PR to any branch
- **Command:** `pytest tests/ -v --cov=homelab_gitops --cov=manage.py --cov-report=term-missing --cov-report=json --cov-report=html:htmlcov`

Unit tests are the foundation of quality. They should:
- Test core logic paths, error handling, input validation
- Use mocks/patches to isolate code under test
- Be deterministic and repeatable
- Run locally before pushing (see CI Validation Checklist)

### Tier 2: Package Build and Clean Install Smoke (Fast, No Infrastructure)
- **Purpose:** Validate the Python package builds as wheel/sdist and the installed console script starts outside the source checkout
- **Location:** `.github/workflows/lint-and-unit-tests.yml`
- **Run Time:** < 2 minutes
- **Dependencies:** `build` and package runtime dependencies from `pyproject.toml`
- **Trigger:** Every push/PR to any branch
- **Command:** `python -m build --sdist --wheel`, then install `dist/*.whl` into a fresh venv and run `homelab-gitops --help`

The clean-install smoke test must use the console script from the fresh virtual environment, not `python -m` from the source tree. This proves packaging metadata includes the CLI entry point and importable package modules.

### GitOps Manifest Validation (Fast, No Infrastructure)
- **Purpose:** Render checked-in Kubernetes kustomizations and catch malformed YAML, missing local resource paths, and missing basic Kubernetes object fields
- **Location:** `scripts/validate_gitops_manifests.py`
- **Run Time:** < 10 seconds
- **Dependencies:** Python and `pyyaml` from `requirements.txt`; no cluster, `kubectl`, or standalone `kustomize` binary required
- **Command:** `python3 scripts/validate_gitops_manifests.py`

Run this command locally after changing files under `kubernetes/`. It validates repository manifest structure only; it does not perform API-server admission checks.

### Tier 3: Integration Tests (Medium Speed, Self-Hosted VM)
- **Purpose:** Validate orchestrator against real infrastructure (vCenter, vSphere, testinfra)
- **Location:** `tests/integration/`
- **Run Time:** 2-5 minutes per test
- **Dependencies:** Self-hosted runner with access to vCenter, test VM, Ansible
- **Coverage Goal:** Coverage as percentage of integration test files (tracked separately)
- **Trigger:** Post-merge to develop/master, or manual trigger on PR
- **Command:** `pytest tests/integration/ -v --hosts='ansible@<vm-ip>' --sudo`

Integration tests verify that components work together. They should:
- Target real VMs provisioned for testing
- Use Ansible discovery or testinfra to inspect VM state
- Validate configuration applied by roles (Docker, security, GitHub runner, etc.)
- Be skipped gracefully if infrastructure unavailable (conftest.py handles this)

### Tier 4: E2E Tests (Slow, Packer + vSphere + Full Pipeline)
- **Purpose:** Validate complete workflow: Build → Deploy → Configure → Test
- **Location:** `tests/e2e/`
- **Run Time:** 30-60 minutes per profile
- **Dependencies:** Packer, vSphere, OpenTofu workspace, Ansible, golden image build
- **Coverage Goal:** All supported profiles and major workflows
- **Trigger:** Manual trigger on release branch or scheduled nightly
- **Command:** `python3 manage.py all PROFILE INDEX --host ESXI_HOST`

E2E tests are expensive but comprehensive. They should:
- Test the complete pipeline for each profile (ubuntu-2404, photon-docker, etc.)
- Validate golden image hardening is preserved
- Confirm post-deployment configuration works end-to-end
- Run only when explicitly requested (manual trigger or scheduled job)

---

## CI Configuration Standards (5 Rules)

### Rule 1: Single Source of Truth
**Coverage configuration must live in ONE place:** `.github/workflows/lint-and-unit-tests.yml`

- Do NOT duplicate coverage settings in `pytest.ini`, `pyproject.toml`, or other files
- `pytest.ini` contains markers and test discovery, NOT coverage config
- CI workflow is the authoritative source for coverage thresholds (currently 85%)
- Keep other config files minimal and focused on their core purpose

### Rule 2: All Dependencies Declared in requirements.txt
**Every tool must be explicitly listed in `requirements.txt`**

Required packages for CI to function:
```
pytest==8.4.2
pytest-cov==7.1.0
build==1.5.0
yamllint==1.38.0
ansible-lint==26.4.0
flake8==7.3.0
pytest-testinfra==10.2.2
pyyaml
paramiko==3.4.0
pexpect==4.9.0
typer
rich
```

- CI install step: `pip install -r requirements.txt`
- CI-only tools used by workflows must also be pinned in `requirements.txt`
- Never assume tools are pre-installed in the runner
- Validate dependencies locally: `pip install -r requirements.txt && pytest`

### Rule 3: Test File References Must Be Validated
**Before adding test file paths to CI workflow, verify they exist locally**

```bash
# Before adding to CI workflow:
ls -la tests/unit/
ls -la tests/cli/
pytest --collect-only tests/unit/ tests/cli/
```

- Unit and CLI test paths in CI: `tests/`
- Integration test path in CI: `tests/integration/`
- E2E test path in CI: `tests/e2e/`
- These paths are validated in the fixture and must exist
- When adding new test tier (e.g., integration), add to a SEPARATE CI workflow job
- Use `--collect-only` flag to verify pytest can find tests before pushing

### Rule 4: Configuration Values Must Match Across Files
**Coverage threshold and test paths must be consistent**

| Setting | Value | Location(s) |
|---------|-------|-------------|
| Coverage threshold | 85% | `.github/workflows/lint-and-unit-tests.yml` |
| Test files (unit) | `tests/` | `.github/workflows/lint-and-unit-tests.yml` |
| Coverage packages | `homelab_gitops` and `manage.py` | `.github/workflows/lint-and-unit-tests.yml` |
| Package smoke | Build wheel/sdist, install wheel in clean venv, run installed CLI help | `.github/workflows/lint-and-unit-tests.yml` |
| Test markers | `unit`, `integration`, `e2e` | pytest.ini line 11-15 |
| Testinfra host | `localhost` (local) or `ansible@<ip>` (remote) | pytest.ini line 19, test command |

When updating ANY of these values, update ALL locations to maintain consistency.

### Rule 5: Local Verification Before Pushing CI Changes
**Always test CI changes locally before pushing**

```bash
# Install local dependencies
pip install -r requirements.txt

# Run unit tests locally with exact coverage config
pytest tests/ -v \
  --cov=homelab_gitops \
  --cov=manage.py \
  --cov-report=term-missing \
  --cov-report=json \
  --cov-report=html:htmlcov

# Verify coverage threshold
python -m coverage report --fail-under=85 --precision=2

# Build and smoke test the installed package
python -m build --sdist --wheel
python -m venv /tmp/homelab-gitops-clean-install
/tmp/homelab-gitops-clean-install/bin/python -m pip install --upgrade pip
/tmp/homelab-gitops-clean-install/bin/pip install dist/*.whl
/tmp/homelab-gitops-clean-install/bin/homelab-gitops --help
/tmp/homelab-gitops-clean-install/bin/homelab-gitops doctor --help

# Validate YAML files referenced in CI
yamllint config/profiles/*.yml config/metadata.yml

# Validate Ansible role paths, playbook references, and metadata
python3 scripts/validate_ansible_structure.py
```

Do NOT push CI changes without verifying they work locally first. This prevents breaking the workflow for all teammates.

---

## Common Mistakes & Fixes

| Symptom | Root Cause | Fix |
|---------|-----------|-----|
| "pytest: command not found" in CI | `pytest` not in requirements.txt | Add a pinned `pytest==...` entry to requirements.txt |
| "ModuleNotFoundError: No module named 'pytest_cov'" | Coverage tool not installed | Add a pinned `pytest-cov==...` entry to requirements.txt, run `pip install -r requirements.txt` |
| "No module named build" in CI | Build frontend not installed | Add a pinned `build==...` entry to requirements.txt, run `pip install -r requirements.txt` |
| Coverage mismatch (80% locally, 75% in CI) | Different test files or coverage config | Verify test paths match in CI workflow and locally; ensure only one coverage config |
| "No such file or directory" for tests in CI | Wrong path in CI workflow | Run `pytest --collect-only <path>` locally; verify path exists before pushing |
| Coverage reports missing in artifact | Wrong report format in workflow | Ensure `--cov-report=html:htmlcov` and `--cov-report=json` are in pytest command |
| "Threshold 85% not met" but tests pass locally | Local coverage differs from CI | Run with the exact CI pytest command from `.github/workflows/lint-and-unit-tests.yml` |
| Integration test passes locally, fails in CI | Test requires infrastructure unavailable in CI | Use `@pytest.mark.integration` to skip in non-infrastructure CI jobs |

---

## Safe vs Risky Changes

### Safe Changes (Low Risk)
- ✅ Adding new unit tests in `tests/unit/` or CLI tests in `tests/cli/`
- ✅ Updating test assertions (does not change coverage config)
- ✅ Adding new test files with descriptive names (ensure `test_*.py` pattern)
- ✅ Refactoring test code for clarity
- ✅ Adding new test markers (e.g., `@pytest.mark.unit`)
- ✅ Improving CI job descriptions or adding comments

### Risky Changes (High Risk — Requires Peer Review)
- ⚠️ Modifying coverage threshold in CI workflow (must update TESTING.md + ROADMAP.md)
- ⚠️ Changing test file paths in CI workflow (verify locally first, document in TESTING.md)
- ⚠️ Adding new dependencies to requirements.txt (document in VERSIONS_AND_UPDATES.md)
- ⚠️ Modifying pytest.ini markers or discovery rules
- ⚠️ Changing coverage report format or locations
- ⚠️ Adding new CI workflows or jobs
- ⚠️ Modifying conftest.py fixtures or hooks

**Before submitting a PR with risky changes:**
1. Test locally using exact CI command
2. Document the change in VERSIONS_AND_UPDATES.md
3. Update this file (TESTING.md) if it affects testing standards
4. Request code review from @TheNorthWestPassage
5. Link to related ADR or design decision in DESIGN.md

---

## Dependency Management

### Adding a New Dependency

1. **Identify the type:**
   - Code dependency (used in manage.py/services/): goes in `requirements.txt`
   - Dev/test dependency (used in CI/tests only): add a pinned entry to `requirements.txt`

2. **For code dependencies:**
   ```bash
   # Update requirements.txt
   echo "package-name==1.2.3" >> requirements.txt
   
   # Install locally
   pip install -r requirements.txt
   
   # Test that code still works
   pytest tests/unit/ tests/cli/
   ```

3. **For CI-only dependencies (yamllint, ansible-lint, flake8):**
   - Add a pinned entry to `requirements.txt`
   - Document in VERSIONS_AND_UPDATES.md
   - Keep the CI workflow install step using `pip install -r requirements.txt`

4. **Before committing:**
   - Verify `pip install -r requirements.txt` succeeds
   - Ensure no version conflicts: `pip check`
   - Test that tests still pass
   - Update VERSIONS_AND_UPDATES.md with new dependency and version

### Pinning Versions
- Use `==` for strict pinning (e.g., `pytest==7.4.3`)
- Use `>=` for minimum version with flexibility (e.g., `pytest>=7.0`)
- Avoid unpinned dependencies in production/CI
- Document version choices in VERSIONS_AND_UPDATES.md

### Removing Dependencies
1. Verify no code imports the package: `grep -r "import package" manage.py scripts/ services/`
2. Remove from requirements.txt
3. Run local tests: `pytest tests/unit/ tests/cli/`
4. Document removal in VERSIONS_AND_UPDATES.md

---

## Optional: Pre-Commit Hooks

Local validation before pushing can catch common issues early. Pre-commit hooks run automatically before each commit and are entirely optional.

### Installation

```bash
# Install pre-commit framework
pip install pre-commit

# Install the git hooks
pre-commit install
```

### What Gets Validated

The `.pre-commit-config.yaml` file configures these checks:

| Hook | Purpose | Triggers On |
|------|---------|-------------|
| `check-yaml` | YAML syntax validation (with unsafe mode) | `.github/workflows/*.yml` files |
| `validate-ci-config` | CI configuration consistency check | CI workflow files, pytest.ini, requirements*.txt, pyproject.toml |
| `validate-test-references` | Verifies test directory structure exists | `.github/workflows/*.yml` files |

### Manual Execution

Run all hooks on all files without committing:

```bash
# Check all staged files
pre-commit run

# Check all files (useful after cloning)
pre-commit run --all-files
```

### Bypassing Hooks (If Needed)

If a hook blocks a legitimate commit:

```bash
# Skip all hooks for this commit only
git commit --no-verify

# Or disable hooks temporarily
pre-commit uninstall
# ... make your commit ...
pre-commit install
```

Note: Skipping hooks should be rare. If hooks consistently fail on valid changes, consider updating the hook configuration in `.pre-commit-config.yaml`.

---

## CI Validation Checklist (8 Items)

Use this checklist before every push to CI-related files (workflows, requirements.txt, pytest.ini, conftest.py):

- [ ] **1. Dependencies verified:** `pip install -r requirements.txt` succeeds without errors
- [ ] **2. Local tests pass:** `pytest tests/unit/ tests/cli/ -v` runs and all tests pass
- [ ] **3. Coverage meets threshold:** `python -m coverage report --fail-under=85` passes (or meets current policy)
- [ ] **4. Test files exist:** All test paths in CI workflow exist locally and are discoverable by pytest
- [ ] **5. YAML linting works:** `yamllint config/profiles/*.yml config/metadata.yml` completes without errors
- [ ] **6. Config values match:** Coverage threshold, test paths, and coverage packages are identical in CI workflow and locally
- [ ] **7. Package build and clean install pass:** `python -m build --sdist --wheel`, clean venv install, and installed CLI smoke commands succeed
- [ ] **8. Documentation updated:** TESTING.md and VERSIONS_AND_UPDATES.md reflect the changes (if applicable)

---

## Related Documentation

- **CLAUDE.md:** Project overview, quick start commands, repository structure
- **GEMINI.md:** Engineering standards, naming conventions, code quality policies
- **DESIGN.md:** Architecture decisions, testing strategy rationale
- **RUNBOOK.md:** Operational procedures for deploying and testing
- **VERSIONS_AND_UPDATES.md:** Release notes, dependency updates, version history
- **CI Workflow:** `.github/workflows/lint-and-unit-tests.yml` — source of truth for CI config
- **pytest.ini:** Test discovery and marker definitions
- **conftest.py:** Shared test fixtures, marker handling, testinfra config

---

## Questions & Support

If you encounter CI issues not covered in this document:

1. Check the CI logs in GitHub Actions (Workflow > Job > Step output)
2. Run the failing command locally with verbose flags: `pytest -vvv`
3. Verify all dependencies: `pip list | grep -E "pytest|coverage"`
4. Consult DESIGN.md for testing strategy context
5. Open an issue or contact @TheNorthWestPassage with logs and reproduction steps
