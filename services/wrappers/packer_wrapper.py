"""Packer wrapper for golden image builds."""

from typing import List
from services.wrappers.base_wrapper import BaseWrapper


class PackerWrapper(BaseWrapper):
    """Packer wrapper for building golden images."""

    @property
    def tool_name(self) -> str:
        return "packer"

    def build(self, target: str) -> bool:
        """
        Build a golden image.

        Args:
            target: Build target (e.g., 'ubuntu-2404', 'photon-docker')

        Returns:
            True if build succeeded, False otherwise
        """
        template = f"packer/{target}.pkr.hcl"
        cmd = ["packer", "build", template]
        result = self._run_command(cmd)
        return result.returncode == 0

    def validate_template(self, template: str) -> bool:
        """
        Validate Packer template without building.

        Args:
            template: Path to Packer template file

        Returns:
            True if template is valid, False otherwise
        """
        cmd = ["packer", "validate", template]
        result = self._run_command(cmd)
        return result.returncode == 0
