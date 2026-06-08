---
title: Phase 2 Tool Integration Design - Service-Oriented Refactor
date: 2026-06-08
status: draft
---

# Phase 2 Tool Integration Design

## Overview

**Goal:** Complete Phase 2 of the service-oriented refactor by implementing actual tool integrations (OpenTofu, Ansible, testinfra, Packer) that were stubbed in Phase 1.

**Current State:** Services have correct structure and tests, but all tool invocations are TODOs returning True.

**Phase 2 Scope:** Implement VM lifecycle operations (deploy, config, test, destroy) with real tool calls. DNS/Technetium deferred to Phase 2.5.

**Architecture:** Wrapper classes encapsulate tool knowledge, keeping services clean and testable.

---

## Architecture: Wrapper Layer Pattern

### Design Principle

```
OrchestrateService (business logic)
         ↓
    Wrappers (tool knowledge)
         ↓
  Subprocess (tool execution)
```

Services call wrapper methods, never subprocess directly. Wrappers:
- Validate tool availability (fail fast)
- Construct command arguments
- Execute via subprocess
- Parse output and return success/failure

This separation:
- ✅ Keeps services tool-agnostic
- ✅ Makes mocking trivial (mock wrappers, not subprocess)
- ✅ Centralizes tool logic (easy to maintain)
- ✅ Enables unit tests without tool installation

### Wrapper Directory Structure

```
services/
├── __init__.py
├── wrappers/                    # NEW
│   ├── __init__.py
│   ├── base_wrapper.py          # Abstract base class
│   ├── tofu_wrapper.py          # OpenTofu integration
│   ├── ansible_wrapper.py       # Ansible playbook execution
│   ├── packer_wrapper.py        # Packer image builds
│   └── testinfra_wrapper.py     # testinfra test execution
├── orchestrate.py               # MODIFIED (use wrappers)
├── infrastructure.py            # May use some wrappers
├── config.py                    # (unchanged)
├── dns.py                       # (unchanged, deferred)
├── secrets.py                   # (unchanged)
└── utils.py                     # (unchanged)
```

---

## Wrapper Classes

### Base Wrapper (Abstract)

**File:** `services/wrappers/base_wrapper.py`

```python
from abc import ABC, abstractmethod
import subprocess
import shutil
from typing import List
from rich.console import Console

console = Console()

class BaseWrapper(ABC):
    """Abstract base for all tool wrappers."""
    
    @property
    @abstractmethod
    def tool_name(self) -> str:
        """Tool name (e.g., 'tofu', 'ansible-playbook')."""
        pass
    
    def __init__(self):
        """Initialize wrapper and validate tool is installed."""
        self._validate_tool_installed()
    
    def _validate_tool_installed(self) -> None:
        """Check if tool exists in PATH. Raise RuntimeError if missing."""
        if not shutil.which(self.tool_name):
            raise RuntimeError(
                f"{self.tool_name} not found in PATH. "
                f"Please install {self.tool_name} and ensure it's in your PATH."
            )
    
    def _run_command(self, cmd: List[str], cwd: str = None) -> subprocess.CompletedProcess:
        """
        Execute a command and return the result.
        
        Args:
            cmd: Command as list of arguments (e.g., ['tofu', 'apply'])
            cwd: Optional working directory
        
        Returns:
            subprocess.CompletedProcess with returncode, stdout, stderr
        
        Raises:
            RuntimeError: If command fails
        """
        try:
            console.print(f"[dim]Running: {' '.join(cmd)}[/dim]")
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                cwd=cwd,
                check=False
            )
            
            if result.returncode != 0:
                console.print(f"[yellow]Command output: {result.stderr}[/yellow]")
            
            return result
        except Exception as e:
            raise RuntimeError(f"Failed to execute {self.tool_name}: {e}")
```

### TofuWrapper

**File:** `services/wrappers/tofu_wrapper.py`

```python
from typing import List, Optional
from services.wrappers.base_wrapper import BaseWrapper

class TofuWrapper(BaseWrapper):
    """OpenTofu command wrapper for IaC operations."""
    
    @property
    def tool_name(self) -> str:
        return "tofu"
    
    def __init__(self, workspace: str = "default", chdir: str = "tofu/"):
        """
        Initialize Tofu wrapper.
        
        Args:
            workspace: OpenTofu workspace name (e.g., 'ubuntu-2404-base-01')
            chdir: Directory containing OpenTofu files (default: 'tofu/')
        """
        super().__init__()
        self.workspace = workspace
        self.chdir = chdir
    
    def _build_apply_command(self) -> List[str]:
        """Build tofu apply command."""
        return [
            "tofu",
            "-chdir=" + self.chdir,
            "apply",
            "-var-file=environments/prod.tfvars",
            "-auto-approve"
        ]
    
    def _build_destroy_command(self) -> List[str]:
        """Build tofu destroy command."""
        return [
            "tofu",
            "-chdir=" + self.chdir,
            "destroy",
            "-auto-approve"
        ]
    
    def apply(self) -> bool:
        """
        Run 'tofu apply' to provision VM.
        
        Returns:
            True if apply succeeded, False otherwise
        """
        cmd = self._build_apply_command()
        result = self._run_command(cmd)
        return result.returncode == 0
    
    def destroy(self) -> bool:
        """
        Run 'tofu destroy' to decommission VM.
        
        Returns:
            True if destroy succeeded, False otherwise
        """
        cmd = self._build_destroy_command()
        result = self._run_command(cmd)
        return result.returncode == 0
    
    def workspace_new(self, name: str) -> bool:
        """Create a new OpenTofu workspace."""
        cmd = ["tofu", "-chdir=" + self.chdir, "workspace", "new", name]
        result = self._run_command(cmd)
        return result.returncode == 0
    
    def workspace_delete(self, name: str) -> bool:
        """Delete an OpenTofu workspace."""
        cmd = ["tofu", "-chdir=" + self.chdir, "workspace", "delete", "-force", name]
        result = self._run_command(cmd)
        return result.returncode == 0
```

### AnsibleWrapper

**File:** `services/wrappers/ansible_wrapper.py`

```python
from typing import List, Dict, Optional
from services.wrappers.base_wrapper import BaseWrapper

class AnsibleWrapper(BaseWrapper):
    """Ansible playbook wrapper for configuration management."""
    
    @property
    def tool_name(self) -> str:
        return "ansible-playbook"
    
    def run_playbook(
        self,
        playbook: str,
        inventory: str = "ansible/inventory/vmware_vms.yml",
        extra_vars: Optional[Dict] = None,
        tags: Optional[List[str]] = None
    ) -> bool:
        """
        Run an Ansible playbook.
        
        Args:
            playbook: Path to playbook file (e.g., 'ansible/site.yml')
            inventory: Path to inventory file
            extra_vars: Dictionary of extra variables to pass to playbook
            tags: List of tags to run (e.g., ['docker', 'security'])
        
        Returns:
            True if playbook succeeded, False otherwise
        """
        cmd = ["ansible-playbook", playbook, "-i", inventory]
        
        # Add extra variables
        if extra_vars:
            for key, value in extra_vars.items():
                cmd.extend(["-e", f"{key}={value}"])
        
        # Add tags
        if tags:
            cmd.extend(["-t", ",".join(tags)])
        
        result = self._run_command(cmd)
        return result.returncode == 0
    
    def validate_syntax(self, playbook: str) -> bool:
        """
        Validate playbook syntax without executing.
        
        Args:
            playbook: Path to playbook file
        
        Returns:
            True if syntax is valid, False otherwise
        """
        cmd = ["ansible-playbook", playbook, "--syntax-check"]
        result = self._run_command(cmd)
        return result.returncode == 0
```

### TestinfraWrapper

**File:** `services/wrappers/testinfra_wrapper.py`

```python
from typing import List, Optional
from services.wrappers.base_wrapper import BaseWrapper

class TestinfraWrapper(BaseWrapper):
    """testinfra (pytest-testinfra) wrapper for VM validation."""
    
    @property
    def tool_name(self) -> str:
        return "pytest"
    
    def run_tests(
        self,
        hosts: List[str],
        test_dir: str = "tests/",
        ssh_key: Optional[str] = None,
        sudo: bool = True
    ) -> bool:
        """
        Run testinfra tests against one or more hosts.
        
        Args:
            hosts: List of host specifications (e.g., ['ansible@10.10.10.50'])
            test_dir: Directory containing testinfra tests
            ssh_key: Optional SSH private key file
            sudo: Whether to use sudo for tests
        
        Returns:
            True if all tests passed, False otherwise
        """
        cmd = ["pytest", test_dir, "-v"]
        
        # Add host specifications
        hosts_str = " ".join(hosts)
        cmd.extend([f"--hosts={hosts_str}"])
        
        # Add SSH options
        if ssh_key:
            ssh_extra = f"-o IdentityFile={ssh_key} -o StrictHostKeyChecking=no"
            cmd.extend(["--ssh-extra-args=" + ssh_extra])
        
        if sudo:
            cmd.append("--sudo")
        
        result = self._run_command(cmd)
        return result.returncode == 0
```

### PackerWrapper

**File:** `services/wrappers/packer_wrapper.py`

```python
from typing import List
from services.wrappers.base_wrapper import BaseWrapper

class PackerWrapper(BaseWrapper):
    """Packer wrapper for golden image builds."""
    
    @property
    def tool_name(self) -> str:
        return "packer"
    
    def build(self, target: str) -> bool:
        """
        Build a golden image.
        
        Args:
            target: Build target (e.g., 'ubuntu-2404', 'photon-docker')
        
        Returns:
            True if build succeeded, False otherwise
        """
        template = f"packer/{target}.pkr.hcl"
        cmd = ["packer", "build", template]
        result = self._run_command(cmd)
        return result.returncode == 0
    
    def validate_template(self, template: str) -> bool:
        """
        Validate Packer template without building.
        
        Args:
            template: Path to Packer template file
        
        Returns:
            True if template is valid, False otherwise
        """
        cmd = ["packer", "validate", template]
        result = self._run_command(cmd)
        return result.returncode == 0
```

---

## Service Integration

### OrchestrateService Changes

**File:** `services/orchestrate.py`

```python
from services.wrappers.tofu_wrapper import TofuWrapper
from services.wrappers.ansible_wrapper import AnsibleWrapper
from services.wrappers.packer_wrapper import PackerWrapper
from services.wrappers.testinfra_wrapper import TestinfraWrapper

class OrchestrateService:
    def __init__(self, infrastructure, config):
        self.infrastructure = infrastructure
        self.config_service = config
        
        # Initialize wrappers
        self.tofu = TofuWrapper()
        self.ansible = AnsibleWrapper()
        self.packer = PackerWrapper()
        self.testinfra = TestinfraWrapper()
    
    def build(self, target: str) -> bool:
        """Build golden image with Packer."""
        console.print(f"[bold blue]Building {target}...[/bold blue]")
        start = time.time()
        
        try:
            result = self.packer.build(target)
            if result:
                console.print("[green]✓ Build succeeded[/green]")
            else:
                console.print("[red]✗ Build failed[/red]")
            track_time(start, f"build {target}")
            return result
        except Exception as e:
            console.print(f"[red]✗ Build failed: {e}[/red]")
            return False
    
    def deploy(self, profile, index, host=None, mac=None) -> bool:
        """Provision VM with OpenTofu."""
        console.print(f"[bold blue]Deploying {profile} {index}...[/bold blue]")
        start = time.time()
        
        try:
            if mac:
                validate_mac(mac)
            
            profile_data = self.config_service.load_profile(profile)
            
            # Create workspace and apply
            workspace_name = f"{profile}-{index}"
            self.tofu.workspace_new(workspace_name)
            result = self.tofu.apply()
            
            if result:
                console.print("[green]✓ Deploy succeeded[/green]")
            else:
                console.print("[red]✗ Deploy failed[/red]")
            track_time(start, f"deploy {profile} {index}")
            return result
        except Exception as e:
            console.print(f"[red]✗ Deploy failed: {e}[/red]")
            return False
    
    def config(self, profile, index) -> bool:
        """Apply Ansible configuration."""
        console.print(f"[bold blue]Configuring {profile} {index}...[/bold blue]")
        start = time.time()
        
        try:
            playbook, extra_vars = self.config_service.resolve_playbook(profile)
            result = self.ansible.run_playbook(playbook, extra_vars=extra_vars)
            
            if result:
                console.print("[green]✓ Config succeeded[/green]")
            else:
                console.print("[red]✗ Config failed[/red]")
            track_time(start, f"config {profile} {index}")
            return result
        except Exception as e:
            console.print(f"[red]✗ Config failed: {e}[/red]")
            return False
    
    def test(self, profile, index) -> bool:
        """Run testinfra validation."""
        console.print(f"[bold blue]Testing {profile} {index}...[/bold blue]")
        start = time.time()
        
        try:
            # Get VM IP (would be determined from deploy output or vCenter)
            vm_ip = "10.10.10.50"  # Example, actual implementation gets from state
            hosts = [f"ansible@{vm_ip}"]
            
            result = self.testinfra.run_tests(hosts=hosts)
            
            if result:
                console.print("[green]✓ Tests passed[/green]")
            else:
                console.print("[red]✗ Tests failed[/red]")
            track_time(start, f"test {profile} {index}")
            return result
        except Exception as e:
            console.print(f"[red]✗ Tests failed: {e}[/red]")
            return False
    
    def destroy(self, identifier) -> bool:
        """Destroy VM."""
        console.print(f"[bold yellow]Destroying {identifier}...[/bold yellow]")
        start = time.time()
        
        try:
            # Find and delete workspace
            result = self.tofu.destroy()
            
            if result:
                console.print("[green]✓ Destroy succeeded[/green]")
            else:
                console.print("[red]✗ Destroy failed[/red]")
            track_time(start, f"destroy {identifier}")
            return result
        except Exception as e:
            console.print(f"[red]✗ Destroy failed: {e}[/red]")
            return False
```

---

## Testing Strategy

### Unit Tests (Existing Pattern, No Changes)

Unit tests continue to mock wrappers:

```python
# tests/test_services/test_orchestrate_service.py

@pytest.fixture
def mock_wrappers():
    return {
        'tofu': Mock(spec=TofuWrapper),
        'ansible': Mock(spec=AnsibleWrapper),
        'testinfra': Mock(spec=TestinfraWrapper),
        'packer': Mock(spec=PackerWrapper),
    }

def test_deploy_calls_tofu_apply(mock_wrappers):
    service = OrchestrateService(
        infrastructure=Mock(),
        config=Mock(),
        tofu_wrapper=mock_wrappers['tofu']
    )
    mock_wrappers['tofu'].apply.return_value = True
    
    result = service.deploy("ubuntu-2404", "01", host="esxi-01.mgmt.plexplease.com")
    
    assert result is True
    mock_wrappers['tofu'].apply.assert_called_once()
```

### Integration Tests (New, Separate from Unit Tests)

Create `tests/integration/` directory for tests that use real tools:

```python
# tests/integration/test_orchestrate_real.py
# (Requires tofu, ansible, pytest installed)

@pytest.mark.integration
def test_deploy_real_infrastructure():
    """Full deploy test against real vCenter and OpenTofu."""
    service = OrchestrateService(
        infrastructure=RealInfrastructureService(),
        config=RealConfigService()
    )
    
    # This uses REAL tofu, real vCenter, etc.
    result = service.deploy("ubuntu-2404-test", "01", host="test-esxi.mgmt")
    
    assert result is True
    # Verify VM created in vCenter
```

---

## Error Handling

### Fail-Fast Strategy

Wrappers validate tool availability at initialization:

```python
try:
    service = OrchestrateService(...)  # Initializes wrappers
except RuntimeError as e:
    # E.g., "tofu not found in PATH"
    console.print(f"[red]Configuration error: {e}[/red]")
    sys.exit(1)
```

### Clear Error Messages

When tool execution fails:

```python
def deploy(self, ...):
    try:
        result = self.tofu.apply()
        if not result:
            raise RuntimeError(
                "tofu apply failed. Check:\n"
                "  1. tofu -chdir=tofu/ validate\n"
                "  2. vCenter credentials in environment\n"
                "  3. OpenTofu state: tofu -chdir=tofu/ show"
            )
        return True
    except RuntimeError as e:
        console.print(f"[red]{e}[/red]")
        return False
```

---

## Implementation Order

1. **BaseWrapper** — Abstract base (no dependencies)
2. **TofuWrapper** — Foundation (deploy/destroy depend on it)
3. **AnsibleWrapper** — Config depends on it
4. **TestinfraWrapper** — Test depends on it
5. **PackerWrapper** — Separate, can be last (build is lower priority)
6. **Update OrchestrateService** — Use wrappers in all methods
7. **Update Unit Tests** — Ensure they mock wrappers correctly
8. **Add Integration Test Skeleton** — Framework for real tool tests

---

## Success Criteria

- ✅ All 4 wrappers implemented with correct interfaces
- ✅ OrchestrateService uses wrappers (no direct subprocess calls)
- ✅ All existing unit tests still pass (30 tests)
- ✅ Services fail fast if tools not installed
- ✅ Clear error messages for tool failures
- ✅ Integration test framework in place (tests runnable separately)
- ✅ No TODOs remaining in OrchestrateService
- ✅ Backward compatible — `python3 manage.py deploy` actually deploys
