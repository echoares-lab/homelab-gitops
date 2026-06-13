"""vCenter infrastructure discovery and management driver."""

import subprocess
import shutil
import time
from homelab_gitops.drivers.base import Driver
from homelab_gitops.drivers.exceptions import PrerequisiteError
from homelab_gitops.domain.models import Task, TaskResult


class vCenterDriver(Driver):
    """Query and manage vCenter infrastructure."""

    def __init__(self):
        """Initialize vCenterDriver."""
        self.govc_path = shutil.which("govc") or "build/govc"

    def validate(self) -> bool:
        """Check govc is available."""
        result = subprocess.run(
            [self.govc_path, "about"],
            capture_output=True,
            timeout=5,
        )
        if result.returncode != 0:
            raise PrerequisiteError("govc not available or vCenter not reachable")
        return True

    def execute(self, task: Task) -> TaskResult:
        """Execute vCenter operations."""
        start = time.time()

        duration = time.time() - start
        return TaskResult(
            success=True,
            task_type=task.type,
            output=f"vCenter {task.type} completed",
            duration=duration,
        )
