---
title: Testing Policy & CI Strategy
date: 2026-06-08
status: Draft
---

# Testing Policy & CI Strategy

## Overview

This document defines the unified testing strategy for the Unified GitOps Template Pipeline. The policy establishes quality gates at each stage of development and deployment, from local commits through production releases.

**Goals:**
- Catch infrastructure misconfigurations early (prevent weeks of manual troubleshooting like Packer golden image issues)
- Enable confident refactoring and architecture improvements
- Maintain high code quality (90% unit test coverage minimum)
- Provide fast feedback loops for developers (lint + unit tests on every PR)
- Ensure infrastructure consistency through integration and E2E validation

---

## Testing Pyramid: Three Tiers

The policy uses a three-tier testing pyramid, each with distinct scope, frequency, and blocking behavior.

### Tier 1: Unit Tests (Every PR — Required)

**Scope:** Logic validation without infrastructure or external dependencies. Tests the orchestrator, configuration validators, and utility functions in isolation.

**What gets tested:**
- **Orchestrator CLI logic** (`manage.py`): Command parsing, argument validation, state transitions, help text
- **Configuration validators**: YAML schema validation, profile relationships, role/tag mappings, naming conventions
- **Utility functions**: Profile/role/playbook generators, command alias resolution, matrix test logic
- **Integration mocks**: vCenter, OpenTofu, Ansible integrations via mocking (no real infrastructure calls)

**Test files responsible:**
- `tests/test_manage.py` — orchestrator commands and profile handling
- `tests/test_connectivity_optimized.py` — SSH connectivity logic
- `tests/test_technitium_manager.py` — DNS manager logic
- Future: validators, CLI parsing, alias resolution

**Success criteria:**
- 90% code coverage on critical paths (orchestrator, validators)
- All unit tests pass
- No external dependencies required (mocked or skipped)

**Blocker:** Yes—PR cannot merge if unit tests fail or coverage drops below threshold.

**Enforcement:**
- GitHub Actions: `lint-and-unit-tests.yml` runs on every push and PR
- Coverage report posted to PR comments
- Merge blocked if coverage < 90%

---

### Tier 2: Integration Tests (Every PR — Required)

**Scope:** Multi-component validation against real infrastructure. Tests that components work together correctly without going through the full golden image build.

**What gets tested:**
- **OpenTofu configuration validation**: `terraform plan` against test vCenter, schema validation, variable interpolation
- **Ansible playbook execution**: Playbooks run against a dedicated test VM, roles execute correctly, handlers fire properly
- **Orchestrator workflows**: Full orchestrator flow (lint → deploy → config) against test infrastructure without building golden images
- **Post-deployment validation**: Testinfra assertions verify OS hardening, package presence, service state, SSH key presence, user accounts

**Test files responsible:**
- `tests/test_os.py` — OS hardening and service state (testinfra-based)
- `tests/test_github_runner.py` — GitHub runner role validation
- New: `tests/test_ansible_integration.py` — playbook execution and handler validation
- New: `tests/test_orchestrator_workflow.py` — end-to-end orchestrator flows
- `scripts/matrix_test.py` — configuration relationship validation

**Success criteria:**
- All integration tests pass
- No configuration drift detected
- All testinfra assertions pass on test VM
- Orchestrator workflows complete without errors

**Blocker:** Yes—PR cannot merge if integration tests fail. This requires a reliable test VM always available.

**Infrastructure requirement:**
A dedicated test VM must be maintained:
- Always powered on and accessible via SSH
- In a known good state (recent golden image deployment)
- Configured with SSH key authentication (passwordless sudo)
- IP address documented and stable

**Enforcement:**
- GitHub Actions: `integration-tests.yml` runs on every push and PR
- Requires access to test VM (runner with homelab connectivity)
- Results posted to PR comments
- Merge blocked if any integration test fails

---

### Tier 3: Full End-to-End Tests (Major Refactors/Releases — Gated)

**Scope:** Complete pipeline validation from golden image build through production readiness. Tests the entire system as users would experience it.

**What gets tested:**
- **Packer golden image builds**: Ubuntu 24.04, Ubuntu 26.04, Photon OS — all standard images build successfully
- **VM deployment**: OpenTofu provisions VMs to vSphere successfully
- **Full configuration**: Ansible applies complete post-deployment configuration
- **Comprehensive validation**: Testinfra validates OS hardening, services, security posture
- **Profile variations**: All profile types (docker, github-runner, base) deploy and configure correctly

**Test files responsible:**
- Packer build logs and artifact validation
- `tests/test_os.py` and custom testinfra suites against freshly deployed VMs
- All integration tests re-run against production deployment

**Success criteria:**
- All golden images build without errors
- Deployed VMs pass all hardening checks
- No manual intervention required post-deployment
- All testinfra assertions pass
- Profile-specific roles execute correctly

**Blocker:** Yes—must pass before releases; strongly encouraged for major refactors but not strictly required.

**Enforcement:**
- Manual trigger: `full-e2e.yml` via workflow dispatch
- Automatic on: release events or designated refactor branches
- Runs in parallel for multiple OS types
- Results documented in release notes

---

## GitHub Actions Workflows

### Workflow 1: Lint & Unit Tests (`lint-and-unit-tests.yml`)

**Trigger:** `push`, `pull_request`

**Runner:** `ubuntu-latest` (no infrastructure required)

**Steps:**
1. Checkout code
2. Set up Python 3.12
3. Install dependencies (`pip install -r requirements.txt`)
4. Run YAML linting (`yamllint config/ ansible/`)
5. Run Ansible linting (`ansible-lint ansible/`)
6. Run Python linting (`flake8 manage.py scripts/ tests/`)
7. Run shell linting (`shellcheck scripts/*.sh`)
8. Run unit tests with coverage (`pytest tests/ -v --cov=manage.py --cov=scripts --cov-report=term-missing`)
9. Enforce coverage threshold (fail if < 90%)
10. Post coverage report as PR comment

**Outcome:** Blocks PR if any check fails.

**Estimated runtime:** 2-3 minutes

---

### Workflow 2: Integration Tests (`integration-tests.yml`)

**Trigger:** `push`, `pull_request`

**Runner:** Requires homelab access (custom runner or GitHub runner with vSphere credentials)

**Prerequisites:**
- Dedicated test VM is powered on and reachable
- SSH key authentication configured
- Test VM IP documented in secrets or runner config

**Steps:**
1. Checkout code
2. Set up Python 3.12
3. Install dependencies
4. Validate OpenTofu configuration (`tofu plan -out=tfplan`)
5. Run Ansible syntax check and dry-run against test VM
6. Run integration tests (`pytest tests/test_os.py tests/test_github_runner.py -v`)
7. Run matrix test validation (`python3 scripts/matrix_test.py`)
8. Post results as PR comment

**Outcome:** Blocks PR if any test fails.

**Estimated runtime:** 5-10 minutes (depends on test VM availability and Ansible execution)

**Failure handling:**
- If test VM is unavailable, workflow fails and PR cannot merge
- Alert/notification should be sent to team to restore infrastructure

---

### Workflow 3: Full E2E Tests (`full-e2e.yml`)

**Trigger:** Manual dispatch (`workflow_dispatch`), release events

**Runner:** Custom runner with Packer + vSphere + Ansible access

**Steps:**
1. Checkout code
2. Build all golden images in parallel (`packer build ubuntu-2404.pkr.hcl`, etc.)
3. Validate images in Content Library
4. Deploy test VMs from each image via OpenTofu
5. Run full Ansible configuration
6. Run comprehensive testinfra validation
7. Cleanup test VMs (optional for debugging)
8. Publish build artifacts and test results

**Outcome:** Must pass for releases; strongly recommended for major refactors.

**Estimated runtime:** 45-90 minutes (image builds are slow)

---

## Developer Workflow

### Before Committing
```bash
# Run linting locally
yamllint config/profiles/*.yml ansible/
ansible-lint ansible/
flake8 manage.py scripts/ tests/
shellcheck scripts/*.sh

# Run unit tests locally
pytest tests/test_*.py -v --cov=manage.py --cov=scripts
```

### Creating a Pull Request
1. Push branch to GitHub
2. **Automatic:** Lint + unit tests run (`lint-and-unit-tests.yml`)
3. **Automatic:** Integration tests run (`integration-tests.yml`) if runner available
4. Review results in PR
5. If tests fail:
   - Fix code locally
   - Push updated commit
   - Tests re-run automatically
6. Once all tests pass, PR is eligible for code review and merge

### For Major Refactors or Releases
1. Create PR as above
2. All three test tiers must pass:
   - Lint + unit tests (automatic)
   - Integration tests (automatic)
   - **Full E2E** (manual trigger or automatic on release)
3. Document test results in PR description or release notes

---

## Coverage Targets

**Unit Test Coverage:** 90% minimum on critical paths
- `manage.py` (orchestrator): 95%+
- `scripts/` utilities: 90%+
- Configuration validators: 95%+
- Helper functions: 80%+ (relaxed standard)

**Coverage exceptions:**
- Error handling for impossible conditions: exempt
- Legacy code under refactor: exempt if documented
- External library wrappers: 70%+ minimum

**Tracking:**
- Coverage reports posted to every PR
- Coverage trends tracked in CI dashboard
- Coverage regressions block merge

---

## Infrastructure Requirements

### Dedicated Test VM
- **Purpose:** Stable target for integration tests
- **OS:** Latest Ubuntu LTS or comparable (matches production)
- **Specs:** Minimum 2 vCPU, 4GB RAM, 20GB disk
- **Availability:** Must be reliably powered on and accessible 24/7
- **State:** Deployed from recent golden image; known good baseline
- **Credentials:** SSH key authentication, passwordless sudo for test user
- **Network:** Static IP or hostname; reachable from GitHub runners

### GitHub Runner (Optional but Recommended)
- **Purpose:** Execute integration tests without exposing homelab IP
- **Location:** Can be self-hosted on homelab infrastructure
- **Credentials:** vCenter/vSphere credentials stored in runner secrets
- **Isolation:** Dedicated runner to avoid conflicts with other jobs

### Secrets & Configuration
- Test VM SSH key stored in GitHub repository secrets
- vCenter credentials stored in repository secrets
- Test VM IP/hostname in `.github/workflows/integration-tests.yml` or runner config

---

## Enforcement & Metrics

### Merge Requirements
- All three tests must show passing (or informational) status:
  - ✅ Lint & Unit Tests: **REQUIRED** — blocks merge if failed
  - ✅ Integration Tests: **REQUIRED** — blocks merge if failed
  - ✅ Full E2E: **OPTIONAL** — informational only (unless release or major refactor)

### Metrics to Track
- **Unit test coverage:** Trend over time, catch regressions
- **Integration test pass rate:** Indicator of infrastructure stability
- **Test runtime:** Monitor for performance degradation
- **Failure reasons:** Categorize to identify patterns (flaky tests, infrastructure issues, logic bugs)

### Review Cadence
- Monthly: Review coverage trends, adjust thresholds if needed
- Quarterly: Audit test suite for dead tests or gaps
- As-needed: Investigate persistent test failures or infrastructure issues

---

## Future Enhancements

1. **Testinfra as a Service:** Containerized testinfra environment for isolated testing without affecting production VMs
2. **Test VM Provisioning Automation:** Automatically rebuild test VM from golden image weekly
3. **Coverage Badges:** Add coverage badge to README
4. **Performance Testing:** Benchmark orchestrator commands for regressions
5. **Security Scanning:** Add trivy/snyk scanning for vulnerabilities in container images
6. **Golden Image Versioning:** Tag and track golden image versions with test results
7. **Flaky Test Detection:** Automatically rerun suspicious tests to identify flakiness
8. **Multi-Profile Integration Testing:** Expand integration tests to cover all profile types, not just one test VM

---

## Related Documents

- `CLAUDE.md` — Development environment setup and commands
- `DESIGN.md` — Architecture and technical principles
- `RUNBOOK.md` — Operational procedures
- `.github/workflows/` — GitHub Actions workflow definitions

