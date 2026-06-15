import pytest
import json
import os
from unittest.mock import patch, MagicMock, mock_open
from homelab_gitops.drivers.migration_driver import MigrationDriver
from homelab_gitops.drivers.exceptions import ExecutionError
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
def opnsense_mock():
    return MagicMock()

@pytest.fixture
def technitium_mock():
    return MagicMock()

@pytest.fixture
def driver(opnsense_mock, technitium_mock):
    return MigrationDriver(
        state_file="test-state.json",
        opnsense_driver=opnsense_mock,
        technitium_driver=technitium_mock
    )

def test_validate_success(driver, opnsense_mock, technitium_mock):
    opnsense_mock.validate.return_value = True
    technitium_mock.validate.return_value = True
    with patch("os.access", return_value=True):
        assert driver.validate() is True

def test_validate_permission_denied(driver):
    with patch("os.access", return_value=False):
        assert driver.validate() is False

def test_validate_subdriver_failure(driver, opnsense_mock, technitium_mock):
    opnsense_mock.validate.return_value = False
    technitium_mock.validate.return_value = True
    with patch("os.access", return_value=True):
        assert driver.validate() is False

def test_execute_save_state(driver, mock_profile):
    task = Task(
        type="migration",
        profile=mock_profile,
        overrides={"action": "save_state", "migrated": [{"id": 1}]}
    )
    with patch("builtins.open", mock_open()) as mocked_file:
        result = driver.execute(task)
        assert result.success is True
        assert result.output["status"] == "saved"
        mocked_file.assert_called_once_with("test-state.json", "w")

def test_execute_load_state(driver, mock_profile):
    task = Task(
        type="migration",
        profile=mock_profile,
        overrides={"action": "load_state"}
    )
    state_data = json.dumps({"migrated": [{"id": 1}], "timestamp": "now"})
    with patch("os.path.exists", return_value=True), \
         patch("builtins.open", mock_open(read_data=state_data)):
        result = driver.execute(task)
        assert result.success is True
        assert result.output["migrated"] == [{"id": 1}]

def test_execute_load_state_not_found(driver, mock_profile):
    task = Task(
        type="migration",
        profile=mock_profile,
        overrides={"action": "load_state"}
    )
    with patch("os.path.exists", return_value=False):
        result = driver.execute(task)
        assert result.success is True
        assert result.output["migrated"] == []

def test_execute_load_state_corrupt(driver, mock_profile):
    task = Task(
        type="migration",
        profile=mock_profile,
        overrides={"action": "load_state"}
    )
    with patch("os.path.exists", return_value=True), \
         patch("builtins.open", mock_open(read_data="invalid json")):
        result = driver.execute(task)
        assert result.success is True
        assert result.output["migrated"] == []

def test_execute_load_state_ioerror(driver, mock_profile):
    task = Task(
        type="migration",
        profile=mock_profile,
        overrides={"action": "load_state"}
    )
    with patch("os.path.exists", return_value=True), \
         patch("builtins.open", side_effect=IOError("Read error")):
        result = driver.execute(task)
        assert result.success is True
        assert result.output["migrated"] == []

def test_execute_rollback_no_state(driver, mock_profile):
    task = Task(
        type="migration",
        profile=mock_profile,
        overrides={"action": "rollback"}
    )
    with patch("os.path.exists", return_value=False):
        result = driver.execute(task)
        assert result.success is True
        assert result.output["status"] == "skipped"

def test_execute_rollback_success(driver, mock_profile, opnsense_mock, technitium_mock):
    task = Task(
        type="migration",
        profile=mock_profile,
        overrides={"action": "rollback"}
    )
    state_data = json.dumps({
        "migrated": [
            {"opnsense_interface": "lan", "technitium_scope": "lan-scope"}
        ]
    })
    with patch("os.path.exists", return_value=True), \
         patch("builtins.open", mock_open(read_data=state_data)), \
         patch("os.remove") as mock_remove:
        
        result = driver.execute(task)
        
        assert result.success is True
        assert result.output["status"] == "success"
        assert opnsense_mock.execute.called
        assert technitium_mock.execute.called
        mock_remove.assert_called_once_with("test-state.json")

def test_execute_rollback_partial_failure(driver, mock_profile, opnsense_mock, technitium_mock):
    task = Task(
        type="migration",
        profile=mock_profile,
        overrides={"action": "rollback"}
    )
    state_data = json.dumps({
        "migrated": [
            {"opnsense_interface": "lan", "technitium_scope": "lan-scope"},
            {"opnsense_interface": "opt1", "technitium_scope": "opt1-scope"}
        ]
    })
    
    # First one succeeds, second one fails
    opnsense_mock.execute.side_effect = [None, Exception("Failed")]
    
    with patch("os.path.exists", return_value=True), \
         patch("builtins.open", mock_open(read_data=state_data)):
        
        result = driver.execute(task)
        
        assert result.success is True
        assert result.output["status"] == "partial_failure"
        assert len(result.output["results"]) == 1
        assert len(result.output["failed"]) == 1

def test_execute_clear_state(driver, mock_profile):
    task = Task(
        type="migration",
        profile=mock_profile,
        overrides={"action": "clear_state"}
    )
    with patch("os.path.exists", return_value=True), \
         patch("os.remove") as mock_remove:
        result = driver.execute(task)
        assert result.success is True
        mock_remove.assert_called_once_with("test-state.json")

def test_execute_unsupported_action(driver, mock_profile):
    task = Task(
        type="migration",
        profile=mock_profile,
        overrides={"action": "invalid"}
    )
    with pytest.raises(ExecutionError, match="Unsupported migration action: invalid"):
        driver.execute(task)

def test_save_state_permission_denied(driver, mock_profile):
    task = Task(
        type="migration",
        profile=mock_profile,
        overrides={"action": "save_state", "migrated": []}
    )
    with patch("builtins.open", side_effect=PermissionError("Permission denied")):
        with pytest.raises(ExecutionError, match="Migration state operation failed: Permission denied"):
            driver.execute(task)

def test_rollback_missing_fields(driver, mock_profile, opnsense_mock):
    # Test that it skips entries with missing fields
    task = Task(
        type="migration",
        profile=mock_profile,
        overrides={"action": "rollback"}
    )
    state_data = json.dumps({
        "migrated": [
            {"opnsense_interface": "lan"}, # missing technitium_scope
            {"technitium_scope": "lan-scope"} # missing opnsense_interface
        ]
    })
    with patch("os.path.exists", return_value=True), \
         patch("builtins.open", mock_open(read_data=state_data)), \
         patch("os.remove") as mock_remove:
        
        result = driver.execute(task)
        
        assert result.success is True
        assert result.output["status"] == "success"
        assert result.output["results"] == []
        assert not opnsense_mock.execute.called
