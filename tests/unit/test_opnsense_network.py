import pytest
from unittest.mock import patch
from opnsense.modules.network import NetworkClient
from opnsense.exceptions import ValidationError

def test_network_client_init():
    """NetworkClient initializes with credentials"""
    client = NetworkClient("key", "secret", "https://opnsense.local/api")
    assert client.api is not None

@patch('opnsense.client.requests.post')
def test_create_vlan_success(mock_post):
    """create_vlan returns VLAN ID on success"""
    mock_post.return_value.status_code = 200
    mock_post.return_value.json.return_value = {'uuid': 'vlan-100'}

    client = NetworkClient("key", "secret", "https://opnsense.local/api")
    result = client.create_vlan(
        interface="em0",
        vlan_id=100,
        description="web-tier"
    )

    assert result['uuid'] == 'vlan-100'

def test_create_vlan_validates_vlan_id_range():
    """create_vlan validates VLAN ID is 1-4094"""
    client = NetworkClient("key", "secret", "https://opnsense.local/api")

    with pytest.raises(ValidationError) as exc:
        client.create_vlan(
            interface="em0",
            vlan_id=5000,
            description="test"
        )

    assert "Invalid VLAN ID" in str(exc.value)

def test_create_vlan_validates_vlan_id_low():
    """create_vlan rejects VLAN ID < 1"""
    client = NetworkClient("key", "secret", "https://opnsense.local/api")

    with pytest.raises(ValidationError) as exc:
        client.create_vlan(
            interface="em0",
            vlan_id=0,
            description="test"
        )

    assert "Invalid VLAN ID" in str(exc.value)

def test_create_vlan_requires_interface():
    """create_vlan validates interface is provided"""
    client = NetworkClient("key", "secret", "https://opnsense.local/api")

    with pytest.raises(ValidationError) as exc:
        client.create_vlan(
            interface="",
            vlan_id=100,
            description="test"
        )

    assert "Interface required" in str(exc.value)

def test_create_vlan_requires_description():
    """create_vlan validates description is provided"""
    client = NetworkClient("key", "secret", "https://opnsense.local/api")

    with pytest.raises(ValidationError) as exc:
        client.create_vlan(
            interface="em0",
            vlan_id=100,
            description=""
        )

    assert "Description required" in str(exc.value)

@patch('opnsense.client.requests.get')
def test_list_vlans(mock_get):
    """list_vlans returns list of VLANs"""
    mock_get.return_value.status_code = 200
    mock_get.return_value.json.return_value = {
        'rows': [
            {'uuid': 'vlan-1', 'vlan_id': 100},
            {'uuid': 'vlan-2', 'vlan_id': 200}
        ]
    }

    client = NetworkClient("key", "secret", "https://opnsense.local/api")
    result = client.list_vlans()

    assert len(result) == 2
    assert result[0]['vlan_id'] == 100

@patch('opnsense.client.requests.get')
def test_get_vlan(mock_get):
    """get_vlan returns single VLAN"""
    mock_get.return_value.status_code = 200
    mock_get.return_value.json.return_value = {
        'vlan': {'uuid': 'vlan-1', 'vlan_id': 100}
    }

    client = NetworkClient("key", "secret", "https://opnsense.local/api")
    result = client.get_vlan('vlan-1')

    assert result['vlan_id'] == 100

@patch('opnsense.client.requests.post')
def test_delete_vlan(mock_post):
    """delete_vlan calls API with VLAN ID"""
    mock_post.return_value.status_code = 200
    mock_post.return_value.json.return_value = {'status': 'deleted'}

    client = NetworkClient("key", "secret", "https://opnsense.local/api")
    result = client.delete_vlan('vlan-1')

    assert result['status'] == 'deleted'

@patch('opnsense.client.requests.get')
def test_list_interfaces(mock_get):
    """list_interfaces returns list of interfaces"""
    mock_get.return_value.status_code = 200
    mock_get.return_value.json.return_value = {
        'interfaces': [
            {'name': 'em0', 'ip': '192.168.1.1'},
            {'name': 'em1', 'ip': '10.0.0.1'}
        ]
    }

    client = NetworkClient("key", "secret", "https://opnsense.local/api")
    result = client.list_interfaces()

    assert len(result) == 2
    assert result[0]['name'] == 'em0'

@patch('opnsense.client.requests.get')
def test_get_interface(mock_get):
    """get_interface returns single interface"""
    mock_get.return_value.status_code = 200
    mock_get.return_value.json.return_value = {
        'interface': {'name': 'em0', 'ip': '192.168.1.1'}
    }

    client = NetworkClient("key", "secret", "https://opnsense.local/api")
    result = client.get_interface('em0')

    assert result['ip'] == '192.168.1.1'

@patch('opnsense.client.requests.post')
def test_configure_interface(mock_post):
    """configure_interface accepts all OPNsense fields"""
    mock_post.return_value.status_code = 200
    mock_post.return_value.json.return_value = {'status': 'updated'}

    client = NetworkClient("key", "secret", "https://opnsense.local/api")
    result = client.configure_interface(
        name="em0",
        ip_address="192.168.1.1",
        gateway="192.168.1.254",
        mtu=1500
    )

    assert result['status'] == 'updated'
