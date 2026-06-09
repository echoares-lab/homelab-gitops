import pytest
from unittest.mock import patch
from technitium.client import TechnitiumRestClient
from technitium.exceptions import (
    TechnitiumError,
    TechnitiumUnauthorized,
    TechnitiumBadRequest,
    TechnitiumServerError,
    TechnitiumTimeoutError,
)


def test_client_init_with_valid_credentials():
    client = TechnitiumRestClient(host="http://10.10.10.2:5380", token="abc123")
    assert client.host == "http://10.10.10.2:5380"
    assert client.token == "abc123"
    assert client.timeout == 10


def test_client_init_custom_timeout():
    client = TechnitiumRestClient(host="http://10.10.10.2:5380", token="abc123", timeout=30)
    assert client.timeout == 30


def test_client_requires_host():
    with pytest.raises(ValueError):
        TechnitiumRestClient(host="", token="abc123")


def test_client_requires_token():
    with pytest.raises(ValueError):
        TechnitiumRestClient(host="http://10.10.10.2:5380", token="")


def test_client_strips_trailing_slash():
    client = TechnitiumRestClient(host="http://10.10.10.2:5380/", token="abc123")
    assert client.host == "http://10.10.10.2:5380"


@patch('technitium.client.requests.get')
def test_get_success_returns_response(mock_get):
    mock_get.return_value.status_code = 200
    mock_get.return_value.json.return_value = {'status': 'ok', 'response': {'scopes': []}}

    client = TechnitiumRestClient(host="http://10.10.10.2:5380", token="abc123")
    result = client.get('/api/dhcp/scopes/list')

    assert result['status'] == 'ok'


@patch('technitium.client.requests.get')
def test_get_includes_token_in_params(mock_get):
    mock_get.return_value.status_code = 200
    mock_get.return_value.json.return_value = {'status': 'ok'}

    client = TechnitiumRestClient(host="http://10.10.10.2:5380", token="mytoken")
    client.get('/api/dhcp/scopes/list')

    call_kwargs = mock_get.call_args.kwargs
    assert call_kwargs['params']['token'] == 'mytoken'


@patch('technitium.client.requests.get')
def test_get_401_raises_unauthorized(mock_get):
    mock_get.return_value.status_code = 401
    mock_get.return_value.text = "Unauthorized"

    client = TechnitiumRestClient(host="http://10.10.10.2:5380", token="abc123")

    with pytest.raises(TechnitiumUnauthorized):
        client.get('/api/dhcp/scopes/list')


@patch('technitium.client.requests.get')
def test_get_500_raises_server_error(mock_get):
    mock_get.return_value.status_code = 500
    mock_get.return_value.text = "Internal server error"

    client = TechnitiumRestClient(host="http://10.10.10.2:5380", token="abc123")

    with pytest.raises(TechnitiumServerError):
        client.get('/api/dhcp/scopes/list')


@patch('technitium.client.requests.get')
def test_get_api_error_status_raises(mock_get):
    mock_get.return_value.status_code = 200
    mock_get.return_value.json.return_value = {
        'status': 'error',
        'errorMessage': 'Scope not found'
    }

    client = TechnitiumRestClient(host="http://10.10.10.2:5380", token="abc123")

    with pytest.raises(TechnitiumError) as exc:
        client.get('/api/dhcp/scopes/enable', {'name': 'nonexistent'})

    assert 'Scope not found' in str(exc.value)


@patch('technitium.client.requests.get')
def test_get_timeout_raises_timeout_error(mock_get):
    import requests as req
    mock_get.side_effect = req.exceptions.Timeout()

    client = TechnitiumRestClient(host="http://10.10.10.2:5380", token="abc123")

    with pytest.raises(TechnitiumTimeoutError):
        client.get('/api/dhcp/scopes/list')
