"""Extended unit tests for CLI core commands."""

import pytest
from typer.testing import CliRunner
from unittest.mock import MagicMock, patch
from homelab_gitops.cli.app import create_app
from homelab_gitops.domain.models import TaskResult, NodeProfile

runner = CliRunner()

@pytest.fixture
def app():
    return create_app()

@pytest.fixture
def valid_profile():
    return NodeProfile(
        name="cli",
        vcenter={"datacenter": "D", "cluster": "C", "datastore": "S", "network": "N"},
        vm_specs={"cpu": 1, "memory": 1, "disk": 1},
        deployment={"tags": [], "roles": [], "playbooks": []}
    )

# --- DNS Command Tests ---

@patch("homelab_gitops.cli.core_commands.dns.DNSService")
def test_dns_list(mock_service_class, app):
    """Test dns list command."""
    mock_service = mock_service_class.return_value
    mock_service.list_records.return_value = [
        {"name": "test", "type": "A", "value": "1.2.3.4", "ttl": 3600}
    ]
    
    result = runner.invoke(app, ["dns", "list", "example.com"])
    assert result.exit_code == 0
    assert "test" in result.stdout
    assert "1.2.3.4" in result.stdout
    mock_service.list_records.assert_called_once_with("example.com")

@patch("homelab_gitops.cli.core_commands.dns.DNSService")
def test_dns_list_empty(mock_service_class, app):
    """Test dns list command with no records."""
    mock_service = mock_service_class.return_value
    mock_service.list_records.return_value = []
    
    result = runner.invoke(app, ["dns", "list", "example.com"])
    assert result.exit_code == 0
    assert "No records found in zone example.com" in result.stdout

@patch("homelab_gitops.cli.core_commands.dns.DNSService")
def test_dns_create(mock_service_class, app):
    """Test dns create command."""
    mock_service = mock_service_class.return_value
    mock_service.provision_manual.return_value = [
        TaskResult(task_type="dns_a", success=True, duration=0.5, output={})
    ]
    
    result = runner.invoke(app, ["dns", "create", "host1", "1.2.3.4", "--zone", "example.com"])
    assert result.exit_code == 0
    assert "Creating DNS records for host1.example.com -> 1.2.3.4" in result.stdout
    assert "SUCCESS" in result.stdout
    mock_service.provision_manual.assert_called_once_with("host1", "1.2.3.4", "example.com")

@patch("homelab_gitops.cli.core_commands.dns.DNSService")
def test_dns_create_prompt(mock_service_class, app):
    """Test dns create command with zone prompt."""
    mock_service = mock_service_class.return_value
    mock_service.provision_manual.return_value = [
        TaskResult(task_type="dns_a", success=True, duration=0.5, output={})
    ]
    
    # Input "example.com" for the prompt
    result = runner.invoke(app, ["dns", "create", "host1", "1.2.3.4"], input="example.com\n")
    assert result.exit_code == 0
    assert "DNS Zone" in result.stdout
    assert "Creating DNS records for host1.example.com -> 1.2.3.4" in result.stdout
    mock_service.provision_manual.assert_called_once_with("host1", "1.2.3.4", "example.com")

@patch("homelab_gitops.cli.core_commands.dns.DNSService")
def test_dns_create_failure(mock_service_class, app):
    """Test dns create command failure."""
    mock_service = mock_service_class.return_value
    mock_service.provision_manual.side_effect = Exception("API Error")
    
    result = runner.invoke(app, ["dns", "create", "host1", "1.2.3.4", "--zone", "example.com"])
    assert result.exit_code == 0
    assert "Error: API Error" in result.stdout

@patch("homelab_gitops.cli.core_commands.dns.DNSService")
def test_dns_delete(mock_service_class, app):
    """Test dns delete command."""
    mock_service = mock_service_class.return_value
    mock_service.deprovision_manual.return_value = [
        TaskResult(task_type="dns_delete", success=True, duration=0.3, output={})
    ]
    
    result = runner.invoke(app, ["dns", "delete", "host1", "--zone", "example.com"])
    assert result.exit_code == 0
    assert "Deleting DNS records for host1.example.com" in result.stdout
    assert "SUCCESS" in result.stdout
    mock_service.deprovision_manual.assert_called_once_with("host1", None, "example.com")

@patch("homelab_gitops.cli.core_commands.dns.DNSService")
def test_dns_delete_prompt(mock_service_class, app):
    """Test dns delete command with zone prompt."""
    mock_service = mock_service_class.return_value
    mock_service.deprovision_manual.return_value = [
        TaskResult(task_type="dns_delete", success=True, duration=0.3, output={})
    ]
    
    # Input "example.com" for the prompt
    result = runner.invoke(app, ["dns", "delete", "host1"], input="example.com\n")
    assert result.exit_code == 0
    assert "DNS Zone" in result.stdout
    assert "Deleting DNS records for host1.example.com" in result.stdout
    mock_service.deprovision_manual.assert_called_once_with("host1", None, "example.com")

# --- Migrate Command Tests ---

@patch("homelab_gitops.cli.core_commands.migrate.MigrationService")
def test_migrate_dhcp(mock_service_class, app):
    """Test dhcp-migrate command."""
    mock_service = mock_service_class.return_value
    mock_service.discover.return_value = {
        "opnsense_interfaces": [{"interface": "lan"}],
        "technitium_scopes": [{"name": "lan-scope"}]
    }
    mock_service.migrate_dhcp.return_value = {"status": "completed"}
    
    # Mock user input: source=lan, target=lan-scope, confirm=y
    result = runner.invoke(app, ["migrate", "dhcp-migrate"], input="lan\nlan-scope\ny\n")
    
    assert result.exit_code == 0
    assert "Step 1 — Discovery" in result.stdout
    assert "OPNsense DHCP" in result.stdout
    assert "Technitium" in result.stdout
    assert "Migration successful: completed" in result.stdout
    mock_service.migrate_dhcp.assert_called_once_with("lan", "lan-scope")

@patch("homelab_gitops.cli.core_commands.migrate.MigrationService")
def test_migrate_dhcp_failure(mock_service_class, app):
    """Test dhcp-migrate command failure."""
    mock_service = mock_service_class.return_value
    mock_service.discover.return_value = {
        "opnsense_interfaces": [{"interface": "lan"}],
        "technitium_scopes": [{"name": "lan-scope"}]
    }
    mock_service.migrate_dhcp.side_effect = Exception("Migration Error")
    
    result = runner.invoke(app, ["migrate", "dhcp-migrate"], input="lan\nlan-scope\ny\n")
    
    assert result.exit_code == 0
    assert "Migration failed: Migration Error" in result.stdout

@patch("homelab_gitops.cli.core_commands.migrate.MigrationService")
def test_migrate_rollback(mock_service_class, app):
    """Test dhcp-rollback command."""
    mock_service = mock_service_class.return_value
    mock_service.rollback.return_value = {"status": "rolled back"}
    
    result = runner.invoke(app, ["migrate", "dhcp-rollback"], input="y\n")
    
    assert result.exit_code == 0
    assert "Rollback complete: rolled back" in result.stdout
    mock_service.rollback.assert_called_once()

# --- OPNsense Command Tests ---

@patch("homelab_gitops.cli.core_commands.opnsense.NodeProfile")
@patch("homelab_gitops.cli.core_commands.opnsense.NetworkingService")
def test_opnsense_list_rules(mock_service_class, mock_profile_class, valid_profile, app):
    """Test opnsense list-rules command."""
    mock_profile_class.return_value = valid_profile
    mock_service = mock_service_class.return_value
    mock_driver = MagicMock()
    mock_service.driver = mock_driver
    
    mock_driver.execute.return_value = MagicMock(output={
        "rules": [
            {"description": "Allow All", "action": "pass", "protocol": "any", "src_net": "any", "dst_net": "any"}
        ]
    })
    
    result = runner.invoke(app, ["opnsense", "list-rules"])
    assert result.exit_code == 0
    assert "OPNsense Firewall Rules" in result.stdout
    assert "Allow All" in result.stdout
    assert "pass" in result.stdout

@patch("homelab_gitops.cli.core_commands.opnsense.NodeProfile")
@patch("homelab_gitops.cli.core_commands.opnsense.NetworkingService")
def test_opnsense_list_rules_empty(mock_service_class, mock_profile_class, valid_profile, app):
    """Test opnsense list-rules command with no rules."""
    mock_profile_class.return_value = valid_profile
    mock_service = mock_service_class.return_value
    mock_driver = MagicMock()
    mock_service.driver = mock_driver
    mock_driver.execute.return_value = MagicMock(output={"rules": []})
    
    result = runner.invoke(app, ["opnsense", "list-rules"])
    assert result.exit_code == 0
    assert "No firewall rules found." in result.stdout

@patch("homelab_gitops.cli.core_commands.opnsense.NodeProfile")
@patch("homelab_gitops.cli.core_commands.opnsense.NetworkingService")
def test_opnsense_list_rules_failure(mock_service_class, mock_profile_class, valid_profile, app):
    """Test opnsense list-rules command failure."""
    mock_profile_class.return_value = valid_profile
    mock_service = mock_service_class.return_value
    mock_service.driver.execute.side_effect = Exception("Driver Error")
    
    result = runner.invoke(app, ["opnsense", "list-rules"])
    assert result.exit_code == 1
    assert "Failed to list rules: Driver Error" in result.stdout

@patch("homelab_gitops.cli.core_commands.opnsense.NodeProfile")
@patch("homelab_gitops.cli.core_commands.opnsense.NetworkingService")
def test_opnsense_list_vlans(mock_service_class, mock_profile_class, valid_profile, app):
    """Test opnsense list-vlans command."""
    mock_profile_class.return_value = valid_profile
    mock_service = mock_service_class.return_value
    mock_driver = MagicMock()
    mock_service.driver = mock_driver
    
    mock_driver.execute.return_value = MagicMock(output={
        "vlans": [
            {"tag": 10, "if": "vlan0.10", "descr": "Management"}
        ]
    })
    
    result = runner.invoke(app, ["opnsense", "list-vlans"])
    assert result.exit_code == 0
    assert "OPNsense VLANs" in result.stdout
    assert "10" in result.stdout
    assert "Management" in result.stdout

@patch("homelab_gitops.cli.core_commands.opnsense.NodeProfile")
@patch("homelab_gitops.cli.core_commands.opnsense.NetworkingService")
def test_opnsense_list_vlans_failure(mock_service_class, mock_profile_class, valid_profile, app):
    """Test opnsense list-vlans command failure."""
    mock_profile_class.return_value = valid_profile
    mock_service = mock_service_class.return_value
    mock_service.driver.execute.side_effect = Exception("Driver Error")
    
    result = runner.invoke(app, ["opnsense", "list-vlans"])
    assert result.exit_code == 1
    assert "Failed to list VLANs: Driver Error" in result.stdout

# --- Cert Command Tests ---

@patch("homelab_gitops.cli.core_commands.cert.CertificateService")
@patch("homelab_gitops.cli.core_commands.cert.AcmeDriver")
@patch("homelab_gitops.cli.core_commands.cert.TechnitiumDriver")
@patch("homelab_gitops.cli.core_commands.cert.SecretsDriver")
def test_cert_issue(mock_secrets, mock_dns, mock_acme, mock_service_class, app):
    """Test cert issue command."""
    mock_service = mock_service_class.return_value
    
    result = runner.invoke(app, ["cert", "issue", "--domain", "example.com", "--email", "admin@example.com"])
    assert result.exit_code == 0
    assert "Starting certificate issuance for example.com..." in result.stdout
    assert "Success! Certificate for example.com has been issued" in result.stdout
    mock_service.issue_certificate.assert_called_once_with("example.com", "admin@example.com")

@patch("homelab_gitops.cli.core_commands.cert.CertificateService")
@patch("homelab_gitops.cli.core_commands.cert.AcmeDriver")
@patch("homelab_gitops.cli.core_commands.cert.TechnitiumDriver")
@patch("homelab_gitops.cli.core_commands.cert.SecretsDriver")
def test_cert_issue_failure(mock_secrets, mock_dns, mock_acme, mock_service_class, app):
    """Test cert issue command failure."""
    mock_service = mock_service_class.return_value
    mock_service.issue_certificate.side_effect = Exception("ACME Error")
    
    result = runner.invoke(app, ["cert", "issue", "--domain", "example.com", "--email", "admin@example.com"])
    assert result.exit_code == 1
    assert "Error: ACME Error" in result.stdout

def test_cert_status(app):
    """Test cert status command."""
    result = runner.invoke(app, ["cert", "status"])
    assert result.exit_code == 0
    assert "Certificate status command is not yet fully implemented." in result.stdout
