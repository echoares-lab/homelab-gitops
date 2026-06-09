# DHCP Migration Design: OPNsense → Technitium

**Document Date:** June 9, 2026
**Status:** Approved
**Scope:** Migrate DHCP service from OPNsense to Technitium DNS Server across all VLANs

---

## 1. Overview

Migrate DHCP authority from OPNsense (10.10.10.1) to Technitium DNS Server (10.10.10.2) across all active VLAN scopes. Reservations are handled manually — this migration covers scope enable/disable orchestration only.

### Goals
- Auto-discover all OPNsense DHCP-enabled interfaces
- Interactively map OPNsense interfaces → Technitium scopes (no 1:1 requirement)
- Orchestrated per-scope cutover with confirmation gates and automatic rollback
- New `manage.py dhcp-migrate` and `manage.py dhcp-rollback` commands
- Credentials via 1Password Connect (existing pattern)

### Non-Goals
- Automated reservation migration (manual, handled separately)
- ARP entry automation (future feature)
- Technitium scope creation (scopes must exist before migration runs)

---

## 2. Architecture

```
manage.py dhcp-migrate
        │
        ├─ Step 1: Discover
        │   ├─ OPNsense API → list all interfaces with DHCP enabled
        │   ├─ Technitium API → list available DHCP scopes
        │   └─ Display side-by-side, prompt for confirmation
        │
        ├─ Step 2: Map
        │   ├─ Interactive: user maps each OPNsense interface → Technitium scope
        │   └─ Unmapped OPNsense interfaces are skipped (not migrated)
        │
        ├─ Step 3: Pre-flight
        │   └─ Verify all mapped Technitium scopes exist before cutover begins
        │
        ├─ Step 4: Cutover (per mapped pair, with confirmation)
        │   ├─ Disable OPNsense DHCP on interface
        │   ├─ Enable Technitium scope
        │   └─ On failure: auto-rollback all migrated interfaces
        │
        └─ Step 5: Summary
            └─ Print migrated/skipped/failed counts + rollback command hint

manage.py dhcp-rollback
        └─ Re-enable OPNsense DHCP on all previously migrated interfaces
```

**New code:**
- `src/opnsense/modules/dhcp.py` — extends existing `BaseClient` pattern
- `src/technitium/client.py` — Technitium REST client
- `src/technitium/modules/dhcp.py` — Technitium DHCP scope management
- `manage.py` — `dhcp-migrate` and `dhcp-rollback` commands

**Credentials (1Password):**
```
OPNSENSE_KEY=op://homelab-gitops/OPNsense/api_key
OPNSENSE_SECRET=op://homelab-gitops/OPNsense/api_secret
OPNSENSE_URL=op://homelab-gitops/OPNsense/url
TECHNITIUM_TOKEN=op://homelab-gitops/Technitium/token
TECHNITIUM_HOST=op://homelab-gitops/Technitium/host
```

---

## 3. Module Design

### OPNsense DHCP Module

**File:** `src/opnsense/modules/dhcp.py`

Extends existing `BaseClient` (same pattern as `firewall.py`, `network.py`):

```python
class DHCPClient(BaseClient):
    def list_enabled_interfaces(self) -> list[dict]:
        """Auto-discover all interfaces with DHCP enabled.
        Returns: [{interface, subnet, range_start, range_end, enabled}]
        """

    def disable_interface(self, interface: str) -> dict:
        """Disable DHCP on a single interface."""

    def enable_interface(self, interface: str) -> dict:
        """Re-enable DHCP on a single interface (rollback)."""
```

OPNsense API endpoints used:
- `GET /api/dhcpv4/settings/get` — discover all interfaces
- `POST /api/dhcpv4/settings/set` — enable/disable per interface

### Technitium DHCP Module

**Files:** `src/technitium/client.py`, `src/technitium/modules/dhcp.py`

New parallel library, same BaseClient pattern:

```python
class TechnitiumDHCPClient:
    def list_scopes(self) -> list[dict]:
        """List all DHCP scopes.
        Returns: [{name, subnet, enabled}]
        """

    def enable_scope(self, name: str) -> dict:
        """Enable a DHCP scope by name."""

    def disable_scope(self, name: str) -> dict:
        """Disable a DHCP scope by name."""
```

Technitium API authentication: `?token=` query parameter.

Technitium API endpoints used:
- `GET /api/dhcp/scopes/list` — list scopes
- `POST /api/dhcp/scopes/enable?name=<name>` — enable scope
- `POST /api/dhcp/scopes/disable?name=<name>` — disable scope

---

## 4. CLI Workflow

```
$ python3 manage.py dhcp-migrate

Step 1 — Discovery
──────────────────────────────────────────────────────────────
OPNsense DHCP interfaces (auto-discovered):
  igc1.10    10.10.10.0/24    [enabled]
  igc1.20    10.10.20.0/24    [enabled]
  igc1.30    10.10.30.0/24    [enabled]
  ...

Technitium DHCP scopes (available):
  mgmt       10.10.10.0/24    [disabled]
  infra      10.10.20.0/24    [disabled]
  servers    10.10.30.0/24    [disabled]
  iot        10.10.50.0/24    [disabled]
  ...

Step 2 — Map Interfaces to Scopes
──────────────────────────────────────────────────────────────
Map igc1.10 (10.10.10.0/24) → Technitium scope [or skip]: mgmt
Map igc1.20 (10.10.20.0/24) → Technitium scope [or skip]: infra
Map igc1.30 (10.10.30.0/24) → Technitium scope [or skip]: servers
...
Unmapped interfaces will not be migrated. Proceed? [y/n]: y

Step 3 — Pre-flight Check
──────────────────────────────────────────────────────────────
✓ mgmt scope exists in Technitium
✓ infra scope exists in Technitium
✓ servers scope exists in Technitium
All scopes verified. Ready to migrate 3 interface(s).

Step 4 — Cutover
──────────────────────────────────────────────────────────────
Migrate igc1.10 → mgmt? [y/n]: y
  ✓ Disabled OPNsense DHCP on igc1.10
  ✓ Enabled Technitium scope: mgmt

Migrate igc1.20 → infra? [y/n]: y
  ✓ Disabled OPNsense DHCP on igc1.20
  ✓ Enabled Technitium scope: infra
...

Step 5 — Summary
──────────────────────────────────────────────────────────────
Migrated:  3 scopes
Skipped:   0
Failed:    0

To roll back: python3 manage.py dhcp-rollback
```

**Rollback behavior:**
- On any failure mid-cutover, automatically re-enables OPNsense on all already-migrated interfaces
- `manage.py dhcp-rollback` manually reverses the full migration
- Migration state is written to `.dhcp-migration-state.json` (gitignored) to support rollback after process exit

---

## 5. Technitium Library Structure

```
src/technitium/
├── __init__.py
├── client.py          # RestClient (token-based auth)
├── base.py            # BaseClient (same pattern as src/opnsense/base.py)
├── exceptions.py      # TechnitiumError hierarchy
└── modules/
    ├── __init__.py
    └── dhcp.py        # TechnitiumDHCPClient
```

Mirrors the `src/opnsense/` structure exactly for consistency.

---

## 6. Testing Strategy

**Unit tests (no live services):**
- `tests/unit/test_technitium_client.py` — RestClient auth, error handling
- `tests/unit/test_technitium_dhcp.py` — scope list/enable/disable with mocked responses
- `tests/unit/test_opnsense_dhcp.py` — interface list/enable/disable with mocked responses

**Integration tests (requires live OPNsense + Technitium):**
- `tests/integration/test_dhcp_migration.py` — marked `@pytest.mark.integration`
- Tests discover → map → cutover → rollback on real endpoints

---

## 7. VLAN Scope Reference

Technitium must have these scopes configured before migration runs:

| VLAN | Name | Subnet | Dynamic Range | Zone |
|------|------|--------|---------------|------|
| 10 | mgmt | 10.10.10.0/24 | .101–.254 | mgmt.plexplease.com |
| 15 | storage | 10.10.15.0/24 | .101–.254 | storage.plexplease.com |
| 20 | infra | 10.10.20.0/24 | .101–.254 | infra.plexplease.com |
| 30 | servers | 10.10.30.0/24 | .101–.254 | srv.plexplease.com |
| 40 | clients | 10.10.40.0/24 | .101–.254 | user.plexplease.com |
| 50 | iot | 10.10.50.0/24 | .101–.254 | iot.plexplease.com |
| 60 | work | 10.10.60.0/24 | .101–.254 | work.plexplease.com |
| 70 | lab | 10.10.70.0/24 | .101–.254 | lab.plexplease.com |
| 80 | admin | 10.10.80.0/24 | .101–.254 | admin.plexplease.com |
| 100 | guest | 10.10.100.0/24 | .101–.254 | guest.plexplease.com |

---

## 8. DHCP Reservations (Manual — Pre-Migration)

Reserved addresses must be configured in Technitium manually before migration. Convention: reserved IPs use host octet < 100; dynamic range is .101–.254.

### VLAN 10 — MGMT_NET (mgmt.plexplease.com)

| MAC | Hostname | Reserved IP | Notes |
|-----|----------|-------------|-------|
| `00:1f:28:d3:66:80` | switch-01 | 10.10.10.15 | HP ProCurve |
| `c4:e3:ce:68:e2:50` | ap-01 | 10.10.10.16 | EWS377-FIT — was .178 |
| `00:50:56:8b:4b:e9` | opnsense-01 | 10.10.10.1 | Static IP — doc only |
| `00:50:56:9f:5e:32` | dns-01 | 10.10.10.2 | Static IP — doc only |

### VLAN 15 — STORAGE_NET (storage.plexplease.com)

| MAC | Hostname | Reserved IP | Notes |
|-----|----------|-------------|-------|
| `ac:1f:6b:3b:93:7f` | ipmi-01 | 10.10.15.10 | SuperMicro IPMI — was .190 |
| `00:50:56:a1:79:c7` | truenas-01 | 10.10.15.20 | TrueNAS SCALE — keep .20 |

### VLAN 20 — INFRA_NET (infra.plexplease.com)

| MAC | Hostname | Reserved IP | Notes |
|-----|----------|-------------|-------|
| `00:0c:29:a9:92:e0` | vcenter-01 | 10.10.20.9 | vCenter — keep .9 |
| `00:50:56:68:e1:ef` | esxi-01 | 10.10.20.11 | 384GB/96C — keep .11 |
| `00:50:56:64:28:5c` | esxi-02 | 10.10.20.12 | 32GB/16C — keep .12 |
| `00:50:56:6c:dc:38` | esxi-03 | 10.10.20.13 | 32GB/8C — keep .13 |
| `00:0c:29:45:15:6c` | nut | 10.10.20.10 | NUT UPS monitor — was .139 |

> ⚠️ ESXi hosts moving from 10.10.10.x → 10.10.20.x requires vCenter + ESXi management network reconfiguration before this reservation takes effect.

### VLAN 30 — SERVERS_NET (srv.plexplease.com)
No reservations.

### VLAN 40 — CLIENTS_NET (user.plexplease.com)
No reservations (personal phones unnamed → dynamic).

### VLAN 50 — IOT_NET (iot.plexplease.com)

| MAC | Hostname | Reserved IP | Notes |
|-----|----------|-------------|-------|
| `dc:03:98:94:07:e6` | tv-01 | 10.10.50.10 | LG G4 OLED — was .106 |
| `00:09:b0:14:91:b1` | onkyo | 10.10.50.11 | Onkyo TX-NR676 — was .158 |
| `40:5b:d8:a1:08:b6` | print-01 | 10.10.50.12 | Printer — was .174 |

All other IoT (Tuya, Amazon, Fitbit, Nest, Espressif) → dynamic .101–.254.

### VLAN 60 — WORK_NET (work.plexplease.com)

| MAC | Hostname | Reserved IP | Notes |
|-----|----------|-------------|-------|
| `4c:b0:4a:67:11:5f` | alex-laptop | 10.10.60.10 | was .163 |
| `ba:ed:38:d6:f3:67` | alex-phone | 10.10.60.11 | was .198 |
| `f4:6d:3f:cf:9c:07` | matthew-laptop | 10.10.60.12 | was .194 |

### VLAN 70 — LAB_NET (lab.plexplease.com)

| MAC | Hostname | Reserved IP | Notes |
|-----|----------|-------------|-------|
| `00:50:56:9f:8f:ab` | codex-01 | 10.10.70.51 | Ubuntu VM — keep .51 |
| `00:50:56:9f:a8:b7` | dev | 10.10.70.52 | Ubuntu VM — keep .52 |

### VLAN 80 — ADMIN_NET (admin.plexplease.com)

| MAC | Hostname | Reserved IP | Notes |
|-----|----------|-------------|-------|
| `04:42:1a:e9:d1:b3` | pc-01 | 10.10.80.5 | Matthew desktop — keep .5 |

### VLAN 100 — GUEST_NET (guest.plexplease.com)
No reservations.

---

## 9. Dependencies

**Runtime (new):**
- `requests` — already in project

**No new dependencies required.**

---

## 10. Related Documents

- `docs/superpowers/specs/2026-06-08-opnsense-integration-design.md` — OPNsense library (Phase 1)
- `src/opnsense/` — existing OPNsense library (firewall, network modules)
- `CLAUDE.md` — project conventions
