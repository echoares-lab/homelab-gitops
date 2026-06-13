---
title: "Critical Infrastructure & Service Maintenance"
created: "2026-06-12T14:30:00Z"
status: "approved"
authors: ["TechLead", "User"]
type: "design"
design_depth: "quick"
task_complexity: "medium"
---

# Critical Infrastructure & Service Maintenance Design Document

## Problem Statement

The homelab-gitops repository currently faces three critical issues that impede its reliability and security:
1. **Broken Tag Resolution**: The `ConfigService.resolve_playbook` method incorrectly attempts to access deployment tags from the profile root instead of the `deployment` nested dictionary.
2. **Incomplete Infrastructure**: The core VM provisioning module (`tofu/modules/vm/main.tf`) is a placeholder, preventing the automated deployment of virtual machines.
3. **Hardcoded Security Risk**: A sensitive password hash is hardcoded in `ansible/deploy.yml`, violating the project's mandate for 1Password-based secrets management.

## Requirements

### Functional Requirements

1. **REQ-1**: `ConfigService.resolve_playbook` must correctly retrieve tags from `profile['deployment']['tags']`.
2. **REQ-2**: `tofu/modules/vm/main.tf` must implement the `vsphere_virtual_machine` resource with PVSCSI and VMXNET3 controllers.
3. **REQ-3**: The hardcoded password hash in `ansible/deploy.yml` must be replaced by a variable sourced from `config/secrets.env`.

### Non-Functional Requirements

1. **REQ-4**: All changes must be validated by the existing `pytest` suite and `scripts/matrix_test.py`.
2. **REQ-5**: Infrastructure changes must adhere to Hardware Version 21 (vmx-21) standards.

## Approach

### Selected Approach

**Surgical Remediation**

We will apply targeted fixes to the identified files while preserving existing architectural patterns. This approach minimizes disruption and focuses on the most critical paths.

1. **Logic Fix**: Update `services/config.py` to fix the dictionary access. Simultaneously update `tests/test_services/test_config_service.py` to use a realistic profile structure.
2. **Infrastructure Completion**: Populate the OpenTofu VM module with a production-ready resource definition matching the project's engineering standards (PVSCSI, VMXNET3, Hardware Version 21).
3. **Secrets Externalization**: Move the password hash to `config/secrets.env` as a 1Password reference and update the Ansible playbook to use it via the standard secrets loading mechanism.

## Architecture

### Component Diagram

```
[ConfigService] -> [Ansible Playbook] -> [OpenTofu VM Module] -> [vCenter]
      |                                       ^
      |                                       |
[Secrets Management (1Password)] -------------/
```

### Agent Team

| Phase | Agent(s) | Parallel | Deliverables |
|-------|----------|----------|--------------|
| 1     | coder    | Yes      | Fixed services/config.py and updated tests. |
| 1     | devops   | Yes      | Implemented tofu/modules/vm/main.tf. |
| 2     | security | No       | Externalized password hash in ansible/deploy.yml. |
| 3     | tester   | No       | Validated all changes with pytest and matrix_test.py. |

## Risk Assessment

| Risk | Severity | Likelihood | Mitigation |
|------|----------|------------|------------|
| Infrastructure Misconfiguration | HIGH | MEDIUM | Extensive validation with scripts/matrix_test.py in a dry-run mode if possible. |
| Unit Test Regression | MEDIUM | LOW | Update and run the full test suite before and after changes. |
| Secrets Loading Failure | MEDIUM | LOW | Verify 1Password connectivity and secret resolution during the validation phase. |

## Success Criteria

1. `pytest` passes for all service-related tests.
2. `scripts/matrix_test.py` confirms that the OpenTofu module generates valid plans.
3. `ansible-lint` confirms that `ansible/deploy.yml` no longer contains hardcoded secrets.
