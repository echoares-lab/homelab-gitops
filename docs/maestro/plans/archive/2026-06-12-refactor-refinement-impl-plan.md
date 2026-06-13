---
title: "Homelab GitOps Refactor Refinement Implementation Plan"
design_ref: "docs/maestro/plans/2026-06-12-refactor-refinement-design.md"
created: "2026-06-12T13:00:00Z"
status: "approved"
total_phases: 4
estimated_files: 30
task_complexity: "medium"
---

# Homelab GitOps Refactor Refinement Implementation Plan

## Plan Overview
This plan finalizes the architectural refactor by standardizing imports, implementing missing DNS CLI logic, and ensuring package-wide PEP 8 compliance. It utilizes 3 specialized agents to handle the sweep across the codebase.

- **Total phases**: 4
- **Agents involved**: `coder` (2), `refactor` (1), `tester` (1)
- **Estimated effort**: Medium

## Dependency Graph
```
Layer 1: Foundation (Service Extension)
[Ph 1: DNSService Manual Logic]
       |
Layer 2: Package Refactoring (Standardization)
[Ph 2: Absolute Import Sweep]
       |
Layer 3: UI & Validation (CLI)
[Ph 3: DNS CLI Implementation]
       |
Layer 4: Final Validation
[Ph 4: E2E Verification]
```

## Execution Strategy
| Stage | Phases | Execution | Agent Count | Notes |
|-------|--------|-----------|-------------|-------|
| 1     | 1      | Sequential | 1 | DNSService Update |
| 2     | 2      | Sequential | 1 | Package-wide Refactor |
| 3     | 3      | Sequential | 1 | CLI Wiring |
| 4     | 4      | Sequential | 1 | Final E2E |

---

## Phase 1: DNSService Manual Logic
### Objective
Extend `DNSService` to support record management without a full `NodeProfile`.
### Agent: `coder`
### Parallel: No
### Implementation Details
- Add `provision_manual(name: str, ip: str, zone: str = None) -> List[TaskResult]` to `src/homelab_gitops/domain/dns.py`.
- Add `deprovision_manual(name: str, zone: str = None) -> List[TaskResult]`.
- Refactor `provision_record` to use these new manual helpers for the actual work.
### Dependencies
- Blocked by: None

## Phase 2: Absolute Import Sweep
### Objective
Convert all relative imports to absolute imports in the `homelab_gitops` package.
### Agent: `refactor`
### Parallel: No
### Implementation Details
- Systemic replace: `from .models` -> `from homelab_gitops.domain.models`.
- Systemic replace: `from ..drivers` -> `from homelab_gitops.drivers`.
- Update all `__init__.py` files to use absolute exports.
- Use `sed` or `replace` to sweep the 26 identified files.
### Dependencies
- Blocked by: None (Independent sweep)

## Phase 3: DNS CLI Implementation
### Objective
Wire the `dns create` and `dns delete` commands to the new service methods.
### Agent: `coder`
### Parallel: No
### Implementation Details
- Update `src/homelab_gitops/cli/core_commands/dns.py`.
- Implement `create_record` to call `service.provision_manual`.
- Implement `delete_record` subcommand to call `service.deprovision_manual`.
- Ensure rich output (tables) for results.
### Dependencies
- Blocked by: 1

## Phase 4: E2E Verification
### Objective
Final dry-run of all commands and driver validation.
### Agent: `tester`
### Parallel: No
### Implementation Details
- Run `manage.py --help` for all commands.
- Run `manage.py opnsense list-rules`.
- Run `manage.py dns list`.
- Verify all drivers pass `validate()`.
### Dependencies
- Blocked by: 2, 3

## File Inventory
| # | File | Phase | Purpose |
|---|------|-------|---------|
| 1 | `src/homelab_gitops/domain/dns.py` | 1 | DNSService Logic |
| 2 | `src/homelab_gitops/cli/core_commands/dns.py` | 3 | DNS CLI |
| 3 | `src/homelab_gitops/*` | 2 | Package-wide Imports |

## Execution Profile
```
Execution Profile:
- Total phases: 4
- Parallelizable phases: 0 (Phases 1 and 2 are independent but sequential is safer for package refactors)
- Sequential-only phases: 4
- Estimated parallel wall time: N/A
- Estimated sequential wall time: ~4 Agent Turns

Note: Native parallel execution is not used for this refinement batch to avoid race conditions during import refactoring.
```
