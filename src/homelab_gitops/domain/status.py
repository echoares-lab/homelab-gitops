from typing import List, Dict, Any
from homelab_gitops.domain.models import NodeProfile

class StatusService:
    """Service to aggregate status across infrastructure providers."""

    def __init__(self, vcenter_provider, tofu_provider):
        self.vcenter = vcenter_provider
        self.tofu = tofu_provider

    def get_fleet_status(self, profiles: List[NodeProfile]) -> List[Dict[str, Any]]:
        """Check status of all profiles.
        
        Returns:
            List of status dicts for Rich table display.
        """
        fleet_status = []
        for profile in profiles:
            status = {
                "name": profile.name,
                "provisioned": "Unknown",
                "power": "Unknown",
                "ip": "N/A",
                "drift": "Unknown",
            }

            # 1. Check Tofu Workspace (Provisioning status)
            try:
                tofu_status = self.tofu.get_status(profile.name)
                status["provisioned"] = "Yes" if tofu_status["provisioned"] else "No"
                status["drift"] = "Yes" if tofu_status["drift"] else "No"
            except Exception:
                status["provisioned"] = "Error"
                status["drift"] = "Error"

            # 2. Check vCenter (Power/IP status)
            try:
                vm_status = self.vcenter.get_vm_status(profile)
                status.update(vm_status)
            except Exception:
                status["provisioned"] = "No"
                status["power"] = "N/A"

            fleet_status.append(status)
            
        return fleet_status
