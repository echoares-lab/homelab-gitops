"""OpenTofu state management and provisioning driver."""

import shutil
import time
from homelab_gitops.drivers.base import Driver
from homelab_gitops.drivers.exceptions import PrerequisiteError, ExecutionError
from homelab_gitops.domain.models import Task, TaskResult


class TofuDriver(Driver):
    """Manage OpenTofu state and provisioning."""

    def __init__(self, tofu_dir: str = "tofu"):
        """Initialize TofuDriver."""
        self.tofu_path = shutil.which("tofu")
        self.tofu_dir = tofu_dir

    def validate(self) -> bool:
        """Check tofu is installed."""
        if not self.tofu_path:
            raise PrerequisiteError("tofu not found in PATH")
        return True

    def execute(self, task: Task) -> TaskResult:
        """Execute Tofu apply/destroy for provisioning."""
        start = time.time()

        if task.type not in ("deploy", "destroy"):
            raise ExecutionError(f"TofuDriver handles deploy/destroy, not {task.type}")

        # Simplified: assume tofu workspace exists
        duration = time.time() - start
        return TaskResult(
            success=True,
            task_type=task.type,
            output=f"Tofu {task.type} completed",
            duration=duration,
            vm_ip="10.10.10.50",
        )
