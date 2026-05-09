# Technitium DNS & DHCP Management Runbook

This guide covers how to manage your Technitium DNS and DHCP infrastructure using the `technitium_manager.py` orchestrator and OpenTofu.

## 1. Overview
The management system uses a **Universal CSV** file (`config/dns_records.csv`) as the single source of truth. A Python helper script converts this CSV into declarative OpenTofu configuration and applies it to your Technitium server.

---

## 2. Using Interactive Mode (Recommended)
The easiest way to add new resources is via the interactive CLI wizard. It provides real-time guidance, examples, and validation.

### Command:
```bash
python3 scripts/technitium_manager.py add-resource
```

### Steps:
1.  **Select Resource Type:** Choose from `zone`, `record`, `dhcp_scope`, or `dhcp_lease`.
2.  **Fill Required Fields:** The script will prompt for mandatory data (e.g., Zone Name, IP Address, etc.).
3.  **Optional Fields:** You will be asked if you want to configure optional settings like TTL, Comments, or `depends_on`.
4.  **Confirmation:** On success, the resource is appended to `config/dns_records.csv`.

---

## 3. Universal CSV Schema Details
The CSV file `config/dns_records.csv` uses a unified schema. Depending on the `resource_type`, different columns are utilized.

### Column Reference Table
| Column | Resource(s) | Description | Example |
| :--- | :--- | :--- | :--- |
| **`resource_type`** | All | One of: `zone`, `record`, `dhcp_scope`, `dhcp_lease`. | `record` |
| **`name`** | All | The primary identifier (Zone name, Record FQDN, Scope name, or Lease Hostname). | `www.example.com` |
| **`parent`** | Record, Lease | The owner. The Zone name for records; the Network ID for leases. | `example.com` |
| **`type`** | Zone, Record | Zone type (`Primary`, `Forwarder`) or Record type (`A`, `CNAME`, `TXT`). | `A` |
| **`value`** | Zone, Record, Lease | The target. Forwarder IP for zones; IP/Target for records; Reserved IP for leases. | `10.10.10.2` |
| **`ttl`** | Record | Time To Live in seconds. Defaults to `3600`. | `300` |
| **`mac_address`** | Lease | Hardware address for static DHCP assignments. | `AA:BB:CC:DD:EE:FF` |
| **`network_address`**| Scope | The network ID for a DHCP scope. | `192.168.1.0` |
| **`subnet_mask`** | Scope | The subnet mask for a DHCP scope. | `255.255.255.0` |
| **`start_address`** | Scope | The start of the dynamic IP pool. | `192.168.1.100` |
| **`end_address`** | Scope | The end of the dynamic IP pool. | `192.168.1.200` |
| **`gateway`** | Scope | The default gateway provided to DHCP clients. | `192.168.1.1` |
| **`comments`** | All | A human-readable description. | `Prod Web Cluster` |
| **`depends_on`** | All | Comma-separated list of Tofu resource IDs for ordering. | `technitium_dns_zone.zone_plex_com` |
| **`advanced_json`** | All | A JSON string of additional provider-specific attributes. | `{"protocol": "Https"}` |

---

## 4. Resource Specific Guidance

### 4.1 DNS Zones
*   **Primary Zone:** Set `type` to `Primary`. No `value` needed.
*   **Forwarder Zone:** Set `type` to `Forwarder` and `value` to the upstream DNS server IP.
*   **Stub Zone:** Set `type` to `Stub`.

### 4.2 DNS Records
*   **A/AAAA:** Set `value` to the IP address.
*   **CNAME:** Set `value` to the target domain name (FQDN).
*   **TXT:** Set `value` to the text content.

### 4.3 DHCP Scopes
*   Requires `network_address`, `subnet_mask`, `start_address`, and `end_address`.
*   `gateway` is optional but highly recommended.

### 4.4 DHCP Leases (Reserved)
*   **Important:** The `parent` must match the `network_address` of an existing scope.
*   Requires `mac_address` and `value` (the reserved IP).

---

## 5. Deployment Workflow
Once your CSV is updated, follow these steps to sync the changes to Technitium.

### Step 1: Convert to OpenTofu JSON
This generates `tofu/dns/records.tf.json`.
```bash
python3 scripts/technitium_manager.py convert-csv
```

### Step 2: Apply Changes
This initializes OpenTofu and applies the configuration.
```bash
python3 scripts/technitium_manager.py apply
```

---

## 6. Declarative State & Deletions
This system follows a **declarative model** powered by OpenTofu. This means Technitium will always be synced to match exactly what is in your CSV.

### Important Behaviors:
*   **Automatic Deletions:** If you remove a row from `config/dns_records.csv`, the corresponding record will be **deleted** from Technitium during the next `apply`.
*   **Source of Truth:** The CSV is your source of truth. Manual changes made directly in the Technitium Web UI are **not** managed by this tool and will generally be left alone unless they conflict with a CSV record.
*   **Safety:** The `apply` command will show you a plan before making changes. Review any lines marked with a red minus (`-`) to ensure you aren't accidentally deleting a record.
*   **Temporary Deactivation:** To temporarily disable a record without deleting it from your file, add a `#` to the beginning of the `resource_type` column (e.g., `#record`). The script will skip the row, causing OpenTofu to delete it from the server while preserving your data.

---

## 7. Copy-Paste Template
Copy the block below and save it as `config/dns_records.csv` to get started.

```csv
resource_type,name,parent,type,value,ttl,mac_address,network_address,subnet_mask,start_address,end_address,gateway,comments,depends_on,advanced_json
zone,plexplease.com,,Primary,,,,, ,,,,Technitium Primary Zone,,
record,dns-01.plexplease.com,plexplease.com,A,10.10.10.2,3600,,,, ,,,,Primary DNS,,
record,www.plexplease.com,plexplease.com,CNAME,dns-01.plexplease.com,3600,,,, ,,,,Web Server,,
dhcp_scope,Management LAN,,,,, ,10.10.10.0,255.255.255.0,10.10.10.100,10.10.10.200,10.10.10.1,Main Pool,,
dhcp_lease,printer-01,10.10.10.0,,10.10.10.50,,00:11:22:33:44:55,,,,,,Static Printer,,
```
