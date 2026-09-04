"""Unit tests for Core Lifecycle wiring and orchestration."""

import pytest
from unittest.mock import MagicMock, patch
import os
from homelab_gitops.domain.workflows import Workflow
from homelab_gitops.domain.status import StatusService
from homelab_gitops.domain.models import NodeProfile, Task, TaskResult, DeploymentState
from homelab_gitops.drivers.packer_driver import PackerDriver
from homelab_gitops.drivers.tofu_driver import TofuDriver
from homelab_gitops.drivers.ansible_driver import AnsibleDriver
from homelab_gitops.drivers.vcenter_driver import vCenterDriver

@pytest.fixture
def dummy_profile():
    return NodeProfile(
        name="test-profile",
        vcenter={"datacenter": "D", "cluster": "C", "datastore": "S", "network": "N"},
        vm_specs={"cpu": 1, "memory": 1, "disk": 1},
        deployment={"tags": [], "roles": [], "playbooks": []}
    )

@pytest.fixture
def mock_drivers():
    return {
        "build": MagicMock(),
        "deploy": MagicMock(),
        "config": MagicMock(),
        "test": MagicMock(),
        "destroy": MagicMock(),
    }

def test_workflow_execute_pipeline(dummy_profile, mock_drivers):
    """Test full build -> deploy -> config pipeline."""
    workflow = Workflow(dummy_profile, drivers=mock_drivers)
    
    # Mock driver results
    for driver in mock_drivers.values():
        driver.execute.return_value = TaskResult(
            success=True, task_type="any", output="ok", duration=1.0, vm_ip="1.2.3.4"
        )
        
    state = workflow.execute(["build", "deploy", "config"])
    
    assert state.state == "configured"
    assert state.vm_ip == "1.2.3.4"
    assert mock_drivers["build"].execute.called
    assert mock_drivers["deploy"].execute.called
    assert mock_drivers["config"].execute.called

def test_status_service_aggregate(dummy_profile):
    """Test StatusService aggregates data from Tofu and vCenter."""
    mock_vcenter = MagicMock()
    mock_tofu = MagicMock()
    
    mock_tofu.get_status.return_value = {"provisioned": True, "drift": False}
    mock_vcenter.get_vm_status.return_value = {"provisioned": "Yes", "power": "On", "ip": "10.0.0.1"}
    
    service = StatusService(vcenter_provider=mock_vcenter, tofu_provider=mock_tofu)
    status = service.get_fleet_status([dummy_profile])
    
    assert len(status) == 1
    assert status[0]["name"] == "test-profile"
    assert status[0]["provisioned"] == "Yes"
    assert status[0]["power"] == "On"
    assert status[0]["ip"] == "10.0.0.1"
    assert status[0]["drift"] == "No"

@patch("shutil.which", return_value="/usr/bin/packer")
@patch("os.path.exists", return_value=True)
@patch("subprocess.run")
def test_packer_driver_execute(mock_run, mock_exists, mock_which):
    """Test PackerDriver execution."""
    mock_run.return_value = MagicMock(returncode=0, stdout="built")
    
    driver = PackerDriver()
    profile = NodeProfile(
        name="p1",
        vcenter={"datacenter": "D", "cluster": "C", "datastore": "S", "network": "N", "os_type": "photon"},
        vm_specs={"cpu": 1, "memory": 1, "disk": 1},
        deployment={"tags": [], "roles": [], "playbooks": []}
    )
    task = Task(type="build", profile=profile)
    
    result = driver.execute(task)
    assert result.success is True
    assert "packer/photon.pkr.hcl" in mock_run.call_args[0][0]

@patch("shutil.which", return_value="/usr/bin/tofu")
@patch("subprocess.run")
def test_tofu_driver_execute_deploy(mock_run, mock_which):
    """Test TofuDriver deploy execution."""
    # Mock outputs for init, workspace list, workspace select, and apply
    mock_run.side_effect = [
        MagicMock(returncode=0), # init
        MagicMock(returncode=0, stdout="default"), # workspace list
        MagicMock(returncode=0), # workspace select
        MagicMock(returncode=0), # apply
        MagicMock(returncode=0, stdout='{"vm_ip": {"value": "1.2.3.4"}}'), # output
    ]
    
    driver = TofuDriver()
    profile = NodeProfile(
        name="p1",
        vcenter={"datacenter": "D", "cluster": "C", "datastore": "S", "network": "N"},
        vm_specs={"cpu": 1, "memory": 1, "disk": 1},
        deployment={"tags": [], "roles": [], "playbooks": []}
    )
    task = Task(type="deploy", profile=profile)
    
    result = driver.execute(task)
    assert result.success is True
    assert result.vm_ip == "1.2.3.4"

@patch("shutil.which", return_value="/usr/bin/ansible-playbook")
@patch("os.path.exists", return_value=True)
@patch("subprocess.run")
def test_ansible_driver_execute_config(mock_run, mock_exists, mock_which):
    """Test AnsibleDriver config execution."""
    mock_run.return_value = MagicMock(returncode=0, stdout="configured")
    mock_exists.side_effect = lambda p: str(p) != "1.2.3.4"
    
    driver = AnsibleDriver()
    profile = NodeProfile(
        name="p1",
        vcenter={"datacenter": "D", "cluster": "C", "datastore": "S", "network": "N"},
        vm_specs={"cpu": 1, "memory": 1, "disk": 1},
        deployment={"tags": [], "roles": [], "playbooks": []}
    )
    task = Task(type="config", profile=profile, target="1.2.3.4")
    
    result = driver.execute(task)
    assert result.success is True
    assert "ansible/site.yml" in mock_run.call_args[0][0]
    assert "1.2.3.4," in mock_run.call_args[0][0]
