# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Unified GitOps Template Pipeline** with **4-layer modular architecture** replacing the monolithic `manage.py`.

The new architecture separates concerns into:
1. **Layer 1 (CLI):** Plugin-based command system (Typer)
2. **Layer 2 (Domain):** Orchestration logic (workflows, state machine, validators)
3. **Layer 3 (Drivers):** Infrastructure adapters (Ansible, Tofu, vCenter)
4. **Layer 4 (IaC):** Infrastructure code (Ansible roles, Tofu modules)

## Quick Start

### Run CLI
```bash
cd /home/dev/repos/homelab-gitops/arch-refactor-work
python -m homelab_gitops.cli.app
```

### Run Tests
```bash
# Unit tests (fast, no infrastructure)
pytest tests/unit/ -v

# Integration tests (mocked infrastructure)
pytest tests/integration/ -v

# All fast tests (excludes E2E)
pytest tests/ -v -m "not slow"

# E2E tests (slow, requires infrastructure)
pytest tests/e2e/ -v -m slow
```

### Add a New Command
1. Create `src/homelab_gitops/cli/core_commands/mycommand.py`
2. Implement `mycommand_command()` function with `typer` decorators
3. Add `command_metadata` dict with name, aliases, help
4. Plugin loader auto-discovers it—no changes to app.py needed

## Architecture

**Layer 1: CLI** → **Layer 2: Domain** → **Layer 3: Drivers** → **Infrastructure**

See: `docs/superpowers/specs/` for detailed design docs

## Project Structure

```
src/homelab_gitops/
  cli/                      # Plugin-based command system
    core_commands/          # Built-in commands (auto-discovered)
    app.py                  # Typer app factory
    plugin_loader.py        # Dynamic plugin discovery
  domain/                   # Orchestration logic (tests without infrastructure)
    models.py               # Data classes
    workflows.py            # Multi-stage pipeline
    state_machine.py        # Lifecycle enforcement
    validators.py           # Profile validation
  drivers/                  # Infrastructure adapters
    base.py                 # Abstract driver interface
    ansible_driver.py       # Playbook execution
    tofu_driver.py          # State management
    vcenter_driver.py       # vCenter queries

tests/
  unit/                     # Fast, no infrastructure (29 tests)
  integration/              # Mocked infrastructure (13 tests)
  e2e/                      # Full pipeline (optional, slow)
  cli/                      # CLI app tests
  fixtures/                 # Pytest fixtures

ansible/
  roles/                    # Reusable Ansible roles
    base/                   # Base OS setup
    docker/                 # Docker runtime
    github_runner/          # GitHub Actions runner
    ... (others)

tofu/
  modules/                  # Modular OpenTofu configuration
    vm/                     # VM provisioning module
    network/                # Network module (stub)
    storage/                # Storage module (stub)
  main.tf                   # Root module calling vm module
  variables.tf              # Root-level variables
```

## Key Standards

**From GEMINI.md:**
- Profile names: lowercase + hyphens
- Role names: lowercase + underscores
- Tags: lowercase + underscores
- All code must pass: yamllint, ansible-lint, flake8, shellcheck
- Tests required for all logic changes

## Testing Strategy

- **Unit Tests:** Domain logic only (no infrastructure)
- **Integration Tests:** Drivers with mocked infrastructure
- **E2E Tests:** Full pipeline (optional, slow)

Default run excludes E2E: `pytest tests/ -v -m "not slow"` (42 tests in ~0.1s)

E2E run requires infrastructure: `pytest tests/e2e/ -v -m slow`

## Implementation Notes

1. **TDD Applied:** All code written with tests first (42 tests passing)
2. **Layered Design:** Each layer testable independently
3. **Plugin System:** No hardcoding required for new commands
4. **Error Handling:** Domain exceptions with context
5. **State Machine:** Prevents invalid transitions
6. **Modular IaC:** OpenTofu modules enable code reuse

## State Transitions

The state machine enforces valid lifecycle transitions:

```
planned
  ↓
deployed
  ↓
configured
  ↓
tested
  ↓
updated

(Any state can transition to: destroyed, failed)
```

## Supported Tags

Valid deployment tags (defined in `validators.py`):
- `ubuntu` - Ubuntu base OS
- `photon` - VMware Photon OS
- `docker` - Docker runtime
- `dns` - DNS services
- `runner` - GitHub Actions runner

## Future Enhancements

- Networking API integration
- Machine registration workflows
- Patching/update automation
- Third-party plugin ecosystem
- Real E2E tests with infrastructure
