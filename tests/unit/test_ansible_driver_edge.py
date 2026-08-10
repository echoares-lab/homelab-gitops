import pytest
import subprocess
import shutil
import os
import json
from unittest.mock import patch, MagicMock
from homelab_gitops.drivers.ansible_driver import AnsibleDriver
from homelab_gitops.drivers.exceptions import PrerequisiteError, ExecutionError
from homelab_gitops.domain.models import Task, NodeProfile

@pytest.fixture
def mock_profile():
    return NodeProfile(
        name="test-profile",
        vcenter={"datacenter": "dc1", "cluster": "cl1", "datastore": "ds1", "network": "net1"},
        vm_specs={"cpu": 2, "memory": 4096, "disk": 40},
        deployment={"roles": ["base"], "tags": ["test"]}
    )

@pytest.fixture
def driver():
    with patch("shutil.which", return_value="/usr/bin/ansible-playbook"):
        return AnsibleDriver()

def test_validate_success(driver):
    assert driver.validate() is True

def test_validate_failure():
    with patch("shutil.which", return_value=None):
        driver = AnsibleDriver()
        with pytest.raises(PrerequisiteError, match="ansible-playbook not found in PATH"):
            driver.validate()

def test_execute_unsupported_type(driver, mock_profile):
    task = Task(type="unsupported", profile=mock_profile)
    with pytest.raises(ExecutionError, match="Unsupported task type: unsupported"):
        driver.execute(task)

def test_execute_playbook_not_found(driver, mock_profile):
    task = Task(type="config", profile=mock_profile, overrides={"playbook": "nonexistent.yml"})
    with patch("os.path.exists", return_value=False):
        with pytest.raises(ExecutionError, match="Playbook not found: nonexistent.yml"):
            driver.execute(task)

def test_execute_success(driver, mock_profile):
    mock_profile.deployment["tags"] = []
    task = Task(
        type="config",
        profile=mock_profile,
        target="1.2.3.4",
        overrides={"playbook": "site.yml", "ssh_user": "admin", "custom_var": "value"}
    )
    
    mock_result = MagicMock()
    mock_result.returncode = 0
    mock_result.stdout = "Ansible output"
    mock_result.stderr = ""

    with patch("os.path.exists", side_effect=lambda x: x == "site.yml"), \
         patch("subprocess.run", return_value=mock_result) as mock_run:
        
        result = driver.execute(task)
        
        assert result.success is True
        assert result.output == "Ansible output"
        
        # Verify command construction
        args, kwargs = mock_run.call_args
        cmd = args[0]
        assert "/usr/bin/ansible-playbook" in cmd
        assert "-i" in cmd
        assert "1.2.3.4," in cmd
        assert "site.yml" in cmd
        assert "-u" in cmd
        assert "admin" in cmd
        assert "-e" in cmd
        
        # Verify extra vars
        extra_vars_str = cmd[cmd.index("-e") + 1]
        extra_vars = json.loads(extra_vars_str)
        assert extra_vars["profile_name"] == "test-profile"
        assert extra_vars["custom_var"] == "value"
        assert "roles" in extra_vars

def test_execute_failure(driver, mock_profile):
    task = Task(type="config", profile=mock_profile, target="localhost")
    
    mock_result = MagicMock()
    mock_result.returncode = 1
    mock_result.stdout = "Some output"
    mock_result.stderr = "Ansible error"

    with patch("os.path.exists", return_value=True), \
         patch("subprocess.run", return_value=mock_result):
        
        with pytest.raises(ExecutionError, match=r"Ansible failed \(RC=1\):\nSTDOUT:\nSome output\nSTDERR:\nAnsible error"):
            driver.execute(task)

def test_execute_failure_no_stderr(driver, mock_profile):
    task = Task(type="config", profile=mock_profile, target="localhost")
    
    mock_result = MagicMock()
    mock_result.returncode = 2
    mock_result.stdout = "Some output"
    mock_result.stderr = ""

    with patch("os.path.exists", return_value=True), \
         patch("subprocess.run", return_value=mock_result):
        
        with pytest.raises(ExecutionError, match=r"Ansible failed \(RC=2\):\nSTDOUT:\nSome output\nSTDERR:\n"):
            driver.execute(task)

def test_execute_ssh_auth_failure(driver, mock_profile):
    task = Task(type="config", profile=mock_profile, target="localhost")
    
    mock_result = MagicMock()
    mock_result.returncode = 255
    mock_result.stdout = ""
    mock_result.stderr = "Permission denied (publickey)."

    with patch("os.path.exists", return_value=True), \
         patch("subprocess.run", return_value=mock_result):
        
        with pytest.raises(ExecutionError, match=r"Ansible failed \(RC=255\):\nSTDOUT:\n\nSTDERR:\nPermission denied \(publickey\)\."):
            driver.execute(task)

def test_execute_timeout(driver, mock_profile):
    task = Task(type="config", profile=mock_profile, overrides={"timeout": 10})
    
    with patch("os.path.exists", return_value=True), \
         patch("subprocess.run", side_effect=subprocess.TimeoutExpired(cmd="ansible", timeout=10)):
        
        with pytest.raises(ExecutionError, match="Ansible execution timed out after 10s"):
            driver.execute(task)

def test_execute_ssh_key(driver, mock_profile):
    task = Task(
        type="config",
        profile=mock_profile,
        overrides={"ssh_key": "/path/to/key"}
    )
    
    mock_result = MagicMock(returncode=0, stdout="", stderr="")
    with patch("os.path.exists", return_value=True), \
         patch("subprocess.run", return_value=mock_result) as mock_run:
        driver.execute(task)
        cmd = mock_run.call_args[0][0]
        assert "--private-key" in cmd
        assert "/path/to/key" in cmd

def test_execute_build_type(driver, mock_profile):
    task = Task(type="build", profile=mock_profile)
    mock_result = MagicMock(returncode=0, stdout="", stderr="")
    with patch("os.path.exists", return_value=True), \
         patch("subprocess.run", return_value=mock_result) as mock_run:
        driver.execute(task)
        cmd = mock_run.call_args[0][0]
        assert "ansible/deploy.yml" in cmd

def test_execute_test_type(driver, mock_profile):
    task = Task(type="test", profile=mock_profile)
    mock_result = MagicMock(returncode=0, stdout="", stderr="")
    with patch("os.path.exists", return_value=True), \
         patch("subprocess.run", return_value=mock_result) as mock_run:
        driver.execute(task)
        cmd = mock_run.call_args[0][0]
        assert "ansible/site.yml" in cmd

def test_execute_inventory_file(driver, mock_profile):
    # If target is a file that exists, it shouldn't add a comma
    task = Task(type="config", profile=mock_profile, target="inventory.ini")
    mock_result = MagicMock(returncode=0, stdout="", stderr="")
    with patch("os.path.exists", side_effect=lambda x: True), \
         patch("subprocess.run", return_value=mock_result) as mock_run:
        driver.execute(task)
        cmd = mock_run.call_args[0][0]
        assert "inventory.ini" in cmd
        assert "inventory.ini," not in cmd

def test_execute_inventory_comma_already_present(driver, mock_profile):
    task = Task(type="config", profile=mock_profile, target="host1,host2")
    mock_result = MagicMock(returncode=0, stdout="", stderr="")
    with patch("os.path.exists", side_effect=lambda x: x == "ansible/site.yml"), \
         patch("subprocess.run", return_value=mock_result) as mock_run:
        driver.execute(task)
        cmd = mock_run.call_args[0][0]
        assert "host1,host2" in cmd
        assert "host1,host2," not in cmd

def test_execute_limit_and_tags(driver, mock_profile):
    task = Task(
        type="config",
        profile=mock_profile,
        overrides={
            "limit": "webservers",
            "tags": ["setup", "config"]
        }
    )
    
    mock_result = MagicMock(returncode=0, stdout="", stderr="")
    with patch("os.path.exists", return_value=True), \
         patch("subprocess.run", return_value=mock_result) as mock_run:
        driver.execute(task)
        cmd = mock_run.call_args[0][0]
        
        assert "--limit" in cmd
        assert "webservers" in cmd
        assert "--tags" in cmd
        assert "setup,config" in cmd
        
        # Verify they are NOT in extra_vars
        extra_vars_str = cmd[cmd.index("-e") + 1]
        extra_vars = json.loads(extra_vars_str)
        assert "limit" not in extra_vars
        assert "tags" not in extra_vars

def test_execute_tags_string(driver, mock_profile):
    task = Task(
        type="config",
        profile=mock_profile,
        overrides={
            "tags": "setup"
        }
    )
    
    mock_result = MagicMock(returncode=0, stdout="", stderr="")
    with patch("os.path.exists", return_value=True), \
         patch("subprocess.run", return_value=mock_result) as mock_run:
        driver.execute(task)
        cmd = mock_run.call_args[0][0]
        
        assert "--tags" in cmd
        assert "setup" in cmd


def test_execute_success_with_tags(driver, mock_profile):
    mock_profile.deployment["tags"] = ["test-tag"]
    task = Task(
        type="config",
        profile=mock_profile,
        target="1.2.3.4",
        overrides={"playbook": "site.yml"}
    )
    
    mock_result = MagicMock(returncode=0, stdout="Ansible output", stderr="")
    
    original_exists = os.path.exists
    def mock_exists(path):
        if path == "site.yml":
            return True
        if "tmp" in str(path) or str(path).endswith(".ini"):
            return True
        return original_exists(path)
        
    with patch("os.path.exists", side_effect=mock_exists), \
         patch("subprocess.run", return_value=mock_result) as mock_run:
         
        result = driver.execute(task)
        assert result.success is True
        
        args, kwargs = mock_run.call_args
        cmd = args[0]
        
        assert "-i" in cmd
        idx = cmd.index("-i")
        inv_path = cmd[idx + 1]
        assert inv_path.endswith(".ini")
        assert "1.2.3.4," not in cmd

