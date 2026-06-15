import pytest
from unittest.mock import MagicMock, patch
import requests
from homelab_gitops.drivers.technitium_driver import TechnitiumDriver
from homelab_gitops.drivers.exceptions import PrerequisiteError, ExecutionError
from homelab_gitops.domain.models import Task, NodeProfile

@pytest.fixture
def driver():
    return TechnitiumDriver(host="http://dns.local", token="fake-token")

@pytest.fixture
def mock_profile():
    return NodeProfile(
        name="test-node",
        vcenter={"datacenter": "dc1", "cluster": "cl1", "datastore": "ds1", "network": "net1"},
        vm_specs={"cpu": 2, "memory": 4096, "disk": 20},
        deployment={"tags": ["test"], "roles": ["base"], "playbooks": ["site.yml"]}
    )

def test_validate_success(driver):
    with patch("requests.get") as mock_get:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"status": "ok"}
        mock_get.return_value = mock_response
        
        assert driver.validate() is True
        mock_get.assert_called_once_with(
            "http://dns.local/api/dns/listZones",
            params={"token": "fake-token"},
            timeout=10
        )

def test_validate_no_host_or_token():
    d = TechnitiumDriver(host="", token="")
    with pytest.raises(PrerequisiteError, match="TECHNITIUM_HOST and TECHNITIUM_TOKEN must be set"):
        d.validate()

def test_validate_unauthorized(driver):
    with patch("requests.get") as mock_get:
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_get.return_value = mock_response
        
        with pytest.raises(PrerequisiteError, match="Invalid Technitium API token"):
            driver.validate()

def test_validate_api_error(driver):
    with patch("requests.get") as mock_get:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"status": "error", "errorMessage": "Some error"}
        mock_get.return_value = mock_response
        
        with pytest.raises(PrerequisiteError, match="Technitium API error: Some error"):
            driver.validate()

def test_validate_unreachable(driver):
    with patch("requests.get") as mock_get:
        mock_get.side_effect = requests.exceptions.ConnectTimeout("Timeout")
        
        with pytest.raises(PrerequisiteError, match="Technitium unreachable"):
            driver.validate()

def test_execute_timeout(driver, mock_profile):
    task = Task(type="provision", profile=mock_profile)
    with patch("requests.get") as mock_get:
        mock_get.side_effect = requests.exceptions.Timeout("Timeout")
        
        with pytest.raises(ExecutionError, match="Technitium request failed"):
            driver.execute(task)

def test_execute_http_error(driver, mock_profile):
    task = Task(type="provision", profile=mock_profile)
    with patch("requests.get") as mock_get:
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"
        mock_get.return_value = mock_response
        
        with pytest.raises(ExecutionError, match=r"Technitium API error \(500\): Internal Server Error"):
            driver.execute(task)

def test_execute_invalid_json(driver, mock_profile):
    task = Task(type="provision", profile=mock_profile)
    with patch("requests.get") as mock_get:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.side_effect = ValueError("Invalid JSON")
        mock_get.return_value = mock_response
        
        with pytest.raises(ExecutionError, match="Technitium operation failed"):
            driver.execute(task)

def test_execute_api_status_error(driver, mock_profile):
    task = Task(type="provision", profile=mock_profile)
    with patch("requests.get") as mock_get:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"status": "error", "errorMessage": "Invalid params"}
        mock_get.return_value = mock_response
        
        with pytest.raises(ExecutionError, match="Technitium Error: Invalid params"):
            driver.execute(task)

def test_execute_unsupported_resource(driver, mock_profile):
    task = Task(type="provision", profile=mock_profile, overrides={"resource": "invalid"})
    with pytest.raises(ExecutionError, match="Unsupported resource type: invalid"):
        driver.execute(task)

def test_handle_dhcp_unsupported_action(driver, mock_profile):
    task = Task(type="provision", profile=mock_profile, overrides={"resource": "dhcp", "action": "invalid"})
    with pytest.raises(ExecutionError, match="Unsupported DHCP action: invalid"):
        driver.execute(task)

def test_handle_record_unsupported_action(driver, mock_profile):
    task = Task(type="provision", profile=mock_profile, overrides={"resource": "record", "action": "invalid"})
    with pytest.raises(ExecutionError, match="Unsupported record action: invalid"):
        driver.execute(task)

def test_handle_zone_unsupported_action(driver, mock_profile):
    task = Task(type="provision", profile=mock_profile, overrides={"resource": "zone", "action": "invalid"})
    with pytest.raises(ExecutionError, match="Unsupported zone action: invalid"):
        driver.execute(task)

def test_handle_backup_export(driver, mock_profile):
    task = Task(type="provision", profile=mock_profile, overrides={"resource": "backup", "action": "export"})
    with patch("requests.get") as mock_get:
        # Mock listZones
        mock_response_list = MagicMock()
        mock_response_list.status_code = 200
        mock_response_list.json.return_value = {
            "status": "ok",
            "response": {"zones": [{"name": "zone1.local"}, {"name": "zone2.local"}]}
        }
        
        # Mock exportZone
        mock_response_export = MagicMock()
        mock_response_export.status_code = 200
        mock_response_export.json.return_value = {
            "status": "ok",
            "response": {"zoneFileContent": "some content"}
        }
        
        mock_get.side_effect = [mock_response_list, mock_response_export, mock_response_export]
        
        result = driver.execute(task)
        assert result.success is True
        assert "zone1.local" in result.output["zones"]
        assert "zone2.local" in result.output["zones"]
        assert result.output["zones"]["zone1.local"] == "some content"

def test_handle_backup_unsupported_action(driver, mock_profile):
    task = Task(type="provision", profile=mock_profile, overrides={"resource": "backup", "action": "invalid"})
    with pytest.raises(ExecutionError, match="Unsupported backup action: invalid"):
        driver.execute(task)

def test_api_call_param_mapping(driver, mock_profile):
    task = Task(
        type="provision", 
        profile=mock_profile, 
        overrides={
            "ip_address": "1.2.3.4",
            "record_type": "A",
            "ttl": 3600,
            "ptr": "test.local"
        }
    )
    with patch("requests.get") as mock_get:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"status": "ok", "response": {"success": True}}
        mock_get.return_value = mock_response
        
        result = driver.execute(task)
        assert result.success is True
        
        # Verify params were mapped correctly
        args, kwargs = mock_get.call_args
        params = kwargs["params"]
        assert params["ipAddress"] == "1.2.3.4"
        assert params["type"] == "A"
        assert params["ttl"] == 3600
        assert params["ptrName"] == "test.local"
        assert "ip_address" not in params
        assert "record_type" not in params

def test_handle_dhcp_actions(driver, mock_profile):
    with patch("requests.get") as mock_get:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"status": "ok"}
        mock_get.return_value = mock_response
        
        driver.execute(Task(type="provision", profile=mock_profile, overrides={"resource": "dhcp", "action": "list"}))
        assert "dhcp/scopes/list" in mock_get.call_args[0][0]
        
        driver.execute(Task(type="provision", profile=mock_profile, overrides={"resource": "dhcp", "action": "enable"}))
        assert "dhcp/scopes/enable" in mock_get.call_args[0][0]
        
        driver.execute(Task(type="provision", profile=mock_profile, overrides={"resource": "dhcp", "action": "disable"}))
        assert "dhcp/scopes/disable" in mock_get.call_args[0][0]

def test_handle_zone_actions(driver, mock_profile):
    with patch("requests.get") as mock_get:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"status": "ok"}
        mock_get.return_value = mock_response
        
        driver.execute(Task(type="provision", profile=mock_profile, overrides={"resource": "zone", "action": "create"}))
        assert "dns/createZone" in mock_get.call_args[0][0]
        
        driver.execute(Task(type="provision", profile=mock_profile, overrides={"resource": "zone", "action": "delete"}))
        assert "dns/deleteZone" in mock_get.call_args[0][0]
        
        driver.execute(Task(type="provision", profile=mock_profile, overrides={"resource": "zone", "action": "list"}))
        assert "dns/listZones" in mock_get.call_args[0][0]

def test_handle_record_actions(driver, mock_profile):
    with patch("requests.get") as mock_get:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"status": "ok"}
        mock_get.return_value = mock_response
        
        driver.execute(Task(type="provision", profile=mock_profile, overrides={"resource": "record", "action": "add"}))
        assert "dns/addRecord" in mock_get.call_args[0][0]
        
        driver.execute(Task(type="provision", profile=mock_profile, overrides={"resource": "record", "action": "delete"}))
        assert "dns/deleteRecord" in mock_get.call_args[0][0]
        
        driver.execute(Task(type="provision", profile=mock_profile, overrides={"resource": "record", "action": "get"}))
        assert "dns/getRecords" in mock_get.call_args[0][0]

def test_provision_infer_params(driver, mock_profile):
    task = Task(type="provision", profile=mock_profile, target="10.0.0.1")
    with patch("requests.get") as mock_get:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"status": "ok"}
        mock_get.return_value = mock_response
        
        driver.execute(task)
        
        params = mock_get.call_args[1]["params"]
        assert params["zone"] == "homelab.internal"
        assert params["domain"] == "test-node.homelab.internal"
        assert params["ipAddress"] == "10.0.0.1"
        assert params["type"] == "A"

def test_execute_destroy_action(driver, mock_profile):
    task = Task(type="destroy", profile=mock_profile)
    with patch("requests.get") as mock_get:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"status": "ok"}
        mock_get.return_value = mock_response
        
        driver.execute(task)
        assert "dns/deleteRecord" in mock_get.call_args[0][0]

def test_execute_custom_action(driver, mock_profile):
    task = Task(type="custom-action", profile=mock_profile)
    with patch("requests.get") as mock_get:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"status": "ok"}
        mock_get.return_value = mock_response
        
        # This will try to call _handle_record with action="custom-action"
        # which will raise ExecutionError because it's not in ("create", "add", "delete", "list", "get")
        with pytest.raises(ExecutionError, match="Unsupported record action: custom-action"):
            driver.execute(task)
