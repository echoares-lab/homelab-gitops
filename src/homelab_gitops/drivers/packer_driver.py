"""Packer image building driver."""

import subprocess
import shutil
import time
import os
from homelab_gitops.drivers.base import Driver
from homelab_gitops.drivers.exceptions import PrerequisiteError, ExecutionError
from homelab_gitops.domain.models import Task, TaskResult


class PackerDriver(Driver):
    """Build golden images using Packer."""

    def __init__(self):
        """Initialize PackerDriver."""
        self.packer_path = shutil.which("packer")

    def validate(self) -> bool:
        """Check packer is installed."""
        if not self.packer_path:
            raise PrerequisiteError("packer not found in PATH")
        return True

    def execute(self, task: Task) -> TaskResult:
        """Execute Packer build for image creation."""
        start = time.time()

        if task.type != "build":
            raise ExecutionError(f"PackerDriver handles build, not {task.type}")

        # Determine template based on profile
        os_type = task.profile.vcenter.get("os_type", "ubuntu2404")
        template = f"packer/{os_type}.pkr.hcl"
        
        if not os.path.exists(template):
            if "photon" in os_type.lower():
                template = "packer/photon.pkr.hcl"
            else:
                template = "packer/ubuntu2404.pkr.hcl"

        cmd = [
            self.packer_path,
            "build",
            "-var", f"name={task.profile.name}",
        ]
        
        # Add overrides as vars
        for k, v in task.overrides.items():
            cmd.extend(["-var", f"{k}={v}"])
            
        cmd.append(template)

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=3600,
            )

            if result.returncode != 0:
                raise ExecutionError(f"Packer failed: {result.stderr}")

            duration = time.time() - start
            return TaskResult(
                success=True,
                task_type=task.type,
                output=result.stdout,
                duration=duration,
            )
        except subprocess.TimeoutExpired:
            raise ExecutionError("Packer execution timed out after 3600s")
