"""DNS domain service for Technitium orchestration."""

import logging
import ipaddress
from typing import Dict, Any, Optional, List
from homelab_gitops.domain.models import NodeProfile, Task, TaskResult

logger = logging.getLogger(__name__)


def calculate_ptr(ip: str) -> tuple[str, str]:
    """Return ``(ptr_zone, ptr_domain)`` for *ip*, the canonical implementation.

    Without a prefix the zone is the record's parent -- for IPv4 that is the /24
    reverse zone (``10.10.10.in-addr.arpa`` for ``10.10.10.5``), which is what
    Technitium is authoritative for here. Slicing a fixed number of labels off
    the end instead yields ``10.in-addr.arpa``, a zone that does not exist, and
    every record written into it silently fails to resolve.
    """
    try:
        if "/" in ip:
            iface = ipaddress.ip_interface(ip)
            addr = iface.ip
            prefix = iface.network.prefixlen
        else:
            addr = ipaddress.ip_address(ip)
            prefix = None

        ptr_domain = addr.reverse_pointer
        parts = ptr_domain.split(".")

        if prefix is not None:
            bits_per_label = 8 if isinstance(addr, ipaddress.IPv4Address) else 4
            num_labels_to_keep = (prefix // bits_per_label) + 2  # +2 for in-addr/ip6 + arpa
            ptr_zone = ".".join(parts[-num_labels_to_keep:])
        else:
            ptr_zone = ".".join(parts[1:])

        return ptr_zone, ptr_domain
    except ValueError as e:
        raise ValueError(f"Invalid IP address for PTR calculation: {ip}") from e


class DNSService:
    """Orchestrate Technitium DNS record lifecycle operations within the Domain layer."""

    def __init__(self, driver=None):
        """Initialize service with a Technitium driver.

        Args:
            driver: Optional TechnitiumDriver instance.
        """
        from homelab_gitops.drivers.technitium_driver import TechnitiumDriver
        self.driver = driver or TechnitiumDriver()

    def provision_manual(self, name: str, ip: str, zone: str = None) -> List[TaskResult]:
        """Provision A and PTR records using direct hostname and IP inputs.

        Args:
            name: The hostname (without zone).
            ip: The IP address.
            zone: The DNS zone (defaults to homelab.internal).

        Returns:
            List of TaskResult objects.
        """
        zone = zone or "homelab.internal"
        hostname = f"{name}.{zone}"
        results = []

        # Dummy profile for the task context
        profile = NodeProfile(
            name=name,
            vcenter={
                "datacenter": "N/A",
                "cluster": "N/A",
                "datastore": "N/A",
                "network": "N/A"
            },
            vm_specs={
                "cpu": 0,
                "memory": 0,
                "disk": "0GB"
            },
            deployment={"ip_address": ip, "vm_name_domain": zone}
        )

        # 1. Provision A Record
        logger.info(f"Provisioning manual A record for {hostname} -> {ip}")
        a_task = Task(
            type="provision",
            profile=profile,
            target=ip,
            overrides={
                "resource": "record",
                "action": "create",
                "zone": zone,
                "domain": hostname,
                "type": "A",
                "ipAddress": ip
            }
        )
        a_result = self.driver.execute(a_task)
        results.append(a_result)

        # 2. Provision PTR Record (if A record succeeded and IP is known)
        if a_result.success and ip:
            try:
                ptr_zone, ptr_domain = self._calculate_ptr(ip)
                logger.info(f"Provisioning manual PTR record for {ip} -> {hostname}")
                ptr_task = Task(
                    type="provision",
                    profile=profile,
                    overrides={
                        "resource": "record",
                        "action": "create",
                        "zone": ptr_zone,
                        "domain": ptr_domain,
                        "type": "PTR",
                        "ptr": hostname
                    }
                )
                results.append(self.driver.execute(ptr_task))
            except Exception as e:
                logger.error(f"Failed to provision manual PTR record: {str(e)}")

        return results

    def deprovision_manual(self, name: str, ip: str = None, zone: str = None) -> List[TaskResult]:
        """Deprovision A and PTR records using direct hostname and optional IP.

        Args:
            name: The hostname (without zone).
            ip: Optional IP address for PTR cleanup.
            zone: The DNS zone (defaults to homelab.internal).

        Returns:
            List of TaskResult objects.
        """
        zone = zone or "homelab.internal"
        hostname = f"{name}.{zone}"
        results = []

        # Dummy profile
        profile = NodeProfile(
            name=name,
            vcenter={
                "datacenter": "N/A",
                "cluster": "N/A",
                "datastore": "N/A",
                "network": "N/A"
            },
            vm_specs={
                "cpu": 0,
                "memory": 0,
                "disk": "0GB"
            },
            deployment={"vm_name_domain": zone}
        )
        if ip:
            profile.deployment["ip_address"] = ip

        # 1. Deprovision A Record
        logger.info(f"Deprovisioning manual A record for {hostname}")
        a_task = Task(
            type="destroy",
            profile=profile,
            overrides={
                "resource": "record",
                "action": "delete",
                "zone": zone,
                "domain": hostname,
                "type": "A"
            }
        )
        results.append(self.driver.execute(a_task))

        # 2. Deprovision PTR Record (if IP is provided)
        if ip:
            try:
                ptr_zone, ptr_domain = self._calculate_ptr(ip)
                logger.info(f"Deprovisioning manual PTR record for {ip}")
                ptr_task = Task(
                    type="destroy",
                    profile=profile,
                    overrides={
                        "resource": "record",
                        "action": "delete",
                        "zone": ptr_zone,
                        "domain": ptr_domain,
                        "type": "PTR"
                    }
                )
                results.append(self.driver.execute(ptr_task))
            except Exception as e:
                logger.warning(f"Failed to deprovision manual PTR record: {str(e)}")

        return results

    def provision_record(self, profile: NodeProfile, ip_address: Optional[str] = None) -> List[TaskResult]:
        """Provision A and PTR records for a node profile.

        Maps NodeProfile deployment details (IP, Hostname) to DNS records.
        Handles multi-record updates (A, PTR) sequentially.

        Args:
            profile: The node profile containing deployment details.
            ip_address: Optional IP address. If not provided, looks in profile.deployment.

        Returns:
            List of TaskResult objects for each operation.
        """
        zone = profile.deployment.get("vm_name_domain", "homelab.internal")
        ip = ip_address or profile.deployment.get("ip_address")

        if not ip:
            logger.warning(f"No IP address resolved for {profile.name}, DNS record might fail.")

        # Delegate to manual method
        return self.provision_manual(profile.name, ip, zone)

    def deprovision_record(self, profile: NodeProfile) -> List[TaskResult]:
        """Deprovision A and PTR records for a node profile.

        Args:
            profile: The node profile to deprovision.

        Returns:
            List of TaskResult objects for each operation.
        """
        zone = profile.deployment.get("vm_name_domain", "homelab.internal")
        ip = profile.deployment.get("ip_address")

        # Delegate to manual method
        return self.deprovision_manual(profile.name, ip, zone)

    def list_records(self, zone: str) -> List[Dict[str, Any]]:
        """List all DNS records in a given zone.

        Args:
            zone: The zone to list records from.

        Returns:
            A list of record dictionaries.
        """
        # Minimal profile for the task
        dummy_profile = NodeProfile(
            name="dns-query",
            vcenter={
                "datacenter": "N/A",
                "cluster": "N/A",
                "datastore": "N/A",
                "network": "N/A"
            },
            vm_specs={
                "cpu": 0,
                "memory": 0,
                "disk": "0GB"
            },
            deployment={"tags": []}
        )

        task = Task(
            type="list",
            profile=dummy_profile,
            overrides={
                "resource": "record",
                "action": "list",
                "zone": zone
            }
        )
        result = self.driver.execute(task)
        if result.success and isinstance(result.output, dict):
            return result.output.get("records", [])
        return []

    def _calculate_ptr(self, ip: str) -> tuple[str, str]:
        """Delegates to :func:`calculate_ptr` -- kept as the service-level entry point."""
        return calculate_ptr(ip)
