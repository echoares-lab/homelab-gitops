---
title: "Homelab GitOps Architectural Synchronization Implementation Plan"
design_ref: "docs/maestro/plans/2026-06-12-arch-refactor-sync-design.md"
created: "2026-06-12T11:00:00Z"
status: "approved"
total_phases: 9
estimated_files: 25
task_complexity: "complex"
---

# Homelab GitOps Architectural Synchronization Implementation Plan

## Plan Overview
This plan synchronizes critical features from the project root into the `arch-refactor-work/` structure. It uses 15 agents in 3 parallelized batches to achieve feature parity with modern OPNsense, DNS, and DHCP migration capabilities.

- **Total phases**: 9
- **Agents involved**: `coder` (10), `architect` (1), `security_engineer` (1), `integration_engineer` (1), `tester` (2)
- **Estimated effort**: High (3 Batches, 15 Agents)

## Dependency Graph
```
Layer 1: Drivers (Foundation)
[Ph 1: OPNsenseDriver] [Ph 2: TechnitiumDriver] [Ph 3: SecretsDriver]
       \                     /                      |
Layer 2: Domain Logic (Services)                   |
[Ph 4: NetworkingService] [Ph 5: DNSService] [Ph 6: MigrationDriver & Service]
       \                     /                      |
Layer 3: Orchestration & UI (CLI)                  |
[Ph 7: OPNsense CLI] [Ph 8: DNS/Migrate CLI] [Ph 9: Full Lifecycle Sync]
```

## Execution Strategy
| Stage | Phases | Execution | Agent Count | Notes |
|-------|--------|-----------|-------------|-------|
| 1     | 1, 2, 3 | Parallel | 5 | Drivers & Foundation Batch |
| 2     | 4, 5, 6 | Parallel | 5 | Domain Services Batch |
| 3     | 7, 8, 9 | Parallel | 5 | CLI & E2E Validation Batch |

---

## Phase 1: OPNsense Driver
### Objective
Port root `src/opnsense/` clients into a standardized `OPNsenseDriver`.
### Agent: `coder`
### Parallel: Yes
### Implementation Details
- Create `src/homelab_gitops/drivers/opnsense_driver.py`.
- Inherit from `Driver`. Implement `execute()` for firewall/vlan tasks.
- Validation: Dry-run check against `OPNSENSE_URL`.
### Dependencies
- Blocked by: None

## Phase 2: Technitium Driver
### Objective
Port root `src/technitium/` clients into a standardized `TechnitiumDriver`.
### Agent: `coder`
### Parallel: Yes
### Implementation Details
- Create `src/homelab_gitops/drivers/technitium_driver.py`.
- Inherit from `Driver`. Implement `execute()` for record management.
### Dependencies
- Blocked by: None

## Phase 3: Secrets Driver Implementation
### Objective
Integrate 1Password and env-based secrets into `SecretsDriver`.
### Agent: `coder`
### Parallel: Yes
### Implementation Details
- Create `src/homelab_gitops/drivers/secrets_driver.py`.
- Ensure 1Password `op` CLI integration.
### Dependencies
- Blocked by: None

## Phase 4: Networking Domain Service
### Objective
Implement `NetworkingService` to orchestrate multi-step network setup.
### Agent: `coder`
### Parallel: Yes
### Dependencies
- Blocked by: 1

## Phase 5: DNS Domain Service
### Objective
Implement `DNSService` for record and zone orchestration.
### Agent: `coder`
### Parallel: Yes
### Dependencies
- Blocked by: 2

## Phase 6: Stateful Migration Driver & Service
### Objective
New `MigrationDriver` for stateful DHCP cutover.
### Agent: `integration_engineer`
### Parallel: Yes
### Dependencies
- Blocked by: 1, 2

## Phase 7: OPNsense CLI Plugin
### Objective
CLI plugin for `opnsense` commands.
### Agent: `coder`
### Parallel: Yes
### Dependencies
- Blocked by: 4

## Phase 8: DNS & Migration CLI Plugins
### Objective
CLI plugins for `dns` and `migrate` commands.
### Agent: `coder`
### Parallel: Yes
### Dependencies
- Blocked by: 5, 6

## Phase 9: E2E Validation & Polish
### Objective
Final verification and README updates.
### Agent: `tester`
### Parallel: Yes
### Dependencies
- Blocked by: 7, 8

## File Inventory
| # | File | Phase | Purpose |
|---|------|-------|---------|
| 1 | `src/homelab_gitops/drivers/opnsense_driver.py` | 1 | OPNsense Driver |
| 2 | `src/homelab_gitops/drivers/technitium_driver.py` | 2 | Technitium Driver |
| 3 | `src/homelab_gitops/drivers/secrets_driver.py` | 3 | Secrets Driver |
| 4 | `src/homelab_gitops/domain/networking.py` | 4 | Networking Service |
| 5 | `src/homelab_gitops/domain/dns.py" | 5 | DNS Service |
| 6 | `src/homelab_gitops/drivers/migration_driver.py" | 6 | Migration Driver |
| 7 | `src/homelab_gitops/cli/core_commands/opnsense.py" | 7 | OPNsense CLI |
| 8 | `src/homelab_gitops/cli/core_commands/dns.py" | 8 | DNS CLI |
| 9 | `src/homelab_gitops/cli/core_commands/migrate.py" | 8 | Migration CLI |

## Execution Profile
```
Execution Profile:
- Total phases: 9
- Parallelizable phases: 9 (in 3 batches)
- Sequential-only phases: 0
- Estimated parallel wall time: ~3 Agent Turns (Batch-based)

Note: Native subagents currently run without user approval gates.
All tool calls are auto-approved without user confirmation.
```
