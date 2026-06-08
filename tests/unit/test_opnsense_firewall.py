import pytest
from unittest.mock import patch
from opnsense.modules.firewall import FirewallClient
from opnsense.exceptions import ValidationError

def test_firewall_client_init():
    """FirewallClient initializes with credentials"""
    client = FirewallClient("key", "secret", "https://opnsense.local/api")
    assert client.api is not None

@patch('opnsense.client.requests.post')
def test_create_firewall_rule_success(mock_post):
    """create_firewall_rule returns rule ID on success"""
    mock_post.return_value.status_code = 200
    mock_post.return_value.json.return_value = {'uuid': 'rule-123'}

    client = FirewallClient("key", "secret", "https://opnsense.local/api")
    result = client.create_firewall_rule(
        name="Allow SSH",
        src_net="10.0.0.0/24",
        dst_net="0.0.0.0/0",
        protocol="tcp",
        port=22,
        action="pass"
    )

    assert result['uuid'] == 'rule-123'

def test_create_firewall_rule_requires_name():
    """create_firewall_rule validates name is not empty"""
    client = FirewallClient("key", "secret", "https://opnsense.local/api")

    with pytest.raises(ValidationError) as exc:
        client.create_firewall_rule(
            name="",
            src_net="10.0.0.0/24",
            dst_net="0.0.0.0/0",
            protocol="tcp",
            port=22,
            action="pass"
        )

    assert "Name required" in str(exc.value)

def test_create_firewall_rule_validates_name_length():
    """create_firewall_rule validates name max 255 chars"""
    client = FirewallClient("key", "secret", "https://opnsense.local/api")

    long_name = "x" * 256

    with pytest.raises(ValidationError) as exc:
        client.create_firewall_rule(
            name=long_name,
            src_net="10.0.0.0/24",
            dst_net="0.0.0.0/0",
            protocol="tcp",
            port=22,
            action="pass"
        )

    assert "max 255" in str(exc.value)

def test_create_firewall_rule_validates_src_net_cidr():
    """create_firewall_rule validates src_net CIDR notation"""
    client = FirewallClient("key", "secret", "https://opnsense.local/api")

    with pytest.raises(ValidationError) as exc:
        client.create_firewall_rule(
            name="test",
            src_net="10.0.0",
            dst_net="0.0.0.0/0",
            protocol="tcp",
            port=22,
            action="pass"
        )

    assert "Invalid CIDR" in str(exc.value) and "src_net" in str(exc.value)

def test_create_firewall_rule_validates_dst_net_cidr():
    """create_firewall_rule validates dst_net CIDR notation"""
    client = FirewallClient("key", "secret", "https://opnsense.local/api")

    with pytest.raises(ValidationError) as exc:
        client.create_firewall_rule(
            name="test",
            src_net="10.0.0.0/24",
            dst_net="192.168.1",
            protocol="tcp",
            port=22,
            action="pass"
        )

    assert "Invalid CIDR" in str(exc.value) and "dst_net" in str(exc.value)

def test_create_firewall_rule_validates_protocol():
    """create_firewall_rule validates protocol is allowed"""
    client = FirewallClient("key", "secret", "https://opnsense.local/api")

    with pytest.raises(ValidationError) as exc:
        client.create_firewall_rule(
            name="test",
            src_net="10.0.0.0/24",
            dst_net="0.0.0.0/0",
            protocol="invalid-protocol",
            port=22,
            action="pass"
        )

    assert "Invalid protocol" in str(exc.value)

def test_create_firewall_rule_validates_action():
    """create_firewall_rule validates action is allowed"""
    client = FirewallClient("key", "secret", "https://opnsense.local/api")

    with pytest.raises(ValidationError) as exc:
        client.create_firewall_rule(
            name="test",
            src_net="10.0.0.0/24",
            dst_net="0.0.0.0/0",
            protocol="tcp",
            port=22,
            action="maybe"
        )

    assert "Invalid action" in str(exc.value)

def test_create_firewall_rule_validates_port_range():
    """create_firewall_rule validates port is 1-65535"""
    client = FirewallClient("key", "secret", "https://opnsense.local/api")

    with pytest.raises(ValidationError) as exc:
        client.create_firewall_rule(
            name="test",
            src_net="10.0.0.0/24",
            dst_net="0.0.0.0/0",
            protocol="tcp",
            port=99999,
            action="pass"
        )

    assert "Port out of range" in str(exc.value)

def test_create_firewall_rule_port_not_required_for_icmp():
    """create_firewall_rule does not require port for ICMP"""
    with patch('opnsense.client.requests.post') as mock_post:
        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = {'uuid': 'rule-123'}

        client = FirewallClient("key", "secret", "https://opnsense.local/api")
        result = client.create_firewall_rule(
            name="test",
            src_net="10.0.0.0/24",
            dst_net="0.0.0.0/0",
            protocol="icmp",
            port=None,
            action="pass"
        )

        assert result['uuid'] == 'rule-123'

@patch('opnsense.client.requests.get')
def test_list_firewall_rules(mock_get):
    """list_firewall_rules returns list of rules"""
    mock_get.return_value.status_code = 200
    mock_get.return_value.json.return_value = {
        'rows': [
            {'uuid': 'rule-1', 'name': 'Rule 1'},
            {'uuid': 'rule-2', 'name': 'Rule 2'}
        ]
    }

    client = FirewallClient("key", "secret", "https://opnsense.local/api")
    result = client.list_firewall_rules()

    assert len(result) == 2
    assert result[0]['name'] == 'Rule 1'

@patch('opnsense.client.requests.get')
def test_get_firewall_rule(mock_get):
    """get_firewall_rule returns single rule"""
    mock_get.return_value.status_code = 200
    mock_get.return_value.json.return_value = {
        'rule': {
            'uuid': 'rule-1',
            'name': 'Allow SSH'
        }
    }

    client = FirewallClient("key", "secret", "https://opnsense.local/api")
    result = client.get_firewall_rule('rule-1')

    assert result['name'] == 'Allow SSH'

@patch('opnsense.client.requests.post')
def test_delete_firewall_rule(mock_post):
    """delete_firewall_rule calls API with rule ID"""
    mock_post.return_value.status_code = 200
    mock_post.return_value.json.return_value = {'status': 'deleted'}

    client = FirewallClient("key", "secret", "https://opnsense.local/api")
    result = client.delete_firewall_rule('rule-1')

    assert result['status'] == 'deleted'
