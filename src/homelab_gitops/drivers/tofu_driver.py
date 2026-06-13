"""OpenTofu state management and provisioning driver."""

import subprocess
import shutil
import time
import json
import os
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

    def _run_tofu(self, args: list) -> subprocess.CompletedProcess:
        """Helper to run tofu commands."""
        cmd = [self.tofu_path] + args
        return subprocess.run(
            cmd,
            cwd=self.tofu_dir,
            capture_output=True,
            text=True,
        )

    def get_status(self, profile_name: str) -> Dict[str, Any]:
        """Check status of a profile's workspace.
        
        Returns:
            Dict with 'provisioned' (bool) and 'drift' (bool).
        """
        self._run_tofu(["init", "-no-color"])
        ws_list = self._run_tofu(["workspace", "list"])
        
        if profile_name not in ws_list.stdout:
            return {"provisioned": False, "drift": False}
            
        self._run_tofu(["workspace", "select", profile_name])
        
        # Check for drift using plan
        # -detailed-exitcode: 0=no changes, 2=changes, 1=error
        plan_res = self._run_tofu(["plan", "-detailed-exitcode", "-no-color", f"-var=name={profile_name}"])
        
        return {
            "provisioned": True,
            "drift": plan_res.returncode == 2
        }

    def execute(self, task: Task) -> TaskResult:
        """Execute Tofu apply/destroy for provisioning."""
        start = time.time()

        if task.type not in ("deploy", "destroy"):
            raise ExecutionError(f"TofuDriver handles deploy/destroy, not {task.type}")

        workspace = task.overrides.get("workspace_id", task.profile.name)
        
        # 1. Tofu Init
        init_res = self._run_tofu(["init", "-no-color"])
        if init_res.returncode != 0:
            raise ExecutionError(f"Tofu init failed: {init_res.stderr}")

        # 2. Workspace Select/New
        ws_list = self._run_tofu(["workspace", "list"])
        if workspace not in ws_list.stdout:
            self._run_tofu(["workspace", "new", workspace])
        else:
            self._run_tofu(["workspace", "select", workspace])

        # 3. Build Apply/Destroy Command
        action = "apply" if task.type == "deploy" else "destroy"
        cmd_args = [action, "-auto-approve", "-no-color"]
        
        # Profile vars
        cmd_args.extend(["-var", f"name={task.profile.name}"])
        
        # Overrides
        for k, v in task.overrides.items():
            if k != "workspace_id":
                cmd_args.extend(["-var", f"{k}={v}"])

        res = self._run_tofu(cmd_args)
        if res.returncode != 0:
            raise ExecutionError(f"Tofu {action} failed: {res.stderr}")

        vm_ip = None
        if task.type == "deploy":
            # 4. Get IP from output
            out_res = self._run_tofu(["output", "-json"])
            if out_res.returncode == 0:
                try:
                    outputs = json.loads(out_res.stdout)
                    vm_ip = outputs.get("vm_ip", {}).get("value")
                except json.JSONDecodeError:
                    pass

        duration = time.time() - start
        return TaskResult(
            success=True,
            task_type=task.type,
            output=res.stdout,
            duration=duration,
            vm_ip=vm_ip,
        )
