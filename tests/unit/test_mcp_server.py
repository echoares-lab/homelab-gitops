import pytest
from unittest.mock import patch, MagicMock, mock_open

from homelab_gitops.mcp_server import mcp, get_fleet_status, issue_certificate, deploy_vm

def test_mcp_server_initialization():
    assert mcp.name == "Homelab-GitOps"
    assert callable(get_fleet_status)
    assert callable(issue_certificate)
    assert callable(deploy_vm)

@patch("homelab_gitops.mcp_server.os.path.exists")
@patch("homelab_gitops.mcp_server.os.listdir")
@patch("builtins.open", new_callable=mock_open, read_data="ip: 192.168.1.10\nmac: aa:bb:cc:dd:ee:ff")
@patch("homelab_gitops.mcp_server.yaml.safe_load")
@patch("homelab_gitops.mcp_server.StatusService")
def test_get_fleet_status_success(mock_status_service, mock_yaml_load, mock_file, mock_listdir, mock_exists):
    mock_exists.return_value = True
    mock_listdir.return_value = ["test_profile.yml"]
    mock_yaml_load.return_value = {
        "vcenter": {"datacenter": "dc", "cluster": "cl", "datastore": "ds", "network": "net"},
        "vm_specs": {"cpu": 2, "memory": 4096, "disk": 20},
        "deployment": {"tags": [], "roles": [], "playbooks": []}
    }
    
    mock_service_instance = MagicMock()
    mock_status_service.return_value = mock_service_instance
    mock_service_instance.get_fleet_status.return_value = [
        {
            "name": "test_profile",
            "provisioned": True,
            "power": "poweredOn",
            "ip": "192.168.1.10",
            "drift": False
        }
    ]
    
    result = get_fleet_status()
    
    assert "Profile: test_profile" in result
    assert "Provisioned: True" in result
    assert "Power: poweredOn" in result
    assert "IP: 192.168.1.10" in result
    assert "Drift: False" in result

@patch("homelab_gitops.mcp_server.os.path.exists")
def test_get_fleet_status_no_dir(mock_exists):
    mock_exists.return_value = False
    result = get_fleet_status()
    assert "Error: config/profiles directory not found." in result

@patch("homelab_gitops.mcp_server.os.path.exists")
def test_get_fleet_status_exception(mock_exists):
    mock_exists.side_effect = Exception("Test error")
    result = get_fleet_status()
    assert "Error getting fleet status: Test error" in result

@patch("homelab_gitops.mcp_server.CertificateService")
def test_issue_certificate_success(mock_cert_service):
    mock_service_instance = MagicMock()
    mock_cert_service.return_value = mock_service_instance
    mock_service_instance.issue_certificate.return_value = "CERT_PEM_DATA"
    
    result = issue_certificate("example.com", "admin@example.com")
    
    assert "Successfully issued certificate for example.com" in result
    assert "CERT_PEM_DATA" in result
    mock_service_instance.issue_certificate.assert_called_once_with("example.com", "admin@example.com")

@patch("homelab_gitops.mcp_server.CertificateService")
def test_issue_certificate_exception(mock_cert_service):
    mock_service_instance = MagicMock()
    mock_cert_service.return_value = mock_service_instance
    mock_service_instance.issue_certificate.side_effect = Exception("Cert error")
    
    result = issue_certificate("example.com", "admin@example.com")
    
    assert "Error issuing certificate: Cert error" in result

@patch("homelab_gitops.mcp_server.os.path.exists")
@patch("builtins.open", new_callable=mock_open, read_data="ip: 192.168.1.10\nmac: aa:bb:cc:dd:ee:ff")
@patch("homelab_gitops.mcp_server.yaml.safe_load")
@patch("homelab_gitops.mcp_server.Workflow")
def test_deploy_vm_success(mock_workflow, mock_yaml_load, mock_file, mock_exists):
    mock_exists.return_value = True
    mock_yaml_load.return_value = {
        "vcenter": {"datacenter": "dc", "cluster": "cl", "datastore": "ds", "network": "net"},
        "vm_specs": {"cpu": 2, "memory": 4096, "disk": 20},
        "deployment": {"tags": [], "roles": [], "playbooks": []}
    }
    
    mock_workflow_instance = MagicMock()
    mock_workflow.return_value = mock_workflow_instance
    mock_state = MagicMock()
    mock_state.vm_ip = "192.168.1.10"
    mock_workflow_instance.execute.return_value = mock_state
    
    result = deploy_vm("test_profile")
    
    assert "Successfully deployed and configured test_profile" in result
    assert "IP: 192.168.1.10" in result
    mock_workflow_instance.execute.assert_called_once_with(["deploy", "config"])

@patch("homelab_gitops.mcp_server.os.path.exists")
def test_deploy_vm_not_found(mock_exists):
    mock_exists.return_value = False
    result = deploy_vm("missing_profile")
    assert "Error: Profile not found" in result

@patch("homelab_gitops.mcp_server.os.path.exists")
def test_deploy_vm_exception(mock_exists):
    mock_exists.side_effect = Exception("Deploy error")
    result = deploy_vm("test_profile")
    assert "Error deploying VM: Deploy error" in result
