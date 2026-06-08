# Architecture Refactor Design: Layered + Plugin System

**Date:** June 7, 2026  
**Scope:** Complete system redesign (CLI, orchestration, drivers, IaC, testing)  
**Approach:** Big bang refactor with backward-compatible CLI  
**Success Criteria:** Developer velocity, test coverage, maintainability, extensibility, performance/reliability

---

## Executive Summary

This design proposes a comprehensive modernization of the HomeLab GitOps pipeline, addressing three critical pain points:
1. **Hard to add features** — Currently requires modifying monolithic `manage.py`
2. **Minimal testing** — Limited unit tests, difficult to test logic without infrastructure
3. **Unclear separation of concerns** — CLI, orchestration, and infrastructure logic are tangled

**Solution:** Reorganize into a **4-layer architecture** with a **plugin-based CLI system**:
- **Layer 1 (CLI):** Modular command plugins (independent, testable)
- **Layer 2 (Domain):** Orchestration logic (workflows, state machines, validators)
- **Layer 3 (Drivers):** Infrastructure adapters (Ansible, Tofu, vCenter)
- **Layer 4 (IaC):** Infrastructure code organized by concern (Ansible roles, Tofu modules)

This design enables:
- ✅ New features added without touching core orchestrator
- ✅ Logic tested independently of infrastructure
- ✅ Clear responsibility boundaries
- ✅ Future extensibility (networking APIs, patching, machine registration)

---

## Design Sections

### 1. Layer 1: CLI & Commands (Plugin Architecture)

**Purpose:** Entry point for users. Each command is a self-contained plugin.

**Directory structure:**
```
src/
  homelab_gitops/
    cli/
      __init__.py
      app.py                 # Main typer app + plugin loader
      core_commands/         # Built-in commands (shipped with project)
        __init__.py
        build.py             # $ manage build PROFILE
        deploy.py            # $ manage deploy PROFILE INDEX
        config.py            # $ manage config PROFILE [INDEX]
        test.py              # $ manage test PROFILE [INDEX]
        destroy.py           # $ manage destroy IDENTIFIER
        status.py            # $ manage status
        lint.py              # $ manage lint PROFILE [INDEX]
      plugins/               # User/third-party plugins (optional)
        __init__.py
        plugin_loader.py     # Discover and register plugins at startup
      exceptions.py          # CLI-level exceptions (CommandError, ValidationError)
      utils.py               # Rich formatting, output utilities
```

**Plugin interface:**

Each plugin exports:
```python
# core_commands/deploy.py
import typer
from typing import Optional

def deploy_command(
    profile: str,
    index: Optional[str] = None,
    host: Optional[str] = None,
    ip: Optional[str] = None,
    gateway: Optional[str] = None,
) -> None:
    """Provision VM via OpenTofu."""
    # Plugin receives arguments, calls domain layer
    pass

# Register with CLI
command_metadata = {
    "name": "deploy",
    "aliases": ["dep"],
    "help": "Provision virtual hardware via OpenTofu",
}
```

**How plugins are loaded:**

`app.py` creates the Typer app and dynamically adds commands:
```python
def load_commands(app: typer.Typer, plugin_dir: str = "cli/core_commands"):
    """Load all plugins from a directory and register with app."""
    for plugin_file in Path(plugin_dir).glob("*.py"):
        if plugin_file.name.startswith("_"):
            continue
        module = import_module(f"homelab_gitops.cli.core_commands.{plugin_file.stem}")
        if hasattr(module, "command_metadata") and hasattr(module, f"{plugin_file.stem}_command"):
            metadata = module.command_metadata
            app.command(
                name=metadata["name"],
                aliases=metadata.get("aliases", []),
                help=metadata["help"],
            )(getattr(module, f"{plugin_file.stem}_command"))
```

**Benefits:**
- New contributors add a command by creating `core_commands/my_command.py` (no changes to `app.py`)
- Each command has its own test file (`tests/cli/test_my_command.py`)
- Plugins can be disabled by removing or renaming the file
- User plugins extend the tool without forking the repository
- Easy to replace commands (swap implementations without touching CLI framework)

---

### 2. Layer 2: Orchestration Domain

**Purpose:** Encapsulate all orchestration logic. Zero infrastructure dependencies.

**Directory structure:**
```
src/
  homelab_gitops/
    domain/
      __init__.py
      models.py              # Data classes (NodeProfile, DeploymentState, Task, TaskResult)
      workflows.py           # Workflow orchestration engine
      validators.py          # Profile validation, schema checks
      exceptions.py          # Domain-level exceptions
      state_machine.py       # Node lifecycle states
```

**Core models:**

```python
# domain/models.py

@dataclass
class NodeProfile:
    """Represents a profile YAML loaded and validated."""
    name: str
    vcenter: dict  # datacenter, cluster, datastore, network
    vm_specs: dict  # cpu, ram, disk
    deployment: dict  # tags, roles, playbooks
    
    def __post_init__(self):
        # Validate structure
        pass

@dataclass
class DeploymentState:
    """Tracks a node through its lifecycle."""
    profile_name: str
    index: str
    vm_name: str
    state: str  # "planned", "deployed", "configured", "tested"
    vm_ip: Optional[str] = None
    workspace_id: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)

@dataclass
class Task:
    """A unit of work for a driver to execute."""
    type: str  # "build", "provision", "configure", "test"
    profile: NodeProfile
    target: Optional[str] = None  # VM IP or name
    overrides: dict = field(default_factory=dict)

@dataclass
class TaskResult:
    """Result of task execution."""
    success: bool
    task_type: str
    output: str
    duration: float
    error: Optional[str] = None
```

**Workflow orchestration:**

```python
# domain/workflows.py

class Workflow:
    """Orchestrates the Build → Provision → Configure → Test pipeline."""
    
    def __init__(
        self,
        profile: NodeProfile,
        validators: List[Validator],
        drivers: Dict[str, Driver],
    ):
        self.profile = profile
        self.validators = validators
        self.drivers = drivers
        self.state = DeploymentState(...)
    
    def execute(self, stages: List[str]) -> DeploymentState:
        """Run stages in order, updating state machine."""
        for stage in stages:
            if not self.state_machine.can_transition(self.state, stage):
                raise InvalidStateTransition(...)
            
            task = self._prepare_task(stage)
            result = self.drivers[stage].execute(task)
            
            if not result.success:
                raise StageFailureError(...)
            
            self.state = self.state_machine.transition(self.state, stage, result)
        
        return self.state
```

**Validators:**

```python
# domain/validators.py

class Validator:
    """Base class for validation."""
    def validate(self, profile: NodeProfile) -> ValidationResult:
        pass

class YAMLSchemaValidator(Validator):
    """Validates profile YAML against JSON schema."""
    pass

class vCenterValidator(Validator):
    """Validates that vCenter infrastructure exists (datastore, network, cluster)."""
    def validate(self, profile: NodeProfile) -> ValidationResult:
        # Injected driver validates against vCenter, but returns pass/fail
        # Does NOT execute provisioning
        pass
```

**State machine:**

```python
# domain/state_machine.py

class StateMachine:
    """Enforces valid state transitions."""
    
    TRANSITIONS = {
        "planned": ["deployed"],
        "deployed": ["configured", "destroyed"],
        "configured": ["tested", "destroyed"],
        "tested": ["updated", "destroyed"],
    }
    
    def can_transition(self, current: str, next_stage: str) -> bool:
        return next_stage in self.TRANSITIONS.get(current, [])
    
    def transition(self, state: DeploymentState, stage: str, result: TaskResult) -> DeploymentState:
        """Update state after successful stage execution."""
        new_state = self._state_after_stage(stage)
        return DeploymentState(..., state=new_state)
```

**Benefits:**
- All orchestration logic is testable without infrastructure (mock drivers)
- Single source of truth for "what's the valid pipeline?"
- Clear error handling with domain exceptions
- Easy to add new validation rules or stages
- State machine prevents invalid operations (e.g., can't test before deploying)

---

### 3. Layer 3: Infrastructure Drivers

**Purpose:** Adapt domain tasks to infrastructure tools. Encapsulate tool-specific complexity.

**Directory structure:**
```
src/
  homelab_gitops/
    drivers/
      __init__.py
      base.py                # Abstract base classes
      ansible_driver.py      # Runs ansible-playbook
      tofu_driver.py         # Runs tofu apply/destroy
      vcenter_driver.py      # Queries/manages vCenter via govc
      exceptions.py          # Driver-level exceptions
```

**Base driver interface:**

```python
# drivers/base.py

class Driver(ABC):
    """Abstract base for all drivers."""
    
    @abstractmethod
    def execute(self, task: Task) -> TaskResult:
        """Execute a task and return result."""
        pass
    
    @abstractmethod
    def validate(self) -> bool:
        """Check prerequisites (govc installed, creds available, etc.)."""
        pass

class AnsibleDriver(Driver):
    """Execute Ansible playbooks."""
    
    def execute(self, task: Task) -> TaskResult:
        # Load playbook for task.profile
        # Resolve credentials
        # Run: ansible-playbook -i inventory playbook.yml
        # Parse output, return TaskResult
        pass
    
    def validate(self) -> bool:
        # Check ansible-playbook is installed
        # Check SSH keys are present
        return True

class TofuDriver(Driver):
    """Manage OpenTofu workspaces and state."""
    
    def execute(self, task: Task) -> TaskResult:
        # Load workspace (create if missing)
        # Translate NodeProfile → tofu variables
        # Run: tofu apply -var-file=...
        # Return: success, vm_ip, workspace_state
        pass
    
    def validate(self) -> bool:
        # Check tofu is installed
        # Check state backend is accessible
        return True

class vCenterDriver(Driver):
    """Query and manage vCenter objects."""
    
    def execute(self, task: Task) -> TaskResult:
        # Task type determines operation: create_tag, query_vm, etc.
        # Use govc CLI to interact with vCenter
        # Parse JSON output, return TaskResult
        pass
    
    def validate(self) -> bool:
        # Check govc is installed
        # Check credentials work: govc about
        return True
```

**Error translation:**

Drivers translate tool-specific errors into domain exceptions:
```python
# Example: TofuDriver catches tofu error → raises ProvisioningError
try:
    result = subprocess.run([tofu, "apply", ...], capture_output=True, text=True)
    if result.returncode != 0:
        if "insufficient resources" in result.stderr:
            raise InsufficientResourcesError(...)
        else:
            raise ProvisioningError(result.stderr)
except subprocess.TimeoutExpired:
    raise ProvisioningTimeout(...)
```

**Benefits:**
- Each driver is independently testable (mock subprocess calls)
- Tool-specific logic is isolated (easy to swap Pulumi for Tofu)
- Clear error translation (tool errors → domain exceptions)
- Credentials loaded once per driver, not scattered across codebase
- Drivers can be mocked in tests without running infrastructure

---

### 4. Layer 4: IaC Code Organization

**Purpose:** Organize infrastructure code by concern, not by tool. Enable reuse and clarity.

**Directory structure:**
```
iac/
  ansible/
    roles/
      base/                  # OS hardening, SSH, users (all OSes)
        tasks/
        handlers/
        templates/
      security/              # Security hardening, firewall
      docker/                # Docker runtime
      dns_technitium/        # DNS server setup
      github_runner/         # GitHub Actions runner + base
      github_runner_base/    # Runner OS dependencies
      dev_cloudflare/        # Cloudflare dev environment
      dev_homelab/           # Homelab dev environment
      dev_combined/          # Combined dev environment
    playbooks/
      site.yml               # Master play (tag-based discovery + role mapping)
      discover.yml           # Gather facts from vCenter inventory
    inventory/
      dynamic/
        vcenter_inventory.py # Generate inventory from vCenter tags
  
  tofu/
    modules/
      vm/                    # VM provisioning (reusable module)
        main.tf
        variables.tf
        outputs.tf
      network/               # Network configuration
        main.tf
        variables.tf
      storage/               # Storage/datastore configuration
        main.tf
    workspaces/              # One workspace per VM (auto-generated, in .gitignore)
      ubuntu-base-01/
        terraform.tfstate
        terraform.tfvars
    main.tf                  # Root module (calls vm/, network/, etc.)
    variables.tf             # Profile → Tofu variable mapping
    outputs.tf               # Fleet status queries
  
  tests/
    unit/                    # No infrastructure required
      test_validators.py     # Profile schema, YAML validation
      test_models.py         # Data class behavior
      test_workflows.py      # Orchestration logic with mocked drivers
      test_state_machine.py  # State transitions
    integration/             # Requires infrastructure (vCenter, optionally SSH to VM)
      test_ansible_driver.py # Playbook execution (mocked subprocess)
      test_tofu_driver.py    # State management, workspace handling
      test_vcenter_driver.py # Tag queries, VM discovery
      test_os.py             # Testinfra: SSH hardening, users, packages
      test_services.py       # Testinfra: docker, DNS, GitHub runner services
    e2e/                     # Full pipeline (optional, slow)
      test_full_deploy.py    # Build → Provision → Config → Test
    fixtures/
      conftest.py            # Pytest config + fixtures (mock drivers, etc.)
```

**Key changes from current structure:**

1. **Ansible roles** stay focused on their domain. No inline tasks in site.yml—use roles.
2. **Tofu modules** are reusable components. `modules/vm/` is called by root module, parameterized by variables.
3. **Tests are organized by layer:** Unit (logic), integration (drivers + infra), E2E (full pipeline).

**Example: Adding a new role**

Old way:
1. Create role directory
2. Update site.yml by hand
3. Update metadata.yml by hand
4. No clear way to test

New way:
1. Create role directory + tasks/main.yml
2. Site.yml auto-discovers roles by tag mapping (metadata-driven)
3. Add test file: `tests/integration/test_my_role.py`
4. Submit PR with role + tests

**Benefits:**
- Clear separation: what does each role/module do?
- Easy to refactor without breaking other subsystems
- Test failures point directly to the problem (CLI? Domain? Driver? IaC?)
- Follows GEMINI.md: immutable images, declarative infra, testinfra validation

---

### 5. Testing Architecture (3-Tier Pyramid)

**Purpose:** Fast feedback loop for developers. Comprehensive coverage without running full infrastructure.

**Tier 1: Unit Tests (Fast, No Infrastructure)**

```python
# tests/unit/test_validators.py
def test_profile_schema_validation():
    """Validate profile YAML against schema."""
    profile_yaml = {"vcenter": {...}, "vm_specs": {...}}
    result = YAMLSchemaValidator().validate(NodeProfile(**profile_yaml))
    assert result.success

def test_invalid_profile_rejects():
    """Invalid profiles are rejected."""
    profile_yaml = {"vcenter": {...}}  # Missing vm_specs
    with pytest.raises(SchemaValidationError):
        NodeProfile(**profile_yaml)

# tests/unit/test_workflows.py
def test_workflow_transition_to_configured():
    """Workflow can transition from deployed to configured."""
    profile = NodeProfile(...)
    workflow = Workflow(profile, drivers={...})
    workflow.state = DeploymentState(..., state="deployed")
    
    assert workflow.state_machine.can_transition("deployed", "configured")

def test_invalid_transition_raises():
    """Can't test before deploying."""
    workflow = Workflow(...)
    with pytest.raises(InvalidStateTransition):
        workflow.state_machine.transition("planned", "test")
```

**Tier 2: Integration Tests (Mocked Infrastructure)**

```python
# tests/integration/test_ansible_driver.py
@pytest.fixture
def mock_subprocess():
    """Mock subprocess.run to simulate ansible-playbook execution."""
    pass

def test_ansible_driver_execute(mock_subprocess):
    """AnsibleDriver successfully executes playbook."""
    mock_subprocess.return_value = CompletedProcess(returncode=0, stdout="OK")
    
    driver = AnsibleDriver()
    task = Task(type="config", profile=...)
    result = driver.execute(task)
    
    assert result.success
    mock_subprocess.assert_called_once()  # ansible-playbook was invoked

# tests/integration/test_workflows_with_mocks.py
def test_full_workflow_with_mocked_drivers(mock_tofu_driver, mock_ansible_driver):
    """Full workflow from deploy to config with mocked infrastructure."""
    profile = NodeProfile(...)
    workflow = Workflow(
        profile,
        drivers={
            "deploy": mock_tofu_driver,
            "config": mock_ansible_driver,
        }
    )
    
    result = workflow.execute(["deploy", "config"])
    
    assert result.state == "configured"
    mock_tofu_driver.execute.assert_called_once()
    mock_ansible_driver.execute.assert_called_once()
```

**Tier 3: E2E Tests (Full Pipeline, Optional)**

```python
# tests/e2e/test_full_deploy.py
@pytest.mark.slow
def test_full_deploy_ubuntu_base():
    """Full pipeline: build → deploy → config → test."""
    # This test actually runs packer, tofu, ansible, testinfra
    # Use pytest.mark.slow + CI skip to keep local dev fast
    profile = NodeProfile.from_file("config/profiles/ubuntu-2404-base.yml")
    workflow = Workflow(profile, drivers=RealDrivers())
    
    result = workflow.execute(["build", "deploy", "config", "test"])
    
    assert result.state == "tested"
```

**Conftest pattern:**

```python
# tests/fixtures/conftest.py

@pytest.fixture
def mock_tofu_driver():
    """Mock driver that records calls without running tofu."""
    class MockTofuDriver:
        def __init__(self):
            self.calls = []
        def execute(self, task):
            self.calls.append(task)
            return TaskResult(success=True, ...)
    return MockTofuDriver()

@pytest.fixture
def mock_vcenter_driver():
    """Mock vCenter driver that returns canned responses."""
    # ...
    pass
```

**Running tests locally:**

```bash
# Fast: unit tests only (no infrastructure)
pytest tests/unit/ -v

# Medium: unit + integration tests (mocked infrastructure)
pytest tests/unit tests/integration -v

# Slow: everything (requires vCenter + VMs)
pytest tests/ -v -m "not slow"  # Skip E2E

# CI: run everything
pytest tests/ -v
```

**Benefits:**
- Local development is fast (unit tests in <1s)
- Developers can test logic without vSphere access
- Integration tests validate driver behavior before running real infrastructure
- E2E tests ensure full pipeline works but are optional for daily development

---

### 6. Data Flow & Integration Points

**Command execution flow:**

When a user runs `python3 manage.py deploy ubuntu-base 01 --host esxi-01`:

```
User Input
    ↓
┌──────────────────────────────────────────────────────────┐
│ Layer 1: CLI (deploy.py plugin)                          │
│ • Parse arguments: profile="ubuntu-base", index="01"     │
│ • Call domain layer                                      │
└──────────────────────────────────────────────────────────┘
    ↓
┌──────────────────────────────────────────────────────────┐
│ Layer 2: Domain (Workflow)                               │
│ 1. Load profile YAML + resolve metadata                  │
│ 2. Validate: YAMLSchemaValidator, vCenterValidator      │
│ 3. Query vCenter: find/create workspace for VM           │
│ 4. Check state machine: can transition from planned?    │
│ 5. Prepare task: {profile, workspace, overrides}        │
│ Returns: Task object to drivers                          │
└──────────────────────────────────────────────────────────┘
    ↓
┌──────────────────────────────────────────────────────────┐
│ Layer 3: Drivers (TofuDriver.execute)                    │
│ 1. Load workspace state from tofu/workspaces/            │
│ 2. Translate NodeProfile → tofu variables                │
│ 3. Run: tofu apply -var-file=... (calls IaC)            │
│ 4. Parse output: extract vm_ip, workspace_state         │
│ Returns: TaskResult {success, vm_ip, duration}          │
└──────────────────────────────────────────────────────────┘
    ↓
┌──────────────────────────────────────────────────────────┐
│ Layer 4: IaC Code (tofu/main.tf)                         │
│ • Calls: tofu/modules/vm/ (provision from golden image)  │
│ • Calls: tofu/modules/network/ (configure NIC)           │
│ • Outputs: vm_ip, workspace_state, etc.                 │
└──────────────────────────────────────────────────────────┘
    ↓
Back through layers to CLI
    ↓
User sees: "✓ Deployed ubuntu-base-01 at 10.10.10.50"
```

**Multi-machine targeting:**

Command: `python3 manage.py config ubuntu-base` (no index)

```
Layer 1: CLI parses profile="ubuntu-base", no index
    ↓
Layer 2: Workflow queries vCenter via vCenterDriver
    • Find all VMs tagged with ubuntu-base deployment tags
    • Returns: [vm1_ip, vm2_ip, vm3_ip, ...]
    • Creates target_list
    ↓
Layer 3: AnsibleDriver receives target_list
    • Run: ansible-playbook -i target_list site.yml
    • Playbook uses dynamic discovery from vCenter
    ↓
Layer 4: Ansible plays apply to all matching hosts
    • tag_ubuntu plays run on all ubuntu VMs
    • Parallel execution (serial: 0)
```

**Error handling flow:**

```
IaC error (tofu apply fails with "insufficient resources")
    ↓
TofuDriver.execute() catches subprocess error
    • Parses stderr for error pattern
    • Raises: InsufficientResourcesError("Cluster has no free resources")
    ↓
Workflow.execute() catches InsufficientResourcesError
    • Updates state: DeploymentState(state="failed", error=...)
    • Logs context: profile, stage, timestamp
    ↓
CLI deploy_command() catches ProvisioningError
    • Formats message: "[bold red]Error:[/bold red] Cluster out of resources. Check vCenter."
    • Prints to user
    • Exit code 1
    ↓
User sees helpful error message and can troubleshoot
```

**Configuration resolution:**

```
Step 1: User provides profile name + CLI args
    • $ manage deploy ubuntu-base 01 --ip 10.10.10.50
    
Step 2: Layer 2 loads YAML
    • Load: config/profiles/ubuntu-base.yml
    • Resolve: deployment.tags → which roles/playbooks to run
    
Step 3: Secrets are resolved
    • If task needs secrets (github_pat, runner_token, etc.)
    • Layer 1 checks: is OP_SERVICE_ACCOUNT_TOKEN set?
    • If not: re-exec with `op run --env-file=config/secrets.env`
    • Layer 2 reads: config/secrets.env (op:// references)
    • Secrets injected into environment
    
Step 4: Layer 3 drivers inject config into tools
    • TofuDriver: translate profile vars → tofu variables
    • AnsibleDriver: load playbook + extra-vars
    • vCenterDriver: pass credentials from environment
    
Step 5: Layer 4 tools execute with fully-resolved config
    • Tofu: `tofu apply -var cpu=4 -var network=10.10.10.0/24`
    • Ansible: `ansible-playbook -e github_pat=$GITHUB_PAT`
```

---

### 7. Migration & Implementation Strategy

**What's included in this refactor:**
- Redesign all 4 layers (CLI, domain, drivers, IaC)
- Implement plugin system + refactor existing commands
- Rewrite test suite (unit + integration + E2E)
- Update documentation (CLAUDE.md, architecture guide)

**What's NOT included (future extensions):**
- Networking API integration
- Machine registration workflows
- Patching/update automation
- Third-party plugin ecosystem (infrastructure in place, no built-in extensions)

**Implementation order:**

1. **Foundation layers (2-3):** Build domain + drivers first (testable before CLI exists)
   - Define models.py, workflows.py, validators.py
   - Implement base.py drivers + mock versions
   - Write unit + driver tests
   - This establishes the contract for Layer 1 to depend on

2. **CLI (Layer 1):** Implement plugin system, migrate commands
   - Build app.py + plugin_loader.py
   - Refactor `manage.py` commands → plugin modules
   - Write CLI tests
   - Keep `manage.py` as a thin wrapper during transition

3. **IaC (Layer 4):** Reorganize Ansible/Tofu
   - Move/rename Ansible roles (mostly file moves)
   - Modularize Tofu (extract modules/)
   - Update playbook structure
   - No functional changes, just organization

4. **Tests:** Comprehensive test suite
   - Unit tests (models, validators, workflows)
   - Integration tests (drivers with mocks)
   - E2E tests (optional, full pipeline)
   - Aim for 80%+ coverage on critical paths

5. **Documentation:**
   - Update CLAUDE.md with new structure
   - Write architecture guide (what goes where)
   - Update RUNBOOK.md for new CLI structure
   - Add contributing guide for plugin development

**Backward compatibility:**

- Final CLI is backward compatible (all existing commands work)
- Flag any breaking changes (e.g., renamed playbooks) in release notes
- Old `manage.py` script replaced by new modular structure, but `python3 manage deploy ...` still works

**Deliverables:**

1. New `src/homelab_gitops/` package structure
2. All existing functionality works (backward compatible)
3. Design document (this file)
4. Updated CLAUDE.md
5. Comprehensive test suite (80%+ coverage)
6. Architecture guide for contributors

---

## Questions & Considerations

**Q: Why big bang instead of gradual migration?**
A: Big bang allows a clean break from the monolithic `manage.py`. Gradual migration would require maintaining two parallel systems, which is more work and confusing for contributors. Big bang is riskier but results in a clearer codebase.

**Q: How do we ensure backward compatibility?**
A: The CLI interface remains the same (`manage build`, `manage deploy`, etc.). The plugin system is an implementation detail. Users don't see any change in how they use the tool.

**Q: What about the existing `matrix_test.py`?**
A: It validates the orchestrator's logic consistency. In the new design, this logic is in Layer 2 (Workflow, StateMachine). Unit tests replace matrix_test's role.

**Q: Can users write plugins?**
A: Yes, the architecture supports it (plugins/ directory). However, official "third-party plugin ecosystem" is future work. For now, users fork and add plugins to `plugins/`.

**Q: What if a new requirement conflicts with this design?**
A: The layered architecture is flexible. New requirements (patching, networking APIs) are added to existing layers without breaking the structure.

---

## Success Criteria Alignment

| Criterion | How Design Addresses It |
|-----------|------------------------|
| **Developer velocity** | Plugin system enables new commands without modifying core. Test infrastructure allows testing logic before infrastructure exists. |
| **Test coverage** | 3-tier pyramid: unit (fast), integration (mocked), E2E (optional). Layer 2 is fully testable in isolation. |
| **Maintainability** | Clear layer separation. 15-minute onboarding: read Layer 1 → 2 → 3 → 4 in order. |
| **Extensibility** | Plugin model + driver adapter pattern allow adding features without forking. Future: networking APIs, patching as new drivers. |
| **Performance/reliability** | Cleaner error handling (domain exceptions). State machine prevents invalid operations. Faster local testing (unit tests run in <1s). |

---

## Risk Mitigation

| Risk | Mitigation |
|------|-----------|
| **Big bang introduces regressions** | Comprehensive test suite validates behavior before, during, and after. E2E tests ensure full pipeline works. |
| **Contributors confused by new structure** | Updated CLAUDE.md + architecture guide explain each layer clearly. Consistent patterns (all drivers follow same interface). |
| **vCenter/secrets integration breaks** | Layer 3 (drivers) is already tested in integration tests. vCenterDriver validates credentials early. |
| **Backward compatibility issues** | All existing commands work in new CLI. CLI tests validate argument parsing matches old behavior. |

---

## Appendix: File Organization Summary

**Before (Monolithic):**
```
manage.py           (2000+ lines)
scripts/
  profile_manager.py
  matrix_test.py
  lint_config.py
  ... (scattered utilities)
```

**After (Modular):**
```
src/homelab_gitops/
  cli/
    core_commands/          (one module per command)
    plugins/                (user extensions)
  domain/                   (business logic, testable)
  drivers/                  (infrastructure adapters)
iac/
  ansible/                  (organized roles)
  tofu/                     (modular HCL)
  tests/                    (3-tier test pyramid)
```

This structure is significantly more navigable and maintainable.
