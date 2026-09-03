#!/usr/bin/env python3
"""
Build Authoritative Homelab Estate Inventory
Consolidates physical hardware, hypervisors, switches, APs, storage pools,
VMs, Kubernetes clusters, Docker containers, network clients, and DNS records.
"""

import json
import yaml
from datetime import datetime, timezone

def generate_estate():
    now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    
    estate = {
        "metadata": {
            "title": "EchoAres Homelab Infrastructure & Network Estate",
            "domain": "infra.plexplease.com",
            "site_cidr": "10.10.10.0/24",
            "public_domain": "plexplease.com",
            "last_updated": now_iso,
            "authoritative_source": "config/estate_inventory.yaml",
            "generated_by": "AGY Antigravity Pair Programmer",
            "version": "1.0.0"
        },
        "network": {
            "firewall_gateway": {
                "name": "pfsense",
                "fqdn": "pfsense.infra.plexplease.com",
                "lan_ipv4": "10.10.10.1",
                "lan_subnet": "10.10.10.0/24",
                "lan_mac": "00:50:56:9F:79:B2",
                "lan_iface": "vmx0",
                "wan_ipv4": "173.48.47.166",
                "wan_subnet": "173.48.47.0/24",
                "wan_gateway": "173.48.47.1",
                "wan_mac": "00:50:56:9F:98:09",
                "wan_iface": "vmx1",
                "os": "FreeBSD 15.0-CURRENT (pfSense-CE 2.8.1-RELEASE)",
                "hypervisor_host": "10.10.10.13 (ESXi-03)",
                "vm_id": "vm-7007",
                "status": "ONLINE",
                "notes": "Primary perimeter firewall & NAT gateway. DHCP disabled (delegated to Technitium at 10.10.10.2)."
            },
            "dns_dhcp_server": {
                "name": "dns-01",
                "fqdn": "dns-01.plexplease.com",
                "ipv4": "10.10.10.2",
                "mac": "00:50:56:9F:5E:32",
                "os": "VMware Photon OS 5.0 (64-bit)",
                "engine": "Technitium DNS Server (.NET 8)",
                "hypervisor_host": "10.10.10.11 (ESXi-01)",
                "vm_id": "vm-7035",
                "ports": {
                    "dns_udp_tcp": 53,
                    "dot": 853,
                    "doh": 443,
                    "web_api": 5380
                },
                "total_zones": 22,
                "total_records": 271,
                "active_dhcp_leases": 47,
                "active_scopes": ["MGMT_NET (10.10.10.1 - 10.10.10.254, enabled: true)"],
                "status": "ONLINE"
            },
            "switches": [
                {
                    "name": "sw-core-01",
                    "model": "Dell EMC PowerSwitch N3224T-ON",
                    "hw_sku": "DellEMC-N3224T",
                    "platform": "x86_64-dellemc_n3224t_c3338-r0",
                    "asic": "Broadcom Helix5 (BCM56370)",
                    "cpu": "Intel Atom C3338 dual-core @ 1.50 GHz",
                    "memory": "4 GiB DDR4 (3.8 GiB usable)",
                    "os": "SONiC.202511-n3224t-slim2.0-39ddd324e (Debian 13.6, Linux 6.12.41+deb13-sonic-amd64)",
                    "ports_summary": "24x 10M/100M/1G/2.5G/5G/10G Base-T + 4x 10G/25G SFP28 + 2x 100G QSFP28",
                    "interfaces": {
                        "eth0_oob": {
                            "ipv4": "10.10.10.146",
                            "subnet": "10.10.10.0/24",
                            "mac": "E8:B2:65:4B:A5:E8",
                            "fqdn": "sonic.mgmt.plexplease.com",
                            "description": "Out-of-band management RJ-45 (connected to ProCurve port 12)"
                        },
                        "ethernet0_inband": {
                            "ipv4": "10.10.10.61",
                            "subnet": "10.10.10.0/24",
                            "mac": "E8:B2:65:4B:A5:E9",
                            "description": "In-band routed uplink to MGMT_NET (connected to ProCurve port 15)"
                        },
                        "vlan100_lab": {
                            "ipv4": "10.10.20.1",
                            "subnet": "10.10.20.0/24",
                            "members": "Ethernet1 through Ethernet23 (untagged)",
                            "description": "Isolated switch lab test subnet"
                        },
                        "loopback0": {
                            "ipv4": "10.1.0.1",
                            "subnet": "10.1.0.1/32"
                        }
                    },
                    "lldp_neighbors": [
                        {"local_port": "Ethernet0", "remote_device": "procurve-j9028b", "remote_port": "15"},
                        {"local_port": "eth0", "remote_device": "procurve-j9028b", "remote_port": "12"},
                        {"local_port": "Ethernet16", "remote_mac": "ac:1f:6b:3a:e3:2a", "description": "Supermicro ESXi-01 vmnic0"}
                    ],
                    "status": "ONLINE"
                },
                {
                    "name": "procurve-j9028b",
                    "model": "HP ProCurve 1800-24G (J9028B)",
                    "vendor": "HP ProCurve / HPN Supply Chain",
                    "ipv4": "10.10.10.131",
                    "mac": "00:1F:28:D3:66:80",
                    "fqdn": "procurve-j9028b.mgmt.plexplease.com",
                    "ports": "24x Gigabit RJ-45",
                    "status": "ONLINE"
                }
            ],
            "access_points": [
                {
                    "name": "ap-01",
                    "model": "EnGenius EWS377-FIT",
                    "vendor": "EnGenius Technologies",
                    "ipv4": "10.10.10.6",
                    "mac": "C4:E3:CE:68:E2:50",
                    "fqdn": "ap-01.infra.plexplease.com",
                    "location": "Top Floor",
                    "notes": "Top floor high-density Wi-Fi 6 access point",
                    "type": "Wi-Fi 6 (802.11ax) Dual-Band 4x4 Managed AP",
                    "managed_by": "EnGenius Private Cloud (EPC) on k3s-01 (wifi.infra.plexplease.com)",
                    "status": "ONLINE"
                },
                {
                    "name": "ap-02",
                    "model": "EnGenius EWS377-FIT",
                    "vendor": "EnGenius Technologies",
                    "ipv4": "10.10.10.8",
                    "mac": "88:DC:97:1C:BD:7C",
                    "fqdn": "ap-02.infra.plexplease.com",
                    "location": "First Floor",
                    "notes": "First floor high-density Wi-Fi 6 access point",
                    "type": "Wi-Fi 6 (802.11ax) Dual-Band 4x4 Managed AP",
                    "managed_by": "EnGenius Private Cloud (EPC) on k3s-01 (wifi.infra.plexplease.com)",
                    "status": "ONLINE"
                },
                {
                    "name": "asus-ap-01",
                    "model": "ASUS Wireless AP",
                    "vendor": "ASUSTek COMPUTER INC",
                    "ipv4": "10.10.10.7",
                    "mac": "C8:7F:54:28:2B:80",
                    "fqdn": "asus-ap-01.infra.plexplease.com",
                    "type": "Wireless Access Point (Legacy)",
                    "status": "ONLINE"
                }
            ]
        },
        "physical_servers": [
            {
                "id": "srv-01",
                "role": "Primary ESXi Hypervisor",
                "name": "esxi-01",
                "fqdn": "esxi-01.mgmt.plexplease.com",
                "mgmt_ipv4": "10.10.10.11",
                "mgmt_mac": "00:50:56:68:E1:EF",
                "bmc": {
                    "name": "ipmi-01",
                    "fqdn": "ipmi-01.mgmt.plexplease.com",
                    "aliases": ["esxi-01-ipmi.mgmt.plexplease.com", "esxi-01-bmc.mgmt.plexplease.com"],
                    "ipv4_reserved": "10.10.10.10",
                    "current_dhcp_lease": "10.10.10.104",
                    "mac": "AC:1F:6B:3B:93:7F",
                    "vendor": "Super Micro Computer, Inc.",
                    "chipset": "ASPEED AST2500",
                    "redfish_version": "1.8.0",
                    "ports": {"http": 80, "https": 443, "ssh": 22, "rmcp": 623},
                    "status": "ONLINE"
                },
                "hardware": {
                    "motherboard": "Supermicro X11DPi-N(T)",
                    "chassis": "Supermicro 2U / 4U Rackmount Server",
                    "bios_version": "3.6",
                    "bios_date": "2022-01-25",
                    "cpu": "Dual Genuine Intel(R) CPU 0000%@ (Xeon Scalable Platinum 8160/8260 QS/ES)",
                    "cpu_topology": "2 Sockets, 48 Physical Cores, 96 Hardware Threads @ 2.60 GHz",
                    "ram_installed": "382.7 GiB DDR4 ECC Registered",
                    "physical_nics": [
                        {"device": "vmnic0", "mac": "AC:1F:6B:3A:E3:2A", "driver": "i40en", "model": "Intel X710/XL710 10/40GbE", "connected_to": "Dell N3224T port Ethernet16"},
                        {"device": "vmnic1", "mac": "AC:1F:6B:3A:E3:2B", "driver": "i40en", "model": "Intel X710/XL710 10/40GbE"}
                    ],
                    "pcie_passthrough": [
                        "Broadcom / LSI SAS2308 PCI-Express Fusion-MPT SAS-2 (to TrueNAS)",
                        "Intel Optane SSD P1600X 118GB NVMe (to TrueNAS)",
                        "Samsung 980 PRO 2TB NVMe (to TrueNAS)"
                    ]
                },
                "hypervisor": {
                    "engine": "VMware ESXi",
                    "version": "8.0.3",
                    "build": "25205845",
                    "vcenter_host_id": "host-7012",
                    "vcenter_status": "CONNECTED / POWERED_ON"
                },
                "hosted_vms": [
                    "dev-01.mgmt.plexplease.com (vm-7036)",
                    "k3s-01 (vm-9073)",
                    "TRUENAS.PLEXPLEASE.COM (vm-7027)",
                    "HOMELAB (vm-7030)",
                    "sonic-build-01 (vm-12002)",
                    "dns-01.mgmt.plexplease.com (vm-7035)",
                    "vCenter-01 (vm-7031)",
                    "home-assistant (vm-7034)",
                    "lab-peer-n3224t (vm-13002)",
                    "vCLS-826b8000 (vm-7041)",
                    "bench-lab-01 (vm-12001, poweredOff)",
                    "nut-ups (vm-11001, poweredOff)",
                    "photon-test-base (poweredOff)",
                    "epc.infra.plexplease.com (vm-9044, poweredOff)",
                    "ubuntu-24.04-lts-golden (vm-9028, poweredOff)",
                    "photon-mcp (vm-7796, poweredOff)"
                ],
                "status": "ONLINE"
            },
            {
                "id": "srv-02",
                "role": "Edge Appliance ESXi Hypervisor",
                "name": "esxi-03",
                "fqdn": "esxi-03.mgmt.plexplease.com",
                "mgmt_ipv4": "10.10.10.13",
                "mgmt_mac": "00:50:56:61:8D:A4",
                "hardware": {
                    "model": "Topton / CWWK Multi-NIC Mini PC (Default string 6083002)",
                    "bios_version": "5.27",
                    "bios_date": "2023-06-26",
                    "cpu": "Intel Core i3-N305 (Alder Lake-N)",
                    "cpu_topology": "1 Socket, 8 Physical Cores, 8 Threads @ 1.80 GHz",
                    "ram_installed": "15.7 GiB DDR5",
                    "physical_nics": [
                        {"device": "vmnic0", "mac": "A8:B8:E0:0A:50:B2", "driver": "ixgben", "model": "Intel 10GbE SFP+"},
                        {"device": "vmnic2", "mac": "34:1A:4C:04:23:23", "driver": "cndi_igc", "model": "Intel i226 2.5GbE"},
                        {"device": "vmnic3", "mac": "34:1A:4C:04:23:24", "driver": "cndi_igc", "model": "Intel i226 2.5GbE"}
                    ]
                },
                "hypervisor": {
                    "engine": "VMware ESXi",
                    "version": "8.0.3",
                    "build": "25205845",
                    "vcenter_host_id": "host-7001",
                    "vcenter_status": "CONNECTED / POWERED_ON"
                },
                "hosted_vms": [
                    "PF-SENSE (vm-7007)",
                    "k3s-deadman (vm-11006)",
                    "vCLS-03000200 (vm-7797)",
                    "OPNsense (vm-7009, poweredOff)"
                ],
                "status": "ONLINE"
            },
            {
                "id": "srv-03",
                "role": "Bare-Metal Talos Kubernetes Node",
                "name": "talos-fty-fw0",
                "fqdn": "talos-fty-fw0.mgmt.plexplease.com",
                "ipv4": "10.10.10.144",
                "mac": "C0:25:A5:03:CF:FC",
                "hardware": {
                    "chassis": "Dell Latitude 5520 Laptop",
                    "service_tag": "9SHLP93",
                    "system_uuid": "4c4c4544-0053-4810-804c-b9c04f503933",
                    "bios_version": "1.4.2",
                    "bios_date": "2021-03-09",
                    "cpu": "11th Gen Intel(R) Core(TM) i7-1185G7 @ 3.00GHz",
                    "cpu_topology": "4 Cores, 8 Threads",
                    "ram_installed": "23.7 GiB DDR4",
                    "storage": "2 TB NVMe SSD"
                },
                "os": "Talos Linux v1.13.5 (Linux 6.18.36-talos)",
                "kubernetes": {
                    "cluster_role": "control-plane, worker",
                    "k8s_version": "v1.36.2",
                    "pod_cidr": "10.244.0.0/24",
                    "cni": "Flannel v0.28.5 (VXLAN)"
                },
                "notes": "Repurposed from historical ESXi host (formerly host-9074 at 10.10.10.102 in vCenter) into bare-metal Talos cluster.",
                "status": "ONLINE"
            },
            {
                "id": "srv-04",
                "role": "AI Hardware Benchmark & GPU Workstation",
                "name": "bench-01 / pop-os",
                "fqdn_bench": "bench-01.infra.plexplease.com",
                "fqdn_popos": "pop-os.mgmt.plexplease.com",
                "current_boot_ipv4": "10.10.10.53",
                "popos_dhcp_ipv4": "10.10.10.239",
                "mac": "04:42:1A:E9:D1:B3",
                "hardware": {
                    "motherboard": "ASUS Intel Z690",
                    "cpu": "13th Gen Intel(R) Core(TM) i7-13700K (Raptor Lake)",
                    "cpu_topology": "16 Cores (8P + 8E), 24 Threads @ 5.40 GHz Boost",
                    "ram_installed": "31 GiB DDR4/DDR5",
                    "gpus": [
                        {"device": "0000:03:00.0", "vendor_id": "8086:e222", "model": "Intel Arc Pro B65 (Battlemage BMG-G21, 16GB GDDR6, PCIe 4.0 x8)"},
                        {"device": "0000:09:00.0", "vendor_id": "8086:e222", "model": "Intel Arc Pro B65 (Battlemage BMG-G21, 16GB GDDR6, PCIe 4.0 x8)"},
                        {"device": "0000:00:02.0", "model": "Intel UHD Graphics 770 (iGPU)"}
                    ],
                    "storage": [
                        {"device": "nvme0n1", "size": "931.5 GB", "model": "M.2 NVMe SSD", "mounts": ["/boot/efi", "/", "/mnt/aistore (582GB)"]},
                        {"device": "sda", "size": "115.9 GB", "type": "USB Drive"},
                        {"device": "sdb", "size": "14.8 GB", "type": "USB Drive"}
                    ]
                },
                "current_os": "Ubuntu 24.04 (Linux 6.17.0-1009-intel #9-Ubuntu SMP PREEMPT_DYNAMIC)",
                "active_workload": "vLLM 0.7+ XPU container (vb_0000_03_00_0) serving Qwen/Qwen2.5-7B-Instruct-GPTQ-Int4 on GPU 03:00.0",
                "status": "ONLINE"
            }
        ],
        "storage": {
            "appliance": {
                "name": "TRUENAS",
                "fqdn": "truenas-01.mgmt.plexplease.com",
                "ipv4": "10.10.10.20",
                "mac": "00:50:56:A1:79:C7",
                "os": "TrueNAS SCALE 25.04.2.6 (Fangtooth)",
                "vm_host": "10.10.10.11 (ESXi-01)",
                "vcpus": 8,
                "ram_mb": 81920,
                "passthrough_hardware": {
                    "sas_hba": "Broadcom / LSI SAS2308 PCI-Express Fusion-MPT SAS-2 (rev 05)",
                    "slog_nvme": "Intel Corporation Optane NVMe SSD P1600X 118GB (SSDPEK1A118GA)",
                    "vmstore_nvme": "Samsung Electronics 980 PRO 2TB NVMe"
                }
            },
            "zfs_pools": [
                {
                    "name": "WHITEBOX",
                    "type": "RAIDZ2",
                    "raw_size": "146 TB",
                    "allocated": "120 TB",
                    "free": "25.2 TB",
                    "health": "ONLINE",
                    "vdevs": "8x 20TB WD Red Pro HDDs (WDC WD201KFGX-68BKJN0: sdd, sde, sdh, sdi, sdl, sdm, sdp, sdq)",
                    "slog_device": "Intel Optane P1600X partition 3",
                    "datasets": [
                        {"name": "WHITEBOX/MEDIA/MOVIES", "used": "54.1 TB", "description": "1080p / 720p Movie library"},
                        {"name": "WHITEBOX/MEDIA/TV", "used": "27.7 TB", "description": "Television series library"},
                        {"name": "WHITEBOX/MEDIA/4K_MOVIES", "used": "3.18 TB", "description": "UHD HDR Movie library"},
                        {"name": "WHITEBOX/MEDIA/DOWNLOAD", "used": "130 GB", "description": "Usenet / Torrent staging"},
                        {"name": "WHITEBOX/WINDOWS_BACKUP", "used": "265 GB", "description": "Desktop PC client system images"},
                        {"name": "WHITEBOX/nexus", "used": "1.07 TB", "description": "Nexus Docker registry & PyPI storage"},
                        {"name": "WHITEBOX/k3s-object-store", "used": "124 GB", "description": "Kubernetes MinIO S3 backing store"},
                        {"name": "WHITEBOX/backups", "used": "74.9 GB", "description": "TrueNAS system configuration & app backups"}
                    ]
                },
                {
                    "name": "K3S_HDD",
                    "type": "3x Mirrors (Striped Mirrors)",
                    "raw_size": "24.5 TB",
                    "allocated": "28.5 GB",
                    "free": "24.5 TB",
                    "health": "ONLINE",
                    "vdevs": "Mirror 0: 2x 12TB WD120EDAZ (sdc, sdf) | Mirror 1: 2x 12TB WD120EDAZ (sdj, sdn) | Mirror 2: 2x 3TB WD30EFRX (sdb, sdg)",
                    "slog_device": "Intel Optane P1600X partition 1",
                    "purpose": "Kubernetes Democratic-CSI persistent volumes (iSCSI & NFS)"
                },
                {
                    "name": "vmstore",
                    "type": "Single NVMe",
                    "raw_size": "1.81 TB",
                    "allocated": "11.0 GB",
                    "free": "1.80 TB",
                    "health": "ONLINE",
                    "vdevs": "Samsung 980 PRO 2TB NVMe SSD",
                    "slog_device": "Intel Optane P1600X partition 2",
                    "purpose": "VMware ESXi iSCSI datastore (iSCSI_vmware LUN)"
                },
                {
                    "name": "boot-pool",
                    "type": "Single Disk",
                    "raw_size": "31.5 GB",
                    "allocated": "22.3 GB",
                    "health": "ONLINE",
                    "vdevs": "VMware Virtual Disk 32GB (sda2)"
                }
            ]
        },
        "virtual_machines": [
            {
                "name": "k3s-01",
                "vm_id": "vm-9073",
                "host": "10.10.10.11 (ESXi-01)",
                "power_state": "poweredOn",
                "vcpus": 16,
                "ram_mb": 65536,
                "primary_ipv4": "10.10.10.50",
                "mac": "00:50:56:9F:71:25",
                "os": "Fedora CoreOS 44.20260607.3.1 (Linux 7.0.11-200.fc44.x86_64)",
                "k8s_version": "v1.35.5+k3s1",
                "container_runtime": "containerd://2.2.3-k3s1",
                "role": "Single-node production Kubernetes cluster (k3s-01)",
                "storage": "Democratic-CSI (iSCSI/NFS to TrueNAS 10.10.10.20) + local-path"
            },
            {
                "name": "dev-01.mgmt.plexplease.com",
                "vm_id": "vm-7036",
                "host": "10.10.10.11 (ESXi-01)",
                "power_state": "poweredOn",
                "vcpus": 40,
                "ram_mb": 81920,
                "primary_ipv4": "10.10.10.52",
                "mac": "00:50:56:9F:A8:B7",
                "os": "Ubuntu Linux 24.04 (Linux 6.8.0-generic)",
                "role": "Primary development & agent operations node; EnGenius EPC Cloud Controller Docker host"
            },
            {
                "name": "TRUENAS.PLEXPLEASE.COM",
                "vm_id": "vm-7027",
                "host": "10.10.10.11 (ESXi-01)",
                "power_state": "poweredOn",
                "vcpus": 8,
                "ram_mb": 81920,
                "primary_ipv4": "10.10.10.20",
                "mac": "00:50:56:A1:79:C7",
                "os": "TrueNAS SCALE 25.04.2.6 (Debian 12)",
                "role": "Central ZFS storage appliance"
            },
            {
                "name": "HOMELAB",
                "vm_id": "vm-7030",
                "host": "10.10.10.11 (ESXi-01)",
                "power_state": "poweredOn",
                "vcpus": 16,
                "ram_mb": 32768,
                "primary_ipv4": "10.10.10.30",
                "mac": "00:0C:29:C8:A8:14",
                "os": "Ubuntu Linux (Linux 7.0.0-30-generic)",
                "role": "Legacy Docker Compose application host (30 running containers)"
            },
            {
                "name": "sonic-build-01",
                "vm_id": "vm-12002",
                "host": "10.10.10.11 (ESXi-01)",
                "power_state": "poweredOn",
                "vcpus": 60,
                "ram_mb": 98304,
                "primary_ipv4": "10.10.10.150",
                "mac": "00:50:56:9F:F1:2A",
                "os": "Ubuntu 24.04 LTS (Linux 6.8.0-138-generic)",
                "role": "SONiC NOS & Broadcom SDK compilation / build VM"
            },
            {
                "name": "dns-01.mgmt.plexplease.com",
                "vm_id": "vm-7035",
                "host": "10.10.10.11 (ESXi-01)",
                "power_state": "poweredOn",
                "vcpus": 4,
                "ram_mb": 8192,
                "primary_ipv4": "10.10.10.2",
                "mac": "00:50:56:9F:5E:32",
                "os": "VMware Photon OS 5.0",
                "role": "Authoritative DNS & DHCP server (Technitium)"
            },
            {
                "name": "vCenter-01",
                "vm_id": "vm-7031",
                "host": "10.10.10.11 (ESXi-01)",
                "power_state": "poweredOn",
                "vcpus": 4,
                "ram_mb": 21504,
                "primary_ipv4": "10.10.10.9",
                "mac": "00:0C:29:A9:92:E0",
                "os": "VMware vCenter Server Appliance 8.0 (Photon OS)",
                "role": "VMware vSphere vCenter Management Appliance"
            },
            {
                "name": "home-assistant",
                "vm_id": "vm-7034",
                "host": "10.10.10.11 (ESXi-01)",
                "power_state": "poweredOn",
                "vcpus": 4,
                "ram_mb": 4096,
                "primary_ipv4": "10.10.10.195",
                "mac": "00:50:56:9F:0C:FB",
                "os": "Home Assistant OS",
                "role": "Smart home automation controller"
            },
            {
                "name": "lab-peer-n3224t",
                "vm_id": "vm-13002",
                "host": "10.10.10.11 (ESXi-01)",
                "power_state": "poweredOn",
                "vcpus": 2,
                "ram_mb": 2048,
                "primary_ipv4": "10.10.10.110",
                "secondary_ipv4": "10.10.20.50 (on LAB_N3224T vSwitch portgroup)",
                "mac": "00:50:56:9F:20:11",
                "os": "Ubuntu Linux (64-bit)",
                "role": "SONiC switch lab peer & validation endpoint"
            },
            {
                "name": "PF-SENSE",
                "vm_id": "vm-7007",
                "host": "10.10.10.13 (ESXi-03)",
                "power_state": "poweredOn",
                "vcpus": 4,
                "ram_mb": 4096,
                "primary_ipv4": "10.10.10.1",
                "mac": "00:50:56:9F:79:B2",
                "os": "FreeBSD 15.0-CURRENT (pfSense-CE 2.8.1-RELEASE)",
                "role": "Edge router & firewall"
            },
            {
                "name": "k3s-deadman",
                "vm_id": "vm-11006",
                "host": "10.10.10.13 (ESXi-03)",
                "power_state": "poweredOn",
                "vcpus": 1,
                "ram_mb": 1024,
                "primary_ipv4": "10.10.10.51",
                "mac": "00:50:56:2D:55:01",
                "os": "VMware Photon OS 5.0 (Linux 6.12.78-3.ph5-esx)",
                "role": "Independent out-of-cluster heartbeat receiver"
            },
            {
                "name": "vCLS-826b8000",
                "vm_id": "vm-7041",
                "host": "10.10.10.11 (ESXi-01)",
                "power_state": "poweredOn",
                "vcpus": 1,
                "ram_mb": 160,
                "role": "VMware Cluster Services System VM"
            },
            {
                "name": "vCLS-03000200",
                "vm_id": "vm-7797",
                "host": "10.10.10.13 (ESXi-03)",
                "power_state": "poweredOn",
                "vcpus": 1,
                "ram_mb": 160,
                "role": "VMware Cluster Services System VM"
            },
            {
                "name": "nut-ups",
                "vm_id": "vm-11001",
                "host": "10.10.10.11 (ESXi-01)",
                "power_state": "poweredOff",
                "vcpus": 1,
                "ram_mb": 1024,
                "mac": "00:50:56:9F:AD:6C",
                "target_ipv4": "10.10.10.139",
                "role": "PeaNUT / Network UPS Tools monitor (Currently OFFLINE)"
            },
            {
                "name": "OPNsense",
                "vm_id": "vm-7009",
                "host": "10.10.10.13 (ESXi-03)",
                "power_state": "poweredOff",
                "vcpus": 4,
                "ram_mb": 4096,
                "mac": "00:50:56:8B:AC:C6",
                "role": "Secondary firewall appliance (Standby / Inactive)"
            },
            {
                "name": "bench-lab-01",
                "vm_id": "vm-12001",
                "host": "10.10.10.11 (ESXi-01)",
                "power_state": "poweredOff",
                "vcpus": 32,
                "ram_mb": 24576,
                "mac": "00:50:56:9F:34:69",
                "role": "Virtual benchmarking worker (poweredOff)"
            },
            {
                "name": "epc.infra.plexplease.com",
                "vm_id": "vm-9044",
                "host": "10.10.10.11 (ESXi-01)",
                "power_state": "poweredOff",
                "vcpus": 4,
                "ram_mb": 8192,
                "mac": "00:50:56:9F:63:BB",
                "role": "Legacy EnGenius EPC VM (superseded by Docker on dev-01)"
            },
            {
                "name": "photon-mcp",
                "vm_id": "vm-7796",
                "host": "10.10.10.11 (ESXi-01)",
                "power_state": "poweredOff",
                "vcpus": 16,
                "ram_mb": 8192,
                "mac": "00:50:56:9F:1F:52",
                "role": "Legacy MCP container VM (superseded)"
            },
            {
                "name": "ubuntu-24.04-lts-golden",
                "vm_id": "vm-9028",
                "host": "10.10.10.11 (ESXi-01)",
                "power_state": "poweredOff",
                "vcpus": 2,
                "ram_mb": 2048,
                "mac": "00:50:56:9F:E3:95",
                "role": "Golden template VM"
            },
            {
                "name": "photon-test-base",
                "host": "10.10.10.11 (ESXi-01)",
                "power_state": "poweredOff",
                "vcpus": 2,
                "ram_mb": 4096,
                "mac": "00:50:56:9F:ED:D9",
                "role": "Test VM"
            }
        ],
        "kubernetes_clusters": [
            {
                "name": "k3s-01",
                "role": "Production Platform Cluster",
                "control_plane_ip": "10.10.10.50",
                "node_name": "k3s-01.infra.plexplease.com",
                "distribution": "k3s v1.35.5+k3s1",
                "container_runtime": "containerd://2.2.3-k3s1",
                "os": "Fedora CoreOS 44.20260607.3.1",
                "kernel": "7.0.11-200.fc44.x86_64",
                "pod_cidr": "10.42.0.0/16",
                "service_cidr": "10.43.0.0/16",
                "dns_resolver": "10.43.0.10 (CoreDNS)",
                "ingress_controller": "Traefik v3 (ports 80, 443)",
                "namespaces": [
                    "ai-gateway", "ai-gateway-staging", "argocd", "backup", "cert-manager",
                    "database", "default", "democratic-csi", "external-dns", "external-secrets",
                    "github-runner", "homarr", "identity", "kube-system", "mlflow", "nexus",
                    "notifications", "observability", "sample-app", "server-partpicker"
                ],
                "core_deployments": [
                    {"name": "argocd-server", "namespace": "argocd", "ingress": "argocd.infra.plexplease.com"},
                    {"name": "authentik-server", "namespace": "identity", "ingress": "authentik.infra.plexplease.com"},
                    {"name": "gateway-engine", "namespace": "ai-gateway", "ingress": "gateway.infra.plexplease.com"},
                    {"name": "agent-gateway", "namespace": "ai-gateway", "ingress": "bifrost.infra.plexplease.com"},
                    {"name": "cpa-manager", "namespace": "ai-gateway", "ingress": "cpa.infra.plexplease.com"},
                    {"name": "langfuse-web", "namespace": "ai-gateway", "ingress": "langfuse.infra.plexplease.com"},
                    {"name": "nexus-0", "namespace": "nexus", "ingress": "nexus.infra.plexplease.com"},
                    {"name": "grafana", "namespace": "observability", "ingress": "grafana.infra.plexplease.com"},
                    {"name": "prometheus", "namespace": "observability", "ingress": "prometheus.infra.plexplease.com"},
                    {"name": "alertmanager", "namespace": "observability", "ingress": "alertmanager.infra.plexplease.com"},
                    {"name": "loki-0", "namespace": "observability", "port": 3100},
                    {"name": "homarr", "namespace": "homarr", "ingress": "homarr.infra.plexplease.com"},
                    {"name": "apprise", "namespace": "notifications", "ingress": "apprise.infra.plexplease.com"},
                    {"name": "mlflow", "namespace": "mlflow", "ingress": "mlflow.infra.plexplease.com"},
                    {"name": "arc-runner", "namespace": "github-runner", "role": "Ephemeral GitHub Actions Runner"}
                ],
                "reverse_proxied_external_services": [
                    {"ingress": "pfsense.infra.plexplease.com", "target": "10.10.10.1:443"},
                    {"ingress": "technitium.infra.plexplease.com", "target": "10.10.10.2:5380"},
                    {"ingress": "vcenter.infra.plexplease.com", "target": "10.10.10.9:443"},
                    {"ingress": "esxi-01.infra.plexplease.com", "target": "10.10.10.11:443"},
                    {"ingress": "esxi-03.infra.plexplease.com", "target": "10.10.10.13:443"},
                    {"ingress": "truenas.infra.plexplease.com", "target": "10.10.10.20:443"},
                    {"ingress": "openbao.infra.plexplease.com", "target": "10.10.10.30:8201"},
                    {"ingress": "plex.infra.plexplease.com", "target": "10.10.10.30:32400"},
                    {"ingress": "sabnzbd.infra.plexplease.com", "target": "10.10.10.30:8080"},
                    {"ingress": "home-assistant.infra.plexplease.com", "target": "10.10.10.195:8123"},
                    {"ingress": "switch.infra.plexplease.com", "target": "10.10.10.4:80 (switch OOB is 10.10.10.146)"},
                    {"ingress": "ap.infra.plexplease.com", "target": "10.10.10.6:80"},
                    {"ingress": "peanut.infra.plexplease.com", "target": "10.10.10.139:8080 (currently offline)"}
                ]
            },
            {
                "name": "talos-cluster",
                "role": "Edge Bare-Metal Talos Cluster",
                "control_plane_ip": "10.10.10.144",
                "node_name": "talos-fty-fw0",
                "distribution": "Talos Linux v1.13.5",
                "kubernetes_version": "v1.36.2",
                "container_runtime": "containerd://2.2.5",
                "os": "Talos Linux (Linux 6.18.36-talos amd64)",
                "hardware_chassis": "Dell Latitude 5520 Laptop (Service Tag: 9SHLP93)",
                "pod_cidr": "10.244.0.0/24",
                "service_cidr": "10.96.0.0/12",
                "cni": "Flannel v0.28.5 (VXLAN)",
                "status": "ONLINE"
            }
        ],
        "docker_hosts": [
            {
                "host_name": "homelab",
                "ipv4": "10.10.10.30",
                "os": "Ubuntu Linux (Linux 7.0.0-30-generic)",
                "vcpus": 16,
                "ram_mb": 32768,
                "running_containers_count": 30,
                "containers": [
                    {"name": "edge-nginx-proxy-manager-1", "image": "jc21/nginx-proxy-manager:latest", "ports": ["80", "81", "443"]},
                    {"name": "plex", "image": "lscr.io/linuxserver/plex:latest", "ports": ["32400 (host net)"]},
                    {"name": "sonarr", "image": "lscr.io/linuxserver/sonarr:latest", "ports": ["8988"]},
                    {"name": "sabnzbd", "image": "lscr.io/linuxserver/sabnzbd:latest", "ports": ["8080"]},
                    {"name": "radarr4k", "image": "lscr.io/linuxserver/radarr:latest", "ports": ["7879"]},
                    {"name": "radarr", "image": "lscr.io/linuxserver/radarr:latest", "ports": ["7870"]},
                    {"name": "ombi", "image": "lscr.io/linuxserver/ombi:latest", "ports": ["3579"]},
                    {"name": "hydra2", "image": "lscr.io/linuxserver/nzbhydra2:latest", "ports": ["5076"]},
                    {"name": "secrets-openbao-1", "image": "ghcr.io/openbao/openbao:latest", "ports": ["8201->8200"]},
                    {"name": "nexus", "image": "sonatype/nexus3:latest", "ports": ["8081", "8082"]},
                    {"name": "db-stack-redis", "image": "redis:alpine", "ports": ["6379"]},
                    {"name": "db-stack-postgres", "image": "postgres:16-alpine", "ports": ["5432"]},
                    {"name": "db-stack-clickhouse", "image": "clickhouse/clickhouse-server:24.3-alpine", "ports": ["8123", "9000"]},
                    {"name": "secrets-op-connect-api-1", "image": "1password/connect-api:1.8.2", "ports": ["8200->8080"]},
                    {"name": "secrets-op-connect-sync-1", "image": "1password/connect-sync:1.8.2", "ports": []},
                    {"name": "ai-stack-litellm", "image": "ghcr.io/berriai/litellm:main-latest", "ports": ["4000"]},
                    {"name": "ai-stack-langfuse", "image": "langfuse/langfuse:3", "ports": ["3000"]},
                    {"name": "ai-stack-clickhouse", "image": "clickhouse/clickhouse-server:24.3-alpine", "ports": ["8123", "9000"]},
                    {"name": "ai-stack-postgres", "image": "postgres:16-alpine", "ports": ["5432"]},
                    {"name": "ai-stack-redis", "image": "redis:alpine", "ports": ["6379"]},
                    {"name": "connectivity-cloudflared-plexplease-1", "image": "cloudflare/cloudflared:latest", "ports": []},
                    {"name": "observability-cadvisor-1", "image": "gcr.io/cadvisor/cadvisor:latest", "ports": ["8088"]},
                    {"name": "uptime-kuma", "image": "louislam/uptime-kuma:latest", "ports": ["3002->3001"]},
                    {"name": "observability-loki-1", "image": "grafana/loki:latest", "ports": ["3100"]},
                    {"name": "observability-prometheus-1", "image": "prom/prometheus:latest", "ports": ["9090"]},
                    {"name": "observability-alloy-1", "image": "grafana/alloy:latest", "ports": ["12345", "1514/udp", "1515/udp"]},
                    {"name": "observability-node-exporter-1", "image": "prom/node-exporter:latest", "ports": ["9100"]},
                    {"name": "observability-grafana-1", "image": "grafana/grafana:latest", "ports": ["3000"]},
                    {"name": "notifications-email-relay-1", "image": "boky/postfix:latest", "ports": ["25", "587"]},
                    {"name": "dockhand", "image": "fnsys/dockhand:latest", "ports": ["3001->3000"]}
                ]
            },
            {
                "host_name": "dev-01",
                "ipv4": "10.10.10.52",
                "os": "Ubuntu 24.04 (Linux 6.8.0-generic)",
                "vcpus": 40,
                "ram_mb": 81920,
                "running_containers_count": 6,
                "containers": [
                    {"name": "epc-api", "image": "public.ecr.aws/d3g4m7o9/epc-api:1.9.0", "ports": ["443", "8088->80"]},
                    {"name": "epc-raccoon", "image": "public.ecr.aws/d3g4m7o9/epc-raccoon:1.9.0", "ports": ["80"]},
                    {"name": "epc-mdns", "image": "public.ecr.aws/d3g4m7o9/epc-mdns:1.9.0", "ports": []},
                    {"name": "epc-otter", "image": "public.ecr.aws/d3g4m7o9/epc-otter:1.9.0", "ports": []},
                    {"name": "epc-db", "image": "public.ecr.aws/d3g4m7o9/epc-db:1.9.0", "ports": []},
                    {"name": "busy_northcutt", "image": "grafana/alloy:v1.17.0", "ports": []}
                ]
            },
            {
                "host_name": "bench-01",
                "ipv4": "10.10.10.53",
                "os": "Ubuntu 24.04 (Linux 6.17.0-1009-intel)",
                "running_containers_count": 1,
                "containers": [
                    {"name": "vb_0000_03_00_0", "image": "vllm-xpu (local image)", "ports": ["8000"], "role": "vLLM serving Qwen2.5-7B-Instruct-GPTQ-Int4 on Intel Arc Pro B65"}
                ]
            }
        ],
        "discrepancies_and_resolutions": [
            {
                "id": "DISC-01",
                "title": "Subnet / VLAN Segmentation Drift",
                "documented": "VLAN.md & network.yaml specify 8 separate VLANs (10=MGMT, 20=SERVERS, 30=CLIENTS, 40=IOT, etc.). Technitium has disabled scopes shifted by +10.",
                "empirical_evidence": "pfSense has only vmx0 (10.10.10.1/24) with no VLAN sub-interfaces. All 61 physical & virtual nodes reside on 10.10.10.0/24 flat network. Dell Switch N3224T has isolated Vlan100 (10.10.20.1/24) for lab testing.",
                "resolution": "State recorded truthfully as single active broadcast domain 10.10.10.0/24. Full VLAN segmentation flagged for future phased rollout."
            },
            {
                "id": "DISC-02",
                "title": "Dell Latitude 5520 Identity (ESXi Host vs. Talos Linux Node)",
                "documented": "vCenter contains disconnected host-9074 (10.10.10.102, Dell Latitude 5520, Service Tag 9SHLP93). network_client_map.md labeled 10.10.10.144 as 'Dell Appliance / Firewall'.",
                "empirical_evidence": "Talos node talos-fty-fw0 at 10.10.10.144 has DMI UUID 4c4c4544-0053-4810-804c-b9c04f503933 (DELL + 9SHLP93). Address 10.10.10.102 in DHCP is currently leased to an iPhone.",
                "resolution": "Resolved: The laptop was wiped from ESXi and reinstalled as bare-metal Talos node talos-fty-fw0. Obsolete vCenter record host-9074 marked for removal."
            },
            {
                "id": "DISC-03",
                "title": "ESXi Host Numbering (esxi-02 vs esxi-03)",
                "documented": "1Password VM inventory labeled 10.10.10.13 as 'ESXi 2'.",
                "empirical_evidence": "Technitium forward/reverse DNS, TLS certs, and vCenter designate 10.10.10.13 as esxi-03.mgmt.plexplease.com. (Former esxi-02 was the laptop at .102).",
                "resolution": "Resolved: Authoritative hostname for 10.10.10.13 is esxi-03."
            },
            {
                "id": "DISC-04",
                "title": "TrueNAS VLAN Placement",
                "documented": "Historical VLAN.md placed TrueNAS on VLAN 20 (SERVERS_NET, 10.10.20.0/24).",
                "empirical_evidence": "TrueNAS answers on 10.10.10.20 (MGMT_NET). k3s-01 democratic-csi targets 10.10.10.20.",
                "resolution": "Resolved per network.yaml rule truenas-discrepancy: TrueNAS is permanently assigned to 10.10.10.20."
            },
            {
                "id": "DISC-05",
                "title": "Dual-Boot Benchmark Desktop (10.10.10.53 vs 10.10.10.239)",
                "documented": "network_client_map.md listed 10.10.10.239 as pop-os.mgmt.plexplease.com.",
                "empirical_evidence": "~/.ssh/config and ARP reveal same physical NIC MAC (04:42:1A:E9:D1:B3) has two IPs: .239 when booted to Pop!_OS, and .53 (bench-01) when booted to Ubuntu 24.04.",
                "resolution": "Resolved: Currently active OS is Ubuntu 24.04 (bench-01 at 10.10.10.53) executing AI hardware benchmarks on dual Intel Arc Pro B65 GPUs."
            },
            {
                "id": "DISC-06",
                "title": "NVIDIA Device Classification (10.10.10.60)",
                "documented": "network_client_map.md listed 10.10.10.60 as 'NVIDIA Node'. 1Password contained an entry for Ollama GPU Node at 10.10.10.55 (offline).",
                "empirical_evidence": "TLS handshake on port 8443 returned subject CN=NVidia darcy Cast ICA. 'darcy' is the hardware codename for NVIDIA SHIELD TV.",
                "resolution": "Resolved: 10.10.10.60 is an NVIDIA SHIELD TV streaming media client."
            },
            {
                "id": "DISC-07",
                "title": "Unknown IoT Devices (10.10.10.130, .134, .135)",
                "documented": "Listed as 'Unknown Vendor' in network client map.",
                "empirical_evidence": "OUI 5C:E7:53 resolves to Shenzhen Intellirocks Tech. Co. Ltd. (manufacturer of Govee smart home appliances).",
                "resolution": "Resolved: Devices identified as Govee smart LED light strips / thermometers."
            },
            {
                "id": "DISC-08",
                "title": "PeaNUT Ingress 502 / Offline UPS Monitor",
                "documented": "dns_records.csv and Homarr define nut-ups-01 at 10.10.10.139.",
                "empirical_evidence": "VM vm-11001 (nut-ups) on ESXi-01 is poweredOff. 10.10.10.139 is 100% packet loss.",
                "resolution": "Resolved: Outage identified as powered-off VM vm-11001."
            },
            {
                "id": "DISC-09",
                "title": "Core Switch Ingress Endpoint (10.10.10.4 vs 10.10.10.146)",
                "documented": "k3s-01 EndpointSlice dell-switch points to 10.10.10.4:80.",
                "empirical_evidence": "Dell Switch N3224T responds on 10.10.10.146 (eth0 OOB) and 10.10.10.61 (in-band Ethernet0). 10.10.10.4 does not answer.",
                "resolution": "Recorded discrepancy: k3s EndpointSlice requires updating to 10.10.10.146."
            }
        ]
    }
    
    return estate

if __name__ == "__main__":
    estate = generate_estate()
    yaml_path = "/home/dev/repos/homelab-gitops/config/estate_inventory.yaml"
    json_path = "/home/dev/repos/homelab-gitops/config/estate_inventory.json"
    
    with open(yaml_path, "w") as f:
        yaml.dump(estate, f, sort_keys=False, indent=2)
    print(f"Wrote authoritative YAML estate inventory to {yaml_path}")
    
    with open(json_path, "w") as f:
        json.dump(estate, f, indent=2)
    print(f"Wrote authoritative JSON estate inventory to {json_path}")
