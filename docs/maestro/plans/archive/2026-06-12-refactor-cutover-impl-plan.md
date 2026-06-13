---
title: "Homelab GitOps Refactor Cutover Implementation Plan"
design_ref: "docs/maestro/plans/2026-06-12-refactor-cutover-design.md"
created: "2026-06-12T15:00:00Z"
status: "approved"
total_phases: 5
estimated_files: 50
task_complexity: "complex"
---

# Homelab GitOps Refactor Cutover Implementation Plan

## Plan Overview
This plan executes the final architectural cutover by replacing the legacy monolithic root structure with the modernized, modular architecture from `arch-refactor-work/`.

- **Total phases**: 5
- **Agents involved**: `refactor` (2), `coder` (1), `tester` (1), `release_manager` (1)
- **Estimated effort**: Medium

## Dependency Graph
```
Layer 1: Preparation
[Ph 1: Cutover Branch]
       |
Layer 2: Clean Sweep
[Ph 2: Atomic Deletion]
       |
Layer 3: Migration
[Ph 3: Move Refactored Code]
       |
Layer 4: Integration
[Ph 4: Shell & Entry Point]
       |
Layer 5: Verification & PR
[Ph 5: Final Validation & PR]
```

## Execution Strategy
| Stage | Phases | Execution | Agent Count | Notes |
|-------|--------|-----------|-------------|-------|
| 1     | 1      | Sequential | 1 | Branch Setup |
| 2     | 2      | Sequential | 1 | Clean Deletion |
| 3     | 3      | Sequential | 1 | Migration |
| 4     | 4      | Sequential | 1 | CLI Registry |
| 5     | 5      | Sequential | 1 | PR creation |

---

## Phase 1: Cutover Branch
### Objective
Create a clean workspace for the cutover.
### Agent: `release_manager`
### Parallel: No
### Implementation Details
- Create a new branch `feat/architectural-cutover` from the latest `master`.
- Merge the current `feat/dns-suite-upgrade` into it to ensure all recent fixes are included.
### Dependencies
- Blocked by: None

## Phase 2: Atomic Deletion
### Objective
Remove legacy monolithic components from the root.
### Agent: `refactor`
### Parallel: No
### Implementation Details
- Delete `services/` directory.
- Delete `src/opnsense/` and `src/technitium/`.
- Delete root `manage.py`.
- Delete `scripts/matrix_test.py` and `scripts/dns_suite/`.
- Delete `tests/test_services/` and `tests/test_manage_cli.py`.
- Delete legacy config: `config/metadata.yml`, `config/ci-runner-repos.yaml`, `config/technitium.token`.
### Dependencies
- Blocked by: 1

## Phase 3: Metal & Meat Migration
### Objective
Move the modernized package structure to the root.
### Agent: `refactor`
### Parallel: No
### Implementation Details
- Move `arch-refactor-work/src/homelab_gitops/` to root `src/homelab_gitops/`.
- Move `arch-refactor-work/scripts/matrix_test.py` to root `scripts/`.
- Move any other relevant refactored assets from `arch-refactor-work/`.
### Dependencies
- Blocked by: 2

## Phase 4: Shell Integration
### Objective
Finalize the CLI entry point and infrastructure config.
### Agent: `coder`
### Parallel: No
### Implementation Details
- Move `arch-refactor-work/manage.py` to root.
- Move `arch-refactor-work/pyproject.toml` and `arch-refactor-work/requirements.txt` to root.
- Update root `README.md` with new command structure.
### Dependencies
- Blocked by: 3

## Phase 5: Final Validation & PR
### Objective
Verify the cutover and create the pull request.
### Agent: `tester`
### Parallel: No
### Implementation Details
- Run `python3 manage.py --help` to verify CLI.
- Run a dry-run of a core command (e.g., `manage lint`).
- Create PR to `master` with description of architectural changes.
### Dependencies
- Blocked by: 4

## File Inventory
| # | File | Phase | Purpose |
|---|------|-------|---------|
| 1 | `src/homelab_gitops/` | 3 | Modernized Package |
| 2 | `manage.py` | 4 | Typer CLI Entry Point |
| 3 | `pyproject.toml` | 4 | Package Metadata |
| 4 | `services/` | 2 | DELETED |
| 5 | `src/opnsense/` | 2 | DELETED |

## Execution Profile
```
Execution Profile:
- Total phases: 5
- Parallelizable phases: 0 (Atomic structural changes require sequential execution)
- Sequential-only phases: 5
- Estimated parallel wall time: N/A
- Estimated sequential wall time: ~5 Agent Turns

Note: Sequential execution is used to prevent state corruption during directory movement.
```
