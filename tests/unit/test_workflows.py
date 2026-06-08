import pytest
from homelab_gitops.domain.workflows import Workflow
from homelab_gitops.domain.models import NodeProfile, Task, TaskResult
from homelab_gitops.domain.state_machine import StateMachine
from homelab_gitops.domain.exceptions import InvalidStateTransition

def test_workflow_execute_deploy():
    """Workflow executes deploy stage."""
    profile_dict = {
        "name": "ubuntu-base",
        "vcenter": {"datacenter": "DC", "cluster": "C", "datastore": "DS", "network": "N"},
        "vm_specs": {"cpu": 4, "memory": 8192, "disk": 50},
        "deployment": {"tags": ["ubuntu"]},
    }
    profile = NodeProfile(**profile_dict)

    class MockDriver:
        def execute(self, task):
            return TaskResult(
                success=True,
                task_type="deploy",
                output="Deployed",
                duration=30.0,
                vm_ip="10.10.10.50",
            )

    workflow = Workflow(profile, drivers={"deploy": MockDriver()})
    state = workflow.execute(["deploy"])

    assert state.state == "deployed"
    assert state.vm_ip == "10.10.10.50"

def test_workflow_invalid_transition():
    """Workflow prevents invalid transitions."""
    profile_dict = {
        "name": "test",
        "vcenter": {"datacenter": "DC", "cluster": "C", "datastore": "DS", "network": "N"},
        "vm_specs": {"cpu": 1, "memory": 1024, "disk": 10},
        "deployment": {"tags": ["ubuntu"]},
    }
    profile = NodeProfile(**profile_dict)

    workflow = Workflow(profile, drivers={})

    with pytest.raises(InvalidStateTransition):
        workflow.execute(["test"])

def test_workflow_validates_profile():
    """Workflow validates profile on creation."""
    from homelab_gitops.domain.exceptions import DomainError

    invalid_profile_dict = {
        "name": "test",
        "vcenter": {},  # Missing required keys
        "vm_specs": {},
        "deployment": {},
    }

    with pytest.raises((DomainError, ValueError)):
        NodeProfile(**invalid_profile_dict)
