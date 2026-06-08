"""Ansible playbook execution driver."""

import subprocess
import shutil
import time
from .base import Driver
from .exceptions import PrerequisiteError, ExecutionError
from homelab_gitops.domain.models import Task, TaskResult


class AnsibleDriver(Driver):
    """Execute Ansible playbooks."""

    def __init__(self):
        """Initialize AnsibleDriver."""
        self.ansible_path = shutil.which("ansible-playbook")

    def validate(self) -> bool:
        """Check ansible-playbook is installed."""
        if not self.ansible_path:
            raise PrerequisiteError("ansible-playbook not found in PATH")
        return True

    def execute(self, task: Task) -> TaskResult:
        """Execute Ansible playbook for configuration task."""
        start = time.time()

        if task.type == "config":
            playbook = "ansible/site.yml"
        elif task.type == "build":
            playbook = "ansible/discover.yml"
        else:
            raise ExecutionError(f"Unsupported task type: {task.type}")

        cmd = [
            self.ansible_path,
            "-i", task.target or "localhost",
            playbook,
            "-e", f"profile_name={task.profile.name}",
        ]

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=600,
            )

            if result.returncode != 0:
                raise ExecutionError(f"Ansible failed: {result.stderr}")

            duration = time.time() - start
            return TaskResult(
                success=True,
                task_type=task.type,
                output=result.stdout,
                duration=duration,
            )
        except subprocess.TimeoutExpired:
            raise ExecutionError("Ansible execution timed out after 600s")
