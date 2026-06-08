import pytest
from unittest.mock import patch
import requests
from opnsense.client import RestClient
from opnsense.exceptions import (
    BadRequest,
    Unauthorized,
    ServerError,
)

def test_rest_client_init_with_valid_credentials():
    """RestClient initializes with API key and secret"""
    client = RestClient(
        api_key="test-key",
        api_secret="test-secret",
        url="https://opnsense.local/api"
    )
    assert client.api_key == "test-key"
    assert client.api_secret == "test-secret"
    assert client.url == "https://opnsense.local/api"
    assert client.timeout == 10

def test_rest_client_init_with_custom_timeout():
    """RestClient accepts custom timeout"""
    client = RestClient(
        api_key="key",
        api_secret="secret",
        url="https://opnsense.local/api",
        timeout=20
    )
    assert client.timeout == 20

def test_rest_client_requires_api_key():
    """RestClient requires api_key"""
    with pytest.raises(ValueError):
        RestClient(api_key=None, api_secret="secret", url="https://...")

def test_rest_client_requires_api_secret():
    """RestClient requires api_secret"""
    with pytest.raises(ValueError):
        RestClient(api_key="key", api_secret=None, url="https://...")

def test_rest_client_requires_url():
    """RestClient requires url"""
    with pytest.raises(ValueError):
        RestClient(api_key="key", api_secret="secret", url=None)

@patch('opnsense.client.requests.get')
def test_get_request_success(mock_get):
    """GET request returns JSON response"""
    mock_get.return_value.status_code = 200
    mock_get.return_value.json.return_value = {'status': 'ok'}

    client = RestClient("key", "secret", "https://opnsense.local/api")
    result = client.get('/firewall/rules/get')

    assert result == {'status': 'ok'}
    mock_get.assert_called_once()

@patch('opnsense.client.requests.get')
def test_get_request_with_params(mock_get):
    """GET request includes query parameters"""
    mock_get.return_value.status_code = 200
    mock_get.return_value.json.return_value = {'results': []}

    client = RestClient("key", "secret", "https://opnsense.local/api")
    client.get('/firewall/rules/get', params={'filter': 'enabled'})

    # Verify params were passed
    call_kwargs = mock_get.call_args.kwargs
    assert 'params' in call_kwargs

@patch('opnsense.client.requests.post')
def test_post_request_success(mock_post):
    """POST request returns JSON response"""
    mock_post.return_value.status_code = 200
    mock_post.return_value.json.return_value = {'uuid': 'abc123'}

    client = RestClient("key", "secret", "https://opnsense.local/api")
    result = client.post('/firewall/rules/set', {'name': 'test'})

    assert result == {'uuid': 'abc123'}
    mock_post.assert_called_once()

@patch('opnsense.client.requests.get')
def test_get_request_400_raises_bad_request(mock_get):
    """400 response raises BadRequest exception"""
    mock_get.return_value.status_code = 400
    mock_get.return_value.text = "Bad request"

    client = RestClient("key", "secret", "https://opnsense.local/api")

    with pytest.raises(BadRequest):
        client.get('/firewall/rules/get')

@patch('opnsense.client.requests.get')
def test_get_request_401_raises_unauthorized(mock_get):
    """401 response raises Unauthorized exception"""
    mock_get.return_value.status_code = 401
    mock_get.return_value.text = "Unauthorized"

    client = RestClient("key", "secret", "https://opnsense.local/api")

    with pytest.raises(Unauthorized):
        client.get('/firewall/rules/get')

@patch('opnsense.client.requests.get')
def test_get_request_500_raises_server_error(mock_get):
    """500 response raises ServerError exception"""
    mock_get.return_value.status_code = 500
    mock_get.return_value.text = "Internal server error"

    client = RestClient("key", "secret", "https://opnsense.local/api")

    with pytest.raises(ServerError):
        client.get('/firewall/rules/get')

@patch('opnsense.client.requests.get')
def test_request_timeout_raises_timeout_error(mock_get):
    """Request timeout raises TimeoutError"""
    import requests
    mock_get.side_effect = requests.exceptions.Timeout()

    client = RestClient("key", "secret", "https://opnsense.local/api")

    from opnsense.exceptions import TimeoutError as OPNTimeoutError
    with pytest.raises(OPNTimeoutError):
        client.get('/firewall/rules/get')

def test_basic_auth_header():
    """RestClient uses Basic Auth in requests"""
    import base64

    client = RestClient("my-key", "my-secret", "https://opnsense.local/api")

    expected_auth = base64.b64encode(b"my-key:my-secret").decode('utf-8')
    assert client.auth == ("my-key", "my-secret")
