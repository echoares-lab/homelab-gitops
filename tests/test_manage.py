import pytest
from unittest.mock import patch, MagicMock
from manage import identify_vm

@patch("manage.console.status")
@patch("manage.run_cmd")
def test_identify_vm_direct_match(mock_run_cmd, mock_status):
    mock_res = MagicMock()
    mock_res.stdout = "  default\n* test-vm\n  other-vm"
    mock_res.returncode = 0
    mock_run_cmd.return_value = mock_res

    result = identify_vm("test-vm")

    assert result == "test-vm"
    mock_run_cmd.assert_called_once_with("tofu workspace list", cwd="tofu", capture=True)

@patch("manage.console.status")
@patch("manage.run_cmd")
def test_identify_vm_ip_match(mock_run_cmd, mock_status):
    def side_effect(cmd, cwd=None, capture=False):
        res = MagicMock()
        if "workspace list" in cmd:
            res.stdout = "  default\n* other-vm"
            res.returncode = 0
        elif "govc find" in cmd:
            res.stdout = "/Datacenter/vm/test-vm-folder/ip-match-vm"
            res.returncode = 0
        return res

    mock_run_cmd.side_effect = side_effect

    result = identify_vm("192.168.1.50")

    assert result == "ip-match-vm"
    assert mock_run_cmd.call_count == 2
    mock_run_cmd.assert_any_call("tofu workspace list", cwd="tofu", capture=True)
    mock_run_cmd.assert_any_call("./build/govc find . -type m -guest.ipAddress '192.168.1.50'", capture=True)

@patch("manage.console.status")
@patch("manage.run_cmd")
def test_identify_vm_partial_match(mock_run_cmd, mock_status):
    def side_effect(cmd, cwd=None, capture=False):
        res = MagicMock()
        res.stdout = "  default\n* test-vm-123\n  other-vm"
        res.returncode = 0
        return res

    mock_run_cmd.side_effect = side_effect

    result = identify_vm("test-vm")

    assert result == "test-vm-123"
    assert mock_run_cmd.call_count == 2
    mock_run_cmd.assert_any_call("tofu workspace list", cwd="tofu", capture=True)

@patch("manage.console.status")
@patch("manage.run_cmd")
def test_identify_vm_no_match(mock_run_cmd, mock_status):
    def side_effect(cmd, cwd=None, capture=False):
        res = MagicMock()
        res.stdout = "  default\n* other-vm"
        res.returncode = 0
        return res

    mock_run_cmd.side_effect = side_effect

    result = identify_vm("nonexistent")

    assert result is None
    assert mock_run_cmd.call_count == 2
