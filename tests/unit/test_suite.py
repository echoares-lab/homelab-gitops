"""Comprehensive unit test suite for domain layer.

This suite consolidates tests for:
- Domain models (NodeProfile, DeploymentState, Task, TaskResult)
- State machine (lifecycle enforcement)
- Validators (YAML schema, tags)
- Workflows (orchestration)
- Exceptions (error context)
"""

import pytest
from datetime import datetime
from homelab_gitops.domain.models import (
    NodeProfile, DeploymentState, Task, TaskResult
)
from homelab_gitops.domain.state_machine import StateMachine
from homelab_gitops.domain.validators import (
    YAMLSchemaValidator, TagValidator, ValidationResult
)
from homelab_gitops.domain.workflows import Workflow
from homelab_gitops.domain.exceptions import (
    DomainError, ValidationError, InvalidStateTransition
)


# ============================================================================
# MODELS TESTS
# ============================================================================

class TestNodeProfile:
    """NodeProfile data model tests."""

    def test_creation_with_valid_data(self):
        """NodeProfile creation with valid data."""
        profile = NodeProfile(
            name="test",
            vcenter={
                "datacenter": "DC",
                "cluster": "C",
                "datastore": "DS",
                "network": "N"
            },
            vm_specs={"cpu": 4, "memory": 8192, "disk": 50},
            deployment={"tags": ["ubuntu", "docker"]}
        )
        assert profile.name == "test"
        assert profile.vcenter["datacenter"] == "DC"
        assert profile.vm_specs["cpu"] == 4

    def test_missing_vcenter_keys_raises_error(self):
        """NodeProfile raises ValueError if vcenter keys missing."""
        with pytest.raises(ValueError, match="vcenter missing required key"):
            NodeProfile(
                name="test",
                vcenter={"datacenter": "DC"},  # Missing cluster, datastore, network
                vm_specs={"cpu": 4, "memory": 8192, "disk": 50},
                deployment={"tags": ["ubuntu"]}
            )

    def test_missing_vm_specs_keys_raises_error(self):
        """NodeProfile raises ValueError if vm_specs keys missing."""
        with pytest.raises(ValueError, match="vm_specs missing required key"):
            NodeProfile(
                name="test",
                vcenter={
                    "datacenter": "DC",
                    "cluster": "C",
                    "datastore": "DS",
                    "network": "N"
                },
                vm_specs={"cpu": 4},  # Missing memory, disk
                deployment={"tags": ["ubuntu"]}
            )


class TestDeploymentState:
    """DeploymentState lifecycle tracking tests."""

    def test_initial_state(self):
        """DeploymentState initializes with 'planned' state."""
        state = DeploymentState(
            profile_name="profile",
            index="01",
            vm_name="vm-01"
        )
        assert state.state == "planned"
        assert state.vm_ip is None
        assert state.error is None
        assert isinstance(state.created_at, datetime)

    def test_state_transitions(self):
        """DeploymentState tracks state changes."""
        state = DeploymentState(
            profile_name="profile",
            index="01",
            vm_name="vm-01"
        )
        # Simulate deployment
        state.state = "deployed"
        state.vm_ip = "10.10.10.50"
        assert state.state == "deployed"
        assert state.vm_ip == "10.10.10.50"

        # Simulate configuration
        state.state = "configured"
        assert state.state == "configured"

    def test_error_tracking(self):
        """DeploymentState can record errors."""
        state = DeploymentState(
            profile_name="profile",
            index="01",
            vm_name="vm-01"
        )
        state.state = "failed"
        state.error = "Provisioning timeout"
        assert state.state == "failed"
        assert "timeout" in state.error


class TestTask:
    """Task unit of work tests."""

    def test_task_creation(self):
        """Task represents a unit of work."""
        profile = NodeProfile(
            name="test",
            vcenter={
                "datacenter": "DC",
                "cluster": "C",
                "datastore": "DS",
                "network": "N"
            },
            vm_specs={"cpu": 1, "memory": 1024, "disk": 10},
            deployment={"tags": ["ubuntu"]}
        )
        task = Task(type="deploy", profile=profile, target="10.10.10.50")
        assert task.type == "deploy"
        assert task.profile == profile
        assert task.target == "10.10.10.50"

    def test_task_with_overrides(self):
        """Task can include configuration overrides."""
        profile = NodeProfile(
            name="test",
            vcenter={
                "datacenter": "DC",
                "cluster": "C",
                "datastore": "DS",
                "network": "N"
            },
            vm_specs={"cpu": 1, "memory": 1024, "disk": 10},
            deployment={"tags": ["ubuntu"]}
        )
        task = Task(
            type="config",
            profile=profile,
            overrides={"dry_run": True}
        )
        assert task.overrides["dry_run"] is True


class TestTaskResult:
    """TaskResult execution result tests."""

    def test_successful_result(self):
        """TaskResult records successful execution."""
        result = TaskResult(
            success=True,
            task_type="deploy",
            output="VM created",
            duration=30.5,
            vm_ip="10.10.10.50"
        )
        assert result.success is True
        assert result.vm_ip == "10.10.10.50"
        assert result.duration == 30.5

    def test_failed_result(self):
        """TaskResult records failures."""
        result = TaskResult(
            success=False,
            task_type="deploy",
            output="",
            duration=5.0,
            error="vCenter connection timeout"
        )
        assert result.success is False
        assert "timeout" in result.error


# ============================================================================
# STATE MACHINE TESTS
# ============================================================================

class TestStateMachine:
    """State machine lifecycle enforcement tests."""

    def test_valid_transitions(self):
        """State machine allows valid transitions."""
        sm = StateMachine()
        assert sm.can_transition("planned", "deployed")
        assert sm.can_transition("deployed", "configured")
        assert sm.can_transition("configured", "tested")

    def test_invalid_transitions(self):
        """State machine rejects invalid transitions."""
        sm = StateMachine()
        # Cannot jump from planned to tested
        assert not sm.can_transition("planned", "tested")
        # Cannot go backwards
        assert not sm.can_transition("configured", "deployed")

    def test_can_transition_to_destroyed_from_deployed(self):
        """Workflow can transition to destroyed from deployed."""
        sm = StateMachine()
        assert sm.can_transition("deployed", "destroyed")
        assert sm.can_transition("configured", "destroyed")
        assert sm.can_transition("tested", "destroyed")

    def test_transition_updates_state(self):
        """Transition updates the state object."""
        sm = StateMachine()
        state = DeploymentState(
            profile_name="p",
            index="01",
            vm_name="vm-01"
        )
        result = TaskResult(
            success=True,
            task_type="deploy",
            output="ok",
            duration=30.0,
            vm_ip="10.10.10.50"
        )
        new_state = sm.transition(state, "deploy", result)
        assert new_state.state == "deployed"
        assert new_state.vm_ip == "10.10.10.50"


# ============================================================================
# VALIDATOR TESTS
# ============================================================================

class TestYAMLSchemaValidator:
    """YAML schema validation tests."""

    def test_valid_profile_passes(self):
        """Validator accepts valid profile."""
        profile = NodeProfile(
            name="test",
            vcenter={
                "datacenter": "DC",
                "cluster": "C",
                "datastore": "DS",
                "network": "N"
            },
            vm_specs={"cpu": 1, "memory": 1024, "disk": 10},
            deployment={"tags": ["ubuntu"]}
        )
        validator = YAMLSchemaValidator()
        result = validator.validate(profile)
        assert result.success

    def test_validator_returns_validation_result(self):
        """Validator returns ValidationResult object."""
        profile = NodeProfile(
            name="test",
            vcenter={
                "datacenter": "DC",
                "cluster": "C",
                "datastore": "DS",
                "network": "N"
            },
            vm_specs={"cpu": 1, "memory": 1024, "disk": 10},
            deployment={"tags": ["ubuntu"]}
        )
        validator = YAMLSchemaValidator()
        result = validator.validate(profile)
        assert isinstance(result, ValidationResult)
        assert hasattr(result, 'success')
        assert hasattr(result, 'errors')


class TestTagValidator:
    """Tag validation tests."""

    def test_valid_tags_pass(self):
        """Validator accepts valid tags."""
        profile = NodeProfile(
            name="test",
            vcenter={
                "datacenter": "DC",
                "cluster": "C",
                "datastore": "DS",
                "network": "N"
            },
            vm_specs={"cpu": 1, "memory": 1024, "disk": 10},
            deployment={"tags": ["ubuntu", "docker"]}
        )
        validator = TagValidator()
        result = validator.validate(profile)
        assert result.success

    def test_empty_tags_accepted(self):
        """Validator accepts profiles with no tags."""
        profile = NodeProfile(
            name="test",
            vcenter={
                "datacenter": "DC",
                "cluster": "C",
                "datastore": "DS",
                "network": "N"
            },
            vm_specs={"cpu": 1, "memory": 1024, "disk": 10},
            deployment={"tags": ["ubuntu"]}
        )
        validator = TagValidator()
        result = validator.validate(profile)
        assert result.success


class TestValidationResult:
    """ValidationResult data structure tests."""

    def test_validation_result_success(self):
        """ValidationResult tracks successful validation."""
        result = ValidationResult(success=True, errors=[])
        assert result.success is True
        assert result.errors == []

    def test_validation_result_failure(self):
        """ValidationResult tracks validation failure."""
        result = ValidationResult(
            success=False,
            errors=["Profile name missing", "vcenter.datacenter required"]
        )
        assert result.success is False
        assert len(result.errors) == 2


# ============================================================================
# WORKFLOW TESTS
# ============================================================================

class TestWorkflowOrchestration:
    """Workflow orchestration tests."""

    @pytest.fixture
    def valid_profile(self):
        """Create a valid profile for workflow tests."""
        return NodeProfile(
            name="test",
            vcenter={
                "datacenter": "DC",
                "cluster": "C",
                "datastore": "DS",
                "network": "N"
            },
            vm_specs={"cpu": 1, "memory": 1024, "disk": 10},
            deployment={"tags": ["ubuntu"]}
        )

    class MockDriver:
        """Mock driver for testing."""
        def __init__(self, success=True, vm_ip=None):
            self.success = success
            self.vm_ip = vm_ip or "10.10.10.50"

        def execute(self, task):
            return TaskResult(
                success=self.success,
                task_type=task.type,
                output="ok",
                duration=1.0,
                vm_ip=self.vm_ip if task.type == "deploy" else None
            )

    def test_workflow_creation_validates_profile(self, valid_profile):
        """Workflow validates profile on creation."""
        drivers = {"deploy": self.MockDriver()}
        workflow = Workflow(valid_profile, drivers=drivers)
        assert workflow.profile == valid_profile

    def test_workflow_execute_single_stage(self, valid_profile):
        """Workflow executes single stage."""
        drivers = {"deploy": self.MockDriver()}
        workflow = Workflow(valid_profile, drivers=drivers)
        state = workflow.execute(["deploy"])
        assert state.state == "deployed"
        assert state.vm_ip == "10.10.10.50"

    def test_workflow_execute_multiple_stages(self, valid_profile):
        """Workflow executes multiple stages in sequence."""
        drivers = {
            "deploy": self.MockDriver(),
            "config": self.MockDriver()
        }
        workflow = Workflow(valid_profile, drivers=drivers)
        state = workflow.execute(["deploy", "config"])
        assert state.state == "configured"

    def test_workflow_invalid_transition_raises_error(self, valid_profile):
        """Workflow rejects invalid stage transitions."""
        drivers = {"deploy": self.MockDriver()}
        workflow = Workflow(valid_profile, drivers=drivers)
        with pytest.raises(InvalidStateTransition):
            # Cannot jump from planned to tested
            workflow.execute(["test"])

    def test_workflow_missing_driver_raises_error(self, valid_profile):
        """Workflow raises error if driver missing."""
        drivers = {}  # No drivers registered
        workflow = Workflow(valid_profile, drivers=drivers)
        with pytest.raises(DomainError, match="No driver for stage"):
            workflow.execute(["deploy"])

    def test_workflow_handles_driver_errors(self, valid_profile):
        """Workflow transitions to failed state on driver error."""
        class FailingDriver:
            def execute(self, task):
                raise Exception("Provisioning failed")

        drivers = {"deploy": FailingDriver()}
        workflow = Workflow(valid_profile, drivers=drivers)
        with pytest.raises(Exception, match="Provisioning failed"):
            workflow.execute(["deploy"])
        assert workflow.state.state == "failed"


# ============================================================================
# EXCEPTION TESTS
# ============================================================================

class TestDomainExceptions:
    """Domain exception tests."""

    def test_domain_error_is_exception(self):
        """DomainError is an Exception."""
        error = DomainError("Something went wrong")
        assert isinstance(error, Exception)
        assert str(error) == "Something went wrong"

    def test_validation_error(self):
        """ValidationError captures validation details."""
        error = ValidationError("Profile invalid", ["Missing name", "Bad CPU"])
        assert "Profile invalid" in str(error)

    def test_invalid_state_transition_error(self):
        """InvalidStateTransition captures state context."""
        error = InvalidStateTransition("planned", "tested")
        error_str = str(error)
        assert "planned" in error_str
        assert "tested" in error_str
        assert isinstance(error, Exception)
