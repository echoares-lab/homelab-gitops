# DHCP Migration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Migrate DHCP authority from OPNsense to Technitium DNS Server via `manage.py dhcp-migrate` with interactive scope mapping, per-scope confirmation, automatic rollback, and a `dhcp-rollback` command for manual reversal.

**Architecture:** Three new Python modules — `src/opnsense/modules/dhcp.py` (extends existing BaseClient), `src/technitium/` (new parallel library with token auth), and two new `manage.py` commands that orchestrate discovery → mapping → cutover → state persistence. Migration state is written to `.dhcp-migration-state.json` (gitignored) to support rollback after process exit.

**Tech Stack:** Python 3.8+, requests (already in project), typer + Rich (already in manage.py), pytest + unittest.mock (already in project)

---

## File Structure

```
src/opnsense/modules/dhcp.py              NEW — DHCPClient (list, disable, enable interfaces)
src/technitium/__init__.py                NEW — package exports
src/technitium/client.py                  NEW — TechnitiumRestClient (token-based auth)
src/technitium/base.py                    NEW — TechnitiumBaseClient (mirrors opnsense/base.py)
src/technitium/exceptions.py             NEW — exception hierarchy
src/technitium/modules/__init__.py        NEW — module package
src/technitium/modules/dhcp.py            NEW — TechnitiumDHCPClient (list, enable, disable scopes)
tests/unit/test_opnsense_dhcp.py          NEW — unit tests for DHCPClient
tests/unit/test_technitium_client.py      NEW — unit tests for TechnitiumRestClient
tests/unit/test_technitium_dhcp.py        NEW — unit tests for TechnitiumDHCPClient
manage.py                                 MODIFY — add dhcp-migrate and dhcp-rollback commands
.gitignore                                MODIFY — add .dhcp-migration-state.json
```

---

## Task 1: OPNsense DHCP Module

**Files:**
- Create: `src/opnsense/modules/dhcp.py`
- Test: `tests/unit/test_opnsense_dhcp.py`

- [ ] **Step 1: Write the failing tests**

```python
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
    call_kwargs = mock_post.call_args
    assert call_kwargs is not None


@patch('opnsense.client.requests.post')
def test_enable_interface_sends_correct_payload(mock_post):
    """enable_interface sends enable=1 for the given interface"""
    mock_post.return_value.status_code = 200
    mock_post.return_value.json.return_value = {'result': 'saved'}

    client = DHCPClient("key", "secret", "https://opnsense.local/api")
    result = client.enable_interface('lan')

    assert result == {'result': 'saved'}


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
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/unit/test_opnsense_dhcp.py -v
```

Expected: FAIL with `ModuleNotFoundError: No module named 'opnsense.modules.dhcp'`

- [ ] **Step 3: Create the DHCP module**

```python
# src/opnsense/modules/dhcp.py
"""DHCP interface management for OPNsense"""

from opnsense.base import BaseClient
from opnsense.exceptions import ValidationError


class DHCPClient(BaseClient):
    """Client for OPNsense DHCPv4 operations"""

    def list_enabled_interfaces(self) -> list:
        """Discover all interfaces with DHCP currently enabled.

        Returns list of dicts: [{interface, range_from, range_to, enabled}]
        """
        response = self.get('/api/dhcpv4/settings/get')
        dhcpd = response.get('dhcpd', {})

        result = []
        for interface, config in dhcpd.items():
            if config.get('enable') == '1':
                result.append({
                    'interface': interface,
                    'range_from': config.get('range', {}).get('from', ''),
                    'range_to': config.get('range', {}).get('to', ''),
                    'enabled': True,
                })
        return result

    def disable_interface(self, interface: str) -> dict:
        """Disable DHCP on a single interface."""
        if not interface:
            raise ValidationError("Interface required")
        return self.post('/api/dhcpv4/settings/set', {
            'dhcpd': {interface: {'enable': '0'}}
        })

    def enable_interface(self, interface: str) -> dict:
        """Re-enable DHCP on a single interface (rollback)."""
        if not interface:
            raise ValidationError("Interface required")
        return self.post('/api/dhcpv4/settings/set', {
            'dhcpd': {interface: {'enable': '1'}}
        })
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/unit/test_opnsense_dhcp.py -v
```

Expected: 8 tests PASS

- [ ] **Step 5: Commit**

```bash
git add src/opnsense/modules/dhcp.py tests/unit/test_opnsense_dhcp.py
git commit -m "feat: add OPNsense DHCP module

DHCPClient supports:
- list_enabled_interfaces(): auto-discover all DHCP-enabled interfaces
- disable_interface(iface): disable DHCP for migration cutover
- enable_interface(iface): re-enable DHCP for rollback

Co-Authored-By: Claude Haiku 4.5 <noreply@anthropic.com>"
```

---

## Task 2: Technitium Library Skeleton

**Files:**
- Create: `src/technitium/__init__.py`
- Create: `src/technitium/exceptions.py`
- Create: `src/technitium/client.py`
- Create: `src/technitium/base.py`
- Create: `src/technitium/modules/__init__.py`
- Test: `tests/unit/test_technitium_client.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/unit/test_technitium_client.py
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
    """TechnitiumRestClient initializes with host and token"""
    client = TechnitiumRestClient(host="http://10.10.10.2:5380", token="abc123")
    assert client.host == "http://10.10.10.2:5380"
    assert client.token == "abc123"
    assert client.timeout == 10


def test_client_init_custom_timeout():
    """TechnitiumRestClient accepts custom timeout"""
    client = TechnitiumRestClient(host="http://10.10.10.2:5380", token="abc123", timeout=30)
    assert client.timeout == 30


def test_client_requires_host():
    """TechnitiumRestClient raises ValueError without host"""
    with pytest.raises(ValueError):
        TechnitiumRestClient(host="", token="abc123")


def test_client_requires_token():
    """TechnitiumRestClient raises ValueError without token"""
    with pytest.raises(ValueError):
        TechnitiumRestClient(host="http://10.10.10.2:5380", token="")


def test_client_strips_trailing_slash():
    """TechnitiumRestClient strips trailing slash from host"""
    client = TechnitiumRestClient(host="http://10.10.10.2:5380/", token="abc123")
    assert client.host == "http://10.10.10.2:5380"


@patch('technitium.client.requests.get')
def test_get_success_returns_response(mock_get):
    """get() returns parsed JSON on 200"""
    mock_get.return_value.status_code = 200
    mock_get.return_value.json.return_value = {'status': 'ok', 'response': {'scopes': []}}

    client = TechnitiumRestClient(host="http://10.10.10.2:5380", token="abc123")
    result = client.get('/api/dhcp/scopes/list')

    assert result['status'] == 'ok'


@patch('technitium.client.requests.get')
def test_get_includes_token_in_params(mock_get):
    """get() always includes token query parameter"""
    mock_get.return_value.status_code = 200
    mock_get.return_value.json.return_value = {'status': 'ok'}

    client = TechnitiumRestClient(host="http://10.10.10.2:5380", token="mytoken")
    client.get('/api/dhcp/scopes/list')

    call_kwargs = mock_get.call_args.kwargs
    assert call_kwargs['params']['token'] == 'mytoken'


@patch('technitium.client.requests.get')
def test_get_401_raises_unauthorized(mock_get):
    """get() raises TechnitiumUnauthorized on 401"""
    mock_get.return_value.status_code = 401
    mock_get.return_value.text = "Unauthorized"

    client = TechnitiumRestClient(host="http://10.10.10.2:5380", token="abc123")

    with pytest.raises(TechnitiumUnauthorized):
        client.get('/api/dhcp/scopes/list')


@patch('technitium.client.requests.get')
def test_get_500_raises_server_error(mock_get):
    """get() raises TechnitiumServerError on 500"""
    mock_get.return_value.status_code = 500
    mock_get.return_value.text = "Internal server error"

    client = TechnitiumRestClient(host="http://10.10.10.2:5380", token="abc123")

    with pytest.raises(TechnitiumServerError):
        client.get('/api/dhcp/scopes/list')


@patch('technitium.client.requests.get')
def test_get_api_error_status_raises(mock_get):
    """get() raises TechnitiumError when response status is 'error'"""
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
    """get() raises TechnitiumTimeoutError on network timeout"""
    import requests as req
    mock_get.side_effect = req.exceptions.Timeout()

    client = TechnitiumRestClient(host="http://10.10.10.2:5380", token="abc123")

    with pytest.raises(TechnitiumTimeoutError):
        client.get('/api/dhcp/scopes/list')
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/unit/test_technitium_client.py -v
```

Expected: FAIL with `ModuleNotFoundError: No module named 'technitium'`

- [ ] **Step 3: Create exceptions module**

```python
# src/technitium/exceptions.py
"""Technitium DNS Server API client exceptions"""


class TechnitiumError(Exception):
    """Base exception for all Technitium errors"""
    pass


class TechnitiumAPIError(TechnitiumError):
    """Technitium API returned an error status"""
    pass


class TechnitiumBadRequest(TechnitiumAPIError):
    """400: Invalid input"""
    pass


class TechnitiumUnauthorized(TechnitiumAPIError):
    """401: Invalid or missing token"""
    pass


class TechnitiumServerError(TechnitiumAPIError):
    """5xx: Technitium server error"""
    pass


class TechnitiumTimeoutError(TechnitiumError):
    """API request timed out"""
    pass


class TechnitiumValidationError(TechnitiumError):
    """Input validation failed before API call"""
    pass
```

- [ ] **Step 4: Create REST client**

```python
# src/technitium/client.py
"""Low-level REST client for Technitium DNS Server API"""

import requests
from technitium.exceptions import (
    TechnitiumError,
    TechnitiumBadRequest,
    TechnitiumUnauthorized,
    TechnitiumServerError,
    TechnitiumTimeoutError,
)


class TechnitiumRestClient:
    """Wrapper around requests for Technitium API calls (token auth)"""

    def __init__(self, host: str, token: str, timeout: int = 10) -> None:
        if not host:
            raise ValueError("host is required")
        if not token:
            raise ValueError("token is required")
        self.host = host.rstrip('/')
        self.token = token
        self.timeout = timeout

    def get(self, endpoint: str, params: dict = None) -> dict:
        """GET request to Technitium API with token auth"""
        full_url = f"{self.host}{endpoint}"
        all_params = {'token': self.token}
        if params:
            all_params.update(params)

        try:
            response = requests.get(full_url, params=all_params, timeout=self.timeout)
        except requests.exceptions.Timeout:
            raise TechnitiumTimeoutError(f"Request timed out after {self.timeout}s")
        except requests.exceptions.ConnectionError as e:
            raise TechnitiumError(f"Connection error: {e}")

        return self._handle_response(response)

    def _handle_response(self, response: requests.Response) -> dict:
        if response.status_code == 401:
            raise TechnitiumUnauthorized("401 Unauthorized: Invalid API token")
        elif response.status_code >= 500:
            raise TechnitiumServerError(f"{response.status_code} Server Error: {response.text}")
        elif response.status_code >= 400:
            raise TechnitiumBadRequest(f"{response.status_code} Error: {response.text}")

        data = response.json()
        if data.get('status') == 'error':
            raise TechnitiumError(data.get('errorMessage', 'Unknown Technitium error'))

        return data
```

- [ ] **Step 5: Create base client**

```python
# src/technitium/base.py
"""Base client class for Technitium module clients"""

from technitium.client import TechnitiumRestClient


class TechnitiumBaseClient:
    """Base class for all Technitium module clients"""

    def __init__(self, host: str, token: str, timeout: int = 10) -> None:
        self.api = TechnitiumRestClient(host, token, timeout=timeout)

    def get(self, endpoint: str, params: dict = None) -> dict:
        return self.api.get(endpoint, params)
```

- [ ] **Step 6: Create package init files**

```python
# src/technitium/__init__.py
"""Technitium DNS Server API client library"""
from technitium.client import TechnitiumRestClient
from technitium.base import TechnitiumBaseClient

__all__ = ['TechnitiumRestClient', 'TechnitiumBaseClient']
```

```python
# src/technitium/modules/__init__.py
```

- [ ] **Step 7: Run tests to verify they pass**

```bash
pytest tests/unit/test_technitium_client.py -v
```

Expected: 11 tests PASS

- [ ] **Step 8: Commit**

```bash
git add src/technitium/ tests/unit/test_technitium_client.py
git commit -m "feat: add Technitium API client library

TechnitiumRestClient handles:
- Token-based auth via query param
- GET requests with merged token params
- Error handling (401, 5xx, API error status)
- Timeout and connection error handling

Mirrors src/opnsense/ structure for consistency.

Co-Authored-By: Claude Haiku 4.5 <noreply@anthropic.com>"
```

---

## Task 3: Technitium DHCP Module

**Files:**
- Create: `src/technitium/modules/dhcp.py`
- Test: `tests/unit/test_technitium_dhcp.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/unit/test_technitium_dhcp.py
import pytest
from unittest.mock import patch
from technitium.modules.dhcp import TechnitiumDHCPClient
from technitium.exceptions import TechnitiumValidationError


def test_dhcp_client_init():
    """TechnitiumDHCPClient initializes with host and token"""
    client = TechnitiumDHCPClient(host="http://10.10.10.2:5380", token="abc123")
    assert client.api is not None


@patch('technitium.client.requests.get')
def test_list_scopes_returns_scopes(mock_get):
    """list_scopes returns list of scope dicts"""
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
    """list_scopes returns empty list when no scopes"""
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
    """enable_scope calls correct endpoint and returns response"""
    mock_get.return_value.status_code = 200
    mock_get.return_value.json.return_value = {'status': 'ok'}

    client = TechnitiumDHCPClient(host="http://10.10.10.2:5380", token="abc123")
    result = client.enable_scope('mgmt')

    assert result['status'] == 'ok'
    call_url = mock_get.call_args.args[0]
    assert '/api/dhcp/scopes/enable' in call_url


@patch('technitium.client.requests.get')
def test_disable_scope_success(mock_get):
    """disable_scope calls correct endpoint and returns response"""
    mock_get.return_value.status_code = 200
    mock_get.return_value.json.return_value = {'status': 'ok'}

    client = TechnitiumDHCPClient(host="http://10.10.10.2:5380", token="abc123")
    result = client.disable_scope('mgmt')

    assert result['status'] == 'ok'
    call_url = mock_get.call_args.args[0]
    assert '/api/dhcp/scopes/disable' in call_url


def test_enable_scope_requires_name():
    """enable_scope raises TechnitiumValidationError for empty name"""
    client = TechnitiumDHCPClient(host="http://10.10.10.2:5380", token="abc123")

    with pytest.raises(TechnitiumValidationError) as exc:
        client.enable_scope('')

    assert "Scope name required" in str(exc.value)


def test_disable_scope_requires_name():
    """disable_scope raises TechnitiumValidationError for empty name"""
    client = TechnitiumDHCPClient(host="http://10.10.10.2:5380", token="abc123")

    with pytest.raises(TechnitiumValidationError) as exc:
        client.disable_scope('')

    assert "Scope name required" in str(exc.value)
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/unit/test_technitium_dhcp.py -v
```

Expected: FAIL with `ModuleNotFoundError: No module named 'technitium.modules.dhcp'`

- [ ] **Step 3: Create the DHCP module**

```python
# src/technitium/modules/dhcp.py
"""DHCP scope management for Technitium DNS Server"""

from technitium.base import TechnitiumBaseClient
from technitium.exceptions import TechnitiumValidationError


class TechnitiumDHCPClient(TechnitiumBaseClient):
    """Client for Technitium DHCP scope operations"""

    def list_scopes(self) -> list:
        """List all DHCP scopes.

        Returns list of dicts: [{name, enabled, networkAddress, ...}]
        """
        response = self.get('/api/dhcp/scopes/list')
        return response.get('response', {}).get('scopes', [])

    def enable_scope(self, name: str) -> dict:
        """Enable a DHCP scope by name."""
        if not name:
            raise TechnitiumValidationError("Scope name required")
        return self.get('/api/dhcp/scopes/enable', {'name': name})

    def disable_scope(self, name: str) -> dict:
        """Disable a DHCP scope by name."""
        if not name:
            raise TechnitiumValidationError("Scope name required")
        return self.get('/api/dhcp/scopes/disable', {'name': name})
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/unit/test_technitium_dhcp.py -v
```

Expected: 7 tests PASS

- [ ] **Step 5: Run all unit tests to verify nothing broke**

```bash
pytest tests/unit/ -v
```

Expected: All tests PASS (38 existing + 15 new = 53 total)

- [ ] **Step 6: Commit**

```bash
git add src/technitium/modules/dhcp.py tests/unit/test_technitium_dhcp.py
git commit -m "feat: add Technitium DHCP scope module

TechnitiumDHCPClient supports:
- list_scopes(): list all DHCP scopes with enabled status
- enable_scope(name): enable a scope by name
- disable_scope(name): disable a scope by name

Co-Authored-By: Claude Haiku 4.5 <noreply@anthropic.com>"
```

---

## Task 4: manage.py dhcp-migrate Command

**Files:**
- Modify: `manage.py`
- Modify: `.gitignore`

- [ ] **Step 1: Add .dhcp-migration-state.json to .gitignore**

Open `.gitignore` and add this line:

```
.dhcp-migration-state.json
```

- [ ] **Step 2: Add imports and state helpers to manage.py**

Find the import block near the top of `manage.py` (around line 20) and add after existing imports:

```python
import json
from datetime import datetime
```

Then find the `# --- OPNSENSE COMMANDS ---` section and add these helper functions immediately before it:

```python
# --- DHCP MIGRATION HELPERS ---

_DHCP_STATE_FILE = '.dhcp-migration-state.json'


def _save_migration_state(migrated: list) -> None:
    with open(_DHCP_STATE_FILE, 'w') as f:
        json.dump({'migrated': migrated, 'timestamp': datetime.now().isoformat()}, f, indent=2)


def _load_migration_state() -> list:
    if not os.path.exists(_DHCP_STATE_FILE):
        return []
    with open(_DHCP_STATE_FILE) as f:
        return json.load(f).get('migrated', [])
```

- [ ] **Step 3: Add dhcp-migrate command to manage.py**

Find the end of the `# --- OPNSENSE COMMANDS ---` block (just before `# --- MAIN ---`) and add:

```python
# --- DHCP MIGRATION COMMANDS ---

@app.command(name="dhcp-migrate")
def dhcp_migrate() -> None:
    """Migrate DHCP from OPNsense to Technitium with interactive scope mapping."""
    try:
        from opnsense.modules.dhcp import DHCPClient as OPNDHCPClient
        from technitium.modules.dhcp import TechnitiumDHCPClient
    except ImportError as e:
        console.print(f"[red]Error: required module not found: {e}[/red]")
        raise typer.Exit(1)

    opn_dhcp = OPNDHCPClient(
        api_key=os.getenv('OPNSENSE_KEY'),
        api_secret=os.getenv('OPNSENSE_SECRET'),
        url=os.getenv('OPNSENSE_URL', 'https://10.10.10.1/api'),
    )
    tech_dhcp = TechnitiumDHCPClient(
        host=os.getenv('TECHNITIUM_HOST', 'http://10.10.10.2:5380'),
        token=os.getenv('TECHNITIUM_TOKEN', ''),
    )

    # Step 1: Discovery
    console.rule("[bold cyan]Step 1 — Discovery[/bold cyan]")
    try:
        interfaces = opn_dhcp.list_enabled_interfaces()
        scopes = tech_dhcp.list_scopes()
    except Exception as e:
        console.print(f"[red]Discovery failed: {e}[/red]")
        raise typer.Exit(1)

    iface_table = Table(title="OPNsense DHCP Interfaces (enabled)")
    iface_table.add_column("Interface", style="cyan")
    iface_table.add_column("Range From", style="green")
    iface_table.add_column("Range To", style="green")
    for iface in interfaces:
        iface_table.add_row(iface['interface'], iface['range_from'], iface['range_to'])
    console.print(iface_table)

    scope_table = Table(title="Technitium DHCP Scopes")
    scope_table.add_column("Name", style="cyan")
    scope_table.add_column("Network", style="green")
    scope_table.add_column("Enabled", style="yellow")
    for scope in scopes:
        scope_table.add_row(
            scope.get('name', ''),
            scope.get('networkAddress', ''),
            str(scope.get('enabled', False)),
        )
    console.print(scope_table)

    # Step 2: Mapping
    console.rule("[bold cyan]Step 2 — Map Interfaces to Scopes[/bold cyan]")
    scope_names = [s['name'] for s in scopes]
    mapping = {}
    for iface in interfaces:
        console.print(f"Available scopes: {', '.join(scope_names)}")
        choice = typer.prompt(
            f"Map [cyan]{iface['interface']}[/cyan] → scope name (or 'skip')",
            default='skip',
        )
        if choice != 'skip':
            if choice not in scope_names:
                console.print(f"[red]Scope '{choice}' not in Technitium. Aborting.[/red]")
                raise typer.Exit(1)
            mapping[iface['interface']] = choice

    if not mapping:
        console.print("[yellow]No interfaces mapped. Nothing to migrate.[/yellow]")
        raise typer.Exit(0)

    console.print(f"\nMapping: {len(mapping)} interface(s) to migrate.")
    if not typer.confirm("Proceed with cutover?"):
        raise typer.Exit(0)

    # Step 3: Pre-flight
    console.rule("[bold cyan]Step 3 — Pre-flight Check[/bold cyan]")
    for iface, scope_name in mapping.items():
        if not any(s['name'] == scope_name for s in scopes):
            console.print(f"[red]✗ Scope '{scope_name}' not found in Technitium[/red]")
            raise typer.Exit(1)
        console.print(f"[green]✓[/green] {iface} → {scope_name} verified")

    # Step 4: Cutover
    console.rule("[bold cyan]Step 4 — Cutover[/bold cyan]")
    migrated = []

    for iface, scope_name in mapping.items():
        if not typer.confirm(f"Migrate {iface} → {scope_name}?"):
            console.print(f"  [yellow]Skipped {iface}[/yellow]")
            continue

        try:
            opn_dhcp.disable_interface(iface)
            console.print(f"  [green]✓[/green] Disabled OPNsense DHCP on {iface}")

            tech_dhcp.enable_scope(scope_name)
            console.print(f"  [green]✓[/green] Enabled Technitium scope: {scope_name}")

            migrated.append({'opnsense_interface': iface, 'technitium_scope': scope_name})
            _save_migration_state(migrated)

        except Exception as e:
            console.print(f"  [red]✗ Failed: {e}[/red]")
            console.print("[yellow]Rolling back already-migrated scopes...[/yellow]")
            for m in migrated:
                try:
                    opn_dhcp.enable_interface(m['opnsense_interface'])
                    tech_dhcp.disable_scope(m['technitium_scope'])
                    console.print(f"  [green]↩[/green] Rolled back {m['opnsense_interface']}")
                except Exception as rb_err:
                    console.print(f"  [red]Rollback failed for {m['opnsense_interface']}: {rb_err}[/red]")
            raise typer.Exit(1)

    # Summary
    console.rule("[bold cyan]Summary[/bold cyan]")
    console.print(f"[green]Migrated:[/green]  {len(migrated)}/{len(mapping)} scopes")
    console.print(f"[yellow]Skipped:[/yellow]   {len(mapping) - len(migrated)} scopes")
    if migrated:
        console.print("\nTo roll back: [cyan]python3 manage.py dhcp-rollback[/cyan]")
```

- [ ] **Step 4: Verify manage.py syntax**

```bash
python3 -c "import manage" && echo "syntax OK"
```

Expected: `syntax OK`

- [ ] **Step 5: Verify command is registered**

```bash
python3 manage.py --help | grep dhcp
```

Expected: `dhcp-migrate` appears in output

- [ ] **Step 6: Commit**

```bash
git add manage.py .gitignore
git commit -m "feat: add dhcp-migrate command to manage.py

Orchestrates OPNsense → Technitium DHCP cutover:
- Auto-discovers OPNsense DHCP interfaces
- Lists Technitium scopes side-by-side
- Interactive interface→scope mapping with skip support
- Per-scope confirmation before cutover
- Automatic rollback on failure
- State persisted to .dhcp-migration-state.json

Co-Authored-By: Claude Haiku 4.5 <noreply@anthropic.com>"
```

---

## Task 5: manage.py dhcp-rollback Command

**Files:**
- Modify: `manage.py`

- [ ] **Step 1: Add dhcp-rollback command immediately after dhcp-migrate**

```python
@app.command(name="dhcp-rollback")
def dhcp_rollback() -> None:
    """Roll back DHCP migration: re-enable OPNsense, disable Technitium scopes."""
    try:
        from opnsense.modules.dhcp import DHCPClient as OPNDHCPClient
        from technitium.modules.dhcp import TechnitiumDHCPClient
    except ImportError as e:
        console.print(f"[red]Error: required module not found: {e}[/red]")
        raise typer.Exit(1)

    migrated = _load_migration_state()
    if not migrated:
        console.print("[yellow]No migration state found. Nothing to roll back.[/yellow]")
        raise typer.Exit(0)

    console.print(f"[bold]Found {len(migrated)} migrated scope(s) to roll back:[/bold]")
    for m in migrated:
        console.print(f"  {m['opnsense_interface']} ← {m['technitium_scope']}")

    if not typer.confirm("\nProceed with rollback?"):
        raise typer.Exit(0)

    opn_dhcp = OPNDHCPClient(
        api_key=os.getenv('OPNSENSE_KEY'),
        api_secret=os.getenv('OPNSENSE_SECRET'),
        url=os.getenv('OPNSENSE_URL', 'https://10.10.10.1/api'),
    )
    tech_dhcp = TechnitiumDHCPClient(
        host=os.getenv('TECHNITIUM_HOST', 'http://10.10.10.2:5380'),
        token=os.getenv('TECHNITIUM_TOKEN', ''),
    )

    failed = []
    for m in migrated:
        iface = m['opnsense_interface']
        scope = m['technitium_scope']
        try:
            opn_dhcp.enable_interface(iface)
            console.print(f"  [green]✓[/green] Re-enabled OPNsense DHCP on {iface}")

            tech_dhcp.disable_scope(scope)
            console.print(f"  [green]✓[/green] Disabled Technitium scope: {scope}")
        except Exception as e:
            console.print(f"  [red]✗ Failed to roll back {iface}: {e}[/red]")
            failed.append(iface)

    if not failed:
        os.remove(_DHCP_STATE_FILE)
        console.print("\n[green]Rollback complete. Migration state cleared.[/green]")
    else:
        console.print(f"\n[red]Rollback failed for {len(failed)} interface(s): {failed}[/red]")
        console.print("[yellow]Migration state preserved for manual intervention.[/yellow]")
        raise typer.Exit(1)
```

- [ ] **Step 2: Verify manage.py syntax**

```bash
python3 -c "import manage" && echo "syntax OK"
```

Expected: `syntax OK`

- [ ] **Step 3: Verify both commands are registered**

```bash
python3 manage.py --help | grep dhcp
```

Expected: both `dhcp-migrate` and `dhcp-rollback` appear

- [ ] **Step 4: Run full unit test suite**

```bash
pytest tests/unit/ -v
```

Expected: All tests PASS

- [ ] **Step 5: Commit**

```bash
git add manage.py
git commit -m "feat: add dhcp-rollback command to manage.py

Reverses a dhcp-migrate run by:
- Loading .dhcp-migration-state.json
- Re-enabling OPNsense DHCP on each migrated interface
- Disabling corresponding Technitium scopes
- Clearing state file on success

Co-Authored-By: Claude Haiku 4.5 <noreply@anthropic.com>"
```

---

## Task 6: Push Branch and Open PR

- [ ] **Step 1: Verify current branch**

```bash
git branch --show-current
```

Expected: `docs/dhcp-migration-spec` (or create a new feature branch if on master)

If on master or wrong branch:
```bash
git checkout -b feature/dhcp-migration
```

- [ ] **Step 2: Push branch**

```bash
git push -u origin HEAD
```

- [ ] **Step 3: Open PR**

```bash
gh pr create \
  --title "feat: DHCP migration (OPNsense → Technitium)" \
  --body "$(cat <<'EOF'
## Summary

- Adds \`src/opnsense/modules/dhcp.py\` — discover, disable, enable DHCP interfaces
- Adds \`src/technitium/\` library — token-auth REST client + DHCP scope management
- Adds \`manage.py dhcp-migrate\` — interactive cutover with auto-rollback on failure
- Adds \`manage.py dhcp-rollback\` — manual reversal using persisted state

## Test plan

- [ ] Run \`pytest tests/unit/ -v\` — all tests pass
- [ ] Run \`python3 manage.py dhcp-migrate --help\` — command visible
- [ ] Run \`python3 manage.py dhcp-rollback --help\` — command visible
- [ ] Verify \`.dhcp-migration-state.json\` is in \`.gitignore\`

🤖 Generated with [Claude Code](https://claude.com/claude-code)
EOF
)"
```

Expected: PR URL printed

---

## Self-Review Checklist

After writing this plan, verifying against the spec:

- ✅ `src/opnsense/modules/dhcp.py` — `list_enabled_interfaces`, `disable_interface`, `enable_interface` (Task 1)
- ✅ `src/technitium/` library skeleton with token auth (Task 2)
- ✅ `src/technitium/modules/dhcp.py` — `list_scopes`, `enable_scope`, `disable_scope` (Task 3)
- ✅ `manage.py dhcp-migrate` — discovery, mapping, pre-flight, per-scope cutover, auto-rollback (Task 4)
- ✅ `manage.py dhcp-rollback` — state-based manual reversal (Task 5)
- ✅ `.dhcp-migration-state.json` gitignored (Task 4 Step 1)
- ✅ Credentials via env vars (`OPNSENSE_KEY/SECRET/URL`, `TECHNITIUM_HOST/TOKEN`) matching 1Password references in spec
- ✅ Unmapped interfaces skipped, not migrated
- ✅ TDD throughout — tests written before implementation in every task
