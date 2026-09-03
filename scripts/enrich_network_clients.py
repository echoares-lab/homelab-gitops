#!/usr/bin/env python3
"""
Enrich network_clients.json with deep verified hardware metadata and regenerate docs/network_client_map.md.
"""

import json
from datetime import datetime, timezone

def enrich():
    with open('/home/dev/repos/homelab-gitops/config/network_clients.json') as f:
        clients = json.load(f)

    # Specific hardware overrides & enrichments
    overrides = {
        "10.10.10.1": {
            "vendor": "Netgate / pfSense (VMware)",
            "hostname": "pfsense.infra.plexplease.com",
            "role": "Firewall & NAT Gateway (FreeBSD 15.0 / pfSense-CE 2.8.1-RELEASE, 4 vCPU, 4GB RAM on ESXi-03)",
            "device_class": "Network / Firewall"
        },
        "10.10.10.2": {
            "vendor": "VMware, Inc. (Photon OS)",
            "hostname": "dns-01.plexplease.com",
            "role": "Authoritative DNS & DHCP Server (Technitium .NET 8, 4 vCPU, 8GB RAM on ESXi-01)",
            "device_class": "Core Infrastructure"
        },
        "10.10.10.6": {
            "vendor": "EnGenius Technologies",
            "hostname": "ap-01.infra.plexplease.com",
            "role": "Wi-Fi 6 Access Point (EWS377-FIT 4x4 Managed AP - Top Floor)",
            "location": "Top Floor",
            "device_class": "Network AP"
        },
        "10.10.10.7": {
            "vendor": "ASUSTek COMPUTER INC",
            "hostname": "asus-ap-01.infra.plexplease.com",
            "role": "Wireless Access Point (Legacy ASUS RT-AX54)",
            "device_class": "Network AP"
        },
        "10.10.10.8": {
            "vendor": "EnGenius Technologies",
            "hostname": "ap-02.infra.plexplease.com",
            "role": "Wi-Fi 6 Access Point (EWS377-FIT 4x4 Managed AP - First Floor)",
            "location": "First Floor",
            "device_class": "Network AP"
        },
        "10.10.10.10": {
            "vendor": "Super Micro Computer, Inc.",
            "hostname": "ipmi-01.mgmt.plexplease.com",
            "role": "Supermicro X11DPi-N(T) ESXi-01 ASPEED AST2500 BMC / IPMI",
            "device_class": "Core Infrastructure",
            "status": "DHCP Reserved (Static: 10.10.10.10)"
        },
        "10.10.10.104": {
            "vendor": "Super Micro Computer, Inc.",
            "hostname": "ipmi-01.mgmt.plexplease.com",
            "role": "Supermicro X11DPi-N(T) ESXi-01 ASPEED AST2500 BMC / IPMI (Active Lease until renewal)",
            "device_class": "Core Infrastructure",
            "status": "Active (Transitioning to .10)"
        },
        "10.10.10.9": {
            "vendor": "VMware, Inc.",
            "hostname": "vcenter.mgmt.plexplease.com",
            "role": "VMware vCenter Server Appliance 8.0 (4 vCPU, 21GB RAM on ESXi-01)",
            "device_class": "Core Infrastructure"
        },
        "10.10.10.11": {
            "vendor": "Supermicro",
            "hostname": "esxi-01.mgmt.plexplease.com",
            "role": "VMware ESXi 8.0.3 Hypervisor 01 (Supermicro X11DPi-N(T), Dual Xeon 48c/96t, 384GB RAM, Intel X710)",
            "device_class": "Physical Hypervisor"
        },
        "10.10.10.13": {
            "vendor": "Topton / CWWK",
            "hostname": "esxi-03.mgmt.plexplease.com",
            "role": "VMware ESXi 8.0.3 Hypervisor 03 (Alder Lake-N i3-N305 8c/8t, 16GB DDR5, 4x2.5G + 2x10G SFP+)",
            "device_class": "Physical Hypervisor"
        },
        "10.10.10.20": {
            "vendor": "iXsystems / TrueNAS",
            "hostname": "truenas-01.mgmt.plexplease.com",
            "role": "TrueNAS SCALE 25.04.2 Storage Appliance (146TB ZFS, LSI 2308 HBA + Optane P1600X SLOG passthrough)",
            "device_class": "Storage Appliance"
        },
        "10.10.10.30": {
            "vendor": "VMware, Inc.",
            "hostname": "homelab.mgmt.plexplease.com",
            "role": "Docker Services Host (Ubuntu Linux 7.0, 16 vCPU, 32GB RAM, 30 containers: Plex, Sonarr, OpenBao, etc.)",
            "device_class": "Server VM"
        },
        "10.10.10.50": {
            "vendor": "Red Hat / CoreOS",
            "hostname": "k3s-01.infra.plexplease.com",
            "role": "Production Kubernetes Cluster (k3s v1.35.5, Fedora CoreOS 44, 16 vCPU, 64GB RAM)",
            "device_class": "Kubernetes Control Plane"
        },
        "10.10.10.51": {
            "vendor": "VMware, Inc. (Photon OS)",
            "hostname": "k3s-deadman-01.infra.plexplease.com",
            "role": "Out-of-Cluster Monitoring Deadman (Photon OS 5.0, 1 vCPU, 1GB RAM on ESXi-03)",
            "device_class": "Monitoring VM"
        },
        "10.10.10.52": {
            "vendor": "VMware, Inc. (Ubuntu)",
            "hostname": "dev-01.mgmt.plexplease.com",
            "role": "Development & AGY Operations VM; EnGenius EPC Cloud Controller Docker host (40 vCPU, 80GB RAM on ESXi-01)",
            "device_class": "Development VM"
        },
        "10.10.10.53": {
            "vendor": "ASUSTek / Custom PC",
            "hostname": "bench-01.infra.plexplease.com",
            "role": "AI Hardware Benchmark Node (Ubuntu 24.04, i7-13700K 16c/24t, 32GB RAM, Dual Intel Arc Pro B65 GPUs)",
            "device_class": "Physical Workstation"
        },
        "10.10.10.60": {
            "vendor": "NVIDIA Corporation",
            "hostname": "nvidia-shield.mgmt.plexplease.com",
            "role": "NVIDIA SHIELD TV (darcy / Google Cast Receiver / Android TV)",
            "device_class": "Smart Home / Media"
        },
        "10.10.10.61": {
            "vendor": "Dell EMC",
            "hostname": "sw-core-01-inband.infra.plexplease.com",
            "role": "Dell PowerSwitch N3224T-ON In-Band Routed Interface (Ethernet0 / Helix5 ASIC)",
            "device_class": "Network Switch"
        },
        "10.10.10.101": {
            "vendor": "LG Electronics",
            "hostname": "LGwebOSTV.mgmt.plexplease.com",
            "role": "LG webOS 4K Smart TV",
            "device_class": "Smart Home / Media"
        },
        "10.10.10.102": {
            "vendor": "Apple Inc. (Private MAC)",
            "hostname": "AlexisAwesome8.mgmt.plexplease.com",
            "role": "Apple iPhone",
            "device_class": "Mobile"
        },
        "10.10.10.110": {
            "vendor": "VMware, Inc.",
            "hostname": "lab-peer-n3224t.mgmt.plexplease.com",
            "role": "SONiC Switch Lab Peer VM (Dual-homed: 10.10.10.110 & 10.10.20.50 on LAB_N3224T)",
            "device_class": "Lab VM"
        },
        "10.10.10.111": {
            "vendor": "Google",
            "hostname": "Matthew-Pixel-10.mgmt.plexplease.com",
            "role": "Google Pixel 10 Smartphone",
            "device_class": "Mobile"
        },
        "10.10.10.113": {
            "vendor": "Google (Private MAC)",
            "hostname": "Pixel-10.mgmt.plexplease.com",
            "role": "Google Pixel 10 Smartphone",
            "device_class": "Mobile"
        },
        "10.10.10.115": {
            "vendor": "Amazon Technologies",
            "hostname": "echoshow-d3f6c8bac7f2e6a5.mgmt.plexplease.com",
            "role": "Amazon Echo Show Smart Display",
            "device_class": "Smart Home / IoT"
        },
        "10.10.10.118": {
            "vendor": "Chongqing Fugui / Foxconn",
            "hostname": "iot-printer.mgmt.plexplease.com",
            "role": "Network Laser/Inkjet Printer",
            "device_class": "Peripherals"
        },
        "10.10.10.124": {
            "vendor": "Onkyo Technology K.K.",
            "hostname": "Onkyo-TX-NR676-EAC531.mgmt.plexplease.com",
            "role": "Onkyo TX-NR676 7.2-Ch Network AV Receiver",
            "device_class": "Smart Home / Media"
        },
        "10.10.10.130": {
            "vendor": "Shenzhen Intellirocks (Govee)",
            "hostname": "govee-iot-130.mgmt.plexplease.com",
            "role": "Govee Smart LED Light Strip / Thermometer",
            "device_class": "Smart Home / IoT"
        },
        "10.10.10.131": {
            "vendor": "HP ProCurve",
            "hostname": "procurve-j9028b.mgmt.plexplease.com",
            "role": "HP ProCurve 1800-24G (J9028B) Managed Gigabit Switch",
            "device_class": "Network Switch"
        },
        "10.10.10.134": {
            "vendor": "Shenzhen Intellirocks (Govee)",
            "hostname": "govee-iot-134.mgmt.plexplease.com",
            "role": "Govee Smart LED Light Strip / Thermometer",
            "device_class": "Smart Home / IoT"
        },
        "10.10.10.135": {
            "vendor": "Shenzhen Intellirocks (Govee)",
            "hostname": "govee-iot-135.mgmt.plexplease.com",
            "role": "Govee Smart LED Light Strip / Thermometer",
            "device_class": "Smart Home / IoT"
        },
        "10.10.10.138": {
            "vendor": "Fitbit Inc.",
            "hostname": "Aria2.mgmt.plexplease.com",
            "role": "Fitbit Aria 2 Wi-Fi Smart Scale",
            "device_class": "Smart Home / IoT"
        },
        "10.10.10.140": {
            "vendor": "Intel Corporate",
            "hostname": "dcw139ma4574935.mgmt.plexplease.com",
            "role": "Intel Corporate Laptop / Workstation",
            "device_class": "Workstation"
        },
        "10.10.10.144": {
            "vendor": "Dell Inc.",
            "hostname": "talos-fty-fw0.mgmt.plexplease.com",
            "role": "Bare-Metal Talos Linux Node (Dell Latitude 5520, i7-1185G7, 24GB RAM, 2TB NVMe, K8s v1.36.2)",
            "device_class": "Kubernetes Node"
        },
        "10.10.10.146": {
            "vendor": "Dell Inc.",
            "hostname": "sonic.mgmt.plexplease.com",
            "role": "Dell PowerSwitch N3224T-ON Out-of-Band Management (SONiC 202511-slim2.0 / eth0)",
            "device_class": "Network Switch"
        },
        "10.10.10.150": {
            "vendor": "VMware, Inc.",
            "hostname": "sonic-build-01.mgmt.plexplease.com",
            "role": "SONiC NOS Compilation Build VM (Ubuntu 24.04, 60 vCPU, 96GB RAM on ESXi-01)",
            "device_class": "Build VM"
        },
        "10.10.10.195": {
            "vendor": "VMware, Inc.",
            "hostname": "homeassistant.mgmt.plexplease.com",
            "role": "Home Assistant OS Automation Server (4 vCPU, 4GB RAM on ESXi-01)",
            "device_class": "Smart Home Controller"
        },
        "10.10.10.236": {
            "vendor": "Google, Inc.",
            "hostname": "Nest-Thermostat-C725.mgmt.plexplease.com",
            "role": "Google Nest Smart Learning Thermostat",
            "device_class": "Smart Home / IoT"
        },
        "10.10.10.237": {
            "vendor": "Google, Inc.",
            "hostname": "Nest-Thermostat-B367.mgmt.plexplease.com",
            "role": "Google Nest Smart Learning Thermostat",
            "device_class": "Smart Home / IoT"
        },
        "10.10.10.239": {
            "vendor": "ASUSTek COMPUTER INC",
            "hostname": "pop-os.mgmt.plexplease.com",
            "role": "Dual-Boot Desktop (Pop!_OS partition on i7-13700K / Arc Pro B65 hardware)",
            "device_class": "Physical Workstation"
        },
        "10.10.10.242": {
            "vendor": "Intel Corporate",
            "hostname": "DESKTOP-DLA0R8I.mgmt.plexplease.com",
            "role": "Windows 11 Desktop PC",
            "device_class": "Physical Workstation"
        }
    }

    # Apply overrides and vendor lookups
    for c in clients:
        ip = c.get('ip')
        if ip in overrides:
            for k, v in overrides[ip].items():
                c[k] = v
        # Standardize smoke alarms
        elif c.get('vendor') == 'Walter Kidde Portabl':
            c['vendor'] = 'Walter Kidde Portable Equipment Inc.'
            c['role'] = 'Kidde Wireless Interconnected Smoke & Carbon Monoxide Detector'
            c['device_class'] = 'Safety / IoT'
        # Standardize Tuya
        elif c.get('vendor') == 'Tuya Smart Inc.':
            c['role'] = 'Tuya / Smart Life Wi-Fi Smart Plug & Power Monitor'
            c['device_class'] = 'Smart Home / IoT'
        # Standardize Espressif
        elif c.get('vendor') == 'Espressif Inc.':
            c['role'] = 'ESPHome / ESP32 Sensor & Automation Node'
            c['device_class'] = 'Smart Home / IoT'
        elif c.get('vendor') == 'Amazon Technologies':
            c['role'] = 'Amazon Echo Smart Speaker'
            c['device_class'] = 'Smart Home / IoT'

    # Save enriched clients
    with open('/home/dev/repos/homelab-gitops/config/network_clients.json', 'w') as f:
        json.dump(clients, f, indent=2)
    print("Updated /home/dev/repos/homelab-gitops/config/network_clients.json with enriched data.")

    # Generate docs/network_client_map.md
    now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    md = []
    md.append("# Homelab Network Client & Device Directory\n")
    md.append(f"> **Generated:** {now_str}  ")
    md.append("> **Data Sources:** pfSense Gateway (`10.10.10.1`), Technitium DNS/DHCP (`10.10.10.2`), vCenter API (`10.10.10.9`), IEEE OUI Database, and Device TLS Handshakes.  ")
    md.append(f"> **Scope:** {len(clients)} Total Discovered Devices across `10.10.10.0/24`.\n")
    md.append("---\n")

    # Categories
    categories = [
        ("Core Servers & Hypervisors", ["Physical Hypervisor", "Core Infrastructure", "Storage Appliance", "Server VM", "Kubernetes Control Plane", "Kubernetes Node", "Development VM", "Build VM", "Monitoring VM", "Lab VM"]),
        ("Network Switches, Routers & Access Points", ["Network / Firewall", "Network Switch", "Network AP"]),
        ("Workstations, PCs & Mobile Devices", ["Physical Workstation", "Workstation", "Mobile"]),
        ("Smart Home, Audio/Video, IoT & Safety", ["Smart Home Controller", "Smart Home / Media", "Smart Home / IoT", "Safety / IoT", "Peripherals"])
    ]

    for cat_title, classes in categories:
        md.append(f"## {cat_title}\n")
        md.append("| IPv4 Address | MAC Address | Hardware Vendor | Hostname / FQDN | Device Classification & Role | Status |")
        md.append("| :--- | :--- | :--- | :--- | :--- | :--- |")
        cat_clients = [c for c in clients if c.get('device_class') in classes]
        # Sort by IP numeric
        cat_clients.sort(key=lambda x: [int(p) for p in x['ip'].split('.') if p.isdigit()] or [0])
        for c in cat_clients:
            ip = f"`{c.get('ip')}`"
            mac = f"`{c.get('mac')}`" if c.get('mac') else "—"
            vendor = c.get('vendor', 'Unknown')
            host = f"`{c.get('hostname')}`" if c.get('hostname') and c.get('hostname') != 'Unknown' else "—"
            role = c.get('role', c.get('device_class', 'General Device'))
            status = c.get('status', 'Active')
            md.append(f"| {ip} | {mac} | {vendor} | {host} | {role} | {status} |")
        md.append("\n---\n")

    # Catch-all for uncategorized
    uncategorized = [c for c in clients if not any(c.get('device_class') in classes for _, classes in categories)]
    if uncategorized:
        md.append("## Other Discovered Devices\n")
        md.append("| IPv4 Address | MAC Address | Hardware Vendor | Hostname / FQDN | Status |")
        md.append("| :--- | :--- | :--- | :--- | :--- |")
        uncategorized.sort(key=lambda x: [int(p) for p in x['ip'].split('.') if p.isdigit()] or [0])
        for c in uncategorized:
            ip = f"`{c.get('ip')}`"
            mac = f"`{c.get('mac')}`" if c.get('mac') else "—"
            vendor = c.get('vendor', 'Unknown')
            host = f"`{c.get('hostname')}`" if c.get('hostname') and c.get('hostname') != 'Unknown' else "—"
            status = c.get('status', 'Active')
            md.append(f"| {ip} | {mac} | {vendor} | {host} | {status} |")
        md.append("\n---\n")

    doc_path = "/home/dev/repos/homelab-gitops/docs/network_client_map.md"
    with open(doc_path, 'w') as f:
        f.write("\n".join(md))
    print(f"Wrote updated documentation to {doc_path}")

if __name__ == "__main__":
    enrich()
