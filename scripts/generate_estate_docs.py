#!/usr/bin/env python3
"""
Generate Comprehensive Homelab Estate Architecture and Inventory Document
"""

from datetime import datetime, timezone

def generate():

    now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    
    doc = f"""# EchoAres Homelab Infrastructure & Estate Architecture

> **Authoritative Inventory Document:** `docs/estate_architecture_and_inventory.md`  
> **Machine-Readable Sources:** [`config/estate_inventory.yaml`](file:///home/dev/repos/homelab-gitops/config/estate_inventory.yaml), [`config/estate_inventory.json`](file:///home/dev/repos/homelab-gitops/config/estate_inventory.json), [`config/network_clients.json`](file:///home/dev/repos/homelab-gitops/config/network_clients.json)  
> **Last Updated:** {now_str}  
> **Status:** Empirically Verified & Consolidated  

---

## 1. Executive Summary & Estate Topology

The EchoAres homelab estate is a hybrid compute and storage environment combining enterprise dual-socket server hardware, multi-NIC edge appliances, modern Open Network Linux (SONiC NOS) switching, bare-metal and virtualized Kubernetes clusters, high-density ZFS storage arrays, dedicated Intel Battlemage AI acceleration, and an IoT smart home ecosystem.

### Complete Layer 1–7 Estate Architecture

```mermaid
graph TD
    subgraph WAN_Perimeter["Perimeter & Edge Gateway"]
        WAN["Comcast Business / Static IP: 173.48.47.166"]
        PFS["pfSense 2.8.1-RELEASE\n(vm-7007 on ESXi-03)\nLAN: 10.10.10.1 | WAN: 173.48.47.166"]
        WAN --- PFS
    end

    subgraph Core_Switching["Physical Network & Switching Fabric"]
        N3224["Dell PowerSwitch N3224T-ON\nSONiC 202511-slim2.0 | Broadcom Helix5\neth0 OOB: 10.10.10.146 | Eth0 In-Band: 10.10.10.61\nVlan100: 10.10.20.1/24 (Lab Segment)"]
        PROCURVE["HP ProCurve 1800-24G (J9028B)\n10.10.10.131 (24x 1GbE RJ-45)"]
        AP1["EnGenius EWS377-FIT AP (ap-01 - Top Floor)\n10.10.10.6 (Wi-Fi 6 4x4)"]
        AP2["EnGenius EWS377-FIT AP (ap-02 - First Floor)\n10.10.10.8 (Wi-Fi 6 4x4)"]
        AP3["ASUSTek Access Point (asus-ap-01)\n10.10.10.7 (Legacy)"]
        
        PFS ---|vmx0 trunk| PROCURVE
        PROCURVE ---|Port 12| N3224
        PROCURVE ---|Port 15| N3224
        PROCURVE --- AP1
        PROCURVE --- AP2
        PROCURVE --- AP3
    end

    subgraph Physical_Compute["Physical Compute & Hypervisors"]
        ESXI1["Supermicro X11DPi-N(T) (esxi-01)\nDual Xeon (48c/96t) | 384 GB ECC RAM\nESXi 8.0.3 b25205845 | 10.10.10.11"]
        ESXI3["Topton i3-N305 Appliance (esxi-03)\n8c/8t | 16 GB DDR5 | 4x2.5G + 2x10G\nESXi 8.0.3 b25205845 | 10.10.10.13"]
        TALOS["Dell Latitude 5520 (talos-fty-fw0)\ni7-1185G7 (4c/8t) | 24 GB RAM | 2TB NVMe\nTalos Linux v1.13.5 (K8s v1.36.2) | 10.10.10.144"]
        BENCH["Custom Desktop (bench-01 / pop-os)\ni7-13700K (16c/24t) | 32 GB | Dual Arc Pro B65\nUbuntu 24.04 (Bench): 10.10.10.53 | Pop!_OS: 10.10.10.239"]

        N3224 ---|Ethernet16 to vmnic0| ESXI1
        PROCURVE --- ESXI3
        PROCURVE --- TALOS
        PROCURVE --- BENCH
    end

    subgraph Virtual_Machines["Virtual Machines (vCenter 8.0 at 10.10.10.9)"]
        ESXI1 --> K3S["k3s-01 (vm-9073)\nFedora CoreOS 44 | 16 vCPU, 64GB RAM\nIP: 10.10.10.50 | Pod CIDR: 10.42.0.0/16"]
        ESXI1 --> TN["TRUENAS SCALE (vm-7027)\n25.04.2 | 8 vCPU, 80GB RAM | IP: 10.10.10.20\nPassthrough: LSI SAS2308, Optane P1600X, 980PRO"]
        ESXI1 --> HL["HOMELAB (vm-7030)\nUbuntu Linux 7.0 | 16 vCPU, 32GB RAM\nIP: 10.10.10.30 | 30 Docker Containers"]
        ESXI1 --> DEV["dev-01 (vm-7036)\nUbuntu 24.04 | 40 vCPU, 80GB RAM\nIP: 10.10.10.52 | EPC Controller Docker"]
        ESXI1 --> BLD["sonic-build-01 (vm-12002)\nUbuntu 24.04 | 60 vCPU, 96GB RAM\nIP: 10.10.10.150 | NOS Build VM"]
        ESXI1 --> DNS["dns-01 (vm-7035)\nPhoton OS 5.0 | 4 vCPU, 8GB RAM\nIP: 10.10.10.2 | Technitium DNS/DHCP"]
        ESXI1 --> HA["home-assistant (vm-7034)\nHome Assistant OS | 4 vCPU, 4GB RAM\nIP: 10.10.10.195"]
        ESXI1 --> PEER["lab-peer-n3224t (vm-13002)\nUbuntu | 2 vCPU, 2GB RAM\n10.10.10.110 & 10.10.20.50"]
        ESXI1 --> VC["vCenter-01 (vm-7031)\nvCenter Appliance | 4 vCPU, 21GB RAM\nIP: 10.10.10.9"]

        ESXI3 --> PFS
        ESXI3 --> DEAD["k3s-deadman-01 (vm-11006)\nPhoton OS 5.0 | 1 vCPU, 1GB RAM\nIP: 10.10.10.51 | Deadman Receiver"]
    end

    subgraph Production_K8s_Services["k3s-01 Production Workloads (10.10.10.50)"]
        TRF["Traefik v3 Ingress (80/443)"]
        AUTH["Authentik Identity (OIDC/SAML)"]
        ARGO["Argo CD GitOps"]
        AIGW["AI Gateway (gateway-engine, bifrost, cpa, langfuse)"]
        NEX["Nexus 3 Registry (hosted, group, pypi)"]
        OBS["Observability (Prometheus, Grafana, Alertmanager, Loki, Alloy)"]
        ARC["ARC GitHub Runners"]
        CSI["Democratic-CSI (iSCSI & NFS to TrueNAS)"]
    end

    K3S --> Production_K8s_Services
    CSI -.->|iSCSI / NFS| TN
```

---

## 2. Physical Hardware & Compute Catalog

| Node Identifier | System Role | Form Factor / Chassis | Motherboard & Processor | Memory Capacity | Storage Configuration | Firmware & Hypervisor | Interfaces & MAC | Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :---: |
| **esxi-01** | Primary Hypervisor & Workload Host | Supermicro 2U/4U Rackmount Server | Supermicro X11DPi-N(T)<br>Dual Genuine Intel Xeon Platinum (48c/96t @ 2.60 GHz) | 382.7 GiB DDR4 ECC Reg | Boot: ZFS iSCSI LUN (`iSCSI_vmware` on TrueNAS)<br>PCIe Passthrough: LSI SAS2308, Optane P1600X, 980PRO | BIOS 3.6 (2022-01-25)<br>VMware ESXi 8.0.3 (Build 25205845) | `vmnic0`: `AC:1F:6B:3A:E3:2A` (Intel X710 -> Dell N3224T eth16)<br>`vmnic1`: `AC:1F:6B:3A:E3:2B` (Intel X710)<br>Management: `10.10.10.11`<br>**BMC/IPMI:** `10.10.10.10` (`AC:1F:6B:3B:93:7F`) | **ONLINE** |
| **ipmi-01** | ESXi-01 Out-of-Band Remote Management | Integrated ASPEED AST2500 BMC | Supermicro Motherboard Embedded BMC (IPMI 2.0 / Redfish 1.8.0) | 512 MB Embedded | Flash ROM | Supermicro IPMI Firmware (TLS: `CN=IPMI, O=Super Micro Computer`) | Dedicated IPMI RJ-45: `AC:1F:6B:3B:93:7F`<br>Static DHCP Reserved: `10.10.10.10`<br>Current Active Lease: `10.10.10.104`<br>FQDN: `ipmi-01.mgmt.plexplease.com` | **ONLINE** |
| **esxi-03** | Edge Firewall & Deadman Hypervisor | Topton / CWWK Multi-NIC Mini PC | Fanless Mini PC (Chassis 6083002)<br>Intel Core i3-N305 Alder Lake-N (8c/8t @ 1.80 GHz) | 15.7 GiB DDR5 | M.2 NVMe SSD | BIOS 5.27 (2023-06-26)<br>VMware ESXi 8.0.3 (Build 25205845) | `vmnic0`: `A8:B8:E0:0A:50:B2` (10G SFP+ ixgben)<br>`vmnic2`: `34:1A:4C:04:23:23` (2.5G i226)<br>`vmnic3`: `34:1A:4C:04:23:24` (2.5G i226)<br>Management: `10.10.10.13` | **ONLINE** |
| **talos-fty-fw0** | Bare-Metal Talos Kubernetes Node | Dell Latitude 5520 Laptop (Service Tag `9SHLP93`) | Dell Inc. Motherboard (UUID `4c4c4544-0053-4810-804c-b9c04f503933`)<br>11th Gen Intel Core i7-1185G7 (4c/8t @ 3.00 GHz) | 23.7 GiB DDR4 | 2 TB NVMe SSD (`/` and Flannel storage) | BIOS 1.4.2 (2021-03-09)<br>Talos Linux v1.13.5 (Kernel 6.18.36-talos) | `eth0`: `C0:25:A5:03:CF:FC` (Intel GbE)<br>IP: `10.10.10.144` | **ONLINE** |
| **bench-01** | AI Hardware Benchmark & Workstation | Custom Mid-Tower Desktop | ASUS Intel Z690<br>13th Gen Intel Core i7-13700K Raptor Lake (16c/24t @ 5.40 GHz) | 31.0 GiB DDR4/DDR5 | 1 TB NVMe (`nvme0n1`, `/mnt/aistore` 582GB)<br>USB Disks: 120GB (`sda`), 16GB (`sdb`) | ASUS UEFI BIOS<br>Ubuntu 24.04 (Kernel 6.17.0-1009-intel) | NIC: `04:42:1A:E9:D1:B3` (Intel I225-V)<br>Bench IP: `10.10.10.53`<br>Pop!_OS IP: `10.10.10.239`<br>Dual Intel Arc Pro B65 GPUs (`8086:e222`) | **ONLINE** |
| **sw-core-01** | Core L2/L3 Network Switch | Dell EMC PowerSwitch N3224T-ON (1U) | DellEMC-N3224T (Platform `x86_64-dellemc_n3224t_c3338-r0`)<br>Intel Atom C3338 dual-core @ 1.50 GHz | 3.8 GiB DDR4 | 32 GB eMMC / SSD | SONiC.202511-n3224t-slim2.0-39ddd324e<br>Broadcom Helix5 ASIC (BCM56370) | 24x 10G Base-T + 4x 25G SFP28 + 2x 100G QSFP28<br>eth0 OOB: `10.10.10.146` (`E8:B2:65:4B:A5:E8`)<br>Ethernet0: `10.10.10.61` (`E8:B2:65:4B:A5:E9`)<br>Vlan100: `10.10.20.1/24` | **ONLINE** |
| **procurve-j9028b** | Distribution / Edge Gigabit Switch | HP ProCurve 1800-24G (J9028B) (1U) | Managed Gigabit Web Switch | Embedded | Internal Flash | HP ProCurve Firmware | 24x 1GbE RJ-45<br>Management IP: `10.10.10.131`<br>MAC: `00:1F:28:D3:66:80` | **ONLINE** |
| **ap-01** | High-Density Wi-Fi 6 AP (Top Floor) | EnGenius EWS377-FIT | Qualcomm Quad-Core Networking SoC | 1 GB RAM | Internal Flash | EnGenius Fit Firmware (Managed by EPC Controller on k3s-01: `wifi.infra.plexplease.com`) | 1x 2.5GbE PoE+ Port<br>IP: `10.10.10.6`<br>MAC: `C4:E3:CE:68:E2:50`<br>Location: Top Floor | **ONLINE** |
| **ap-02** | High-Density Wi-Fi 6 AP (First Floor) | EnGenius EWS377-FIT | Qualcomm Quad-Core Networking SoC | 1 GB RAM | Internal Flash | EnGenius Fit Firmware (Managed by EPC Controller on k3s-01: `wifi.infra.plexplease.com`) | 1x 2.5GbE PoE+ Port<br>IP: `10.10.10.8`<br>MAC: `88:DC:97:1C:BD:7C`<br>Location: First Floor | **ONLINE** |
| **asus-ap-01** | Legacy Wi-Fi AP | ASUSTek Wireless AP | Broadcom Wi-Fi SoC | Embedded | Internal Flash | ASUSWRT Firmware | 1x GbE WAN + 4x GbE LAN<br>IP: `10.10.10.7`<br>MAC: `C8:7F:54:28:2B:80` | **ONLINE** |
| **nvidia-shield** | 4K HDR Streaming & Cast Receiver | NVIDIA SHIELD TV (2019 "darcy") | NVIDIA Tegra X1+ (4x A57 + 4x A53) | 3 GB LPDDR4 | 16 GB eMMC | Android TV 11 (Widevine L1, Google Cast)<br>TLS: `CN=NVidia darcy Cast ICA` | Gigabit Ethernet<br>IP: `10.10.10.60`<br>MAC: `00:04:4B:B1:CE:D1` | **ONLINE** |

---

## 3. Storage Subsystems & ZFS Pool Topology

Storage is anchored by **TrueNAS SCALE 25.04.2.6 (Fangtooth)** operating as a high-performance VM (`vm-7027` on ESXi-01) with dedicated PCIe passthrough of the physical storage controller and high-speed NVMe devices:
- **Broadcom / LSI SAS2308 PCI-Express Fusion-MPT SAS-2 (rev 05)** — Controls all SATA/SAS spinners.
- **Intel Optane SSD P1600X 118GB NVMe (`SSDPEK1A118GA`, Serial `PHOC202100GT118B`)** — High-endurance 3D XPoint partitioned as dedicated SLOG/ZIL write cache across pools.
- **Samsung 980 PRO 2TB NVMe (`S6B0NL0W403962N`)** — High-speed PCIe 4.0 flash storage for VM datastores.

### ZFS Pool Breakdown

```
┌───────────────────────────────────────────────────────────────────────────────────────────┐
│                                TRUENAS SCALE ZFS TOPOLOGY                                 │
├─────────────┬──────────┬──────────┬──────────┬──────────┬─────────────────────────────────┤
│ Pool Name   │ Raw Size │ Alloc    │ Free     │ Health   │ Configuration & Disks           │
├─────────────┼──────────┼──────────┼──────────┼──────────┼─────────────────────────────────┤
│ WHITEBOX    │ 146 TB   │ 120 TB   │ 25.2 TB  │ ONLINE   │ RAIDZ2 (8x 20TB WD Red Pro)     │
│             │          │          │          │          │ SLOG: Optane P1600X (part 3)    │
│ K3S_HDD     │ 24.5 TB  │ 28.5 GB  │ 24.5 TB  │ ONLINE   │ 3x Mirrors (4x 12TB + 2x 3TB)   │
│             │          │          │          │          │ SLOG: Optane P1600X (part 1)    │
│ vmstore     │ 1.81 TB  │ 11.0 GB  │ 1.80 TB  │ ONLINE   │ 1x NVMe (Samsung 980 PRO 2TB)   │
│             │          │          │          │          │ SLOG: Optane P1600X (part 2)    │
│ boot-pool   │ 31.5 GB  │ 22.3 GB  │ 9.22 GB  │ ONLINE   │ 1x Virtual Disk (32GB sda2)     │
└─────────────┴──────────┴──────────┴──────────┴──────────┴─────────────────────────────────┘
```

### Key ZFS Datasets & Usages
1. `WHITEBOX/MEDIA/MOVIES` (54.1 TB) — Primary 1080p/720p Plex Movie collection.
2. `WHITEBOX/MEDIA/TV` (27.7 TB) — Television series archive.
3. `WHITEBOX/MEDIA/4K_MOVIES` (3.18 TB) — High-bitrate 4K UHD Remux / HDR media.
4. `WHITEBOX/nexus` (1.07 TB) — Sonatype Nexus hosted container registry & PyPI repository.
5. `WHITEBOX/WINDOWS_BACKUP` (265 GB) — Desktop workstation bare-metal disk images.
6. `WHITEBOX/MEDIA/DOWNLOAD` (130 GB) — Usenet (SABnzbd) and torrent staging filesystem.
7. `WHITEBOX/k3s-object-store` (124 GB) — Backing storage for MinIO S3 cluster storage.
8. `WHITEBOX/backups` (74.9 GB) — TrueNAS configuration, database dumps, and disaster recovery snapshots.
9. `K3S_HDD/k3s-iscsi/*` — Democratic-CSI persistent volumes mounted dynamically into k3s pods.
10. `vmstore/iSCSI_vmware/producation` (1.02 TB allocated) — High-speed VM datastore exported via iSCSI to VMware ESXi.

---

## 4. Virtual Machine Estate Directory

Consolidated from VMware vCenter Server 8.0 (`vcenter.mgmt.plexplease.com` at `10.10.10.9`):

| VM Name | VM ID | Hypervisor Host | State | vCPUs | RAM (MB) | Primary IP | Primary MAC Address | Guest OS Platform | Functional Description |
| :--- | :--- | :--- | :---: | :---: | :---: | :--- | :--- | :--- | :--- |
| **k3s-01** | `vm-9073` | `10.10.10.11` (ESXi-01) | **poweredOn** | 16 | 65,536 | `10.10.10.50` | `00:50:56:9F:71:25` | Fedora CoreOS 44 | Production Kubernetes cluster host |
| **TRUENAS.PLEXPLEASE.COM** | `vm-7027` | `10.10.10.11` (ESXi-01) | **poweredOn** | 8 | 81,920 | `10.10.10.20` | `00:50:56:A1:79:C7` | Debian 12 (TrueNAS SCALE 25.04) | Core enterprise ZFS NAS appliance |
| **HOMELAB** | `vm-7030` | `10.10.10.11` (ESXi-01) | **poweredOn** | 16 | 32,768 | `10.10.10.30` | `00:0C:29:C8:A8:14` | Ubuntu Linux (Kernel 7.0) | Legacy Docker application stack (30 containers) |
| **dev-01.mgmt.plexplease.com** | `vm-7036` | `10.10.10.11` (ESXi-01) | **poweredOn** | 40 | 81,920 | `10.10.10.52` | `00:50:56:9F:A8:B7` | Ubuntu Linux 24.04 LTS | Agent runtime, dev workspace, EnGenius EPC host |
| **sonic-build-01** | `vm-12002` | `10.10.10.11` (ESXi-01) | **poweredOn** | 60 | 98,304 | `10.10.10.150` | `00:50:56:9F:F1:2A` | Ubuntu 24.04 LTS | High-parallelism SONiC NOS compilation VM |
| **dns-01.mgmt.plexplease.com** | `vm-7035` | `10.10.10.11` (ESXi-01) | **poweredOn** | 4 | 8,192 | `10.10.10.2` | `00:50:56:9F:5E:32` | VMware Photon OS 5.0 | Authoritative DNS & DHCP Server (Technitium) |
| **vCenter-01** | `vm-7031` | `10.10.10.11` (ESXi-01) | **poweredOn** | 4 | 21,504 | `10.10.10.9` | `00:0C:29:A9:92:E0` | VMware Photon OS (vCenter 8.0) | Central vSphere management appliance |
| **home-assistant** | `vm-7034` | `10.10.10.11` (ESXi-01) | **poweredOn** | 4 | 4,096 | `10.10.10.195` | `00:50:56:9F:0C:FB` | Home Assistant OS | Smart home automation orchestrator |
| **lab-peer-n3224t** | `vm-13002` | `10.10.10.11` (ESXi-01) | **poweredOn** | 2 | 2,048 | `10.10.10.110` | `00:50:56:9F:20:11` | Ubuntu Linux (64-bit) | SONiC Switch Lab Peer (NIC 2: `10.10.20.50`) |
| **vCLS-826b8000** | `vm-7041` | `10.10.10.11` (ESXi-01) | **poweredOn** | 1 | 160 | DHCP Dynamic | N/A | VMware Photon OS | vSphere Cluster Services VM (ESXi-01) |
| **PF-SENSE** | `vm-7007` | `10.10.10.13` (ESXi-03) | **poweredOn** | 4 | 4,096 | `10.10.10.1` | `00:50:56:9F:79:B2` | FreeBSD 15.0 (pfSense 2.8.1) | Primary firewall, NAT router, and edge gateway |
| **k3s-deadman** | `vm-11006` | `10.10.10.13` (ESXi-03) | **poweredOn** | 1 | 1,024 | `10.10.10.51` | `00:50:56:2D:55:01` | VMware Photon OS 5.0 | Independent monitoring heartbeat receiver |
| **vCLS-03000200** | `vm-7797` | `10.10.10.13` (ESXi-03) | **poweredOn** | 1 | 160 | DHCP Dynamic | N/A | VMware Photon OS | vSphere Cluster Services VM (ESXi-03) |
| **nut-ups** | `vm-11001` | `10.10.10.11` (ESXi-01) | **poweredOff** | 1 | 1,024 | `10.10.10.139` (target) | `00:50:56:9F:AD:6C` | Ubuntu Linux | PeaNUT / UPS monitoring appliance (Offline) |
| **OPNsense** | `vm-7009` | `10.10.10.13` (ESXi-03) | **poweredOff** | 4 | 4,096 | Unassigned | `00:50:56:8B:AC:C6` | FreeBSD (OPNsense) | Inactive standby firewall |
| **bench-lab-01** | `vm-12001` | `10.10.10.11` (ESXi-01) | **poweredOff** | 32 | 24,576 | Unassigned | `00:50:56:9F:34:69` | Ubuntu Linux | Virtual benchmarking worker |
| **epc.infra.plexplease.com** | `vm-9044` | `10.10.10.11` (ESXi-01) | **poweredOff** | 4 | 8,192 | Unassigned | `00:50:56:9F:63:BB` | Ubuntu Linux | Legacy EPC VM (superseded by Docker on dev-01) |
| **photon-mcp** | `vm-7796` | `10.10.10.11` (ESXi-01) | **poweredOff** | 16 | 8,192 | Unassigned | `00:50:56:9F:1F:52` | VMware Photon OS | Retired MCP container host |
| **ubuntu-24.04-lts-golden** | `vm-9028` | `10.10.10.11` (ESXi-01) | **poweredOff** | 2 | 2,048 | Unassigned | `00:50:56:9F:E3:95` | Ubuntu 24.04 LTS | Standardized golden VM template |
| **photon-test-base** | N/A | `10.10.10.11` (ESXi-01) | **poweredOff** | 2 | 4,096 | Unassigned | `00:50:56:9F:ED:D9` | VMware Photon OS | Base testing VM |

---

## 5. Kubernetes & Container Services Catalog

### 5.1 Production Platform Cluster (`k3s-01` at `10.10.10.50`)
- **Distribution:** k3s v1.35.5+k3s1 (containerd 2.2.3-k3s1, crun/runc)
- **Host System:** Fedora CoreOS 44 (`c3771f42-6b0b-657a-4fd8-d5a4273c7e82`, 16 vCPU, 64 GB RAM)
- **Networking:** Pod Network `10.42.0.0/16` (Flannel VXLAN VNI 1), Service Network `10.43.0.0/16`, Resolver `10.43.0.10`
- **Ingress Layer:** Traefik v3 (ports 80 & 443, host IP `10.10.10.50`)

#### Workloads by Namespace
1. **`argocd`**: GitOps Continuous Delivery controller & UI (`argocd.infra.plexplease.com`).
2. **`identity`**: Authentik Identity Provider (`authentik.infra.plexplease.com`, ports 9000/9443).
3. **`ai-gateway`**:
   - `gateway-engine` (`gateway.infra.plexplease.com`, port 4000) — Unified AI proxy.
   - `agent-gateway` (`bifrost.infra.plexplease.com`, port 8089) — High-performance Rust LLM router.
   - `cpa-manager` (`cpa.infra.plexplease.com`, port 18317) — CLIProxy analytics.
   - `cliproxy` (port 8317) — Consumer OAuth load balancer.
   - `langfuse-web` (`langfuse.infra.plexplease.com`, port 3000) — Observability & evaluation tracing.
   - `docs-server` (port 8002).
4. **`nexus`**: Sonatype Nexus Repository Manager 3 (`nexus.infra.plexplease.com`, Docker pull-through on `nexus-registry`, Docker hosted on `nexus-docker`).
5. **`observability`**:
   - Prometheus (`prometheus.infra.plexplease.com`, port 9090).
   - Grafana (`grafana.infra.plexplease.com`, port 3000).
   - Alertmanager (`alertmanager.infra.plexplease.com`, port 9093).
   - Loki (`loki-0`, port 3100, Memcached chunks & results caches).
   - Grafana Alloy (`alloy`, port 12345) — Unified telemetry pipeline.
   - Kube-State-Metrics (port 8080) & Prometheus Node Exporter (port 9100).
6. **`homarr`**: Homarr unified homelab dashboard (`homarr.infra.plexplease.com`, port 7575) & icons CDN (`homarr-icons.infra.plexplease.com`).
7. **`notifications`**: Apprise notification gateway (`apprise.infra.plexplease.com`, port 8000) & Alertmanager webhook router (port 3000).
8. **`github-runner`**: GitHub Actions Runner Controller (ARC) with auto-scaling ephemeral runner pods.
9. **`database`**: CloudNative-PG PostgreSQL cluster, ClickHouse analytical DB, Redis cache, MinIO S3 object storage.
10. **`mlflow`**: MLflow experiment tracking (`mlflow.infra.plexplease.com`, port 5000).
11. **`server-partpicker`**: Hardware spec ingestion consumer (`ingest-consumer`).
12. **`deal-finder`**: Hardware deal scraping engine (`deal-finder.infra.plexplease.com`).
13. **`democratic-csi`**: Storage driver linking TrueNAS ZFS iSCSI & NFS targets into Kubernetes PVCs.
14. **`external-secrets` & `cert-manager`**: OpenBao secret syncing and Automated ACME TLS issuance.

### 5.2 Bare-Metal Talos Cluster (`talos-fty-fw0` at `10.10.10.144`)
- **Distribution:** Talos Linux v1.13.5 (containerd 2.2.5, runc)
- **Kubernetes Version:** v1.36.2
- **Hardware:** Physical Dell Latitude 5520 laptop (Intel Core i7-1185G7, 24 GB RAM, 2 TB NVMe)
- **Networking:** Pod Network `10.244.0.0/24`, Service Network `10.96.0.0/12`
- **Core Pods:** CoreDNS v1.14.2, Flannel v0.28.5, Kube-Apiserver v1.36.2, Kube-Controller-Manager v1.36.2, Kube-Scheduler v1.36.2, Kube-Proxy v1.36.2.

### 5.3 Docker Compose Workloads on `homelab` (`10.10.10.30`)
30 active containers supporting media automation, data persistence, and legacy infrastructure:
- **Media Suite:** Plex Media Server (`host` network, port 32400), Sonarr (8988), Radarr (7870), Radarr4K (7879), SABnzbd (8080), Ombi (3579), NZBHydra2 (5076).
- **Core & Secrets:** OpenBao (`secrets-openbao-1`, port 8201->8200), 1Password Connect API (`secrets-op-connect-api-1`, port 8200->8080) & Sync daemon.
- **Databases:** PostgreSQL 16 (5432), Redis (6379), ClickHouse (8123, 9000).
- **AI Stack (Co-located):** LiteLLM proxy (4000), Langfuse (3000), ClickHouse & Postgres.
- **Observability:** Prometheus (9090), Grafana (3000), Loki (3100), Alloy (12345, 1514-1515/udp), Node Exporter (9100), cAdvisor (8088), Uptime Kuma (3002).
- **Management & Utilities:** Nginx Proxy Manager (80, 81, 443), Sonatype Nexus 3 (8081, 8082), Dockhand (3001), Postfix email relay (25, 587), Cloudflared tunnel.

### 5.4 Docker Workloads on `dev-01` (`10.10.10.52`)
- **EnGenius Private Cloud (EPC) Stack:**
  - `epc-api:1.9.0` (FastAPI / Gunicorn, ports 443, 8088)
  - `epc-raccoon:1.9.0` (Web UI proxy, port 80)
  - `epc-otter:1.9.0` (AP communication engine)
  - `epc-mdns:1.9.0` (mDNS discovery)
  - `epc-db:1.9.0` (PostgreSQL datastore)
  - `busy_northcutt` (`grafana/alloy:v1.17.0`)

---

## 6. Discrepancy Matrix & Empirical Resolutions

| ID | Subject | Documented / Assumed State | Empirical Finding & Evidence | Definitive Resolution |
| :---: | :--- | :--- | :--- | :--- |
| **DISC-01** | **VLAN Segmentation** | `VLAN.md` & `network.yaml` define 8 distinct VLANs (`10.10.10.0/24` to `10.10.100.0/24`). Technitium has disabled scopes shifted by +10. | pfSense interface `vmx0` is `10.10.10.1/24` with **zero VLAN sub-interfaces**. All 61 hosts share a single flat Layer 2 broadcast domain (`10.10.10.0/24`). Dell N3224T has isolated `Vlan100` (`10.10.20.1/24`) for switch lab traffic. | **Recorded reality as flat `/24` subnet.** Documented the isolated lab segment on the Dell switch. Retained the multi-VLAN model in policy as a blueprint for future phased implementation. |
| **DISC-02** | **Dell Latitude 5520 Identity** | vCenter records `host-9074` at `10.10.10.102` (Dell Latitude 5520, Service Tag `9SHLP93`) as `DISCONNECTED`. `network_client_map.md` labeled `10.10.10.144` as "Dell Appliance / Firewall". | Talos Linux node `talos-fty-fw0` at `10.10.10.144` carries System UUID `4c4c4544-0053-4810-804c-b9c04f503933` (`DELL` + `9SHLP93`). Address `10.10.10.102` in DHCP is now leased to an iPhone. | **Resolved:** The physical laptop was wiped and reprovisioned bare-metal as the Talos control-plane node. The vCenter host record is obsolete. |
| **DISC-03** | **ESXi Host Naming** | 1Password VM inventory labeled `10.10.10.13` as "ESXi 2". | Technitium forward/reverse DNS, TLS certificates, and vCenter designate `10.10.10.13` as `esxi-03.mgmt.plexplease.com`. (Former `esxi-02` was the laptop at `.102`). | **Resolved:** Authoritative name is `esxi-03`. |
| **DISC-04** | **TrueNAS Subnet Placement** | `VLAN.md` placed TrueNAS on VLAN 20 (`10.10.20.0/24`). | TrueNAS answers on `10.10.10.20` (`MGMT_NET`). k3s Democratic-CSI targets `10.10.10.20`. | **Resolved:** Permanent IP is `10.10.10.20` (as ratified by `network.yaml` rule `truenas-discrepancy`). |
| **DISC-05** | **Desktop Workstation Dual Boot** | `network_client_map.md` listed `10.10.10.239` as `pop-os.mgmt.plexplease.com`. | Same physical NIC MAC (`04:42:1A:E9:D1:B3`) has two IPs: `10.10.10.239` when booted to Pop!_OS, and `10.10.10.53` (`bench-01`) when booted to Ubuntu 24.04. | **Resolved:** Currently booted to Ubuntu 24.04 (`10.10.10.53`) running vLLM XPU on dual Intel Arc Pro B65 GPUs. |
| **DISC-06** | **NVIDIA Device Identity** | Labeled as generic "NVIDIA Node" at `10.10.10.60`. | TLS handshake on port 8443 returned subject `CN=NVidia darcy Cast ICA`. "darcy" is the hardware codename for NVIDIA SHIELD TV. | **Resolved:** Identified as NVIDIA SHIELD TV 4K streaming client. |
| **DISC-07** | **Unknown IoT Devices (.130, .134, .135)** | Labeled as "Unknown Vendor" in ARP table. | IEEE OUI `5C:E7:53` belongs to Shenzhen Intellirocks Tech. Co. Ltd. (manufacturer of Govee smart appliances). | **Resolved:** Identified as Govee smart LED light strips / environmental sensors. |
| **DISC-08** | **PeaNUT Ingress Outage (502)** | DNS defines `nut-ups-01` at `10.10.10.139`. Ingress returned 502 Bad Gateway. | VM `vm-11001` (`nut-ups`) on ESXi-01 is `poweredOff`. IP `10.10.10.139` is unreachable. | **Resolved:** Outage root cause verified as powered-off VM `vm-11001`. |
| **DISC-09** | **Core Switch Ingress IP** | k3s Ingress points to `10.10.10.4:80`. | Switch responds on `10.10.10.146` (eth0 OOB) and `10.10.10.61` (in-band Ethernet0). `10.10.10.4` does not answer. | **Recorded discrepancy:** k3s EndpointSlice requires update to `10.10.10.146`. |

---

## 7. Authoritative IP & Network Directory

Consolidated directory of all active, statically assigned, and reserved endpoints in `10.10.10.0/24`:

| IPv4 Address | MAC Address | Hostname / FQDN | Device & Service Description | Status |
| :--- | :--- | :--- | :--- | :---: |
| `10.10.10.1` | `00:50:56:9F:79:B2` | `pfsense.infra.plexplease.com` | pfSense 2.8.1-RELEASE Gateway / Firewall (LAN `vmx0`) | **Active** |
| `10.10.10.2` | `00:50:56:9F:5E:32` | `dns-01.plexplease.com` | Technitium DNS & DHCP Primary Server | **Active** |
| `10.10.10.6` | `C4:E3:CE:68:E2:50` | `ap-01.infra.plexplease.com` | EnGenius EWS377-FIT Wi-Fi 6 AP (Top Floor) | **Active** |
| `10.10.10.7` | `C8:7F:54:28:2B:80` | `asus-ap-01.infra.plexplease.com` | ASUSTek Wireless Access Point (Legacy) | **Active** |
| `10.10.10.8` | `88:DC:97:1C:BD:7C` | `ap-02.infra.plexplease.com` | EnGenius EWS377-FIT Wi-Fi 6 AP (First Floor) | **Active** |
| `10.10.10.9` | `00:0C:29:A9:92:E0` | `vcenter.mgmt.plexplease.com` | VMware vCenter Server Appliance 8.0 | **Active** |
| `10.10.10.10` | `AC:1F:6B:3B:93:7F` | `ipmi-01.mgmt.plexplease.com` | Supermicro X11DPi-N(T) ESXi-01 ASPEED AST2500 BMC / IPMI | **Reserved** |
| `10.10.10.104`| `AC:1F:6B:3B:93:7F` | `ipmi-01.mgmt.plexplease.com` | Supermicro BMC Temporary Active DHCP Lease (Transitioning to .10) | **Active** |
| `10.10.10.11` | `00:50:56:68:E1:EF` | `esxi-01.mgmt.plexplease.com` | VMware ESXi 8.0.3 (Supermicro X11DPi-N(T) Dual Xeon) | **Active** |
| `10.10.10.13` | `00:50:56:61:8D:A4` | `esxi-03.mgmt.plexplease.com` | VMware ESXi 8.0.3 (Topton i3-N305 Appliance) | **Active** |
| `10.10.10.20` | `00:50:56:A1:79:C7` | `truenas-01.mgmt.plexplease.com` | TrueNAS SCALE 25.04.2 Storage Appliance | **Active** |
| `10.10.10.30` | `00:0C:29:C8:A8:14` | `homelab.mgmt.plexplease.com` | Ubuntu Docker Host (30 containers: Plex, Sonarr, OpenBao, etc.) | **Active** |
| `10.10.10.50` | `00:50:56:9F:71:25` | `k3s-01.infra.plexplease.com` | Production Kubernetes Node (k3s v1.35.5, FCOS 44) | **Active** |
| `10.10.10.51` | `00:50:56:2D:55:01` | `k3s-deadman-01.infra.plexplease.com` | Out-of-Cluster Monitoring Deadman Receiver | **Active** |
| `10.10.10.52` | `00:50:56:9F:A8:B7` | `dev-01.mgmt.plexplease.com` | Dev & AGY Operations Node | **Active** |
| `10.10.10.53` | `04:42:1A:E9:D1:B3` | `bench-01.infra.plexplease.com` | AI Benchmark Workstation (Ubuntu 24.04, Dual Arc Pro B65) | **Active** |
| `10.10.10.60` | `00:04:4B:B1:CE:D1` | `nvidia-shield.mgmt.plexplease.com` | NVIDIA SHIELD TV (darcy / Google Cast / Android TV) | **Active** |
| `10.10.10.61` | `E8:B2:65:4B:A5:E9` | `sw-core-01-inband.infra.plexplease.com`| Dell PowerSwitch N3224T-ON In-Band Ethernet0 | **Active** |
| `10.10.10.101` | `DC:03:98:94:07:E6` | `LGwebOSTV.mgmt.plexplease.com` | LG webOS 4K Smart TV | **Active** |
| `10.10.10.102` | `BA:ED:38:D6:F3:67` | `AlexisAwesome8.mgmt.plexplease.com` | Apple iPhone (Dynamic DHCP) | **Active** |
| `10.10.10.104` | `C2:02:EF:68:F3:42` | `iPad.mgmt.plexplease.com` | Apple iPad | **Active** |
| `10.10.10.110` | `00:50:56:9F:20:11` | `lab-peer-n3224t.mgmt.plexplease.com` | SONiC Switch Lab Peer VM | **Active** |
| `10.10.10.111` | `B0:D5:FB:CA:C9:30` | `Matthew-Pixel-10.mgmt.plexplease.com`| Google Pixel 10 Smartphone | **Active** |
| `10.10.10.113` | `AE:D3:60:83:48:88` | `Pixel-10.mgmt.plexplease.com` | Google Pixel 10 Smartphone | **Active** |
| `10.10.10.115` | `4C:60:AD:B7:9D:DA` | `echoshow-d3f6c8bac7f2e6a5.mgmt.plexplease.com`| Amazon Echo Show Smart Display | **Active** |
| `10.10.10.118` | `40:5B:D8:A1:08:B6` | `iot-printer.mgmt.plexplease.com` | Network Laser/Inkjet Printer | **Active** |
| `10.10.10.124` | `00:09:B0:14:91:B1` | `Onkyo-TX-NR676-EAC531.mgmt.plexplease.com`| Onkyo TX-NR676 AV Receiver | **Active** |
| `10.10.10.130` | `5C:E7:53:3F:97:E4` | `govee-iot-130.mgmt.plexplease.com` | Govee Smart Device (Shenzhen Intellirocks) | **Active** |
| `10.10.10.131` | `00:1F:28:D3:66:80` | `procurve-j9028b.mgmt.plexplease.com`| HP ProCurve 1800-24G (J9028B) Gigabit Switch | **Active** |
| `10.10.10.134` | `5C:E7:53:41:B7:A2` | `govee-iot-134.mgmt.plexplease.com` | Govee Smart Device (Shenzhen Intellirocks) | **Active** |
| `10.10.10.135` | `5C:E7:53:3F:49:34` | `govee-iot-135.mgmt.plexplease.com` | Govee Smart Device (Shenzhen Intellirocks) | **Active** |
| `10.10.10.138` | `18:00:DB:0A:8A:FF` | `Aria2.mgmt.plexplease.com` | Fitbit Aria 2 Wi-Fi Smart Scale | **Active** |
| `10.10.10.139` | `00:50:56:9F:AD:6C` | `nut-ups-01.mgmt.plexplease.com` | PeaNUT / UPS Monitor VM (`vm-11001`, poweredOff) | Offline |
| `10.10.10.140` | `F4:6D:3F:CF:9C:07` | `dcw139ma4574935.mgmt.plexplease.com`| Intel Corporate Laptop | **Active** |
| `10.10.10.144` | `C0:25:A5:03:CF:FC` | `talos-fty-fw0.mgmt.plexplease.com` | Bare-Metal Talos Linux Node (Dell Latitude 5520) | **Active** |
| `10.10.10.146` | `E8:B2:65:4B:A5:E8` | `sonic.mgmt.plexplease.com` | Dell PowerSwitch N3224T-ON OOB eth0 (SONiC NOS) | **Active** |
| `10.10.10.150` | `00:50:56:9F:F1:2A` | `sonic-build-01.mgmt.plexplease.com`| SONiC NOS Compilation Build VM (60 vCPU, 96GB) | **Active** |
| `10.10.10.195` | `00:50:56:9F:0C:FB` | `homeassistant.mgmt.plexplease.com` | Home Assistant OS Automation Controller | **Active** |
| `10.10.10.236` | `3C:31:74:27:C7:25` | `Nest-Thermostat-C725.mgmt.plexplease.com`| Google Nest Learning Thermostat (Zone 1) | **Active** |
| `10.10.10.237` | `3C:31:74:29:B3:67` | `Nest-Thermostat-B367.mgmt.plexplease.com`| Google Nest Learning Thermostat (Zone 2) | **Active** |
| `10.10.10.239` | `04:42:1A:E9:D1:B3` | `pop-os.mgmt.plexplease.com` | Custom Desktop PC (Pop!_OS alternate boot) | Dual-boot |
| `10.10.10.242` | `14:F6:D8:F6:74:5D` | `DESKTOP-DLA0R8I.mgmt.plexplease.com`| Windows 11 Desktop PC | **Active** |
| `10.10.20.50` | `00:50:56:9F:1D:D3` | `lab-peer-vlan100.mgmt.plexplease.com`| `lab-peer-n3224t` NIC 2 on Switch Vlan100 | **Active** |
"""

    doc_path = "/home/dev/repos/homelab-gitops/docs/estate_architecture_and_inventory.md"
    with open(doc_path, 'w') as f:
        f.write(doc)
    print(f"Generated comprehensive estate documentation at {doc_path}")

if __name__ == "__main__":
    generate()
