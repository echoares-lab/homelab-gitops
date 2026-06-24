"""Read-only provider adapters for status and diagnostics flows."""

import socket
from typing import Any, Callable, Dict, Protocol

from homelab_gitops.domain.models import NodeProfile, Task


class HealthCheckProvider(Protocol):
    """Provider capability for read-only health checks."""

    def validate(self) -> bool:
        """Validate provider connectivity and prerequisites."""
        ...


class TofuStatusProvider(Protocol):
    """Provider capability for OpenTofu profile status."""

    def get_status(self, profile_name: str) -> Dict[str, Any]:
        """Return provisioning and drift state for a profile."""
        ...


class VCenterStatusProvider(Protocol):
    """Provider capability for vCenter VM status."""

    def get_vm_status(self, profile: NodeProfile) -> Dict[str, Any]:
        """Return VM provision, power, and guest IP state for a profile."""
        ...


class VCenterDriverStatusAdapter:
    """Read-only status adapter around the current vCenter driver."""

    def __init__(self, driver: Any):
        self.driver = driver

    def get_vm_status(self, profile: NodeProfile) -> Dict[str, Any]:
        task = Task(type="test", profile=profile, target=profile.name)
        result = self.driver.execute(task)

        if not result.success:
            return {"provisioned": "No", "power": "N/A", "ip": "N/A"}

        power = "Suspended"
        if "poweredOn" in result.output:
            power = "On"
        elif "poweredOff" in result.output:
            power = "Off"

        return {
            "provisioned": "Yes",
            "power": power,
            "ip": result.vm_ip or "N/A",
        }


class ReadOnlyProviderFactory:
    """Construct provider adapters for read-only application flows."""

    def status_service(self):
        from homelab_gitops.domain.status import StatusService

        return StatusService(
            vcenter_provider=self.vcenter_status_provider(),
            tofu_provider=self.tofu_status_provider(),
        )

    def doctor_service(self):
        from homelab_gitops.domain.doctor import DoctorService

        return DoctorService(
            health_checks=self.health_checks(),
            dns_resolver=self.dns_resolver(),
        )

    def vcenter_status_provider(self) -> VCenterStatusProvider:
        from homelab_gitops.drivers.vcenter_driver import vCenterDriver

        return VCenterDriverStatusAdapter(vCenterDriver())

    def tofu_status_provider(self) -> TofuStatusProvider:
        from homelab_gitops.drivers.tofu_driver import TofuDriver

        return TofuDriver()

    def health_checks(self) -> Dict[str, HealthCheckProvider]:
        from homelab_gitops.drivers.opnsense_driver import OPNsenseDriver
        from homelab_gitops.drivers.technitium_driver import TechnitiumDriver
        from homelab_gitops.drivers.tofu_driver import TofuDriver
        from homelab_gitops.drivers.vcenter_driver import vCenterDriver

        return {
            "vcenter": vCenterDriver(),
            "technitium": TechnitiumDriver(),
            "opnsense": OPNsenseDriver(),
            "tofu": TofuDriver(),
        }

    def dns_resolver(self) -> Callable[[str], str]:
        return socket.gethostbyname
