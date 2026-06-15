"""Unit tests for OpnsenseDriver."""

import pytest
import requests
from unittest.mock import MagicMock, patch
from homelab_gitops.drivers.opnsense_driver import OPNsenseDriver
from homelab_gitops.drivers.exceptions import PrerequisiteError, ExecutionError
from homelab_gitops.domain.models import Task, NodeProfile

@pytest.fixture
def node_profile():
    return NodeProfile(
        name="test-node",
        vcenter={
            "datacenter": "dc",
            "cluster": "cl",
            "datastore": "ds",
            "network": "nw"
        },
        vm_specs={
            "cpu": 2,
            "memory": 4096,
            "disk": 40
        },
        deployment={
            "tags": ["test"],
            "roles": ["base"],
            "playbooks": ["site.yml"]
        }
    )

@pytest.fixture
def opnsense_driver():
    with patch.dict("os.environ", {
        "OPNSENSE_URL": "https://fw.local",
        "OPNSENSE_KEY": "key",
        "OPNSENSE_SECRET": "secret"
    }):
        return OPNsenseDriver()

def test_opnsense_driver_init():
    with patch.dict("os.environ", {"OPNSENSE_URL": "http://fw"}):
        driver = OPNsenseDriver()
        assert driver.url == "http://fw"

def test_opnsense_driver_validate_success(opnsense_driver):
    with patch("requests.get") as mock_get:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response
        assert opnsense_driver.validate() is True

def test_opnsense_driver_validate_failure(opnsense_driver):
    with patch("requests.get") as mock_get:
        mock_get.side_effect = requests.exceptions.ConnectionError("API Down")
        with pytest.raises(PrerequisiteError):
            opnsense_driver.validate()

def test_opnsense_driver_execute_list_vlans(opnsense_driver, node_profile):
    with patch("requests.get") as mock_get:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"rows": [{"tag": "10", "descr": "IOT"}]}
        mock_get.return_value = mock_response
        
        task = Task(
            type="provision",
            profile=node_profile,
            overrides={"resource": "vlan", "action": "list"}
        )
        result = opnsense_driver.execute(task)
        assert result.success is True
        assert len(result.output["vlans"]) == 1

def test_opnsense_driver_handle_dhcp(opnsense_driver, node_profile):
    with patch("requests.get") as mock_get:
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = {"rows": []}
        
        task = Task(
            type="provision",
            profile=node_profile,
            overrides={"resource": "dhcp", "action": "list_enabled", "interface": "lan"}
        )
        result = opnsense_driver.execute(task)
        assert result.success is True

def test_opnsense_driver_handle_firewall(opnsense_driver, node_profile):
    with patch("requests.get") as mock_get:
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = {"rows": []}
        
        task = Task(
            type="provision",
            profile=node_profile,
            overrides={"resource": "firewall", "action": "list"}
        )
        result = opnsense_driver.execute(task)
        assert result.success is True

def test_opnsense_driver_validation_helpers(opnsense_driver):
    opnsense_driver._validate_rule_name("ValidName")
    with pytest.raises(ExecutionError):
        opnsense_driver._validate_rule_name("")
        
    opnsense_driver._validate_cidr("192.168.1.0/24", "src")
    with pytest.raises(ExecutionError):
        opnsense_driver._validate_cidr("invalid", "src")
        
    opnsense_driver._validate_protocol("tcp")
    with pytest.raises(ExecutionError):
        opnsense_driver._validate_protocol("invalid")
        
    opnsense_driver._validate_port(80)
    with pytest.raises(ExecutionError):
        opnsense_driver._validate_port(70000)

def test_opnsense_driver_handle_interface(opnsense_driver, node_profile):
    with patch("requests.get") as mock_get:
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = {"rows": []}
        
        task = Task(
            type="provision",
            profile=node_profile,
            overrides={"resource": "interface", "action": "list"}
        )
        result = opnsense_driver.execute(task)
        assert result.success is True

def test_opnsense_driver_execute_unsupported(opnsense_driver, node_profile):
    task = Task(
        type="provision",
        profile=node_profile,
        overrides={"resource": "invalid"}
    )
    with pytest.raises(ExecutionError):
        opnsense_driver.execute(task)

def test_opnsense_driver_handle_vlan_create(opnsense_driver, node_profile):
    with patch("requests.post") as mock_post:
        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = {"status": "saved"}
        
        task = Task(
            type="provision",
            profile=node_profile,
            overrides={
                "resource": "vlan",
                "action": "create",
                "interface": "em0",
                "vlan_id": 100,
                "description": "Test VLAN"
            }
        )
        result = opnsense_driver.execute(task)
        assert result.success is True
        assert result.output["status"] == "saved"

def test_opnsense_driver_handle_vlan_create_invalid(opnsense_driver, node_profile):
    # Missing interface
    task = Task(
        type="provision",
        profile=node_profile,
        overrides={"resource": "vlan", "action": "create", "vlan_id": 100, "description": "X"}
    )
    with pytest.raises(ExecutionError, match="Interface required"):
        opnsense_driver.execute(task)
        
    # Invalid VLAN ID
    task = Task(
        type="provision",
        profile=node_profile,
        overrides={"resource": "vlan", "action": "create", "interface": "em0", "vlan_id": 5000, "description": "X"}
    )
    with pytest.raises(ExecutionError, match="Invalid VLAN ID"):
        opnsense_driver.execute(task)

def test_opnsense_driver_handle_vlan_delete(opnsense_driver, node_profile):
    with patch("requests.post") as mock_post:
        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = {"status": "deleted"}
        
        task = Task(
            type="provision",
            profile=node_profile,
            overrides={"resource": "vlan", "action": "delete", "uuid": "some-uuid"}
        )
        result = opnsense_driver.execute(task)
        assert result.success is True

def test_opnsense_driver_handle_firewall_create(opnsense_driver, node_profile):
    with patch("requests.post") as mock_post:
        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = {"status": "saved"}
        
        task = Task(
            type="provision",
            profile=node_profile,
            overrides={
                "resource": "firewall",
                "action": "create",
                "name": "AllowHTTP",
                "src_net": "192.168.1.0/24",
                "dst_net": "any",
                "protocol": "tcp",
                "port": 80
            }
        )
        result = opnsense_driver.execute(task)
        assert result.success is True

def test_opnsense_driver_handle_firewall_delete(opnsense_driver, node_profile):
    with patch("requests.post") as mock_post:
        mock_post.return_value.status_code = 200
        
        task = Task(
            type="provision",
            profile=node_profile,
            overrides={"resource": "firewall", "action": "delete", "uuid": "rule-uuid"}
        )
        result = opnsense_driver.execute(task)
        assert result.success is True

def test_opnsense_driver_handle_interface_ops(opnsense_driver, node_profile):
    with patch("requests.get") as mock_get, patch("requests.post") as mock_post:
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = {"interface": {"descr": "WAN"}}
        mock_post.return_value.status_code = 200
        
        # Get
        task = Task(
            type="provision",
            profile=node_profile,
            overrides={"resource": "interface", "action": "get", "name": "wan"}
        )
        result = opnsense_driver.execute(task)
        assert result.success is True
        
        # Configure
        task = Task(
            type="provision",
            profile=node_profile,
            overrides={"resource": "interface", "action": "configure", "name": "wan", "enable": "1"}
        )
        result = opnsense_driver.execute(task)
        assert result.success is True

def test_opnsense_driver_handle_dhcp_ops(opnsense_driver, node_profile):
    with patch("requests.get") as mock_get, patch("requests.post") as mock_post:
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = {
            "dnsmasq": {"dhcp": {"no_interface": {"lan": {"selected": 0}}}}
        }
        mock_post.return_value.status_code = 200
        
        # Disable
        task = Task(
            type="provision",
            profile=node_profile,
            overrides={"resource": "dhcp", "action": "disable", "interface": "lan"}
        )
        result = opnsense_driver.execute(task)
        assert result.success is True
        
        # Enable
        task = Task(
            type="provision",
            profile=node_profile,
            overrides={"resource": "dhcp", "action": "enable", "interface": "lan"}
        )
        result = opnsense_driver.execute(task)
        assert result.success is True

def test_opnsense_driver_handle_backup(opnsense_driver, node_profile):
    with patch("requests.get") as mock_get:
        mock_get.return_value.status_code = 200
        mock_get.return_value.text = "<xml>config</xml>"
        
        task = Task(
            type="provision",
            profile=node_profile,
            overrides={"resource": "backup", "action": "export"}
        )
        result = opnsense_driver.execute(task)
        assert result.success is True
        assert result.output["content"] == "<xml>config</xml>"

def test_opnsense_driver_api_error(opnsense_driver):
    with patch("requests.get") as mock_get:
        mock_get.return_value.status_code = 500
        mock_get.return_value.text = "Internal Server Error"
        
        with pytest.raises(ExecutionError, match=r"API Error \(500\)"):
            opnsense_driver._get("/some/endpoint")

def test_opnsense_driver_validate_missing_env():
    with patch.dict("os.environ", {}, clear=True):
        driver = OPNsenseDriver()
        with pytest.raises(PrerequisiteError, match="OPNSENSE_URL, OPNSENSE_KEY, and OPNSENSE_SECRET must be set"):
            driver.validate()

def test_opnsense_driver_handle_dhcp_list_with_ranges(opnsense_driver, node_profile):
    with patch("requests.get") as mock_get:
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = {
            "dnsmasq": {
                "dhcp": {"no_interface": {"wan": {"selected": 1}}},
                "dhcp_ranges": {
                    "uuid1": {
                        "interface": {"lan": {"selected": 1}},
                        "start_addr": "192.168.1.100",
                        "end_addr": "192.168.1.200"
                    }
                }
            }
        }
        
        task = Task(
            type="provision",
            profile=node_profile,
            overrides={"resource": "dhcp", "action": "list_enabled"}
        )
        result = opnsense_driver.execute(task)
        assert len(result.output["interfaces"]) == 1
        assert result.output["interfaces"][0]["interface"] == "lan"

def test_opnsense_driver_handle_dhcp_missing_interface(opnsense_driver, node_profile):
    task = Task(
        type="provision",
        profile=node_profile,
        overrides={"resource": "dhcp", "action": "enable"}
    )
    with pytest.raises(ExecutionError, match="Interface required"):
        opnsense_driver.execute(task)

def test_opnsense_driver_handle_dhcp_unsupported(opnsense_driver, node_profile):
    task = Task(
        type="provision",
        profile=node_profile,
        overrides={"resource": "dhcp", "action": "invalid"}
    )
    with pytest.raises(ExecutionError, match="Unsupported DHCP action"):
        opnsense_driver.execute(task)

def test_opnsense_driver_handle_backup_unsupported(opnsense_driver, node_profile):
    task = Task(
        type="provision",
        profile=node_profile,
        overrides={"resource": "backup", "action": "invalid"}
    )
    with pytest.raises(ExecutionError, match="Unsupported backup action"):
        opnsense_driver.execute(task)

def test_opnsense_driver_handle_interface_missing_name(opnsense_driver, node_profile):
    # Get
    task = Task(
        type="provision",
        profile=node_profile,
        overrides={"resource": "interface", "action": "get"}
    )
    with pytest.raises(ExecutionError, match="Interface name required"):
        opnsense_driver.execute(task)
    
    # Configure
    task = Task(
        type="provision",
        profile=node_profile,
        overrides={"resource": "interface", "action": "configure"}
    )
    with pytest.raises(ExecutionError, match="Interface name required"):
        opnsense_driver.execute(task)

def test_opnsense_driver_handle_interface_unsupported(opnsense_driver, node_profile):
    task = Task(
        type="provision",
        profile=node_profile,
        overrides={"resource": "interface", "action": "invalid"}
    )
    with pytest.raises(ExecutionError, match="Unsupported interface action"):
        opnsense_driver.execute(task)

def test_opnsense_driver_handle_vlan_unsupported(opnsense_driver, node_profile):
    task = Task(
        type="provision",
        profile=node_profile,
        overrides={"resource": "vlan", "action": "invalid"}
    )
    with pytest.raises(ExecutionError, match="Unsupported VLAN action"):
        opnsense_driver.execute(task)

def test_opnsense_driver_handle_firewall_delete_missing_uuid(opnsense_driver, node_profile):
    task = Task(
        type="provision",
        profile=node_profile,
        overrides={"resource": "firewall", "action": "delete"}
    )
    with pytest.raises(ExecutionError, match="Firewall rule UUID required"):
        opnsense_driver.execute(task)

def test_opnsense_driver_handle_firewall_unsupported(opnsense_driver, node_profile):
    task = Task(
        type="provision",
        profile=node_profile,
        overrides={"resource": "firewall", "action": "invalid"}
    )
    with pytest.raises(ExecutionError, match="Unsupported firewall action"):
        opnsense_driver.execute(task)

def test_opnsense_driver_validate_port_fail(opnsense_driver):
    with pytest.raises(ExecutionError, match="Invalid port"):
        opnsense_driver._validate_port(0)
    with pytest.raises(ExecutionError, match="Invalid port"):
        opnsense_driver._validate_port(65536)

def test_opnsense_driver_validate_cidr_special(opnsense_driver):
    opnsense_driver._validate_cidr("any", "src")
    opnsense_driver._validate_cidr("lan", "src")
    opnsense_driver._validate_cidr("wan", "src")
    with pytest.raises(ExecutionError, match="Invalid CIDR"):
        opnsense_driver._validate_cidr("invalid", "src")

def test_opnsense_driver_handle_response_error(opnsense_driver):
    mock_response = MagicMock()
    mock_response.status_code = 400
    mock_response.text = "Bad Request"
    with pytest.raises(ExecutionError, match=r"API Error \(400\)"):
        opnsense_driver._handle_response(mock_response)

def test_opnsense_driver_validate_credentials_fail(opnsense_driver):
    with patch("requests.get") as mock_get:
        mock_get.return_value.status_code = 401
        with pytest.raises(PrerequisiteError, match="Invalid OPNsense API credentials"):
            opnsense_driver.validate()
        
        mock_get.return_value.status_code = 500
        with pytest.raises(PrerequisiteError, match="OPNsense connection failed with status: 500"):
            opnsense_driver.validate()

def test_opnsense_driver_handle_firewall_create_with_action(opnsense_driver, node_profile):
    with patch("requests.post") as mock_post:
        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = {"status": "saved"}
        
        task = Task(
            type="provision",
            profile=node_profile,
            overrides={
                "resource": "firewall",
                "action": "create",
                "name": "BlockSSH",
                "src_net": "any",
                "dst_net": "lan",
                "protocol": "tcp",
                "rule_action": "block",
                "port": 22
            }
        )
        result = opnsense_driver.execute(task)
        assert result.success is True
