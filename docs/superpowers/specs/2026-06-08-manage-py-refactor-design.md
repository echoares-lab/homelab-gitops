---
title: manage.py Refactoring to Service-Oriented Architecture
date: 2026-06-08
status: Draft
---

# manage.py Refactoring to Service-Oriented Architecture

## Overview

This document defines the refactoring of `manage.py` from a monolithic 1335-line file into a service-oriented architecture. The refactoring extracts business logic into testable, composable services while keeping the CLI interface unchanged for end users.

**Goals:**
- Improve testability by extracting services that can be unit-tested independently
- Prepare for future API layer (services can become API endpoints)
- Reduce manage.py complexity from 1335 lines to ~200-300 lines
- Enable easier addition of new commands and services
- Maintain backward compatibility with existing CLI interface

**Key Principle:** Services contain business logic; CLI is a thin presentation layer that calls services.

---

## Architecture: Service-Oriented Design

### Package Structure

```
homelab-gitops/
├── manage.py                          # CLI entry point (thin wrapper)
├── services/                          # NEW: Service layer
│   ├── __init__.py
│   ├── orchestrate.py                 # OrchestrateService
│   ├── config.py                      # ConfigService
│   ├── infrastructure.py               # InfrastructureService
│   ├── secrets.py                     # SecretsService
│   ├── dns.py                         # DNSService
│   └── utils.py                       # Shared utilities
├── tests/
│   ├── test_services/                 # NEW: Service unit tests
│   │   ├── test_orchestrate_service.py
│   │   ├── test_config_service.py
│   │   ├── test_infrastructure_service.py
│   │   ├── test_secrets_service.py
│   │   └── test_dns_service.py
│   └── [existing tests remain]
└── [other directories unchanged]
```

### Service Responsibilities

**SecretsService** (`services/secrets.py`)
- Bootstrap 1Password secrets from `config/secrets.env`
- Determine if secrets are needed for a given command
- Inject environment variables before command execution

**ConfigService** (`services/config.py`)
- Load, parse, and validate profiles (YAML)
- Create new profiles (CRUD)
- Create new Ansible roles and playbooks
- Resolve playbooks based on tags
- Load profiles into environment variables

**InfrastructureService** (`services/infrastructure.py`)
- vCenter integration (query VMs, create/manage tags)
- OpenTofu integration (plan, apply, destroy, workspace management)
- Ansible integration (run playbooks, validate syntax)
- Fleet status collection (vCenter + OpenTofu state)
- Common infrastructure helpers (MAC validation, host info)

**OrchestrateService** (`services/orchestrate.py`)
- Full VM lifecycle: build, lint, deploy, config, test, destroy, status
- Depends on: InfrastructureService, ConfigService
- Orchestrates multi-step workflows (lint → deploy → config → test)

**DNSService** (`services/dns.py`)
- Technetium DNS integration (list, create, delete records)
- DNS validation and management
- (Mirrors current `technetium_manager.py` functionality)

**utils.py** (`services/utils.py`)
- Shared utilities: `validate_mac()`, `track_time()`, `run_cmd()`, etc.
- No service-specific logic; pure helper functions

### Service Interfaces (Pseudocode)

```python
# SecretsService
class SecretsService:
    def bootstrap_secrets(self) -> bool:
        """Load secrets from 1Password if not already loaded."""
    
    def should_bootstrap(self, argv: List[str]) -> bool:
        """Determine if this command needs secrets."""

# ConfigService
class ConfigService:
    def load_profile(self, profile_name: str) -> dict:
        """Load and parse a profile YAML."""
    
    def validate_profile(self, profile: dict) -> bool:
        """Validate profile structure and required fields."""
    
    def create_profile(self, name: str, spec: dict, tags: List[str]) -> bool:
        """Create a new profile file."""
    
    def create_role(self, name: str) -> bool:
        """Create a new Ansible role directory structure."""
    
    def create_playbook(self, name: str) -> bool:
        """Create a new Ansible playbook file."""
    
    def resolve_playbook(self, profile: str) -> Tuple[str, List[str]]:
        """Get playbook and required extra vars for a profile's tags."""

# InfrastructureService
class InfrastructureService:
    def ensure_tags_exist(self, tags: List[str]) -> None:
        """Create vCenter tags if they don't exist."""
    
    def get_host_info(self, hostname: str) -> dict:
        """Query ESXi host info from vCenter."""
    
    def list_cluster_hosts(self) -> List[str]:
        """List all ESXi hosts in cluster."""
    
    def select_host_by_arch(self, preferred_arch: str) -> Optional[str]:
        """Select best ESXi host for deployment."""
    
    def collect_fleet_status(self) -> List[dict]:
        """Get status of all managed VMs."""
    
    def get_vm_status(self, vm_name: str) -> dict:
        """Get individual VM power/network/tag status."""
    
    def run_ansible_playbook(self, playbook: str, inventory: str, extra_vars: dict) -> bool:
        """Execute Ansible playbook."""

# OrchestrateService
class OrchestrateService:
    def __init__(self, infrastructure: InfrastructureService, config: ConfigService):
        """Depends on infrastructure and config services."""
    
    def build(self, target: str) -> bool:
        """Run Packer build (ubuntu-2404, ubuntu-2604, photon-docker)."""
    
    def lint(self, profile: str, index: str) -> bool:
        """Validate profile and infrastructure."""
    
    def deploy(self, profile: str, index: str, host: Optional[str], mac: Optional[str]) -> bool:
        """Provision VM via OpenTofu."""
    
    def config(self, profile: str, index: str) -> bool:
        """Apply Ansible configuration."""
    
    def test(self, profile: str, index: str) -> bool:
        """Run testinfra validation."""
    
    def destroy(self, identifier: str) -> bool:
        """Destroy VM by name, IP, or MAC."""
    
    def status(self) -> List[dict]:
        """Report fleet health and drift."""
    
    def all(self, profile: str, index: str, host: str) -> bool:
        """Full pipeline: lint → deploy → config → test."""

# DNSService
class DNSService:
    def list_records(self) -> List[dict]:
        """List all DNS records."""
    
    def create_record(self, name: str, ip: str, ttl: int) -> bool:
        """Create DNS A record."""
    
    def delete_record(self, name: str) -> bool:
        """Delete DNS record."""
    
    def validate_record(self, name: str, ip: str) -> bool:
        """Verify DNS resolves correctly."""
```

---

## CLI Refactoring (manage.py)

After refactoring, `manage.py` becomes a thin CLI wrapper (~200-300 lines):

```python
#!/usr/bin/env python3
"""CLI entry point. Wraps services with Typer + Rich."""

import typer
from rich.console import Console
from services.secrets import SecretsService
from services.config import ConfigService
from services.infrastructure import InfrastructureService
from services.orchestrate import OrchestrateService
from services.dns import DNSService

app = typer.Typer(help="Unified HomeLab GitOps Orchestrator")
console = Console()

# Initialize services
secrets = SecretsService()
config = ConfigService()
infrastructure = InfrastructureService()
orchestrate = OrchestrateService(infrastructure, config)
dns = DNSService()

# Bootstrap secrets before CLI runs
if __name__ == "__main__":
    secrets.bootstrap_secrets()

@app.command()
def build(target: str):
    """Build golden image (ubuntu-2404, ubuntu-2604, photon-docker)."""
    try:
        if orchestrate.build(target):
            console.print("[green]✓ Build completed[/green]")
        else:
            console.print("[red]✗ Build failed[/red]")
            raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)

@app.command()
def lint(profile: str, index: str):
    """Validate profile and vCenter infrastructure."""
    if orchestrate.lint(profile, index):
        console.print("[green]✓ Validation passed[/green]")
    else:
        raise typer.Exit(1)

@app.command()
def status():
    """Report fleet health."""
    rows = orchestrate.status()
    # Format and print as Rich table

# Similar thin wrappers for all other commands
```

**Key characteristics:**
- Each command is 5-10 lines (input validation + service call + output formatting)
- No business logic in manage.py
- All logic in services (testable, composable, reusable)
- CLI is pure presentation (Typer, Rich formatting)

---

## Testing Strategy

### Unit Tests (Services Only)

Services are tested with mocked dependencies:

```python
# tests/test_services/test_orchestrate_service.py
import pytest
from unittest.mock import Mock, patch
from services.orchestrate import OrchestrateService

class TestOrchestrateService:
    @pytest.fixture
    def mock_infrastructure(self):
        return Mock()
    
    @pytest.fixture
    def mock_config(self):
        return Mock()
    
    @pytest.fixture
    def service(self, mock_infrastructure, mock_config):
        return OrchestrateService(mock_infrastructure, mock_config)
    
    def test_lint_validates_profile(self, service, mock_config):
        """Test that lint loads and validates a profile."""
        mock_config.load_profile.return_value = {"name": "ubuntu-2404-base"}
        result = service.lint("ubuntu-2404-base", "01")
        assert result is True
        mock_config.load_profile.assert_called_once()
```

**Benefits:**
- Services tested independently (no vCenter, OpenTofu, Ansible needed)
- Mocked dependencies ensure tests are fast and isolated
- Test only service logic, not implementation details
- Easy to add new tests for new services

### Integration Tests (Unchanged)

Integration tests still target real infrastructure:
- Test VM with Ansible playbook execution
- OpenTofu plan/apply validation
- Testinfra assertions

### CLI Tests

CLI tests verify that Typer commands map correctly to services:
```python
# tests/test_cli.py
def test_build_command_calls_service(mock_orchestrate_service):
    """Test that CLI build command calls service.build()."""
    runner = CliRunner()
    result = runner.invoke(app, ["build", "ubuntu-2404"])
    mock_orchestrate_service.build.assert_called_once_with("ubuntu-2404")
```

---

## Migration Path: Two Phases

### Phase 1: Extract Services (No CLI Changes)

**Duration:** 1-2 days

**Scope:**
- Create `services/` directory with all service classes
- Extract logic from `manage.py` into appropriate services
- Write unit tests for each service
- Services are complete and tested; manage.py is unchanged

**Deliverables:**
- `services/orchestrate.py`, `services/config.py`, etc.
- `tests/test_services/` with comprehensive unit tests
- Services pass 90%+ coverage threshold
- No changes to manage.py CLI interface

**Risk:** None — existing CLI is untouched

### Phase 2: Refactor CLI to Use Services

**Duration:** 1 day

**Scope:**
- Replace function calls in `manage.py` with service method calls
- Remove old monolithic functions from `manage.py`
- Update existing tests to verify service integration
- Verify all commands still work as users expect

**Deliverables:**
- `manage.py` refactored to use services (~200-300 lines)
- All CLI commands still work (user-facing interface unchanged)
- All tests pass (unit + integration + CLI)
- Old code completely removed

**Risk:** Low — services already tested, CLI is just wiring

### Rollback Plan

If Phase 2 has issues:
1. Keep Phase 1 (services) — they're valuable on their own
2. Revert Phase 2 (keep old manage.py)
3. Services can be integrated gradually or used by API layer

---

## Future: API Layer

After refactoring, services are ready to become API endpoints:

```python
# api/orchestrate.py (future)
from fastapi import FastAPI
from services.orchestrate import OrchestrateService

app = FastAPI()
orchestrate = OrchestrateService(...)

@app.post("/orchestrate/build/{target}")
async def build(target: str):
    result = orchestrate.build(target)
    return {"success": result}

@app.get("/orchestrate/status")
async def status():
    return {"fleet": orchestrate.status()}
```

Services are reusable: same logic powers CLI and API.

---

## Related Documents

- `docs/superpowers/specs/2026-06-08-testing-policy-design.md` — Testing policy (will be easier to implement after refactor)
- `CLAUDE.md` — Development environment and conventions
- `DESIGN.md` — Architecture and principles

