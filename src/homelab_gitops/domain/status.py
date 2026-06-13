from typing import List, Dict, Any
from homelab_gitops.domain.models import NodeProfile, Task, TaskResult
from homelab_gitops.drivers.vcenter_driver import vCenterDriver
from homelab_gitops.drivers.tofu_driver import TofuDriver

class StatusService:
    """Service to aggregate status across infrastructure providers."""

    def __init__(self, vcenter_driver: vCenterDriver, tofu_driver: TofuDriver):
        self.vcenter = vcenter_driver
        self.tofu = tofu_driver

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
                task = Task(type="test", profile=profile, target=profile.name)
                result = self.vcenter.execute(task)
                
                if result.success:
                    status["provisioned"] = "Yes"
                    # Parse output "VM: name, Power: poweredOn, IP: 1.2.3.4"
                    # Actually result has vm_ip
                    status["ip"] = result.vm_ip or "N/A"
                    
                    if "poweredOn" in result.output:
                        status["power"] = "On"
                    elif "poweredOff" in result.output:
                        status["power"] = "Off"
                    else:
                        status["power"] = "Suspended"
                else:
                    status["provisioned"] = "No"
                    status["power"] = "N/A"
            except Exception:
                status["provisioned"] = "No"
                status["power"] = "N/A"

            fleet_status.append(status)
            
        return fleet_status
