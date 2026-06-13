---
title: "Homelab GitOps Architectural Refactor Refinement"
created: "2026-06-12T12:00:00Z"
status: "approved"
authors: ["TechLead", "User"]
type: "design"
design_depth: "standard"
task_complexity: "medium"
---

# Homelab GitOps Architectural Refactor Refinement Design Document

## Problem Statement
The `arch-refactor-work/` project has achieved 90% structural parity but lacks functional completeness in the DNS CLI and suffers from inconsistent import patterns. We need to bridge the "manual record" gap in the DNS service, enforce a strict absolute-import convention, and perform a final validation of the environment configuration to ensure a seamless cutover from the root project.

## Requirements

### Functional Requirements
1. **REQ-1**: Extend `DNSService` with `provision_manual(name, ip)` for non-profile record management.
2. **REQ-2**: Implement `manage dns create` and `manage dns delete` in the refactored CLI.
3. **REQ-3**: Standardize all package imports to the absolute `homelab_gitops.` namespace.

### Non-Functional Requirements
- Maintain idempotency in DNS operations.
- Ensure strict PEP 8 compliance for imports.

## Approach

### Selected Approach: Service Extension & Absolute Standardization
We will modify the `DNSService` to handle direct inputs and perform a package-wide refactor of import statements.

### Decision Matrix
| Criterion | Weight | Selected Approach |
|-----------|--------|-------------------|
| Architectural Purity | 30% | 4: Absolute imports ensure long-term health. |
| Functional Readiness | 40% | 5: Direct service wiring for DNS ensures full parity. |
| Maintainability | 30% | 5: Service-level logic is cleaner than CLI shims. |
| **Total** | **100%** | **4.7** |

## Risk Assessment
- **Idempotency Gaps**: Mitigated by existence checks in `DNSService`.
- **Import Fragility**: Mitigated by strict use of the `homelab_gitops` root namespace.

## Success Criteria
1. Full CLI parity for DNS management.
2. Zero import or linting errors.
3. Successful driver validation.
