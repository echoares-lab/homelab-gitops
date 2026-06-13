---
title: "Homelab GitOps Architectural Synchronization"
created: "2026-06-12T10:00:00Z"
status: "approved"
authors: ["TechLead", "User"]
type: "design"
design_depth: "deep"
task_complexity: "complex"
---

# Homelab GitOps Architectural Synchronization Design Document

## Problem Statement
The `arch-refactor-work/` directory contains a superior architectural framework but is functionally "stale" compared to the root project. We need to synchronize the root's critical features (OPNsense, DNS, DHCP Migration, 1Password) into the refactored structure without losing architectural integrity.

## Requirements

### Functional Requirements
1. **REQ-1**: Port OPNsense Firewall/Network clients into `OPNsenseDriver` and `NetworkingService`.
2. **REQ-2**: Port Technitium DNS logic into `TechnitiumDriver` and `DNSService`.
3. **REQ-3**: Implement a stateful `MigrationDriver` for DHCP cutover with rollback.
4. **REQ-4**: Integrate 1Password `SecretsService` into the refactor's `SecretsDriver`.
5. **REQ-5**: Synchronize CLI plugins to match root feature parity.

### Non-Functional Requirements
- Adherence to `arch-refactor-work/GEMINI.md` standards.
- Support for 15-agent concurrent execution via atomic worktrees.
- 100% pass rate on `pytest-testinfra`.

## Approach

### Selected Approach: Hybrid Module Synchronization
Group the synchronization into three Feature Clusters assigned to agent batches working on atomic worktrees.

### Decision Matrix
| Criterion | Weight | Approach A | Approach B | Approach C (Hybrid) |
|-----------|--------|------------|------------|---------------------|
| Agent Scale | 40% | 1: Low | 5: High | 4: High |
| Safety | 30% | 5: High | 2: Low | 4: Medium-High |
| Cohesion | 20% | 5: High | 2: Low | 5: High |
| Speed | 10% | 2: Low | 4: High | 5: High |
| **Total** | **100%** | **2.9** | **3.6** | **4.3** |

## Architecture

### Component Mapping
- **OPNsense**: `OPNsenseDriver` -> `NetworkingService` -> `cli/core_commands/opnsense.py`
- **DNS**: `TechnitiumDriver` -> `DNSService` -> `cli/core_commands/dns.py`
- **Migration**: `MigrationDriver` (Stateful) -> `MigrationService` -> `migrate.py`
- **Secrets**: `SecretsDriver` -> `SecretsService`

## Agent Team
- **Batch 1 (Foundation)**: 5 Agents (Coder x3, Architect x1, Security x1)
- **Batch 2 (Domain/Logic)**: 5 Agents (Coder x4, Integration x1)
- **Batch 3 (CLI/Validation)**: 5 Agents (Coder x3, Tester x2)

## Risk Assessment
- **Merge Conflicts**: HIGH - Mitigated by atomic worktrees and batch-based gates.
- **Hardware Contention**: MEDIUM - Mitigated by API mocking for initial cycles.

## Success Criteria
1. Full feature parity with root `manage.py`.
2. 100% lint/test pass rate.
3. Successful `dhcp-migrate` dry-run.
