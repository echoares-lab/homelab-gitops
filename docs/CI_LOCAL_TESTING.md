# Testing CI Locally

Before pushing changes that touch CI workflows, test dependencies, or test files, validate your changes locally to catch issues before CI runs.

## Quick Validation (Before Commit)

Run the CI configuration validator to catch common mistakes:

```bash
python3 scripts/validate_ci_config.py
```

This checks:
- ✅ Coverage configuration is not duplicated
- ✅ All dependencies are declared in requirements.txt
- ✅ Test files referenced in workflows exist
- ✅ Coverage thresholds are consistent
- ✅ PYTHONPATH is configured for src/ imports
- ✅ Scripts referenced in workflows exist
- ✅ Code imports are declared in requirements.txt

**Pre-commit hook:** This validator runs automatically on commit. If it fails, fix the issues before committing.

## Full CI Simulation Locally

Test the exact same commands as CI before pushing:

### 1. Set up environment

```bash
# Create a clean virtual environment to simulate CI
python3 -m venv .venv-ci-test
source .venv-ci-test/bin/activate

# Install dependencies (same as CI)
pip install --upgrade pip
pip install -r requirements.txt
pip install yamllint ansible-lint flake8

# Optionally: install pytest plugins for integration tests
pip install pytest-testinfra paramiko pexpect
```

### 2. Run linting (same as CI)

```bash
# YAML linting
echo "=== YAML Linting ==="
yamllint config/profiles/*.yml config/metadata.yml || true
yamllint ansible/site.yml || true

# Ansible linting
echo "=== Ansible Linting ==="
ansible-lint ansible/ || true

# Python linting (PEP 8)
echo "=== Python Linting (flake8) ==="
flake8 manage.py scripts/ src/ tests/ --count --select=E9,F63,F7,F82 --show-source --statistics
flake8 manage.py scripts/ src/ tests/ --count --exit-zero --max-complexity=10 --max-line-length=127 --statistics

# Shell linting
echo "=== Shell Linting ==="
shellcheck scripts/*.sh || true

# CI config validation
echo "=== CI Configuration Validation ==="
python3 scripts/validate_ci_config.py
```

### 3. Run unit tests (same as CI)

```bash
# Set PYTHONPATH (same as CI workflow)
export PYTHONPATH=/full/path/to/repo/src

# Run tests with coverage (same as CI)
echo "=== Unit Tests with Coverage ==="
pytest tests/test_services/ tests/unit/ -v \
  --cov=services \
  --cov=src/opnsense \
  --cov=manage.py \
  --cov-report=term-missing \
  --cov-report=json \
  --cov-report=html:htmlcov

# Check coverage threshold
echo "=== Coverage Check ==="
python -m coverage report --fail-under=85 --precision=2
```

### 4. Cleanup

```bash
# Remove test environment
deactivate
rm -rf .venv-ci-test htmlcov .coverage .coverage.json
```

## Debugging Specific Issues

### Import Errors in Tests

**Error:** `ModuleNotFoundError: No module named 'opnsense'`

**Fix:** Ensure PYTHONPATH is set correctly:
```bash
export PYTHONPATH="$(pwd)/src"
pytest tests/unit/test_opnsense*.py -v
```

### Script Not Found in CI

**Error:** `python3: can't open file 'scripts/validate-ci-config.py': No such file or directory`

**Fix:** Check the exact filename:
```bash
ls scripts/ | grep validate
# Look for underscore vs hyphen in filename
```

### Coverage Below Threshold

**Error:** `Coverage below 85% threshold!`

**Fix:** Run tests and check which modules lack coverage:
```bash
pytest tests/test_services/ tests/unit/ --cov=services --cov=src/opnsense --cov-report=term-missing
```

Then add tests for uncovered code or adjust the coverage targets.

### Dependency Not Found During CI

**Error:** `ModuleNotFoundError: No module named 'requests'`

**Fix:** Add to requirements.txt and validate:
```bash
echo "requests" >> requirements.txt
python3 scripts/validate_ci_config.py
```

## Workflow

Recommended workflow before pushing:

```bash
# 1. Make code changes
# 2. Run the validator
python3 scripts/validate_ci_config.py

# 3. If validator passes, run full CI simulation
source .venv-ci-test/bin/activate
export PYTHONPATH="$(pwd)/src"
pytest tests/test_services/ tests/unit/ -v --cov=services --cov=src/opnsense --cov=manage.py --fail-under=85

# 4. If all pass, commit
git add ...
git commit -m "..."

# 5. If CI still fails on GitHub, check workflow logs for environment-specific issues
# (e.g., missing env vars, different Python version)
```

## CI Workflow Checklist

When modifying CI workflows:

- [ ] Run `python3 scripts/validate_ci_config.py` - passes ✅
- [ ] All test commands run locally without errors
- [ ] PYTHONPATH is set in env for src/ imports
- [ ] All referenced scripts/test files exist
- [ ] Coverage threshold matches between CI and local
- [ ] Dependencies added to requirements.txt (not just pip install in workflow)
- [ ] Pre-commit hook passes
- [ ] Commit message explains CI change

## Common CI Patterns

### Pattern: Add New Test File

1. Create test file: `tests/unit/test_feature.py`
2. Add test function: `def test_something():`
3. Run locally: `pytest tests/unit/test_feature.py -v`
4. Commit when passing
5. **CI runs automatically on push**

### Pattern: Add New Dependency

1. Add to `requirements.txt`: `echo "new-package" >> requirements.txt`
2. Run validator: `python3 scripts/validate_ci_config.py`
3. Run tests: `pytest tests/ -v`
4. Commit when passing
5. **CI will pick it up from requirements.txt**

### Pattern: Modify Workflow

1. Update `.github/workflows/workflow-name.yml`
2. Run validator: `python3 scripts/validate_ci_config.py`
3. Verify syntax: `yamllint .github/workflows/workflow-name.yml`
4. Test affected commands locally
5. Commit when validation passes

## References

- `.github/workflows/lint-and-unit-tests.yml` - Main CI workflow (what this simulates)
- `scripts/validate_ci_config.py` - CI configuration validator
- `pytest.ini` - Pytest configuration
- `requirements.txt` - Python dependencies
- `GEMINI.md` - Standards on CI changes
- `AGENTS.md` - Agent guidelines on CI validation
