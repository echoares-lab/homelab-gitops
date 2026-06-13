---
title: "Homelab GitOps Refactor Cutover"
created: "2026-06-12T14:00:00Z"
status: "approved"
authors: ["TechLead", "User"]
type: "design"
design_depth: "quick"
task_complexity: "complex"
---

# Homelab GitOps Refactor Cutover Design Document

## Problem Statement
The project root currently uses a monolithic architecture (`services/`, direct `src/` modules) that is difficult to maintain. A superior, modular architecture has been developed and validated in `arch-refactor-work/`. We need to atomically replace the root with this modernized structure to establish it as the new project standard.

## Approach
**Selected Approach: Clean Sweep Cutover**
- **Preparation**: Create cutover branch.
- **Deletion**: Remove `services/`, old `src/` modules, and root `manage.py`.
- **Migration**: Move `homelab_gitops` package and refactored entry points to the root.
- **Verification**: Functional dry-run of all 10 core command groups.

## Risk Assessment
- **Logic Loss**: Mitigated by pre-validation of feature parity.
- **Merge Conflicts**: Mitigated by atomic cutover branch isolation.

## Success Criteria
1. Root `manage.py` is the modernized Typer CLI.
2. `services/` directory is removed.
3. Full feature parity confirmed via dry-run.
