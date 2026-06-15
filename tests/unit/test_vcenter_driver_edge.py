import pytest
import subprocess
import json
from unittest.mock import MagicMock, patch
from homelab_gitops.drivers.vcenter_driver import vCenterDriver
from homelab_gitops.drivers.exceptions import PrerequisiteError, ExecutionError
from homelab_gitops.domain.models import Task, NodeProfile

@pytest.fixture
def driver():
    with patch("shutil.which", return_value="/usr/local/bin/govc"):
        return vCenterDriver()

@pytest.fixture
def mock_profile():
    return NodeProfile(
        name="test-vm",
        vcenter={"datacenter": "dc1", "cluster": "cl1", "datastore": "ds1", "network": "net1"},
        vm_specs={"cpu": 2, "memory": 4096, "disk": 20},
        deployment={"tags": ["test"], "roles": ["base"], "playbooks": ["site.yml"]}
    )

def test_init_default_path():
    with patch("shutil.which", return_value=None):
        driver = vCenterDriver()
        assert driver.govc_path == "build/govc"

def test_validate_success(driver):
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0)
        assert driver.validate() is True
        mock_run.assert_called_once()

def test_validate_govc_not_found():
    with patch("shutil.which", return_value=None):
        d = vCenterDriver()
        # govc_path will be "build/govc"
        with patch("subprocess.run", side_effect=FileNotFoundError):
            with pytest.raises(PrerequisiteError, match="govc tool not found or failed to run"):
                d.validate()

def test_validate_govc_error(driver):
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=1)
        with pytest.raises(PrerequisiteError, match="govc not available or vCenter not reachable"):
            driver.validate()

def test_validate_subprocess_error(driver):
    with patch("subprocess.run", side_effect=subprocess.SubprocessError):
        with pytest.raises(PrerequisiteError, match="govc tool not found or failed to run"):
            driver.validate()

def test_execute_test_success(driver, mock_profile):
    task = Task(type="test", profile=mock_profile)
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout=json.dumps({
                "VirtualMachines": [{
                    "Runtime": {"PowerState": "poweredOn"},
                    "Guest": {"IpAddress": "192.168.1.10"}
                }]
            })
        )
        result = driver.execute(task)
        assert result.success is True
        assert result.vm_ip == "192.168.1.10"
        assert "Power: poweredOn" in result.output

def test_execute_test_vm_not_found(driver, mock_profile):
    task = Task(type="test", profile=mock_profile)
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout=json.dumps({"VirtualMachines": []})
        )
        with pytest.raises(ExecutionError, match="VM test-vm not found"):
            driver.execute(task)

def test_execute_test_govc_error(driver, mock_profile):
    task = Task(type="test", profile=mock_profile)
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=1, stderr="Some error")
        with pytest.raises(ExecutionError, match="Failed to get VM info for test-vm: Some error"):
            driver.execute(task)

def test_execute_test_invalid_json(driver, mock_profile):
    task = Task(type="test", profile=mock_profile)
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0, stdout="not json")
        with pytest.raises(ExecutionError, match="Failed to parse govc output"):
            driver.execute(task)

def test_execute_destroy_success(driver, mock_profile):
    task = Task(type="destroy", profile=mock_profile)
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0)
        result = driver.execute(task)
        assert result.success is True
        assert "destroyed" in result.output
        assert mock_run.call_count == 2

def test_execute_destroy_error(driver, mock_profile):
    task = Task(type="destroy", profile=mock_profile)
    with patch("subprocess.run") as mock_run:
        # First call (power off) succeeds, second (destroy) fails
        mock_run.side_effect = [
            MagicMock(returncode=0),
            MagicMock(returncode=1, stderr="Destroy failed")
        ]
        with pytest.raises(ExecutionError, match="Failed to destroy VM test-vm: Destroy failed"):
            driver.execute(task)

def test_execute_unsupported_type(driver, mock_profile):
    task = Task(type="unsupported", profile=mock_profile)
    with pytest.raises(ExecutionError, match="vCenterDriver doesn't handle unsupported yet"):
        driver.execute(task)
