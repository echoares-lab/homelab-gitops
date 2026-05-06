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

## 4. Matrix Testing (`scripts/matrix_test.py`)
To prevent regressions in the orchestrator's logic or hardware mapping, agents must validate their changes using the Matrix Test suite.

**MANDATE:** Agents MUST execute `python3 scripts/matrix_test.py` before considering any of the following tasks complete:
*   Refactoring `manage.py` argument parsing or command logic.
*   Modifying OpenTofu `main.tf` or `variables.tf`.
*   Updating Ansible dynamic inventory grouping logic.
*   Adding new lifecycle phases or generator helpers.

If a change breaks the current matrix, the agent MUST update `scripts/matrix_test.py` to reflect the new expected behavior.
