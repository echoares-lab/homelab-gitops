"""Unit tests for OpnsenseDriver."""

import pytest
import requests
from unittest.mock import MagicMock, patch
from homelab_gitops.drivers.opnsense_driver import OPNsenseDriver
from homelab_gitops.drivers.exceptions import PrerequisiteError, ExecutionError
from homelab_gitops.domain.models import Task

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

def test_opnsense_driver_execute_list_vlans(opnsense_driver):
    with patch("requests.get") as mock_get:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"rows": [{"tag": "10", "descr": "IOT"}]}
        mock_get.return_value = mock_response
        
        task = Task(
            type="provision",
            profile=MagicMock(),
            overrides={"resource": "vlan", "action": "list"}
        )
        result = opnsense_driver.execute(task)
        assert result.success is True
        assert len(result.output["vlans"]) == 1

def test_opnsense_driver_handle_dhcp(opnsense_driver):
    with patch("requests.get") as mock_get:
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = {"rows": []}
        
        task = Task(
            type="provision",
            profile=MagicMock(),
            overrides={"resource": "dhcp", "action": "list_enabled", "interface": "lan"}
        )
        result = opnsense_driver.execute(task)
        assert result.success is True

def test_opnsense_driver_handle_firewall(opnsense_driver):
    with patch("requests.get") as mock_get:
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = {"rows": []}
        
        task = Task(
            type="provision",
            profile=MagicMock(),
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

def test_opnsense_driver_handle_interface(opnsense_driver):
    with patch("requests.get") as mock_get:
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = {"rows": []}
        
        task = Task(
            type="provision",
            profile=MagicMock(),
            overrides={"resource": "interface", "action": "list"}
        )
        result = opnsense_driver.execute(task)
        assert result.success is True

def test_opnsense_driver_execute_unsupported(opnsense_driver):
    task = Task(
        type="provision",
        profile=MagicMock(),
        overrides={"resource": "invalid"}
    )
    with pytest.raises(ExecutionError):
        opnsense_driver.execute(task)
