import pytest
from unittest.mock import patch, MagicMock, mock_open
from typer.testing import CliRunner

from homelab_gitops.domain.observability import ObservabilityService
from homelab_gitops.domain.models import NodeProfile, TaskResult
from homelab_gitops.cli.core_commands.monitor import app as monitor_app

runner = CliRunner()

def create_mock_profile(name="test-node"):
    return NodeProfile(
        name=name,
        vcenter={"datacenter": "dc1", "cluster": "cl1", "datastore": "ds1", "network": "net1"},
        vm_specs={"cpu": 2, "memory": 4096, "disk": 20},
        deployment={"tags": [], "roles": [], "playbooks": []}
    )

class TestObservabilityService:
    @patch('homelab_gitops.domain.observability.AnsibleDriver')
    def test_deploy_monitoring(self, mock_ansible_driver):
        mock_ansible_instance = mock_ansible_driver.return_value
        mock_ansible_instance.execute.return_value = TaskResult(success=True, task_type="config", output={}, duration=1.0)

        service = ObservabilityService()
        profile = create_mock_profile()
        
        result = service.deploy_monitoring(profile)

        assert result.success is True
        mock_ansible_instance.execute.assert_called_once()
        
        # Check the task passed to execute
        task = mock_ansible_instance.execute.call_args[0][0]
        assert task.type == "config"
        assert task.target == "test-node"
        assert task.overrides == {"tags": "alloy,docker_metrics"}

    def test_get_metrics(self):
        service = ObservabilityService()
        profile = create_mock_profile()
        
        result = service.get_metrics(profile)
        
        assert result["status"] == "ok"
        assert "metrics" in result

class TestMonitorCLI:
    @patch('homelab_gitops.cli.core_commands.monitor.os.path.exists')
    @patch('builtins.open', new_callable=mock_open, read_data="vcenter:\n  datacenter: dc1\n  cluster: cl1\n  datastore: ds1\n  network: net1\nvm_specs:\n  cpu: 2\n  memory: 4096\n  disk: 20\ndeployment:\n  tags: []\n  roles: []\n  playbooks: []\n")
    @patch('homelab_gitops.cli.core_commands.monitor.ObservabilityService')
    def test_monitor_setup_success(self, mock_obs_service, mock_file, mock_exists):
        mock_exists.return_value = True
        mock_instance = mock_obs_service.return_value
        mock_instance.deploy_monitoring.return_value = TaskResult(success=True, task_type="config", output={}, duration=1.0)

        result = runner.invoke(monitor_app, ["setup", "test-node"])
        
        assert result.exit_code == 0
        assert "Setting up monitoring for profile: test-node..." in result.stdout
        assert "Successfully deployed monitoring to test-node" in result.stdout
        
        mock_instance.deploy_monitoring.assert_called_once()
        profile_arg = mock_instance.deploy_monitoring.call_args[0][0]
        assert profile_arg.name == "test-node"

    @patch('homelab_gitops.cli.core_commands.monitor.os.path.exists')
    @patch('builtins.open', new_callable=mock_open, read_data="vcenter:\n  datacenter: dc1\n  cluster: cl1\n  datastore: ds1\n  network: net1\nvm_specs:\n  cpu: 2\n  memory: 4096\n  disk: 20\ndeployment:\n  tags: []\n  roles: []\n  playbooks: []\n")
    @patch('homelab_gitops.cli.core_commands.monitor.ObservabilityService')
    def test_monitor_setup_failure(self, mock_obs_service, mock_file, mock_exists):
        mock_exists.return_value = True
        mock_instance = mock_obs_service.return_value
        mock_instance.deploy_monitoring.return_value = TaskResult(success=False, task_type="config", output={}, duration=1.0, error="Ansible failed")

        result = runner.invoke(monitor_app, ["setup", "test-node"])
        
        assert result.exit_code == 1
        assert "Failed to deploy monitoring: Ansible failed" in result.stdout

    @patch('homelab_gitops.cli.core_commands.monitor.os.path.exists')
    @patch('builtins.open', new_callable=mock_open, read_data="vcenter:\n  datacenter: dc1\n  cluster: cl1\n  datastore: ds1\n  network: net1\nvm_specs:\n  cpu: 2\n  memory: 4096\n  disk: 20\ndeployment:\n  tags: []\n  roles: []\n  playbooks: []\n")
    @patch('homelab_gitops.cli.core_commands.monitor.ObservabilityService')
    def test_monitor_health_success(self, mock_obs_service, mock_file, mock_exists):
        mock_exists.return_value = True
        mock_instance = mock_obs_service.return_value
        mock_instance.get_metrics.return_value = {"status": "ok", "metrics": {"cpu": "50%"}}

        result = runner.invoke(monitor_app, ["health", "test-node"])
        
        assert result.exit_code == 0
        assert "Checking health for profile: test-node..." in result.stdout
        assert "Health check passed for test-node" in result.stdout
        assert "cpu" in result.stdout

    @patch('homelab_gitops.cli.core_commands.monitor.os.path.exists')
    def test_monitor_setup_profile_not_found(self, mock_exists):
        mock_exists.return_value = False

        result = runner.invoke(monitor_app, ["setup", "missing-node"])
        
        assert result.exit_code == 1
        assert "Setup failed: Profile not found" in result.stdout
