# tests/unit/test_opnsense_dhcp.py
import pytest
from unittest.mock import patch
from opnsense.modules.dhcp import DHCPClient
from opnsense.exceptions import ValidationError


def test_dhcp_client_init():
    """DHCPClient initializes with credentials"""
    client = DHCPClient("key", "secret", "https://opnsense.local/api")
    assert client.api is not None


@patch('opnsense.client.requests.get')
def test_list_enabled_interfaces_returns_enabled_only(mock_get):
    """list_enabled_interfaces returns only interfaces with enable='1'"""
    mock_get.return_value.status_code = 200
    mock_get.return_value.json.return_value = {
        'dhcpd': {
            'lan': {'enable': '1', 'range': {'from': '10.10.10.101', 'to': '10.10.10.254'}},
            'opt1': {'enable': '0', 'range': {'from': '10.10.20.101', 'to': '10.10.20.254'}},
            'opt2': {'enable': '1', 'range': {'from': '10.10.30.101', 'to': '10.10.30.254'}},
        }
    }

    client = DHCPClient("key", "secret", "https://opnsense.local/api")
    result = client.list_enabled_interfaces()

    assert len(result) == 2
    interfaces = [r['interface'] for r in result]
    assert 'lan' in interfaces
    assert 'opt2' in interfaces
    assert 'opt1' not in interfaces


@patch('opnsense.client.requests.get')
def test_list_enabled_interfaces_includes_range(mock_get):
    """list_enabled_interfaces includes range_from and range_to"""
    mock_get.return_value.status_code = 200
    mock_get.return_value.json.return_value = {
        'dhcpd': {
            'lan': {'enable': '1', 'range': {'from': '10.10.10.101', 'to': '10.10.10.254'}},
        }
    }

    client = DHCPClient("key", "secret", "https://opnsense.local/api")
    result = client.list_enabled_interfaces()

    assert result[0]['range_from'] == '10.10.10.101'
    assert result[0]['range_to'] == '10.10.10.254'


@patch('opnsense.client.requests.get')
def test_list_enabled_interfaces_empty_dhcpd(mock_get):
    """list_enabled_interfaces returns empty list when no interfaces"""
    mock_get.return_value.status_code = 200
    mock_get.return_value.json.return_value = {'dhcpd': {}}

    client = DHCPClient("key", "secret", "https://opnsense.local/api")
    result = client.list_enabled_interfaces()

    assert result == []


@patch('opnsense.client.requests.post')
def test_disable_interface_sends_correct_payload(mock_post):
    """disable_interface sends enable=0 for the given interface"""
    mock_post.return_value.status_code = 200
    mock_post.return_value.json.return_value = {'result': 'saved'}

    client = DHCPClient("key", "secret", "https://opnsense.local/api")
    result = client.disable_interface('lan')

    assert result == {'result': 'saved'}
    posted_json = mock_post.call_args[1].get('json')
    assert posted_json == {'dhcpd': {'lan': {'enable': '0'}}}


@patch('opnsense.client.requests.post')
def test_enable_interface_sends_correct_payload(mock_post):
    """enable_interface sends enable=1 for the given interface"""
    mock_post.return_value.status_code = 200
    mock_post.return_value.json.return_value = {'result': 'saved'}

    client = DHCPClient("key", "secret", "https://opnsense.local/api")
    result = client.enable_interface('lan')

    assert result == {'result': 'saved'}
    posted_json = mock_post.call_args[1].get('json')
    assert posted_json == {'dhcpd': {'lan': {'enable': '1'}}}


def test_disable_interface_requires_interface():
    """disable_interface raises ValidationError for empty interface"""
    client = DHCPClient("key", "secret", "https://opnsense.local/api")

    with pytest.raises(ValidationError) as exc:
        client.disable_interface('')

    assert "Interface required" in str(exc.value)


def test_enable_interface_requires_interface():
    """enable_interface raises ValidationError for empty interface"""
    client = DHCPClient("key", "secret", "https://opnsense.local/api")

    with pytest.raises(ValidationError) as exc:
        client.enable_interface('')

    assert "Interface required" in str(exc.value)
