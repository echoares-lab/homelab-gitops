"""Ansible playbook execution driver."""

import subprocess
import shutil
import time
import os
import json
from homelab_gitops.drivers.base import Driver
from homelab_gitops.drivers.exceptions import PrerequisiteError, ExecutionError
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
            playbook = task.overrides.get("playbook", "ansible/site.yml")
        elif task.type == "build":
            # For ansible, build might mean discovering or preparing
            playbook = task.overrides.get("playbook", "ansible/deploy.yml")
        elif task.type == "test":
            playbook = task.overrides.get("playbook", "ansible/site.yml")
            # We might want a specific test playbook or just run with --check/--tags
        else:
            raise ExecutionError(f"Unsupported task type: {task.type}")

        if not os.path.exists(playbook):
             raise ExecutionError(f"Playbook not found: {playbook}")

        # Build command
        # Use comma if target is a single IP/hostname and not a file
        target = task.target or "localhost"
        temp_inv_path = None
        if not os.path.exists(target) and "," not in target:
            if task.profile and task.profile.deployment.get("tags"):
                import tempfile
                temp_inv = tempfile.NamedTemporaryFile(mode="w", suffix=".ini", delete=False)
                temp_inv.write(f"\n[all]\n{target}\n")
                for tag in task.profile.deployment.get("tags", []):
                    temp_inv.write(f"\n[tag_{tag}]\n{target}\n")
                temp_inv.close()
                inventory = temp_inv.name
                temp_inv_path = temp_inv.name
            else:
                inventory = f"{target},"
        else:
            inventory = target

        cmd = [
            self.ansible_path,
            "-i", inventory,
            playbook,
        ]

        # SSH Identity
        ssh_key = task.overrides.get("ssh_key") or os.environ.get("SSH_PRIVATE_KEY_PATH") or (task.profile.deployment.get("ssh_private_key_path") if task.profile else None)
        if ssh_key:
            ssh_key = os.path.expanduser(ssh_key)
            if not os.path.exists(ssh_key):
                if os.path.exists(os.path.expanduser("~/.ssh/id_ed25519")):
                    ssh_key = os.path.expanduser("~/.ssh/id_ed25519")
                elif os.path.exists(os.path.expanduser("~/.ssh/id_rsa")):
                    ssh_key = os.path.expanduser("~/.ssh/id_rsa")
            cmd.extend(["--private-key", ssh_key])
            
        ssh_user = task.overrides.get("ssh_user") or os.environ.get("SSH_ADMIN_USERNAME") or (task.profile.deployment.get("ssh_admin_username") if task.profile else None) or "ansible"
        if ssh_user:
            cmd.extend(["-u", ssh_user])

        limit = task.overrides.get("limit")
        if limit:
            cmd.extend(["--limit", limit])

        tags = task.overrides.get("tags")
        if tags:
            if isinstance(tags, list):
                tags = ",".join(tags)
            cmd.extend(["--tags", tags])

        # Extra vars
        extra_vars = {
            "profile_name": task.profile.name,
        }
        # Merge task overrides into extra_vars (except driver-specific ones)
        for k, v in task.overrides.items():
            if k not in ("playbook", "ssh_key", "ssh_user", "timeout", "limit", "tags"):
                extra_vars[k] = v
        
        # Add profile's deployment roles/vars
        for k, v in task.profile.deployment.items():
            if k not in ("limit", "tags"):
                extra_vars[k] = v

        cmd.extend(["-e", json.dumps(extra_vars)])

        # Set Ansible environment variables
        env = os.environ.copy()
        env["ANSIBLE_HOST_KEY_CHECKING"] = "False"
        env["ANSIBLE_STDOUT_CALLBACK"] = "default"

        timeout = task.overrides.get("timeout", 1800)

        try:
            try:
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=timeout,
                    env=env,
                )

                if result.returncode != 0:
                    raise ExecutionError(f"Ansible failed (RC={result.returncode}):\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}")

                duration = time.time() - start
                return TaskResult(
                    success=True,
                    task_type=task.type,
                    output=result.stdout,
                    duration=duration,
                )
            except subprocess.TimeoutExpired:
                raise ExecutionError(f"Ansible execution timed out after {timeout}s")
        finally:
            if temp_inv_path and os.path.exists(temp_inv_path):
                try:
                    os.unlink(temp_inv_path)
                except Exception:
                    pass
