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

    def _build_apply_command(self) -> List[str]:
        """Build tofu apply command."""
        return [
            "tofu",
            f"-chdir={self.chdir}",
            "apply",
            "-var-file=environments/prod.tfvars",
            "-auto-approve"
        ]

    def _build_destroy_command(self) -> List[str]:
        """Build tofu destroy command."""
        return [
            "tofu",
            f"-chdir={self.chdir}",
            "destroy",
            "-auto-approve"
        ]

    def apply(self) -> bool:
        """
        Run 'tofu apply' to provision VM.

        Returns:
            True if apply succeeded, False otherwise
        """
        cmd = self._build_apply_command()
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

    def workspace_new(self, name: str) -> bool:
        """Create a new OpenTofu workspace."""
        cmd = ["tofu", f"-chdir={self.chdir}", "workspace", "new", name]
        result = self._run_command(cmd)
        return result.returncode == 0

    def workspace_delete(self, name: str) -> bool:
        """Delete an OpenTofu workspace."""
        cmd = ["tofu", f"-chdir={self.chdir}", "workspace", "delete", "-force", name]
        result = self._run_command(cmd)
        return result.returncode == 0
