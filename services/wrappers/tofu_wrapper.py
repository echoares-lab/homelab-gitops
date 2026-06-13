"""OpenTofu wrapper for IaC operations."""

from typing import List, Optional
from services.wrappers.base_wrapper import BaseWrapper


class TofuWrapper(BaseWrapper):
    """OpenTofu command wrapper for VM provisioning and destruction."""

    @property
    def tool_name(self) -> str:
        return "tofu"

    def __init__(self, workspace: str = "default", chdir: str = "tofu/"):
        """
        Initialize Tofu wrapper.

        Args:
            workspace: OpenTofu workspace name (e.g., 'ubuntu-2404-base-01')
            chdir: Directory containing OpenTofu files (default: 'tofu/')
        """
        self.workspace = workspace
        self.chdir = chdir
        super().__init__()

    def _build_apply_command(self, variables: Optional[dict] = None) -> List[str]:
        """Build tofu apply command."""
        cmd = [
            "tofu",
            f"-chdir={self.chdir}",
            "apply",
            "-auto-approve"
        ]

        if variables:
            for key, value in variables.items():
                cmd.extend(["-var", f"{key}={value}"])

        return cmd

    def _build_destroy_command(self) -> List[str]:
        """Build tofu destroy command."""
        return [
            "tofu",
            f"-chdir={self.chdir}",
            "destroy",
            "-auto-approve"
        ]

    def apply(self, variables: Optional[dict] = None) -> bool:
        """
        Run 'tofu apply' to provision VM.

        Args:
            variables: Optional dictionary of variables to pass to tofu

        Returns:
            True if apply succeeded, False otherwise
        """
        cmd = self._build_apply_command(variables)
        result = self._run_command(cmd)
        return result.returncode == 0

    def destroy(self) -> bool:
        """
        Run 'tofu destroy' to decommission VM.

        Returns:
            True if destroy succeeded, False otherwise
        """
        cmd = self._build_destroy_command()
        result = self._run_command(cmd)
        return result.returncode == 0

    def init(self) -> bool:
        """Run 'tofu init'."""
        cmd = ["tofu", f"-chdir={self.chdir}", "init"]
        result = self._run_command(cmd)
        return result.returncode == 0

    def workspace_new(self, name: str) -> bool:
        """Create a new OpenTofu workspace. If it exists, select it."""
        cmd = ["tofu", f"-chdir={self.chdir}", "workspace", "new", name]
        result = self._run_command(cmd)
        if result.returncode != 0:
            # Try selecting it
            cmd = ["tofu", f"-chdir={self.chdir}", "workspace", "select", name]
            result = self._run_command(cmd)
        return result.returncode == 0

    def workspace_delete(self, name: str) -> bool:
        """Delete an OpenTofu workspace."""
        cmd = ["tofu", f"-chdir={self.chdir}", "workspace", "delete", "-force", name]
        result = self._run_command(cmd)
        return result.returncode == 0
