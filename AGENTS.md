# AI Agent Operational Standards

This document provides foundational mandates for AI agents interacting with the HomeLab GitOps repository. These rules ensure that automated changes remain human-readable, documented, and compatible with the interactive orchestrator.

## 1. Metadata Maintenance (`config/metadata.yml`)
The interactive command builder (`manage.py`) and various lifecycle phases rely on the `config/metadata.yml` file to provide human-readable guidance and context to users.

**MANDATE:** Whenever an agent performs any of the following actions, the corresponding metadata MUST be updated in the same turn:
*   **New Role:** Add a one-sentence description explaining the role's purpose to the `roles:` section.
*   **New Tag:** Add a description explaining the configuration triggered by this tag to the `tags:` section.
*   **New Command:** Add any new orchestrator subcommand and its purpose to the `commands:` section.
*   **Profile Update:** Ensure the metadata accurately reflects any major changes in profile behavior or requirements.

### Metadata Schema Example:
```yaml
tags:
  new_service: "Description of what this tag configures."
roles:
  install_service: "Detailed intent of this Ansible role."
```

## 2. Interactive Mode Compatibility
Agents must ensure that all CLI prompts remain compatible with the `Rich` and `Typer` standards used in `manage.py`.
*   Always use `console.print()` with appropriate styling for feedback.
*   Prefer `Table` or `Panel` for complex data displays.
*   Use `Confirm.ask()` for dangerous operations like `destroy`.

## 3. Documentation Synchronicity
As established in `GEMINI.md`, any significant feature change must be reflected across:
1.  `ROADMAP.md` (Update status to [DONE]).
2.  `VERSIONS_AND_UPDATES.md` (Add new version entry).
3.  `RUNBOOK.md` (Update usage examples).
4.  `DESIGN.md` (Update architectural diagrams if workflow changes).

## 4. Pull Request Submission
Agents submitting a pull request MUST enable auto-merge for that PR whenever repository permissions and branch protection allow it. Auto-merge must still respect required reviews, required status checks, and branch protection rules; agents must not bypass or weaken those protections to merge faster.

## 4.1 Working-Tree and PR Hygiene
Agents must keep issue work isolated from unrelated dirty files and generated local state. See `docs/AGENT_WORKFLOW_HYGIENE.md` for the repository-specific guidance on claim comments, generated artifacts, one-issue/one-PR flow, and auto-merge expectations.

## 5. Matrix Testing (`scripts/matrix_test.py`)
To prevent regressions in the orchestrator's logic or hardware mapping, agents must validate their changes using the Matrix Test suite.

**MANDATE:** Agents MUST execute `python3 scripts/matrix_test.py` before considering any of the following tasks complete:
*   Refactoring `manage.py` argument parsing or command logic.
*   Modifying OpenTofu `main.tf` or `variables.tf`.
*   Updating Ansible dynamic inventory grouping logic.
*   Adding new lifecycle phases or generator helpers.

If a change breaks the current matrix, the agent MUST update `scripts/matrix_test.py` to reflect the new expected behavior.

## 6. CI & Testing Modifications
When modifying CI workflows, test configurations, or test dependencies, agents must follow a structured validation process to prevent silent failures and infrastructure drift.

### 6.1 Key Steps for Safe CI Changes

1. **Dependency Verification:** Before using a package or tool in CI, verify it is already present in `requirements.txt` or add it. All CI dependencies must be pinned to a specific version and documented in the requirements file.

2. **Configuration Validation:** Run `python3 scripts/validate-ci-config.py` to detect conflicts between CI workflow files, test configurations, and environment variables. This catches duplicate settings and inconsistent values before deployment.

3. **Local Test Execution:** Always run the full test suite locally using the exact same arguments and environment as CI. This includes pytest flags, coverage thresholds, and any conditional test filtering.

4. **File Reference Validation:** If CI workflows reference test files, configuration files, or scripts, verify they actually exist in the repository before committing. Use `ls -la` or `find` to confirm paths are correct.

5. **Documentation:** Update `docs/TESTING.md` if changing testing standards, coverage thresholds, test organization, or CI behavior. Ensure the documentation reflects the actual CI implementation.

### 6.2 Red Flags in CI Changes

Watch for these patterns that indicate problematic CI modifications:

*   ❌ **Duplicate configuration:** Same setting appears in two or more files (e.g., coverage threshold in both `pyproject.toml` and `.github/workflows/ci.yml`).
*   ❌ **Unrecognized arguments in CI logs:** Test commands fail with "unrecognized argument" or similar errors, indicating mismatched tool versions or incorrect flag usage.
*   ❌ **Missing dependencies from requirements.txt:** CI workflow installs packages that aren't in `requirements.txt`, creating non-reproducible builds.
*   ❌ **Test file references that don't exist:** CI workflow references test files or paths that have been removed or renamed, causing silent skips or failures.
*   ❌ **Inconsistent values:** Threshold messages don't match actual checks (e.g., CI logs say "80% coverage required" but pyproject.toml defines 85%).

### 6.3 Reference to Testing Policy

See `docs/TESTING.md` for the complete testing policy, coverage requirements, and approved test frameworks. Any changes to test organization or CI standards must be synchronized with that documentation.
