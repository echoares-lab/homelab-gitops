#!/usr/bin/env python3
"""
Homelab Network Client Discovery & Mapping Tool
Correlates:
- pfSense ARP table (IPv4 Layer 2)
- pfSense NDP table (IPv6 Layer 2)
- pfSense State table (Active outbound/inbound traffic flows)
- Technitium DHCP leases & static reservations (DHCP Hostname, Scope, Lease times)
- Technitium DNS Reverse PTR lookups (Authoritative FQDN)
- IEEE OUI database (Hardware vendor/manufacturer)
"""

import csv
import json
import os
import re
import subprocess
import time
import urllib.request
from collections import defaultdict


def run_cmd(cmd, timeout=15):
    try:
        res = subprocess.run(
            cmd, shell=True, capture_output=True, text=True, timeout=timeout
        )
        return res.returncode, res.stdout, res.stderr
    except subprocess.TimeoutExpired:
        return -1, "", "Timeout"


def get_pfsense_ssh_prefix():
    return (
        'SSHPASS=$(op item get 5v6pgsaztzudgidd5th2xemvvm --vault "Homelab Access" --fields password --reveal) '
        "sshpass -e ssh -o StrictHostKeyChecking=accept-new -o BatchMode=no admin@10.10.10.1 "
    )


def get_technitium_token():
    return (
        subprocess.check_output(
            [
                "op",
                "item",
                "get",
                "mbyxafapjd2kmbdahxli6abz4y",
                "--vault",
                "Homelab-GitOps",
                "--fields",
                "token",
                "--reveal",
            ]
        )
        .decode()
        .strip()
    )


def load_oui_database():
    ouis = {}
    csv_paths = [
        "/usr/share/ieee-data/oui.csv",
        "/usr/share/ieee-data/mam.csv",
        "/usr/share/ieee-data/iab.csv",
        "/usr/share/ieee-data/oui36.csv",
    ]
    for path in csv_paths:
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8", errors="ignore") as f:
                    reader = csv.reader(f)
                    for row in reader:
                        if len(row) >= 3 and row[1]:
                            prefix = (
                                row[1].upper().replace(":", "").replace("-", "").strip()
                            )
                            vendor = row[2].strip()
                            if prefix and vendor:
                                ouis[prefix] = vendor
            except Exception:
                pass
    return ouis


def lookup_vendor(mac, ouis):
    if not mac:
        return "Unknown"
    norm = mac.upper().replace(":", "").replace("-", "")
    # Check 6-char (24-bit OUI)
    if len(norm) >= 6 and norm[:6] in ouis:
        return ouis[norm[:6]]
    # Check 7-char (28-bit MAM)
    if len(norm) >= 7 and norm[:7] in ouis:
        return ouis[norm[:7]]
    # Check 9-char (36-bit OUI36/IAB)
    if len(norm) >= 9 and norm[:9] in ouis:
        return ouis[norm[:9]]

    # Check if locally administered / randomized
    try:
        first_byte = int(norm[:2], 16)
        if (first_byte & 0x02) != 0:
            return "Randomized / Private MAC"
    except Exception:
        pass
    return "Unknown Vendor"


def fetch_pfsense_data():
    print("1. Querying pfSense (10.10.10.1) ARP, NDP, and State tables...")
    ssh_prefix = get_pfsense_ssh_prefix()

    # 1. ARP Table
    _, arp_out, _ = run_cmd(ssh_prefix + '"arp -an"')
    arp_entries = {}
    for line in arp_out.splitlines():
        # ? (10.10.10.11) at 00:50:56:68:e1:ef on vmx0 expires in 648 seconds [ethernet]
        m = re.search(r"\(([\d\.]+)\)\s+at\s+([0-9a-fA-F:]{17})\s+on\s+([^\s]+)", line)
        if m:
            ip = m.group(1)
            mac = m.group(2).lower()
            iface = m.group(3)
            permanent = "permanent" in line
            arp_entries[ip] = {
                "mac": mac,
                "iface": iface,
                "permanent": permanent,
                "raw": line.strip(),
            }

    # 2. NDP Table (IPv6)
    _, ndp_out, _ = run_cmd(ssh_prefix + '"ndp -an"')
    ndp_entries = {}
    for line in ndp_out.splitlines():
        # 2600:4040:... 00:50:56:9f:a8:b7 vmx0 ...
        parts = line.strip().split()
        if len(parts) >= 3:
            ip6 = parts[0]
            mac = parts[1].lower()
            if re.match(r"^[0-9a-fA-F:]{17}$", mac):
                ndp_entries[ip6] = {
                    "mac": mac,
                    "iface": parts[2] if len(parts) > 2 else "unknown",
                }

    # 3. Active States (who is passing traffic right now)
    _, state_out, _ = run_cmd(ssh_prefix + '"pfctl -ss"')
    active_traffic_counts = defaultdict(int)
    for line in state_out.splitlines():
        m_ip = re.search(r"10\.10\.\d+\.\d+", line)
        if m_ip:
            ip = m_ip.group(0)
            if ip != "10.10.10.1":
                active_traffic_counts[ip] += 1

    print(
        f"   Found {len(arp_entries)} ARP entries, {len(ndp_entries)} NDP entries, {len(active_traffic_counts)} active traffic flows."
    )
    return arp_entries, ndp_entries, active_traffic_counts


def fetch_technitium_dhcp():
    print("2. Querying Technitium (10.10.10.2) DHCP Leases & Reservations...")
    token = get_technitium_token()
    url = f"http://10.10.10.2:5380/api/dhcp/leases/list?token={token}"
    req = urllib.request.urlopen(url)
    data = json.loads(req.read().decode())

    leases = {}
    for item in data.get("response", {}).get("leases", []):
        ip = item.get("address")
        raw_mac = item.get("hardwareAddress")
        mac = raw_mac.replace("-", ":").lower() if raw_mac else None
        hostname = item.get("hostName")
        scope = item.get("scope")
        lease_type = item.get("type")
        expires = item.get("leaseExpires")
        if ip:
            leases[ip] = {
                "mac": mac,
                "hostname": hostname,
                "scope": scope,
                "type": lease_type,
                "expires": expires,
            }

    # Also fetch configured static reservations from MGMT_NET scope
    try:
        scope_url = (
            f"http://10.10.10.2:5380/api/dhcp/scopes/get?token={token}&name=MGMT_NET"
        )
        scope_req = urllib.request.urlopen(scope_url)
        scope_data = json.loads(scope_req.read().decode())
        for res in scope_data.get("response", {}).get("reservedLeases", []):
            ip = res.get("address")
            if ip and ip not in leases:
                raw_mac = res.get("hardwareAddress")
                mac = raw_mac.replace("-", ":").lower() if raw_mac else None
                leases[ip] = {
                    "mac": mac,
                    "hostname": res.get("hostName"),
                    "scope": "MGMT_NET",
                    "type": "Reserved (Offline)",
                    "expires": None,
                }
    except Exception:
        pass

    print(f"   Fetched {len(leases)} DHCP leases and static reservations.")
    return leases


def query_ptr(ip):
    try:
        cmd = f"dig +short -x {ip} @10.10.10.2"
        rc, out, _ = run_cmd(cmd, timeout=2)
        if rc == 0 and out.strip():
            return out.strip().splitlines()[0].rstrip(".")
    except Exception:
        pass
    return None


def main():
    t0 = time.time()
    ouis = load_oui_database()
    arp_entries, ndp_entries, active_states = fetch_pfsense_data()
    dhcp_leases = fetch_technitium_dhcp()

    print("3. Correlating IP, MAC, Hostname, Vendor, and Active State...")
    # Consolidate all known IPv4 IPs
    all_ips = (
        set(arp_entries.keys()) | set(dhcp_leases.keys()) | set(active_states.keys())
    )
    # Exclude WAN public IPs and gateway
    lan_ips = sorted(
        [ip for ip in all_ips if ip.startswith("10.10.")],
        key=lambda x: [int(p) for p in x.split(".")],
    )

    devices = []
    for ip in lan_ips:
        arp = arp_entries.get(ip)
        dhcp = dhcp_leases.get(ip)
        active_flows = active_states.get(ip, 0)

        # MAC determination
        mac = None
        if arp and arp.get("mac"):
            mac = arp["mac"]
        elif dhcp and dhcp.get("mac"):
            mac = dhcp["mac"]

        # Hostname determination
        hostname = None
        if dhcp and dhcp.get("hostname"):
            hostname = dhcp["hostname"]

        # Check reverse PTR if missing hostname or has default
        ptr = query_ptr(ip)
        if ptr and not hostname:
            hostname = ptr
        elif ptr and hostname and ptr.lower() != hostname.lower():
            if not hostname.endswith(".plexplease.com") and ptr.endswith(
                ".plexplease.com"
            ):
                hostname = f"{hostname} ({ptr})"

        if not hostname:
            hostname = ptr if ptr else "Unknown"

        vendor = lookup_vendor(mac, ouis) if mac else "Unknown"

        # Find associated IPv6 addresses matching this MAC
        associated_ip6 = []
        if mac:
            for ip6, ndp in ndp_entries.items():
                if ndp.get("mac") == mac:
                    associated_ip6.append(ip6)

        # Status
        status = []
        if active_flows > 0:
            status.append(f"Active ({active_flows} flows)")
        elif arp:
            status.append("In ARP Cache")
        elif dhcp:
            status.append(f"DHCP {dhcp['type']}")
        else:
            status.append("Idle")

        status_str = ", ".join(status)
        scope = dhcp.get("scope") if dhcp else "MGMT_NET"

        devices.append(
            {
                "ip": ip,
                "mac": mac.upper() if mac else "Unknown",
                "hostname": hostname,
                "vendor": vendor,
                "scope": scope,
                "status": status_str,
                "active_flows": active_flows,
                "ipv6": associated_ip6,
                "dhcp_type": dhcp.get("type") if dhcp else "Static/Manual",
            }
        )

    # Save to JSON
    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    output_path = os.path.join(repo_root, "config", "network_clients.json")
    with open(output_path, "w") as f:
        json.dump(devices, f, indent=2)

    print(f"\nDiscovered {len(devices)} total clients across the network.")
    print(f"Full inventory saved to: {output_path}")

    # Print formatted summary table
    print("\n" + "=" * 115)
    print(
        f"{'IPv4 Address':<16} {'MAC Address':<18} {'Vendor / Manufacturer':<24} {'Hostname / Device':<34} {'Active Status':<18}"
    )
    print("=" * 115)
    for d in devices:
        ip_str = d["ip"]
        mac_str = d["mac"]
        vendor_str = (d["vendor"][:22] + "..") if len(d["vendor"]) > 24 else d["vendor"]
        host_str = (
            (d["hostname"][:32] + "..") if len(d["hostname"]) > 34 else d["hostname"]
        )
        stat_str = d["status"]
        print(
            f"{ip_str:<16} {mac_str:<18} {vendor_str:<24} {host_str:<34} {stat_str:<18}"
        )
    print("=" * 115)
    print(f"Discovery completed in {time.time() - t0:.2f}s.\n")


if __name__ == "__main__":
    main()
