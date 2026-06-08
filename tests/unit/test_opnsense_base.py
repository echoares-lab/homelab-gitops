import pytest
from unittest.mock import patch, MagicMock
from opnsense.base import BaseClient

def test_base_client_init():
    """BaseClient initializes with credentials"""
    client = BaseClient(
        api_key="key",
        api_secret="secret",
        url="https://opnsense.local/api"
    )

    assert client.api is not None
    assert client.api.api_key == "key"
    assert client.api.api_secret == "secret"

def test_base_client_init_with_timeout():
    """BaseClient accepts custom timeout"""
    client = BaseClient(
        api_key="key",
        api_secret="secret",
        url="https://opnsense.local/api",
        timeout=20
    )

    assert client.api.timeout == 20

@patch('opnsense.client.requests.get')
def test_base_client_get(mock_get):
    """BaseClient.get() delegates to RestClient"""
    mock_get.return_value.status_code = 200
    mock_get.return_value.json.return_value = {'data': 'value'}

    client = BaseClient("key", "secret", "https://opnsense.local/api")
    result = client.get('/test/endpoint')

    assert result == {'data': 'value'}

@patch('opnsense.client.requests.post')
def test_base_client_post(mock_post):
    """BaseClient.post() delegates to RestClient"""
    mock_post.return_value.status_code = 200
    mock_post.return_value.json.return_value = {'uuid': 'abc123'}

    client = BaseClient("key", "secret", "https://opnsense.local/api")
    result = client.post('/test/endpoint', {'name': 'test'})

    assert result == {'uuid': 'abc123'}
