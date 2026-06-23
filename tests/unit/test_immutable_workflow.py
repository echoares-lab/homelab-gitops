import pytest
import os
from unittest.mock import patch, MagicMock
from homelab_gitops.domain.models import NodeProfile, Task, TaskResult, DeploymentState
from homelab_gitops.domain.exceptions import InvalidStateTransition, DomainError
from homelab_gitops.domain.immutable_workflow import ImmutableWorkflow

@pytest.fixture
def valid_profile():
    profile_dict = {
        "name": "fcos-node",
        "vcenter": {"datacenter": "DC", "cluster": "C", "datastore": "DS", "network": "N", "os_type": "fcos"},
        "vm_specs": {"cpu": 4, "memory": 8192, "disk": 50},
        "deployment": {"tags": ["fcos"]},
    }
    return NodeProfile(**profile_dict)

@pytest.fixture
def talos_profile():
    profile_dict = {
        "name": "talos-node",
        "vcenter": {"datacenter": "DC", "cluster": "C", "datastore": "DS", "network": "N", "os_type": "talos"},
        "vm_specs": {"cpu": 4, "memory": 8192, "disk": 50},
        "deployment": {"tags": ["talos"]},
    }
    return NodeProfile(**profile_dict)

class MockDriver:
    def __init__(self, task_type="build"):
        self.task_type = task_type

    def execute(self, task):
        return TaskResult(
            success=True,
            task_type=self.task_type,
            output=f"Executed {self.task_type}",
            duration=1.0,
            vm_ip="10.10.10.10",
        )

def test_immutable_workflow_init(valid_profile):
    drivers = {"build": MockDriver("build")}
    workflow = ImmutableWorkflow(valid_profile, drivers)
    assert workflow.profile == valid_profile
    assert workflow.state.state == "planned"

def test_immutable_workflow_invalid_profile():
    # Profile that fails validation (missing keys etc., though NodeProfile itself might raise first depending on Pydantic, but let's test YAMLSchemaValidator)
    # Actually if NodeProfile requires them, we can't instantiate it easily without them, but let's assume we can mock the validator.
    profile_dict = {
        "name": "invalid",
        "vcenter": {"datacenter": "DC", "cluster": "C", "datastore": "DS", "network": "N"},
        "vm_specs": {"cpu": 4, "memory": 8192, "disk": 50},
        "deployment": {"tags": []},
    }
    profile = NodeProfile(**profile_dict)
    
    with patch("homelab_gitops.domain.immutable_workflow.YAMLSchemaValidator") as mock_val_class:
        mock_val = MagicMock()
        mock_val.validate.return_value = MagicMock(success=False, errors=["bad"])
        mock_val_class.return_value = mock_val
        
        with pytest.raises(DomainError, match="Profile validation failed"):
            ImmutableWorkflow(profile, {})

def test_immutable_workflow_execute_build(valid_profile):
    drivers = {"build": MockDriver("build")}
    workflow = ImmutableWorkflow(valid_profile, drivers)
    state = workflow.execute(["build"])
    assert state.state == "built"

def test_immutable_workflow_execute_deploy_fcos(valid_profile):
    drivers = {"build": MockDriver("build"), "deploy": MockDriver("deploy")}
    workflow = ImmutableWorkflow(valid_profile, drivers)
    workflow.state.state = "built" # mock state progression
    
    with patch("homelab_gitops.immutable.transpilers.butane.ButaneTranspiler") as mock_butane, \
         patch("homelab_gitops.drivers.secrets_driver.SecretsDriver") as mock_secrets:
        
        # mock secrets to throw exception so it falls back to env vars
        mock_secrets.side_effect = Exception("No secrets")
        
        mock_instance = MagicMock()
        mock_instance.transpile.return_value = "fcos_ignition_data"
        mock_butane.return_value = mock_instance
        
        state = workflow.execute(["deploy"])
        assert state.state == "deployed"

def test_immutable_workflow_execute_deploy_talos(talos_profile):
    drivers = {"build": MockDriver("build"), "deploy": MockDriver("deploy")}
    workflow = ImmutableWorkflow(talos_profile, drivers)
    workflow.state.state = "built"
    
    with patch("homelab_gitops.immutable.transpilers.talos.TalosTranspiler") as mock_talos, \
         patch("homelab_gitops.drivers.secrets_driver.SecretsDriver") as mock_secrets:
        
        mock_secrets_instance = MagicMock()
        mock_secrets_instance.execute.return_value = MagicMock(output="secret")
        mock_secrets.return_value = mock_secrets_instance
        
        mock_instance = MagicMock()
        mock_instance.transpile.return_value = "talos_machine_config"
        mock_talos.return_value = mock_instance
        
        state = workflow.execute(["deploy"])
        assert state.state == "deployed"

def test_immutable_workflow_config_driver_override(valid_profile):
    drivers = {"config": MockDriver("config")} # This driver should be bypassed
    workflow = ImmutableWorkflow(valid_profile, drivers)
    workflow.state.state = "deployed"
    
    with patch("homelab_gitops.immutable.drivers.immutable_driver.ImmutableDriver") as mock_imm_driver:
        mock_instance = MagicMock()
        mock_instance.execute.return_value = TaskResult(success=True, task_type="config", output="done", duration=1.0)
        mock_imm_driver.return_value = mock_instance
        
        state = workflow.execute(["config"])
        assert state.state == "configured"
        mock_instance.execute.assert_called_once()

def test_immutable_workflow_invalid_transition(valid_profile):
    drivers = {"test": MockDriver("test")}
    workflow = ImmutableWorkflow(valid_profile, drivers)
    with pytest.raises(InvalidStateTransition):
        workflow.execute(["test"]) # Can't go to tested from pending

def test_immutable_workflow_missing_driver(valid_profile):
    workflow = ImmutableWorkflow(valid_profile, {})
    with pytest.raises(DomainError, match="No driver for stage"):
        workflow.execute(["build"])

def test_immutable_workflow_execution_failure(valid_profile):
    class FailingDriver:
        def execute(self, task):
            raise Exception("Execution failed")
            
    drivers = {"build": FailingDriver()}
    workflow = ImmutableWorkflow(valid_profile, drivers)
    
    with pytest.raises(Exception, match="Execution failed"):
        workflow.execute(["build"])
        
    assert workflow.state.state == "failed"
