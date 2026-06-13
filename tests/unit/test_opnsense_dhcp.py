# tests/unit/test_opnsense_dhcp.py
import pytest
from unittest.mock import patch, MagicMock
from opnsense.modules.dhcp import DHCPClient
from opnsense.exceptions import ValidationError


def test_dhcp_client_init():
    """DHCPClient initializes with credentials"""
    client = DHCPClient("key", "secret", "https://opnsense.local/api")
    assert client.api is not None


@patch('opnsense.client.requests.get')
def test_list_enabled_interfaces_returns_enabled_only(mock_get):
    """list_enabled_interfaces returns only interfaces not in no_interface list"""
    mock_get.return_value.status_code = 200
    mock_get.return_value.json.return_value = {
        'dnsmasq': {
            'dhcp': {
                'no_interface': {
                    'opt1': {'selected': 1},  # opt1 is excluded
                    'opt2': {'selected': 0},
                }
            },
            'dhcp_ranges': {
                'uuid1': {
                    'interface': {'lan': {'selected': 1}},
                    'start_addr': '10.10.10.101',
                    'end_addr': '10.10.10.254'
                },
                'uuid2': {
                    'interface': {'opt1': {'selected': 1}},
                    'start_addr': '10.10.20.101',
                    'end_addr': '10.10.20.254'
                },
                'uuid3': {
                    'interface': {'opt2': {'selected': 1}},
                    'start_addr': '10.10.30.101',
                    'end_addr': '10.10.30.254'
                }
            }
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
        'dnsmasq': {
            'dhcp': {'no_interface': {}},
            'dhcp_ranges': {
                'uuid1': {
                    'interface': {'lan': {'selected': 1}},
                    'start_addr': '10.10.10.101',
                    'end_addr': '10.10.10.254'
                }
            }
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
    mock_get.return_value.json.return_value = {
        'dnsmasq': {
            'dhcp': {'no_interface': {}},
            'dhcp_ranges': {}
        }
    }

    client = DHCPClient("key", "secret", "https://opnsense.local/api")
    result = client.list_enabled_interfaces()

    assert result == []


@patch('opnsense.client.requests.get')
@patch('opnsense.client.requests.post')
def test_disable_interface_sends_correct_payload(mock_post, mock_get):
    """disable_interface sends updated no_interface list"""
    mock_get.return_value.status_code = 200
    mock_get.return_value.json.return_value = {
        'dnsmasq': {
            'dhcp': {
                'no_interface': {
                    'opt1': {'selected': 1}
                }
            }
        }
    }
    mock_post.return_value.status_code = 200
    mock_post.return_value.json.return_value = {'result': 'saved'}

    client = DHCPClient("key", "secret", "https://opnsense.local/api")
    result = client.disable_interface('lan')

    assert result == {'result': 'saved'}
    # Check that it combined 'opt1' (already excluded) and 'lan'
    # Call 0 is for the 'set' operation
    posted_json = mock_post.call_args_list[0][1].get('json')
    assert 'opt1,lan' in posted_json['dnsmasq']['dhcp']['no_interface'] or \
           'lan,opt1' in posted_json['dnsmasq']['dhcp']['no_interface']


@patch('opnsense.client.requests.get')
@patch('opnsense.client.requests.post')
def test_enable_interface_sends_correct_payload(mock_post, mock_get):
    """enable_interface removes interface from no_interface list"""
    mock_get.return_value.status_code = 200
    mock_get.return_value.json.return_value = {
        'dnsmasq': {
            'dhcp': {
                'no_interface': {
                    'opt1': {'selected': 1},
                    'lan': {'selected': 1}
                }
            }
        }
    }
    mock_post.return_value.status_code = 200
    mock_post.return_value.json.return_value = {'result': 'saved'}

    client = DHCPClient("key", "secret", "https://opnsense.local/api")
    result = client.enable_interface('lan')

    assert result == {'result': 'saved'}
    # Check that 'lan' was removed, only 'opt1' remains
    posted_json = mock_post.call_args_list[0][1].get('json')
    assert posted_json['dnsmasq']['dhcp']['no_interface'] == 'opt1'


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
