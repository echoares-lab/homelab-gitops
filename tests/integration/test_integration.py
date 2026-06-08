"""Integration tests with mocked infrastructure.

These tests verify workflows with mocked drivers without requiring
actual vCenter, Ansible, or OpenTofu infrastructure.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from homelab_gitops.domain.workflows import Workflow
from homelab_gitops.domain.models import NodeProfile, TaskResult
from homelab_gitops.domain.exceptions import DomainError


class MockTofuDriver:
    """Mock OpenTofu driver for testing."""
    def __init__(self, success=True, vm_ip="10.10.10.50", duration=30.0):
        self.success = success
        self.vm_ip = vm_ip
        self.duration = duration
        self.calls = []

    def execute(self, task):
        """Execute a deploy task."""
        self.calls.append(task)
        if not self.success:
            raise Exception("Terraform apply failed")
        return TaskResult(
            success=True,
            task_type="deploy",
            output="VM deployed successfully",
            duration=self.duration,
            vm_ip=self.vm_ip
        )


class MockAnsibleDriver:
    """Mock Ansible driver for testing."""
    def __init__(self, success=True, duration=60.0):
        self.success = success
        self.duration = duration
        self.calls = []

    def execute(self, task):
        """Execute a config/test task."""
        self.calls.append(task)
        if not self.success:
            raise Exception("Ansible playbook failed")
        return TaskResult(
            success=True,
            task_type=task.type,
            output="Ansible playbook completed",
            duration=self.duration
        )


class TestWorkflowWithMockedDrivers:
    """Full workflow integration tests with mocked drivers."""

    @pytest.fixture
    def valid_profile(self):
        """Create a valid test profile."""
        return NodeProfile(
            name="ubuntu-base",
            vcenter={
                "datacenter": "DC",
                "cluster": "C",
                "datastore": "DS",
                "network": "N"
            },
            vm_specs={"cpu": 4, "memory": 8192, "disk": 50},
            deployment={"tags": ["ubuntu"]}
        )

    def test_deploy_only_workflow(self, valid_profile):
        """Single-stage workflow: deploy only."""
        deploy_driver = MockTofuDriver(vm_ip="10.10.10.51")
        workflow = Workflow(valid_profile, drivers={"deploy": deploy_driver})

        state = workflow.execute(["deploy"])

        assert state.state == "deployed"
        assert state.vm_ip == "10.10.10.51"
        assert len(deploy_driver.calls) == 1
        assert deploy_driver.calls[0].type == "deploy"

    def test_deploy_then_configure_workflow(self, valid_profile):
        """Multi-stage workflow: deploy → configure."""
        deploy_driver = MockTofuDriver(vm_ip="10.10.10.52")
        config_driver = MockAnsibleDriver()

        workflow = Workflow(valid_profile, drivers={
            "deploy": deploy_driver,
            "config": config_driver
        })

        state = workflow.execute(["deploy", "config"])

        assert state.state == "configured"
        assert state.vm_ip == "10.10.10.52"
        assert len(deploy_driver.calls) == 1
        assert len(config_driver.calls) == 1
        assert config_driver.calls[0].type == "config"

    def test_full_pipeline_deploy_config_test(self, valid_profile):
        """Full pipeline: deploy → configure → test."""
        deploy_driver = MockTofuDriver(vm_ip="10.10.10.53")
        config_driver = MockAnsibleDriver()
        test_driver = MockAnsibleDriver(duration=45.0)

        workflow = Workflow(valid_profile, drivers={
            "deploy": deploy_driver,
            "config": config_driver,
            "test": test_driver
        })

        state = workflow.execute(["deploy", "config", "test"])

        assert state.state == "tested"
        assert state.vm_ip == "10.10.10.53"
        assert len(deploy_driver.calls) == 1
        assert len(config_driver.calls) == 1
        assert len(test_driver.calls) == 1

    def test_deployment_state_carries_vm_ip(self, valid_profile):
        """VM IP from deploy stage is preserved through subsequent stages."""
        deploy_driver = MockTofuDriver(vm_ip="192.168.1.100")
        config_driver = MockAnsibleDriver()

        workflow = Workflow(valid_profile, drivers={
            "deploy": deploy_driver,
            "config": config_driver
        })

        state = workflow.execute(["deploy", "config"])

        # VM IP should persist through all stages
        assert state.vm_ip == "192.168.1.100"
        # Config driver should have received the task with target set
        assert config_driver.calls[0].target == "192.168.1.100"


class TestDriverErrorHandling:
    """Error handling and recovery tests."""

    @pytest.fixture
    def valid_profile(self):
        """Create a valid test profile."""
        return NodeProfile(
            name="ubuntu-base",
            vcenter={
                "datacenter": "DC",
                "cluster": "C",
                "datastore": "DS",
                "network": "N"
            },
            vm_specs={"cpu": 4, "memory": 8192, "disk": 50},
            deployment={"tags": ["ubuntu"]}
        )

    def test_deploy_driver_failure_transitions_to_failed(self, valid_profile):
        """Deployment failure transitions workflow to failed state."""
        failing_deploy = MockTofuDriver(success=False)
        workflow = Workflow(valid_profile, drivers={"deploy": failing_deploy})

        with pytest.raises(Exception, match="Terraform apply failed"):
            workflow.execute(["deploy"])

        assert workflow.state.state == "failed"
        assert "Terraform apply failed" in workflow.state.error

    def test_config_driver_failure_transitions_to_failed(self, valid_profile):
        """Configuration failure transitions workflow to failed state."""
        deploy_driver = MockTofuDriver()
        failing_config = MockAnsibleDriver(success=False)

        workflow = Workflow(valid_profile, drivers={
            "deploy": deploy_driver,
            "config": failing_config
        })

        with pytest.raises(Exception, match="Ansible playbook failed"):
            workflow.execute(["deploy", "config"])

        assert workflow.state.state == "failed"
        assert "Ansible playbook failed" in workflow.state.error

    def test_failure_during_second_stage_preserves_deployment_state(self, valid_profile):
        """Failed second stage preserves state from first stage."""
        deploy_driver = MockTofuDriver(vm_ip="10.10.10.200")
        failing_config = MockAnsibleDriver(success=False)

        workflow = Workflow(valid_profile, drivers={
            "deploy": deploy_driver,
            "config": failing_config
        })

        with pytest.raises(Exception):
            workflow.execute(["deploy", "config"])

        # VM IP should still be recorded even though config failed
        assert workflow.state.vm_ip == "10.10.10.200"
        assert workflow.state.state == "failed"


class TestDriverIntegration:
    """Driver interface and integration tests."""

    @pytest.fixture
    def valid_profile(self):
        """Create a valid test profile."""
        return NodeProfile(
            name="test-profile",
            vcenter={
                "datacenter": "DC",
                "cluster": "C",
                "datastore": "DS",
                "network": "N"
            },
            vm_specs={"cpu": 2, "memory": 4096, "disk": 25},
            deployment={"tags": ["ubuntu"]}
        )

    def test_driver_receives_correct_task_properties(self, valid_profile):
        """Drivers receive properly constructed task objects."""
        deploy_driver = MockTofuDriver()
        workflow = Workflow(valid_profile, drivers={"deploy": deploy_driver})

        workflow.execute(["deploy"])

        task = deploy_driver.calls[0]
        assert task.type == "deploy"
        assert task.profile == valid_profile
        assert isinstance(task.target, (str, type(None)))

    def test_driver_task_includes_profile(self, valid_profile):
        """Driver receives full profile data in task."""
        deploy_driver = MockTofuDriver()
        workflow = Workflow(valid_profile, drivers={"deploy": deploy_driver})

        workflow.execute(["deploy"])

        task = deploy_driver.calls[0]
        assert task.profile.name == "test-profile"
        assert task.profile.vm_specs["cpu"] == 2
        assert "ubuntu" in task.profile.deployment["tags"]

    def test_task_result_with_multiple_fields(self, valid_profile):
        """TaskResult properly captures all driver output fields."""
        class DetailedMockDriver:
            def execute(self, task):
                return TaskResult(
                    success=True,
                    task_type="deploy",
                    output="Complex output with details",
                    duration=42.5,
                    error=None,
                    vm_ip="10.10.10.100"
                )

        workflow = Workflow(valid_profile, drivers={
            "deploy": DetailedMockDriver()
        })

        state = workflow.execute(["deploy"])

        assert state.vm_ip == "10.10.10.100"
        assert state.state == "deployed"


class TestWorkflowStateTransitions:
    """State machine transitions through workflow execution."""

    @pytest.fixture
    def valid_profile(self):
        """Create a valid test profile."""
        return NodeProfile(
            name="transition-test",
            vcenter={
                "datacenter": "DC",
                "cluster": "C",
                "datastore": "DS",
                "network": "N"
            },
            vm_specs={"cpu": 1, "memory": 2048, "disk": 20},
            deployment={"tags": ["ubuntu"]}
        )

    def test_planned_to_deployed(self, valid_profile):
        """Workflow transitions from planned to deployed."""
        workflow = Workflow(valid_profile, drivers={"deploy": MockTofuDriver()})
        assert workflow.state.state == "planned"

        workflow.execute(["deploy"])

        assert workflow.state.state == "deployed"

    def test_deployed_to_configured(self, valid_profile):
        """Workflow transitions from deployed to configured."""
        workflow = Workflow(valid_profile, drivers={
            "deploy": MockTofuDriver(),
            "config": MockAnsibleDriver()
        })

        workflow.execute(["deploy", "config"])

        assert workflow.state.state == "configured"

    def test_configured_to_tested(self, valid_profile):
        """Workflow transitions from configured to tested."""
        workflow = Workflow(valid_profile, drivers={
            "deploy": MockTofuDriver(),
            "config": MockAnsibleDriver(),
            "test": MockAnsibleDriver()
        })

        workflow.execute(["deploy", "config", "test"])

        assert workflow.state.state == "tested"
