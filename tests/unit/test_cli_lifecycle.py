"""Unit tests for CLI core lifecycle commands."""

import pytest
from typer.testing import CliRunner
from unittest.mock import MagicMock, patch
from homelab_gitops.cli.app import create_app

runner = CliRunner()

@pytest.fixture
def app():
    return create_app()

@pytest.fixture
def mock_workflow():
    with patch("homelab_gitops.cli.core_commands.deploy.Workflow") as mock_w:
        instance = mock_w.return_value
        instance.execute.return_value = MagicMock(vm_ip="1.2.3.4")
        yield instance

@patch("os.path.exists", return_value=True)
@patch("builtins.open", new_callable=MagicMock)
@patch("yaml.safe_load", return_value={
    "vcenter": {"datacenter": "D", "cluster": "C", "datastore": "S", "network": "N"},
    "vm_specs": {"cpu": 1, "memory": 1, "disk": 1, "guest_id": "G"},
    "deployment": {"tags": [], "roles": [], "playbooks": []}
})
@patch("homelab_gitops.cli.core_commands.build.Workflow")
@patch("homelab_gitops.cli.core_commands.build.PackerDriver")
def test_cli_build(mock_packer, mock_workflow, mock_yaml, mock_open, mock_exists, app):
    """Test build command."""
    mock_workflow.return_value.execute.return_value = MagicMock(state="built")
    result = runner.invoke(app, ["build", "test-profile"])
    assert result.exit_code == 0
    assert "Building test-profile" in result.stdout

@patch("os.path.exists", return_value=True)
@patch("builtins.open", new_callable=MagicMock)
@patch("yaml.safe_load", return_value={
    "vcenter": {"datacenter": "D", "cluster": "C", "datastore": "S", "network": "N"},
    "vm_specs": {"cpu": 1, "memory": 1, "disk": 1, "guest_id": "G"},
    "deployment": {"tags": [], "roles": [], "playbooks": []}
})
@patch("homelab_gitops.cli.core_commands.deploy.Workflow")
@patch("homelab_gitops.cli.core_commands.deploy.TofuDriver")
def test_cli_deploy(mock_tofu, mock_workflow, mock_yaml, mock_open, mock_exists, app):
    """Test deploy command."""
    mock_workflow.return_value.execute.return_value = MagicMock(vm_ip="1.2.3.4")
    result = runner.invoke(app, ["deploy", "photon-docker", "01"])
    assert result.exit_code == 0
    assert "Workflow completed for photon-docker at 1.2.3.4" in result.stdout

@patch("os.path.exists", return_value=True)
@patch("builtins.open", new_callable=MagicMock)
@patch("yaml.safe_load", return_value={
    "vcenter": {"datacenter": "D", "cluster": "C", "datastore": "S", "network": "N"},
    "vm_specs": {"cpu": 1, "memory": 1, "disk": 1, "guest_id": "G"},
    "deployment": {"tags": [], "roles": [], "playbooks": []}
})
@patch("homelab_gitops.cli.core_commands.destroy.Workflow")
@patch("homelab_gitops.cli.core_commands.destroy.TofuDriver")
def test_cli_destroy(mock_tofu, mock_workflow, mock_yaml, mock_open, mock_exists, app):
    """Test destroy command."""
    mock_workflow.return_value.execute.return_value = MagicMock(state="destroyed")
    result = runner.invoke(app, ["destroy", "test-profile"])
    assert result.exit_code == 0
    assert "Destroyed test-profile" in result.stdout

@patch("homelab_gitops.cli.core_commands.status.StatusService")
@patch("homelab_gitops.cli.core_commands.status.NodeProfile")
@patch("os.listdir", return_value=["p1.yml"])
@patch("os.path.exists", return_value=True)
@patch("builtins.open", new_callable=MagicMock)
@patch("yaml.safe_load", return_value={
    "vcenter": {"datacenter": "D", "cluster": "C", "datastore": "S", "network": "N"},
    "vm_specs": {"cpu": 1, "memory": 1, "disk": 1, "guest_id": "G"},
    "deployment": {"tags": [], "roles": [], "playbooks": []}
})
def test_cli_status(mock_yaml, mock_open, mock_exists, mock_listdir, mock_profile, mock_status_service, app):
    """Test status command."""
    mock_status_service.return_value.get_fleet_status.return_value = [
        {"name": "test-vm", "provisioned": "Yes", "power": "On", "ip": "1.2.3.4", "drift": "No"}
    ]
    result = runner.invoke(app, ["status"])
    assert result.exit_code == 0
    assert "test-vm" in result.stdout
    assert "1.2.3.4" in result.stdout

@patch("os.path.exists", return_value=True)
@patch("builtins.open", new_callable=MagicMock)
@patch("yaml.safe_load", return_value={
    "vcenter": {"datacenter": "D", "cluster": "C", "datastore": "S", "network": "N"},
    "vm_specs": {"cpu": 1, "memory": 1, "disk": 1, "guest_id": "G"},
    "deployment": {"tags": [], "roles": [], "playbooks": []}
})
@patch("homelab_gitops.cli.core_commands.test.Workflow")
@patch("homelab_gitops.cli.core_commands.test.AnsibleDriver")
def test_cli_test(mock_ansible, mock_workflow, mock_yaml, mock_open, mock_exists, app):
    """Test test command."""
    mock_workflow.return_value.execute.return_value = MagicMock(state="tested")
    result = runner.invoke(app, ["test", "test-profile"])
    assert result.exit_code == 0
    assert "Tests passed for test-profile" in result.stdout
