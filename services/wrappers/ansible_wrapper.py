"""Ansible wrapper for configuration management."""

from typing import List, Dict, Optional
from services.wrappers.base_wrapper import BaseWrapper


class AnsibleWrapper(BaseWrapper):
    """Ansible playbook wrapper for node configuration."""

    @property
    def tool_name(self) -> str:
        return "ansible-playbook"

    def run_playbook(
        self,
        playbook: str,
        inventory: str = "ansible/inventory/vmware_vms.yml",
        extra_vars: Optional[Dict] = None,
        tags: Optional[List[str]] = None
    ) -> bool:
        """
        Run an Ansible playbook.

        Args:
            playbook: Path to playbook file (e.g., 'ansible/site.yml')
            inventory: Path to inventory file
            extra_vars: Dictionary of extra variables to pass to playbook
            tags: List of tags to run (e.g., ['docker', 'security'])

        Returns:
            True if playbook succeeded, False otherwise
        """
        cmd = ["ansible-playbook", playbook, "-i", inventory]

        if extra_vars:
            for key, value in extra_vars.items():
                cmd.extend(["-e", f"{key}={value}"])

        if tags:
            cmd.extend(["-t", ",".join(tags)])

        result = self._run_command(cmd)
        return result.returncode == 0

    def validate_syntax(self, playbook: str) -> bool:
        """
        Validate playbook syntax without executing.

        Args:
            playbook: Path to playbook file

        Returns:
            True if syntax is valid, False otherwise
        """
        cmd = ["ansible-playbook", playbook, "--syntax-check"]
        result = self._run_command(cmd)
        return result.returncode == 0
