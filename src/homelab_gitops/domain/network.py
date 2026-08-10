"""Network generation service for automatically assigning MAC, IP, and DNS."""
import random
import ipaddress
import csv
import os
import subprocess
from typing import Optional, Tuple
from homelab_gitops.domain.models import NodeProfile
from homelab_gitops.domain.dns import calculate_ptr

class NetworkService:
    def __init__(self, dns_csv_path: str = "config/dns_records.csv"):
        self.csv_path = dns_csv_path
        # Addresses handed out by this instance but not yet on disk. Without
        # this, a batch provisioning run re-reads the same CSV for every host
        # and gives them all the same address.
        self._pending_ips: set = set()
        self.headers = [
            "resource_type", "name", "parent", "type", "value", "ttl", 
            "mac_address", "network_address", "subnet_mask", 
            "start_address", "end_address", "gateway", 
            "comments", "depends_on", "advanced_json"
        ]

    def generate_mac(self) -> str:
        """Generate a random VMware MAC address."""
        mac = [0x00, 0x50, 0x56,
               random.randint(0x00, 0x3f),
               random.randint(0x00, 0xff),
               random.randint(0x00, 0xff)]
        return ':'.join(map(lambda x: "%02x" % x, mac))
        
    def get_next_ip(self, scope_network: str) -> str:
        """IP allocation: finds first available IP in the exclusion zone (2-100) for reservations."""
        used_ips = set(self._pending_ips)
        
        if os.path.exists(self.csv_path):
            with open(self.csv_path, "r") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    val = row.get("value")
                    if val:
                        try:
                            used_ips.add(ipaddress.IPv4Address(val))
                        except ipaddress.AddressValueError:
                            pass
                            
        try:
            # If missing cidr, assume /24
            network_str = scope_network if '/' in scope_network else f"{scope_network}/24"
            network = ipaddress.IPv4Network(network_str, strict=False)
            
            # Use the exclusion range for reservations (typically 2-100)
            start_ip_obj = network.network_address + 2
            end_ip_obj = network.network_address + 100
        except ValueError:
            return ""
                
        current_ip_int = int(start_ip_obj)
        end_ip_int = int(end_ip_obj)
        
        for ip_int in range(current_ip_int, end_ip_int + 1):
            ip_obj = ipaddress.IPv4Address(ip_int)
            ip_str = str(ip_obj)
            
            if ip_obj in used_ips:
                continue
                
            try:
                res = subprocess.run(["ping", "-c", "1", "-W", "1", ip_str], capture_output=True)
                if res.returncode != 0:
                    self._pending_ips.add(ip_obj)
                    return ip_str
            except Exception:
                pass
                
        return ""

    def append_dns_records(self, mac: str, ip: str, hostname: str, domain: str, scope_network: str, comments: str = ""):
        """Appends the DHCP Lease, A record, and PTR record to the CSV."""
        os.makedirs(os.path.dirname(self.csv_path), exist_ok=True)
        file_exists = os.path.exists(self.csv_path)
        
        with open(self.csv_path, "a", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=self.headers)
            if not file_exists:
                writer.writeheader()
                
            writer.writerow({
                "resource_type": "dhcp_lease",
                "name": hostname,
                "parent": scope_network,
                "value": ip,
                "mac_address": mac,
                "comments": comments
            })
            
            writer.writerow({
                "resource_type": "record",
                "name": hostname,
                "parent": domain,
                "type": "A",
                "value": ip,
                "comments": comments
            })
            
            try:
                ptr_zone, ptr_domain = calculate_ptr(ip)
                
                writer.writerow({
                    "resource_type": "record",
                    "name": ptr_domain,
                    "parent": ptr_zone,
                    "type": "PTR",
                    "value": f"{hostname}.{domain}",
                    "comments": comments
                })
            except Exception:
                pass

        try:
            self._pending_ips.discard(ipaddress.IPv4Address(ip))
        except ValueError:
            pass

    def get_existing_records(self, hostname: str) -> Tuple[Optional[str], Optional[str]]:
        """Check if records exist for a hostname. Returns (mac, ip)."""
        if not os.path.exists(self.csv_path):
            return None, None
            
        mac, ip = None, None
        with open(self.csv_path, "r") as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row.get("name") == hostname:
                    if row.get("resource_type") == "dhcp_lease":
                        mac = row.get("mac_address")
                        ip = row.get("value")
                    elif row.get("resource_type") == "record" and row.get("type") == "A":
                        ip = row.get("value")
        return mac, ip

    def ensure_network(self, profile: NodeProfile, index: Optional[str] = None):
        """Ensure network records exist. If not, generate them and attach to profile."""
        hostname = f"{profile.name}-{index}" if index else profile.name
        mac, ip = self.get_existing_records(hostname)
        
        if mac and ip:
            profile.deployment["mac_address"] = mac
            if not profile.deployment.get("dhcp_only", False):
                profile.deployment["ip_address"] = ip
            return

        mac = self.generate_mac()
        scope_network = profile.deployment.get("dhcp_scope", "10.10.10.0")
        ip = self.get_next_ip(scope_network)
        domain = profile.deployment.get("vm_name_domain", "mgmt.plexplease.com")
        
        if ip:
            self.append_dns_records(mac, ip, hostname, domain, scope_network, f"Auto-generated for {hostname}")
            profile.deployment["mac_address"] = mac
            if not profile.deployment.get("dhcp_only", False):
                profile.deployment["ip_address"] = ip
