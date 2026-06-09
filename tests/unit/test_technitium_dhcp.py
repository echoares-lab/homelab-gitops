import pytest
from unittest.mock import patch
from technitium.modules.dhcp import TechnitiumDHCPClient
from technitium.exceptions import TechnitiumValidationError


def test_dhcp_client_init():
    client = TechnitiumDHCPClient(host="http://10.10.10.2:5380", token="abc123")
    assert client.api is not None


@patch('technitium.client.requests.get')
def test_list_scopes_returns_scopes(mock_get):
    mock_get.return_value.status_code = 200
    mock_get.return_value.json.return_value = {
        'status': 'ok',
        'response': {
            'scopes': [
                {'name': 'mgmt', 'enabled': False, 'networkAddress': '10.10.10.0'},
                {'name': 'infra', 'enabled': False, 'networkAddress': '10.10.20.0'},
            ]
        }
    }

    client = TechnitiumDHCPClient(host="http://10.10.10.2:5380", token="abc123")
    result = client.list_scopes()

    assert len(result) == 2
    assert result[0]['name'] == 'mgmt'
    assert result[1]['name'] == 'infra'


@patch('technitium.client.requests.get')
def test_list_scopes_empty(mock_get):
    mock_get.return_value.status_code = 200
    mock_get.return_value.json.return_value = {
        'status': 'ok',
        'response': {'scopes': []}
    }

    client = TechnitiumDHCPClient(host="http://10.10.10.2:5380", token="abc123")
    result = client.list_scopes()

    assert result == []


@patch('technitium.client.requests.get')
def test_enable_scope_success(mock_get):
    mock_get.return_value.status_code = 200
    mock_get.return_value.json.return_value = {'status': 'ok'}

    client = TechnitiumDHCPClient(host="http://10.10.10.2:5380", token="abc123")
    result = client.enable_scope('mgmt')

    assert result['status'] == 'ok'
    call_url = mock_get.call_args.args[0]
    assert '/api/dhcp/scopes/enable' in call_url


@patch('technitium.client.requests.get')
def test_disable_scope_success(mock_get):
    mock_get.return_value.status_code = 200
    mock_get.return_value.json.return_value = {'status': 'ok'}

    client = TechnitiumDHCPClient(host="http://10.10.10.2:5380", token="abc123")
    result = client.disable_scope('mgmt')

    assert result['status'] == 'ok'
    call_url = mock_get.call_args.args[0]
    assert '/api/dhcp/scopes/disable' in call_url


def test_enable_scope_requires_name():
    client = TechnitiumDHCPClient(host="http://10.10.10.2:5380", token="abc123")

    with pytest.raises(TechnitiumValidationError) as exc:
        client.enable_scope('')

    assert "Scope name required" in str(exc.value)


def test_disable_scope_requires_name():
    client = TechnitiumDHCPClient(host="http://10.10.10.2:5380", token="abc123")

    with pytest.raises(TechnitiumValidationError) as exc:
        client.disable_scope('')

    assert "Scope name required" in str(exc.value)
