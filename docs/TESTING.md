# Testing and CI Policy

This document establishes testing standards, CI configuration best practices, and procedures for maintaining test quality and reliability across the Unified GitOps Template Pipeline.

## Testing Hierarchy (3 Tiers)

### Tier 1: Unit Tests (Fast, No Infrastructure)
- **Purpose:** Validate business logic, orchestrator functions, service classes
- **Location:** `tests/test_services/` and `tests/test_manage_cli.py`
- **Run Time:** < 30 seconds
- **Dependencies:** No external services, VMs, or infrastructure
- **Coverage Goal:** 85% minimum (enforced in CI)
- **Trigger:** Every push/PR to any branch
- **Command:** `pytest tests/test_services/ tests/test_manage_cli.py -v --cov=services --cov=manage.py --cov-report=term-missing`

Unit tests are the foundation of quality. They should:
- Test core logic paths, error handling, input validation
- Use mocks/patches to isolate code under test
- Be deterministic and repeatable
- Run locally before pushing (see CI Validation Checklist)

### Tier 2: Integration Tests (Medium Speed, Self-Hosted VM)
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

### Tier 3: E2E Tests (Slow, Packer + vSphere + Full Pipeline)
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
pytest>=7.0
pytest-cov>=4.0
pyyaml
paramiko
pexpect
typer
rich
```

- CI install step: `pip install -r requirements.txt`
- Additional CI-only tools (yamllint, ansible-lint, flake8) installed separately in workflow
- Never assume tools are pre-installed in the runner
- Validate dependencies locally: `pip install -r requirements.txt && pytest`

### Rule 3: Test File References Must Be Validated
**Before adding test file paths to CI workflow, verify they exist locally**

```bash
# Before adding to CI workflow:
ls -la tests/test_services/
ls -la tests/test_manage_cli.py
pytest --collect-only tests/test_services/ tests/test_manage_cli.py
```

- Test file paths in CI: `tests/test_services/ tests/test_manage_cli.py`
- These paths are validated in the fixture and must exist
- When adding new test tier (e.g., integration), add to a SEPARATE CI workflow job
- Use `--collect-only` flag to verify pytest can find tests before pushing

### Rule 4: Configuration Values Must Match Across Files
**Coverage threshold and test paths must be consistent**

| Setting | Value | Location(s) |
|---------|-------|-------------|
| Coverage threshold | 85% | CI workflow line 75 |
| Test files (unit) | `tests/test_services/ tests/test_manage_cli.py` | CI workflow line 68 |
| Coverage packages | `services` and `manage.py` | CI workflow lines 69-70 |
| Test markers | `unit`, `integration`, `e2e` | pytest.ini line 11-15 |
| Testinfra host | `localhost` (local) or `ansible@<ip>` (remote) | pytest.ini line 19, test command |

When updating ANY of these values, update ALL locations to maintain consistency.

### Rule 5: Local Verification Before Pushing CI Changes
**Always test CI changes locally before pushing**

```bash
# Install local dependencies
pip install -r requirements.txt pytest pytest-cov

# Run unit tests locally with exact coverage config
pytest tests/test_services/ tests/test_manage_cli.py \
  --cov=services --cov=manage.py --cov-report=term-missing

# Verify coverage threshold
python -m coverage report --fail-under=85 --precision=2

# Validate YAML files referenced in CI
yamllint config/profiles/*.yml config/metadata.yml
```

Do NOT push CI changes without verifying they work locally first. This prevents breaking the workflow for all teammates.

---

## Common Mistakes & Fixes

| Symptom | Root Cause | Fix |
|---------|-----------|-----|
| "pytest: command not found" in CI | `pytest` not in requirements.txt | Add `pytest>=7.0` to requirements.txt |
| "ModuleNotFoundError: No module named 'pytest_cov'" | Coverage tool not installed | Add `pytest-cov>=4.0` to requirements.txt, run `pip install -r requirements.txt` |
| Coverage mismatch (80% locally, 75% in CI) | Different test files or coverage config | Verify test paths match in CI workflow and locally; ensure only one coverage config |
| "No such file or directory: tests/test_services/" | Wrong path in CI workflow | Run `ls -la tests/test_services/` locally; verify path exists before pushing |
| Coverage reports missing in artifact | Wrong report format in workflow | Ensure `--cov-report=html:htmlcov` and `--cov-report=json` are in pytest command |
| "Threshold 85% not met" but tests pass locally | Local coverage differs from CI | Run with exact same command: `pytest tests/test_services/ tests/test_manage_cli.py --cov=services --cov=manage.py --cov-report=term-missing` |
| Integration test passes locally, fails in CI | Test requires infrastructure unavailable in CI | Use `@pytest.mark.integration` to skip in non-infrastructure CI jobs |

---

## Safe vs Risky Changes

### Safe Changes (Low Risk)
- ✅ Adding new unit tests in `tests/test_services/` or `tests/test_manage_cli.py`
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
   - Dev/test dependency (used in CI/tests only): install separately in CI workflow

2. **For code dependencies:**
   ```bash
   # Update requirements.txt
   echo "package-name==1.2.3" >> requirements.txt
   
   # Install locally
   pip install -r requirements.txt
   
   # Test that code still works
   pytest tests/test_services/ tests/test_manage_cli.py
   ```

3. **For CI-only dependencies (yamllint, ansible-lint, flake8):**
   - Add to CI workflow `Install dependencies` step
   - Document in VERSIONS_AND_UPDATES.md
   - Do NOT add to requirements.txt

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
3. Run local tests: `pytest tests/test_services/ tests/test_manage_cli.py`
4. Document removal in VERSIONS_AND_UPDATES.md

---

## CI Validation Checklist (7 Items)

Use this checklist before every push to CI-related files (workflows, requirements.txt, pytest.ini, conftest.py):

- [ ] **1. Dependencies verified:** `pip install -r requirements.txt` succeeds without errors
- [ ] **2. Local tests pass:** `pytest tests/test_services/ tests/test_manage_cli.py -v` runs and all tests pass
- [ ] **3. Coverage meets threshold:** `python -m coverage report --fail-under=85` passes (or meets current policy)
- [ ] **4. Test files exist:** All test paths in CI workflow exist locally and are discoverable by pytest
- [ ] **5. YAML linting works:** `yamllint config/profiles/*.yml config/metadata.yml` completes without errors
- [ ] **6. Config values match:** Coverage threshold, test paths, and coverage packages are identical in CI workflow and locally
- [ ] **7. Documentation updated:** TESTING.md and VERSIONS_AND_UPDATES.md reflect the changes (if applicable)

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
