# Homelab Network Client & Device Directory

> **Generated:** 2026-09-03 03:32 UTC  
> **Data Sources:** pfSense Gateway (`10.10.10.1`), Technitium DNS/DHCP (`10.10.10.2`), vCenter API (`10.10.10.9`), IEEE OUI Database, and Device TLS Handshakes.  
> **Scope:** 61 Total Discovered Devices across `10.10.10.0/24`.

---

## Core Servers & Hypervisors

| IPv4 Address | MAC Address | Hardware Vendor | Hostname / FQDN | Device Classification & Role | Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `10.10.10.2` | `00:50:56:9F:5E:32` | VMware, Inc. (Photon OS) | `dns-01.plexplease.com` | Authoritative DNS & DHCP Server (Technitium .NET 8, 4 vCPU, 8GB RAM on ESXi-01) | Active (834 flows) |
| `10.10.10.9` | `00:0C:29:A9:92:E0` | VMware, Inc. | `vcenter.mgmt.plexplease.com` | VMware vCenter Server Appliance 8.0 (4 vCPU, 21GB RAM on ESXi-01) | Active (2 flows) |
| `10.10.10.11` | `00:50:56:68:E1:EF` | Supermicro | `esxi-01.mgmt.plexplease.com` | VMware ESXi 8.0.3 Hypervisor 01 (Supermicro X11DPi-N(T), Dual Xeon 48c/96t, 384GB RAM, Intel X710) | Active (4 flows) |
| `10.10.10.13` | `00:50:56:61:8D:A4` | Topton / CWWK | `esxi-03.mgmt.plexplease.com` | VMware ESXi 8.0.3 Hypervisor 03 (Alder Lake-N i3-N305 8c/8t, 16GB DDR5, 4x2.5G + 2x10G SFP+) | Active (322 flows) |
| `10.10.10.20` | `00:50:56:A1:79:C7` | iXsystems / TrueNAS | `truenas-01.mgmt.plexplease.com` | TrueNAS SCALE 25.04.2 Storage Appliance (146TB ZFS, LSI 2308 HBA + Optane P1600X SLOG passthrough) | In ARP Cache |
| `10.10.10.30` | `00:0C:29:C8:A8:14` | VMware, Inc. | `homelab.mgmt.plexplease.com` | Docker Services Host (Ubuntu Linux 7.0, 16 vCPU, 32GB RAM, 30 containers: Plex, Sonarr, OpenBao, etc.) | Active (16 flows) |
| `10.10.10.50` | `00:50:56:9F:71:25` | Red Hat / CoreOS | `k3s-01.infra.plexplease.com` | Production Kubernetes Cluster (k3s v1.35.5, Fedora CoreOS 44, 16 vCPU, 64GB RAM) | Active (30 flows) |
| `10.10.10.51` | `00:50:56:2D:55:01` | VMware, Inc. (Photon OS) | `k3s-deadman-01.infra.plexplease.com` | Out-of-Cluster Monitoring Deadman (Photon OS 5.0, 1 vCPU, 1GB RAM on ESXi-03) | In ARP Cache |
| `10.10.10.52` | `00:50:56:9F:A8:B7` | VMware, Inc. (Ubuntu) | `dev-01.mgmt.plexplease.com` | Development & AGY Operations VM; EnGenius EPC Cloud Controller Docker host (40 vCPU, 80GB RAM on ESXi-01) | Active (122 flows) |
| `10.10.10.110` | `00:50:56:9F:20:11` | VMware, Inc. | `lab-peer-n3224t.mgmt.plexplease.com` | SONiC Switch Lab Peer VM (Dual-homed: 10.10.10.110 & 10.10.20.50 on LAB_N3224T) | In ARP Cache |
| `10.10.10.144` | `C0:25:A5:03:CF:FC` | Dell Inc. | `talos-fty-fw0.mgmt.plexplease.com` | Bare-Metal Talos Linux Node (Dell Latitude 5520, i7-1185G7, 24GB RAM, 2TB NVMe, K8s v1.36.2) | Active (2 flows) |
| `10.10.10.150` | `00:50:56:9F:F1:2A` | VMware, Inc. | `sonic-build-01.mgmt.plexplease.com` | SONiC NOS Compilation Build VM (Ubuntu 24.04, 60 vCPU, 96GB RAM on ESXi-01) | DHCP Dynamic |

---

## Network Switches, Routers & Access Points

| IPv4 Address | MAC Address | Hardware Vendor | Hostname / FQDN | Device Classification & Role | Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `10.10.10.1` | `00:50:56:9F:79:B2` | Netgate / pfSense (VMware) | `pfsense.infra.plexplease.com` | Firewall & NAT Gateway (FreeBSD 15.0 / pfSense-CE 2.8.1-RELEASE, 4 vCPU, 4GB RAM on ESXi-03) | In ARP Cache |
| `10.10.10.6` | `C4:E3:CE:68:E2:50` | EnGenius Technologies | `ap-01.infra.plexplease.com` | Wi-Fi 6 Access Point (EWS377-FIT 4x4 Managed AP - Top Floor) | Active (5 flows) |
| `10.10.10.7` | `C8:7F:54:28:2B:80` | ASUSTek COMPUTER INC | `asus-ap-01.infra.plexplease.com` | Wireless Access Point (Legacy ASUS RT-AX54) | Active (1 flows) |
| `10.10.10.8` | `88:DC:97:1C:BD:7C` | EnGenius Technologies | `ap-02.infra.plexplease.com` | Wi-Fi 6 Access Point (EWS377-FIT 4x4 Managed AP - First Floor) | DHCP Reserved (Offline) |
| `10.10.10.131` | `00:1F:28:D3:66:80` | HP ProCurve | `procurve-j9028b.mgmt.plexplease.com` | HP ProCurve 1800-24G (J9028B) Managed Gigabit Switch | DHCP Dynamic |
| `10.10.10.146` | `E8:B2:65:4B:A5:E8` | Dell Inc. | `sonic.mgmt.plexplease.com` | Dell PowerSwitch N3224T-ON Out-of-Band Management (SONiC 202511-slim2.0 / eth0) | DHCP Dynamic |

---

## Workstations, PCs & Mobile Devices

| IPv4 Address | MAC Address | Hardware Vendor | Hostname / FQDN | Device Classification & Role | Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `10.10.10.53` | `04:42:1A:E9:D1:B3` | ASUSTek / Custom PC | `bench-01.infra.plexplease.com` | AI Hardware Benchmark Node (Ubuntu 24.04, i7-13700K 16c/24t, 32GB RAM, Dual Intel Arc Pro B65 GPUs) | Active (8 flows) |
| `10.10.10.102` | `BA:ED:38:D6:F3:67` | Apple Inc. (Private MAC) | `AlexisAwesome8.mgmt.plexplease.com` | Apple iPhone | Active (4 flows) |
| `10.10.10.111` | `B0:D5:FB:CA:C9:30` | Google | `Matthew-Pixel-10.mgmt.plexplease.com` | Google Pixel 10 Smartphone | Active (136 flows) |
| `10.10.10.113` | `AE:D3:60:83:48:88` | Google (Private MAC) | `Pixel-10.mgmt.plexplease.com` | Google Pixel 10 Smartphone | Active (26 flows) |
| `10.10.10.140` | `F4:6D:3F:CF:9C:07` | Intel Corporate | `dcw139ma4574935.mgmt.plexplease.com` | Intel Corporate Laptop / Workstation | Active (2 flows) |
| `10.10.10.239` | `04:42:1A:E9:D1:B3` | ASUSTek COMPUTER INC | `pop-os.mgmt.plexplease.com` | Dual-Boot Desktop (Pop!_OS partition on i7-13700K / Arc Pro B65 hardware) | Active (10 flows) |
| `10.10.10.242` | `14:F6:D8:F6:74:5D` | Intel Corporate | `DESKTOP-DLA0R8I.mgmt.plexplease.com` | Windows 11 Desktop PC | Active (36 flows) |

---

## Smart Home, Audio/Video, IoT & Safety

| IPv4 Address | MAC Address | Hardware Vendor | Hostname / FQDN | Device Classification & Role | Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `10.10.10.60` | `00:04:4B:B1:CE:D1` | NVIDIA Corporation | `nvidia-shield.mgmt.plexplease.com` | NVIDIA SHIELD TV (darcy / Google Cast Receiver / Android TV) | Active (10 flows) |
| `10.10.10.107` | `D8:1F:12:E7:B2:19` | Tuya Smart Inc. | `wlan0.mgmt.plexplease.com` | Tuya / Smart Life Wi-Fi Smart Plug & Power Monitor | Active (3 flows) |
| `10.10.10.108` | `D8:BF:C0:E9:D9:F3` | Espressif Inc. | `ESP_E9D9F3.mgmt.plexplease.com` | ESPHome / ESP32 Sensor & Automation Node | Active (3 flows) |
| `10.10.10.109` | `CC:8C:BF:28:F3:10` | Tuya Smart Inc. | `wlan0.mgmt.plexplease.com` | Tuya / Smart Life Wi-Fi Smart Plug & Power Monitor | Active (3 flows) |
| `10.10.10.115` | `4C:60:AD:B7:9D:DA` | Amazon Technologies | `echoshow-d3f6c8bac7f2e6a5.mgmt.plexplease.com` | Amazon Echo Show Smart Display | Active (13 flows) |
| `10.10.10.116` | `CC:8C:BF:0C:BC:D0` | Tuya Smart Inc. | `wlan0.mgmt.plexplease.com` | Tuya / Smart Life Wi-Fi Smart Plug & Power Monitor | Active (3 flows) |
| `10.10.10.117` | `D8:BF:C0:F0:64:9D` | Espressif Inc. | `ESP_F0649D.mgmt.plexplease.com` | ESPHome / ESP32 Sensor & Automation Node | Active (3 flows) |
| `10.10.10.118` | `40:5B:D8:A1:08:B6` | Chongqing Fugui / Foxconn | `iot-printer.mgmt.plexplease.com` | Network Laser/Inkjet Printer | Active (120 flows) |
| `10.10.10.121` | `EC:FA:BC:D7:55:65` | Espressif Inc. | `ESP_D75565.mgmt.plexplease.com` | ESPHome / ESP32 Sensor & Automation Node | Active (3 flows) |
| `10.10.10.123` | `10:52:1C:F1:45:EF` | Espressif Inc. | `ESP_F145EF.mgmt.plexplease.com` | ESPHome / ESP32 Sensor & Automation Node | Active (3 flows) |
| `10.10.10.124` | `00:09:B0:14:91:B1` | Onkyo Technology K.K. | `Onkyo-TX-NR676-EAC531.mgmt.plexplease.com` | Onkyo TX-NR676 7.2-Ch Network AV Receiver | Active (4 flows) |
| `10.10.10.130` | `5C:E7:53:3F:97:E4` | Shenzhen Intellirocks (Govee) | `govee-iot-130.mgmt.plexplease.com` | Govee Smart LED Light Strip / Thermometer | DHCP Dynamic |
| `10.10.10.134` | `5C:E7:53:41:B7:A2` | Shenzhen Intellirocks (Govee) | `govee-iot-134.mgmt.plexplease.com` | Govee Smart LED Light Strip / Thermometer | In ARP Cache |
| `10.10.10.135` | `5C:E7:53:3F:49:34` | Shenzhen Intellirocks (Govee) | `govee-iot-135.mgmt.plexplease.com` | Govee Smart LED Light Strip / Thermometer | In ARP Cache |
| `10.10.10.138` | `18:00:DB:0A:8A:FF` | Fitbit Inc. | `Aria2.mgmt.plexplease.com` | Fitbit Aria 2 Wi-Fi Smart Scale | DHCP Dynamic |
| `10.10.10.195` | `00:50:56:9F:0C:FB` | VMware, Inc. | `homeassistant.mgmt.plexplease.com` | Home Assistant OS Automation Server (4 vCPU, 4GB RAM on ESXi-01) | Active (4 flows) |
| `10.10.10.236` | `3C:31:74:27:C7:25` | Google, Inc. | `Nest-Thermostat-C725.mgmt.plexplease.com` | Google Nest Smart Learning Thermostat | Active (2 flows) |
| `10.10.10.237` | `3C:31:74:29:B3:67` | Google, Inc. | `Nest-Thermostat-B367.mgmt.plexplease.com` | Google Nest Smart Learning Thermostat | Active (2 flows) |

---

## Other Discovered Devices

| IPv4 Address | MAC Address | Hardware Vendor | Hostname / FQDN | Status |
| :--- | :--- | :--- | :--- | :--- |
| `10.10.10.103` | `84:07:C4:1C:87:72` | Walter Kidde Portable Equipment, Inc. | `Amazon.mgmt.plexplease.com` | Active (2 flows) |
| `10.10.10.106` | `00:50:56:61:83:8F` | VMware, Inc. | — | DHCP Dynamic |
| `10.10.10.112` | `40:A2:DB:82:41:9D` | Amazon Technologies Inc. | — | Active (31 flows) |
| `10.10.10.114` | `F4:03:2A:B4:AF:98` | Amazon Technologies Inc. | — | Active (9 flows) |
| `10.10.10.119` | `C4:95:00:C6:B9:EC` | Amazon Technologies Inc. | — | Active (13 flows) |
| `10.10.10.120` | `50:99:5A:6E:3F:F0` | Unknown Vendor | — | Active (7 flows) |
| `10.10.10.122` | `00:F3:61:7B:35:4F` | Amazon Technologies Inc. | — | Active (9 flows) |
| `10.10.10.126` | `84:07:C4:1C:81:B6` | Walter Kidde Portable Equipment, Inc. | `Amazon.mgmt.plexplease.com` | Active (2 flows) |
| `10.10.10.127` | `84:07:C4:1C:8A:54` | Walter Kidde Portable Equipment, Inc. | `Amazon.mgmt.plexplease.com` | Active (2 flows) |
| `10.10.10.129` | `84:07:C4:1C:84:EC` | Walter Kidde Portable Equipment, Inc. | `Amazon.mgmt.plexplease.com` | Active (2 flows) |
| `10.10.10.133` | `84:07:C4:1C:8A:24` | Walter Kidde Portable Equipment, Inc. | `Amazon.mgmt.plexplease.com` | Active (2 flows) |
| `10.10.10.137` | `84:07:C4:1C:88:4A` | Walter Kidde Portable Equipment, Inc. | `Amazon.mgmt.plexplease.com` | Active (2 flows) |
| `10.10.10.141` | `84:07:C4:1C:7B:E8` | Walter Kidde Portable Equipment, Inc. | `Amazon.mgmt.plexplease.com` | Active (2 flows) |
| `10.10.10.142` | `84:07:C4:1C:82:28` | Walter Kidde Portable Equipment, Inc. | `Amazon.mgmt.plexplease.com` | Active (2 flows) |
| `10.10.10.143` | `84:07:C4:1C:89:64` | Walter Kidde Portable Equipment, Inc. | `Amazon.mgmt.plexplease.com` | Active (2 flows) |
| `10.10.10.241` | `Unknown` | Unknown | — | Active (2 flows) |
| `10.10.10.255` | `Unknown` | Unknown | — | Active (4 flows) |
| `10.10.30.179` | `Unknown` | Unknown | — | Active (6 flows) |

---
