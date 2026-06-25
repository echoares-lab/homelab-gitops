from unittest.mock import patch, MagicMock
from homelab_gitops.drivers.packer_driver import PackerDriver
from homelab_gitops.domain.models import Task, NodeProfile

@patch("shutil.which", return_value="/usr/bin/packer")
@patch("os.path.exists", return_value=True)
@patch("subprocess.run")
def test_packer_driver_includes_overrides(mock_run, mock_exists, mock_which):
    """Test that overrides correctly form variable arguments."""
    mock_run.return_value = MagicMock(returncode=0, stdout="built")
    driver = PackerDriver()
    
    profile = NodeProfile(
        name="test-prof",
        vcenter={"datacenter": "D", "cluster": "C", "datastore": "S", "network": "N", "os_type": "fcos"},
        vm_specs={"cpu": 1, "memory": 1, "disk": 1},
        deployment={"tags": [], "roles": [], "playbooks": []}
    )
    
    task = Task(type="build", profile=profile, overrides={"host": "esxi-01.mgmt", "vm_cpu": 16})
    
    result = driver.execute(task)
    
    assert result.success is True
    cmd_args = mock_run.call_args[0][0]
    
    # Assert variables are passed correctly
    assert "-force" in cmd_args
    assert "-var" in cmd_args
    assert "name=test-prof" in cmd_args
    assert "host=esxi-01.mgmt" in cmd_args
    assert "vm_cpu=16" in cmd_args
    assert "packer/fcos.pkr.hcl" in cmd_args

@patch("shutil.which", return_value="/usr/bin/packer")
@patch("os.path.exists", return_value=True)
@patch("subprocess.run")
def test_packer_driver_defaults_to_ubuntu(mock_run, mock_exists, mock_which):
    """Test that it defaults to ubuntu template if missing or not specified."""
    mock_run.return_value = MagicMock(returncode=0, stdout="built")
    driver = PackerDriver()
    
    profile = NodeProfile(
        name="test-prof",
        vcenter={"datacenter": "D", "cluster": "C", "datastore": "S", "network": "N"},
        vm_specs={"cpu": 1, "memory": 1, "disk": 1},
        deployment={"tags": [], "roles": [], "playbooks": []}
    )
    
    task = Task(type="build", profile=profile, overrides={})
    
    # Mock exists returns false, so it falls back to ubuntu2404
    mock_exists.return_value = False
    
    result = driver.execute(task)
    
    assert result.success is True
    cmd_args = mock_run.call_args[0][0]
    
    assert "packer/ubuntu2404.pkr.hcl" in cmd_args
