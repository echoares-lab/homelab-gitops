# OPNsense Integration Design

**Document Date:** June 8, 2026  
**Status:** Design (Approved)  
**Scope:** OPNsense library, manage.py integration, future REST API  
**Primary Interface:** Human-first (manage.py CLI)

---

## 1. Overview

This design documents the integration of OPNsense network firewall/switching management into the homelab-gitops unified orchestrator. The integration enables humans to define and manage firewall rules, VLAN assignments, and interface configuration through manage.py, with automated setup during the pre-deploy phase of host provisioning.

### Goals
- **Human-first:** manage.py CLI remains the primary interface for operators
- **Full API coverage:** Library designed to support all OPNsense endpoints (not just MVP)
- **Extensible:** Adding new OPNsense modules requires minimal code and no refactoring
- **Future-proof:** REST API layer designed but not implemented, ready for future agent integration
- **Integrated:** OPNsense setup happens as part of the deployment workflow, not as a separate tool

### Non-Goals
- MCP server (revisited and deprioritized)
- Standalone agent interface (focus on manage.py integration)
- Comprehensive OPNsense feature coverage in Phase 1 (Tier 1 only: firewall rules, VLANs, interfaces)

---

## 2. Architecture

### High-Level Design

```
┌─────────────────────────────────────┐
│   OPNsense Python Library           │
│   src/opnsense/                     │
│   - Core REST client                │
│   - Module pattern (extensible)     │
│   - Models & exceptions             │
└─────────────────────────────────────┘
         ↓              ↓              ↓
    ┌────────────┐ ┌──────────┐  ┌────────────┐
    │ manage.py  │ │ REST API │  │ CLI Tools  │
    │ (Primary)  │ │ (Future) │  │ (Testing)  │
    └────────────┘ └──────────┘  └────────────┘
```

**Core Library:**
- Lives in `src/opnsense/` (separate from manage.py)
- Handles all OPNsense API interactions via REST + Basic Auth
- No dependencies on manage.py or CLI layer
- Can be imported and used standalone

**manage.py Integration:**
- Primary interface for humans
- Imports OPNsense library
- Pre-deploy phase: configures rules, VLANs before VM creation
- Interactive CLI: `manage.py opnsense` subcommands
- Rich-styled prompts for field input

**REST API (Future):**
- Thin FastAPI wrapper around library
- Standard CRUD endpoints
- Deferred implementation (after manage.py usage is validated)

---

## 3. Library Design

### Directory Structure

```
src/opnsense/
├── __init__.py                  # Package exports
├── client.py                    # Base REST client (auth, requests)
├── models.py                    # Dataclasses (FirewallRule, VLAN, etc.)
├── base.py                      # BaseClient class for module pattern
├── exceptions.py                # Custom exceptions
│
├── modules/
│   ├── __init__.py
│   ├── firewall.py              # FirewallClient (Phase 1)
│   └── network.py               # NetworkClient (Phase 1)
│
└── docs/
    └── API_STRUCTURE.md         # Guide for adding new modules
```

### Base Client Pattern

All module clients inherit from `BaseClient`:

```python
# src/opnsense/base.py
class BaseClient:
    def __init__(self, api_key: str, api_secret: str, url: str, timeout: int = 10):
        self.api = RestClient(api_key, api_secret, url, timeout)
    
    def get(self, endpoint: str, params: dict = None) -> dict:
        """GET request to OPNsense API"""
        return self.api.get(endpoint, params)
    
    def post(self, endpoint: str, data: dict = None) -> dict:
        """POST request to OPNsense API"""
        return self.api.post(endpoint, data)
```

Adding a new module requires only:

```python
# src/opnsense/modules/dhcp.py (future example)
class DHCPRelayClient(BaseClient):
    def configure_relay(self, interface: str, servers: list) -> dict:
        return self.post(f'dhcprelay/settings/set', {
            'interface': interface,
            'servers': servers
        })
```

### Phase 1: Firewall Module

**File:** `src/opnsense/modules/firewall.py`

```python
class FirewallClient(BaseClient):
    def create_firewall_rule(self, **kwargs) -> dict:
        """Create firewall rule. Accepts all OPNsense rule fields."""
        # Validate inputs
        # Call API
        
    def delete_firewall_rule(self, rule_id: str) -> dict:
        """Delete firewall rule by ID"""
        
    def list_firewall_rules(self, filter: dict = None) -> list:
        """List all firewall rules, optionally filtered"""
        
    def get_firewall_rule(self, rule_id: str) -> dict:
        """Get single rule by ID"""
        
    def update_firewall_rule(self, rule_id: str, **kwargs) -> dict:
        """Update rule (supports all OPNsense rule fields)"""
```

**Supported Fields (Example):**
```
name, description, enabled, log, action, protocol, src_net, dst_net,
port, state_policy, schedule, direction, interface, statetype, category,
... (all OPNsense firewall rule fields)
```

All fields are passed via `**kwargs`, allowing full API access without curating parameters.

### Phase 1: Network Module

**File:** `src/opnsense/modules/network.py`

```python
class NetworkClient(BaseClient):
    def create_vlan(self, **kwargs) -> dict:
        """Create VLAN. Accepts all OPNsense VLAN fields."""
        
    def delete_vlan(self, vlan_id: str) -> dict:
        """Delete VLAN"""
        
    def list_vlans(self) -> list:
        """List all VLANs"""
        
    def get_vlan(self, vlan_id: str) -> dict:
        """Get single VLAN"""
        
    def list_interfaces(self) -> list:
        """List all network interfaces"""
        
    def get_interface(self, name: str) -> dict:
        """Get single interface details"""
        
    def configure_interface(self, name: str, **kwargs) -> dict:
        """Configure interface (all OPNsense fields)"""
```

### Data Models

**File:** `src/opnsense/models.py`

```python
from dataclasses import dataclass

@dataclass
class FirewallRule:
    id: str
    name: str
    description: str
    enabled: bool
    action: str  # 'pass', 'block', 'reject'
    protocol: str
    src_net: str
    dst_net: str
    port: int
    # ... all other OPNsense fields

@dataclass
class VLAN:
    id: str
    interface: str
    vlan_id: int
    description: str
    enabled: bool

@dataclass
class Interface:
    name: str
    ip_address: str
    gateway: str
    dns_servers: list
    mtu: int
    # ... all other fields
```

---

## 4. manage.py Integration

### Workflow Integration

When a human runs the deployment command:

```bash
python3 manage.py deploy PROFILE INDEX --host HOST
```

The orchestration flow becomes:

```
1. Lint phase           (existing)
2. OPNsense prepare     (NEW) ← Pre-deploy setup
   - Create VLANs
   - Create firewall rules
   - Verify configuration
3. Deploy phase         (existing, OpenTofu)
4. Config phase         (existing, Ansible)
5. Test phase           (existing, Testinfra)
```

### Implementation in manage.py

**File:** `manage.py` (additions)

```python
from opnsense.modules.firewall import FirewallClient
from opnsense.modules.network import NetworkClient

def opnsense_prepare(profile_config: dict) -> bool:
    """Pre-deploy: Setup OPNsense for new host"""
    
    fw = FirewallClient(
        api_key=os.getenv('OPNSENSE_KEY'),
        api_secret=os.getenv('OPNSENSE_SECRET'),
        url=os.getenv('OPNSENSE_URL')
    )
    
    net = NetworkClient(
        api_key=os.getenv('OPNSENSE_KEY'),
        api_secret=os.getenv('OPNSENSE_SECRET'),
        url=os.getenv('OPNSENSE_URL')
    )
    
    console.print("[bold cyan]Preparing OPNsense...[/]")
    
    try:
        # Create VLAN from profile
        if 'vlan' in profile_config:
            console.print(f"Creating VLAN {profile_config['vlan']['id']}... ", end="")
            net.create_vlan(
                interface=profile_config['vlan']['interface'],
                vlan_id=profile_config['vlan']['id'],
                description=profile_config['vlan']['name']
            )
            console.print("[green]✓[/]")
        
        # Create firewall rules from profile
        if 'firewall_rules' in profile_config:
            for rule in profile_config['firewall_rules']:
                console.print(f"Creating rule '{rule['name']}'... ", end="")
                fw.create_firewall_rule(**rule)
                console.print("[green]✓[/]")
        
        # Verify rules are live
        console.print("Verifying OPNsense configuration... ", end="")
        # (simple check: list rules, verify count)
        console.print("[green]✓[/]")
        
        return True
        
    except OPNsenseError as e:
        console.print(f"[red]✗ Error: {e}[/]")
        return False
```

### Profile Format

Profiles extend existing YAML to include OPNsense config:

**File:** `config/profiles/ubuntu-2404-base.yml`

```yaml
metadata:
  name: Ubuntu 24.04 Base
  version: 1.0

opnsense:
  vlan:
    interface: em0
    id: 100
    name: "web-tier"
  
  firewall_rules:
    - name: "Allow SSH"
      src_net: "10.0.0.0/24"
      dst_net: "0.0.0.0/0"
      protocol: "tcp"
      port: 22
      action: "pass"
      enabled: true
      log: true
    
    - name: "Allow HTTPS"
      src_net: "0.0.0.0/0"
      dst_net: "0.0.0.0/0"
      protocol: "tcp"
      port: 443
      action: "pass"
      enabled: true
```

### CLI Commands

New `manage.py opnsense` subcommands for direct management:

```bash
# List operations
python3 manage.py opnsense list-rules
python3 manage.py opnsense list-vlans
python3 manage.py opnsense list-interfaces

# Create operations (interactive)
python3 manage.py opnsense create-rule
python3 manage.py opnsense create-vlan

# Get operations
python3 manage.py opnsense get-rule RULE_ID
python3 manage.py opnsense get-vlan VLAN_ID

# Delete operations (with confirmation)
python3 manage.py opnsense delete-rule RULE_ID
python3 manage.py opnsense delete-vlan VLAN_ID

# Bulk operations
python3 manage.py opnsense import --from-json rules.json
```

### Interactive Mode

When a human runs `manage.py opnsense create-rule` (no flags), they get an interactive wizard:

```
Create Firewall Rule
────────────────────────────────────
Name: [required] my-rule
Description: [optional] 
Source Network: [required] 10.0.0.0/24
Destination Network: [optional] 0.0.0.0/0
Protocol: [required] tcp
  > tcp
    udp
    icmp
Port: [required] 22
Action: [required] pass
  > pass
    block
    reject
Enabled: [y/n] y
Log Traffic: [y/n] y
State Policy: [required] established
  > established
    new
    closed
Schedule: [optional] 
Direction: [in/out] in
  > in
    out
Interface: [optional] em0

Review (all fields):
────────────────────────────────────
Name:                  my-rule
Source Network:        10.0.0.0/24
Destination Network:   0.0.0.0/0
Protocol:              tcp
Port:                  22
Action:                pass
Enabled:               yes
Log Traffic:           yes
State Policy:          established
Direction:             in
Interface:             em0

Create rule? [y/n] y
✓ Rule created (ID: abc123)
```

### Human Experience

All errors are clear and actionable:

```
Error: Invalid CIDR notation for 'src_net'
Expected format: 10.0.0.0/24 (CIDR notation)
Got: 10.0.0 (missing prefix length)

Hint: Use /24 for a /24 subnet, /8 for a /8 subnet, /32 for a single host.
```

---

## 5. Error Handling

### Exception Hierarchy

```python
# src/opnsense/exceptions.py

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

### Validation Strategy

Input validation happens **before** API calls to give users early feedback:

```python
def create_firewall_rule(self, name: str, src_net: str, dst_net: str, 
                         protocol: str, port: int, action: str, **kwargs):
    # Validate name
    if not name or len(name) > 255:
        raise ValidationError("Name required, max 255 characters")
    
    # Validate CIDR notation
    if not self._is_valid_cidr(src_net):
        raise ValidationError(f"Invalid CIDR for src_net: {src_net}")
    if not self._is_valid_cidr(dst_net):
        raise ValidationError(f"Invalid CIDR for dst_net: {dst_net}")
    
    # Validate protocol
    valid_protocols = ['tcp', 'udp', 'icmp', 'esp', 'ah', 'gre']
    if protocol not in valid_protocols:
        raise ValidationError(f"Invalid protocol: {protocol}. Must be one of: {valid_protocols}")
    
    # Validate action
    valid_actions = ['pass', 'block', 'reject']
    if action not in valid_actions:
        raise ValidationError(f"Invalid action: {action}. Must be one of: {valid_actions}")
    
    # Validate port
    if protocol in ['tcp', 'udp'] and (port < 1 or port > 65535):
        raise ValidationError(f"Port out of range: {port}. Must be 1-65535")
    
    # Only call API if validation passes
    return self.post('/firewall/rules/set', {
        'name': name,
        'src_net': src_net,
        'dst_net': dst_net,
        'protocol': protocol,
        'port': port,
        'action': action,
        **kwargs
    })
```

### Configuration

Credentials are read from environment variables or config file:

```python
# Priority order:
# 1. Environment variables: OPNSENSE_KEY, OPNSENSE_SECRET, OPNSENSE_URL
# 2. Config file: ~/.opnsense/config.toml
# 3. Profile-specific: Profile YAML can override

# Config file format:
# [opnsense]
# key = "xxxxxxx"
# secret = "yyyyyyyyy"
# url = "https://opnsense.local/api"
# timeout = 10
```

---

## 6. Testing Strategy

### Unit Tests (No OPNsense Instance Required)

**File:** `tests/unit/test_opnsense_firewall.py`

```python
def test_validate_rule_name_required():
    """Rule name cannot be empty"""
    fw = FirewallClient(...)
    
    with pytest.raises(ValidationError) as exc:
        fw.create_firewall_rule(name="", ...)
    
    assert "Name required" in str(exc.value)

def test_validate_cidr_notation():
    """CIDR notation must be valid"""
    fw = FirewallClient(...)
    
    with pytest.raises(ValidationError) as exc:
        fw.create_firewall_rule(src_net="10.0.0", ...)
    
    assert "Invalid CIDR" in str(exc.value)

def test_validate_protocol():
    """Protocol must be in allowed list"""
    fw = FirewallClient(...)
    
    with pytest.raises(ValidationError) as exc:
        fw.create_firewall_rule(protocol="invalid", ...)
    
    assert "Invalid protocol" in str(exc.value)

def test_api_call_success(mocker):
    """Successful API call returns response"""
    fw = FirewallClient(...)
    
    mock_post = mocker.patch.object(fw, 'post')
    mock_post.return_value = {'uuid': 'abc123'}
    
    result = fw.create_firewall_rule(
        name="test", src_net="10.0.0.0/24", dst_net="0.0.0.0/0",
        protocol="tcp", port=22, action="pass"
    )
    
    assert result['uuid'] == 'abc123'
```

**File:** `tests/unit/test_opnsense_network.py`

```python
def test_validate_vlan_id():
    """VLAN ID must be in valid range (1-4094)"""
    net = NetworkClient(...)
    
    with pytest.raises(ValidationError) as exc:
        net.create_vlan(interface="em0", vlan_id=5000, description="test")
    
    assert "Invalid VLAN ID" in str(exc.value)
```

### Integration Tests (Requires OPNsense Instance)

**File:** `tests/integration/test_opnsense_e2e.py`

```python
@pytest.mark.integration
def test_create_and_delete_rule(opnsense_client):
    """End-to-end: Create rule, verify it exists, delete it"""
    fw = FirewallClient(
        api_key=os.getenv('OPNSENSE_KEY'),
        api_secret=os.getenv('OPNSENSE_SECRET'),
        url=os.getenv('OPNSENSE_URL')
    )
    
    # Create
    result = fw.create_firewall_rule(
        name="test-rule-e2e",
        src_net="10.0.0.0/24",
        dst_net="192.168.0.0/24",
        protocol="tcp",
        port=443,
        action="pass"
    )
    rule_id = result['uuid']
    
    # Verify exists
    rule = fw.get_firewall_rule(rule_id)
    assert rule['name'] == "test-rule-e2e"
    
    # Delete
    fw.delete_firewall_rule(rule_id)
    
    # Verify deleted
    with pytest.raises(APIError):
        fw.get_firewall_rule(rule_id)

@pytest.mark.integration
def test_create_and_delete_vlan(opnsense_client):
    """End-to-end: Create VLAN, verify, delete"""
    net = NetworkClient(...)
    
    result = net.create_vlan(
        interface="em0",
        vlan_id=100,
        description="test-vlan"
    )
    vlan_id = result['uuid']
    
    vlan = net.get_vlan(vlan_id)
    assert vlan['vlan_id'] == 100
    
    net.delete_vlan(vlan_id)
    
    with pytest.raises(APIError):
        net.get_vlan(vlan_id)
```

### Test Configuration

**File:** `pytest.ini` (additions)

```ini
[pytest]
markers =
    integration: marks tests as integration tests (require OPNsense)
    unit: marks tests as unit tests (no OPNsense)
```

Run tests:
```bash
# Unit tests only
pytest tests/unit/ -v

# Integration tests (requires OPNsense)
pytest tests/integration/ -v -m integration

# All tests
pytest tests/ -v
```

---

## 7. REST API (Future, Designed Not Implemented)

### Deferred Implementation

REST API is designed but **not implemented in Phase 1**. This section documents the design so implementation is trivial when needed.

### Endpoint Design

```
POST   /api/firewall/rules          Create rule
GET    /api/firewall/rules          List rules
GET    /api/firewall/rules/{id}     Get rule
PUT    /api/firewall/rules/{id}     Update rule
DELETE /api/firewall/rules/{id}     Delete rule

POST   /api/network/vlans           Create VLAN
GET    /api/network/vlans           List VLANs
GET    /api/network/vlans/{id}      Get VLAN
DELETE /api/network/vlans/{id}      Delete VLAN

GET    /api/network/interfaces      List interfaces
GET    /api/network/interfaces/{name} Get interface
PUT    /api/network/interfaces/{name} Configure interface
```

### Request/Response Format

```json
POST /api/firewall/rules
{
  "name": "Allow SSH",
  "src_net": "10.0.0.0/24",
  "dst_net": "0.0.0.0/0",
  "protocol": "tcp",
  "port": 22,
  "action": "pass"
}

Response:
{
  "uuid": "abc123",
  "name": "Allow SSH",
  "src_net": "10.0.0.0/24",
  "dst_net": "0.0.0.0/0",
  "protocol": "tcp",
  "port": 22,
  "action": "pass",
  "created_at": "2026-06-08T12:00:00Z"
}
```

### Implementation Template

When REST API is needed:

```python
# src/opnsense_api/main.py
from fastapi import FastAPI, HTTPException
from opnsense.modules.firewall import FirewallClient

app = FastAPI()

@app.post("/api/firewall/rules")
def create_rule(request: FirewallRuleRequest):
    try:
        fw = FirewallClient(...)
        return fw.create_firewall_rule(**request.dict())
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except OPNsenseError as e:
        raise HTTPException(status_code=500, detail=str(e))
```

No refactoring of the library needed — it's just a wrapper.

---

## 8. Implementation Phases

### Phase 1 (MVP): Firewall + Network
- Library: `firewall.py`, `network.py` modules
- manage.py integration: Pre-deploy hook + CLI
- Testing: Unit + integration tests
- Timeline: 2-3 weeks

### Phase 2: Additional Modules (As Needed)
- DHCP relay
- DNS configuration
- NAT rules
- Port forwards
- Timeline: When needed

### Phase 3: REST API
- FastAPI wrapper
- Standard CRUD endpoints
- Timeline: After Phase 1 is mature

---

## 9. Configuration & Deployment

### Environment Setup

```bash
# Set OPNsense credentials
export OPNSENSE_KEY="your-api-key"
export OPNSENSE_SECRET="your-api-secret"
export OPNSENSE_URL="https://opnsense.local/api"

# Or store in ~/.opnsense/config.toml:
[opnsense]
key = "your-api-key"
secret = "your-api-secret"
url = "https://opnsense.local/api"
timeout = 10
```

### Profile Configuration

Profiles define OPNsense setup inline:

```yaml
# config/profiles/ubuntu-2404-base.yml
metadata:
  name: Ubuntu 24.04 Base

opnsense:
  vlan:
    interface: em0
    id: 100
    name: "web-tier"
  
  firewall_rules:
    - name: "Allow SSH from mgmt"
      src_net: "10.0.0.0/24"
      dst_net: "0.0.0.0/0"
      protocol: "tcp"
      port: 22
      action: "pass"
```

---

## 10. Dependencies

**Runtime:**
- `requests` — HTTP client (minimal, no extras)
- `pydantic` — Data validation (already in project)

**Development:**
- `pytest` — Testing (already in project)
- `pytest-mock` — Mocking (already in project)

**No additional dependencies** beyond what's already in the project.

---

## 11. Open Questions & Deferred Decisions

None at this time. Design is complete and approved.

---

## 12. Related Documents

- `CLAUDE.md` — Project overview and conventions
- `GEMINI.md` — Engineering standards and naming
- `manage.py` — Unified orchestrator (integration point)
- `docs/DESIGN.md` — Architecture overview (to be updated)
