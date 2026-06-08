"""Data models for OPNsense API objects"""

from dataclasses import dataclass
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
