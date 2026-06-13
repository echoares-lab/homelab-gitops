"""vCenter infrastructure discovery and management driver."""

import subprocess
import shutil
import time
import json
from typing import Dict, Any
from homelab_gitops.drivers.base import Driver
from homelab_gitops.drivers.exceptions import PrerequisiteError, ExecutionError
from homelab_gitops.domain.models import Task, TaskResult


class vCenterDriver(Driver):
    """Query and manage vCenter infrastructure."""

    def __init__(self):
        """Initialize vCenterDriver."""
        self.govc_path = shutil.which("govc") or "build/govc"

    def validate(self) -> bool:
        """Check govc is available."""
        try:
            result = subprocess.run(
                [self.govc_path, "about"],
                capture_output=True,
                timeout=5,
            )
            if result.returncode != 0:
                raise PrerequisiteError("govc not available or vCenter not reachable")
            return True
        except (subprocess.SubprocessError, FileNotFoundError):
             raise PrerequisiteError("govc tool not found or failed to run")

    def execute(self, task: Task) -> TaskResult:
        """Execute vCenter operations."""
        start = time.time()

        vm_name = task.target or task.profile.name
        vm_ip = None
        success = False
        output = ""
        
        # Determine operation
        if task.type == "test":
            # Check VM status
            cmd = [self.govc_path, "vm.info", "-json", vm_name]
            res = subprocess.run(cmd, capture_output=True, text=True)
            
            if res.returncode != 0:
                raise ExecutionError(f"Failed to get VM info for {vm_name}: {res.stderr}")
            
            try:
                data = json.loads(res.stdout)
                vms = data.get("VirtualMachines", [])
                if not vms:
                    raise ExecutionError(f"VM {vm_name} not found")
                
                vm = vms[0]
                power_state = vm.get("Runtime", {}).get("PowerState")
                guest_ip = vm.get("Guest", {}).get("IpAddress")
                
                output = f"VM: {vm_name}, Power: {power_state}, IP: {guest_ip}"
                success = (power_state == "poweredOn")
                vm_ip = guest_ip
            except (json.JSONDecodeError, KeyError, IndexError) as e:
                raise ExecutionError(f"Failed to parse govc output: {str(e)}")

        elif task.type == "destroy":
             # Power off and destroy
             subprocess.run([self.govc_path, "vm.power", "-off", "-force", vm_name], capture_output=True)
             res = subprocess.run([self.govc_path, "vm.destroy", vm_name], capture_output=True, text=True)
             if res.returncode != 0:
                 raise ExecutionError(f"Failed to destroy VM {vm_name}: {res.stderr}")
             output = f"VM {vm_name} destroyed"
             success = True
             vm_ip = None
        else:
            raise ExecutionError(f"vCenterDriver doesn't handle {task.type} yet")

        duration = time.time() - start
        return TaskResult(
            success=success,
            task_type=task.type,
            output=output,
            duration=duration,
            vm_ip=vm_ip,
        )
