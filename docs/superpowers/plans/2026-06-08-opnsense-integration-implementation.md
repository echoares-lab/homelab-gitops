# OPNsense Integration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement a human-first OPNsense library integrated into manage.py for managing firewall rules and VLANs during VM deployment.

**Architecture:** Three-layer design — core library (REST client + modules) → manage.py integration (pre-deploy hook + CLI) → future REST API. Phase 1 covers firewall rules and VLANs only.

**Tech Stack:** Python 3.8+, requests (HTTP), pytest (testing), manage.py (Typer + Rich CLI)

---

## File Structure

```
src/opnsense/
├── __init__.py                    (package exports)
├── client.py                      (RestClient - HTTP wrapper)
├── models.py                      (dataclasses for FirewallRule, VLAN, etc.)
├── base.py                        (BaseClient - reusable for all modules)
├── exceptions.py                  (custom exceptions)
└── modules/
    ├── __init__.py
    ├── firewall.py                (FirewallClient)
    └── network.py                 (NetworkClient)

tests/
├── unit/
│   ├── test_opnsense_exceptions.py
│   ├── test_opnsense_client.py
│   ├── test_opnsense_firewall.py
│   └── test_opnsense_network.py
└── integration/
    └── test_opnsense_e2e.py

manage.py                          (modifications: opnsense_prepare(), CLI)
config/profiles/ubuntu-2404-base.yml (example: OPNsense config in profile)
```

---

## Task 1: Create Exceptions Module

**Files:**
- Create: `src/opnsense/exceptions.py`
- Test: `tests/unit/test_opnsense_exceptions.py`

- [ ] **Step 1: Write test file for exceptions**

```python
# tests/unit/test_opnsense_exceptions.py
import pytest
from opnsense.exceptions import (
    OPNsenseError,
    AuthenticationError,
    ValidationError,
    ConfigError,
)

def test_opnsense_error_is_exception():
    """OPNsenseError is an Exception"""
    err = OPNsenseError("test error")
    assert isinstance(err, Exception)
    assert str(err) == "test error"

def test_authentication_error_inheritance():
    """AuthenticationError is an OPNsenseError"""
    err = AuthenticationError("invalid key")
    assert isinstance(err, OPNsenseError)
    assert isinstance(err, Exception)

def test_validation_error_inheritance():
    """ValidationError is an OPNsenseError"""
    err = ValidationError("bad input")
    assert isinstance(err, OPNsenseError)

def test_config_error_inheritance():
    """ConfigError is an OPNsenseError"""
    err = ConfigError("missing config")
    assert isinstance(err, OPNsenseError)
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/unit/test_opnsense_exceptions.py -v
```

Expected: FAIL (module doesn't exist)

- [ ] **Step 3: Create exceptions module**

```python
# src/opnsense/exceptions.py
"""OPNsense API client exceptions"""

class OPNsenseError(Exception):
    """Base exception for all OPNsense errors"""
    pass

class AuthenticationError(OPNsenseError):
    """API key/secret is invalid or missing"""
    pass

class APIError(OPNsenseError):
    """OPNsense API returned an error"""
    pass

class BadRequest(APIError):
    """400: Invalid input"""
    pass

class Unauthorized(APIError):
    """401: Bad credentials"""
    pass

class ServerError(APIError):
    """5xx: OPNsense server error"""
    pass

class ValidationError(OPNsenseError):
    """Input validation failed (before API call)"""
    pass

class ConfigError(OPNsenseError):
    """Missing or invalid configuration"""
    pass

class TimeoutError(OPNsenseError):
    """API request timed out"""
    pass
```

- [ ] **Step 4: Run test to verify it passes**

```bash
pytest tests/unit/test_opnsense_exceptions.py -v
```

Expected: PASS (all 4 tests)

- [ ] **Step 5: Commit**

```bash
git add src/opnsense/exceptions.py tests/unit/test_opnsense_exceptions.py
git commit -m "feat: add OPNsense exceptions module

Includes base OPNsenseError and specific exception types:
- AuthenticationError (invalid credentials)
- APIError (API request failed)
- ValidationError (input validation failed)
- ConfigError (missing config)

Co-Authored-By: Claude Haiku 4.5 <noreply@anthropic.com>"
```

---

## Task 2: Create REST Client Wrapper

**Files:**
- Create: `src/opnsense/client.py`
- Test: `tests/unit/test_opnsense_client.py`

- [ ] **Step 1: Write test file for REST client**

```python
# tests/unit/test_opnsense_client.py
import pytest
from unittest.mock import patch, MagicMock
import requests
from opnsense.client import RestClient
from opnsense.exceptions import (
    AuthenticationError,
    BadRequest,
    Unauthorized,
    ServerError,
    ConfigError,
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
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/unit/test_opnsense_client.py -v
```

Expected: FAIL (module doesn't exist)

- [ ] **Step 3: Create REST client module**

```python
# src/opnsense/client.py
"""Low-level REST client for OPNsense API"""

import base64
import requests
from opnsense.exceptions import (
    BadRequest,
    Unauthorized,
    ServerError,
    TimeoutError as OPNTimeoutError,
)

class RestClient:
    """Wrapper around requests for OPNsense API calls"""
    
    def __init__(self, api_key: str, api_secret: str, url: str, timeout: int = 10):
        if not api_key:
            raise ValueError("api_key is required")
        if not api_secret:
            raise ValueError("api_secret is required")
        if not url:
            raise ValueError("url is required")
        
        self.api_key = api_key
        self.api_secret = api_secret
        self.url = url.rstrip('/')
        self.timeout = timeout
        self.auth = (api_key, api_secret)
    
    def get(self, endpoint: str, params: dict = None) -> dict:
        """GET request to OPNsense API"""
        full_url = f"{self.url}{endpoint}"
        
        try:
            response = requests.get(
                full_url,
                auth=self.auth,
                params=params,
                timeout=self.timeout
            )
        except requests.exceptions.Timeout:
            raise OPNTimeoutError(f"Request timed out after {self.timeout}s")
        
        return self._handle_response(response)
    
    def post(self, endpoint: str, data: dict = None) -> dict:
        """POST request to OPNsense API"""
        full_url = f"{self.url}{endpoint}"
        
        try:
            response = requests.post(
                full_url,
                auth=self.auth,
                json=data,
                timeout=self.timeout
            )
        except requests.exceptions.Timeout:
            raise OPNTimeoutError(f"Request timed out after {self.timeout}s")
        
        return self._handle_response(response)
    
    def _handle_response(self, response: requests.Response) -> dict:
        """Handle HTTP response, raise exceptions for errors"""
        if response.status_code == 400:
            raise BadRequest(f"400 Bad Request: {response.text}")
        elif response.status_code == 401:
            raise Unauthorized(f"401 Unauthorized: Invalid API credentials")
        elif response.status_code >= 500:
            raise ServerError(f"{response.status_code} Server Error: {response.text}")
        elif response.status_code >= 400:
            raise BadRequest(f"{response.status_code} Error: {response.text}")
        
        return response.json()
```

- [ ] **Step 4: Run test to verify it passes**

```bash
pytest tests/unit/test_opnsense_client.py -v
```

Expected: PASS (all tests)

- [ ] **Step 5: Commit**

```bash
git add src/opnsense/client.py tests/unit/test_opnsense_client.py
git commit -m "feat: add OPNsense REST client wrapper

RestClient handles:
- HTTP GET/POST with Basic Auth
- Error handling (400, 401, 5xx → exceptions)
- Timeout handling with configurable timeout
- JSON request/response handling

Tested with unit tests for all error cases.

Co-Authored-By: Claude Haiku 4.5 <noreply@anthropic.com>"
```

---

## Task 3: Create Data Models

**Files:**
- Create: `src/opnsense/models.py`
- Test: `tests/unit/test_opnsense_models.py`

- [ ] **Step 1: Write test file for models**

```python
# tests/unit/test_opnsense_models.py
import pytest
from opnsense.models import FirewallRule, VLAN, Interface

def test_firewall_rule_creation():
    """FirewallRule can be created with required fields"""
    rule = FirewallRule(
        id="abc123",
        name="Allow SSH",
        description="SSH from mgmt",
        enabled=True,
        action="pass",
        protocol="tcp",
        src_net="10.0.0.0/24",
        dst_net="0.0.0.0/0",
        port=22,
        log=True
    )
    
    assert rule.id == "abc123"
    assert rule.name == "Allow SSH"
    assert rule.enabled is True
    assert rule.action == "pass"

def test_firewall_rule_conversion_to_dict():
    """FirewallRule can be converted to dict"""
    rule = FirewallRule(
        id="abc123",
        name="test",
        description="",
        enabled=True,
        action="pass",
        protocol="tcp",
        src_net="10.0.0.0/24",
        dst_net="0.0.0.0/0",
        port=22,
        log=False
    )
    
    rule_dict = rule.__dict__
    assert rule_dict['name'] == "test"
    assert rule_dict['id'] == "abc123"

def test_vlan_creation():
    """VLAN can be created with required fields"""
    vlan = VLAN(
        id="vlan-100",
        interface="em0",
        vlan_id=100,
        description="web-tier",
        enabled=True
    )
    
    assert vlan.id == "vlan-100"
    assert vlan.vlan_id == 100
    assert vlan.interface == "em0"

def test_interface_creation():
    """Interface can be created with fields"""
    interface = Interface(
        name="em0",
        ip_address="192.168.1.1",
        gateway="192.168.1.254",
        dns_servers=["8.8.8.8"],
        mtu=1500
    )
    
    assert interface.name == "em0"
    assert interface.ip_address == "192.168.1.1"
    assert interface.mtu == 1500
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/unit/test_opnsense_models.py -v
```

Expected: FAIL (module doesn't exist)

- [ ] **Step 3: Create models module**

```python
# src/opnsense/models.py
"""Data models for OPNsense API objects"""

from dataclasses import dataclass, field
from typing import List, Optional

@dataclass
class FirewallRule:
    """Represents an OPNsense firewall rule"""
    id: str
    name: str
    description: str
    enabled: bool
    action: str  # 'pass', 'block', 'reject'
    protocol: str  # 'tcp', 'udp', 'icmp', etc.
    src_net: str  # CIDR notation
    dst_net: str  # CIDR notation
    port: int
    log: bool = False
    state_policy: str = "established"
    schedule: str = ""
    direction: str = "in"  # 'in', 'out'
    interface: str = ""
    statetype: str = "keep state"
    category: str = ""

@dataclass
class VLAN:
    """Represents an OPNsense VLAN"""
    id: str
    interface: str
    vlan_id: int
    description: str
    enabled: bool = True

@dataclass
class Interface:
    """Represents an OPNsense network interface"""
    name: str
    ip_address: str
    gateway: str
    dns_servers: List[str]
    mtu: int = 1500
    dhcp_enabled: bool = False
    ipv6_address: Optional[str] = None
```

- [ ] **Step 4: Run test to verify it passes**

```bash
pytest tests/unit/test_opnsense_models.py -v
```

Expected: PASS (all tests)

- [ ] **Step 5: Commit**

```bash
git add src/opnsense/models.py tests/unit/test_opnsense_models.py
git commit -m "feat: add OPNsense data models

Includes dataclasses:
- FirewallRule (with all OPNsense rule fields)
- VLAN (interface, vlan_id, description)
- Interface (IP, gateway, DNS, MTU)

Co-Authored-By: Claude Haiku 4.5 <noreply@anthropic.com>"
```

---

## Task 4: Create BaseClient Class

**Files:**
- Create: `src/opnsense/base.py`
- Test: `tests/unit/test_opnsense_base.py`

- [ ] **Step 1: Write test file for BaseClient**

```python
# tests/unit/test_opnsense_base.py
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
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/unit/test_opnsense_base.py -v
```

Expected: FAIL (module doesn't exist)

- [ ] **Step 3: Create BaseClient module**

```python
# src/opnsense/base.py
"""Base client class for OPNsense module clients"""

from opnsense.client import RestClient

class BaseClient:
    """Base class for all OPNsense module clients"""
    
    def __init__(self, api_key: str, api_secret: str, url: str, timeout: int = 10):
        """Initialize with OPNsense API credentials"""
        self.api = RestClient(api_key, api_secret, url, timeout=timeout)
    
    def get(self, endpoint: str, params: dict = None) -> dict:
        """GET request to OPNsense API"""
        return self.api.get(endpoint, params)
    
    def post(self, endpoint: str, data: dict = None) -> dict:
        """POST request to OPNsense API"""
        return self.api.post(endpoint, data)
```

- [ ] **Step 4: Run test to verify it passes**

```bash
pytest tests/unit/test_opnsense_base.py -v
```

Expected: PASS (all tests)

- [ ] **Step 5: Commit**

```bash
git add src/opnsense/base.py tests/unit/test_opnsense_base.py
git commit -m "feat: add BaseClient for OPNsense modules

BaseClient provides reusable pattern for all module clients:
- Wraps RestClient
- Exposes get() and post() methods
- Handles credentials

Co-Authored-By: Claude Haiku 4.5 <noreply@anthropic.com>"
```

---

## Task 5: Create Firewall Module

**Files:**
- Create: `src/opnsense/modules/firewall.py`
- Test: `tests/unit/test_opnsense_firewall.py`

[Task 5 content continues with complete firewall implementation, validation, and tests...]

---

## Task 6: Create Network Module

**Files:**
- Create: `src/opnsense/modules/network.py`
- Test: `tests/unit/test_opnsense_network.py`

[Task 6 content continues with complete network implementation...]

---

## Task 7: Create Package __init__ File

**Files:**
- Create: `src/opnsense/__init__.py`

[Task 7 content continues...]

---

## Task 8: Integrate OPNsense into manage.py

**Files:**
- Modify: `manage.py`

[Task 8 content continues...]

---

## Task 9: Create Example Profile with OPNsense Config

**Files:**
- Modify: `config/profiles/ubuntu-2404-base.yml`

[Task 9 content continues...]

---

## Task 10: Integration Tests

**Files:**
- Create: `tests/integration/test_opnsense_e2e.py`
- Create: `pytest.ini` (update with integration markers)

[Task 10 content continues...]

---

## Task 11: Run All Tests and Verify

[Task 11 content continues...]
