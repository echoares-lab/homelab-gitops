"""testinfra wrapper for VM validation."""

from typing import List, Optional
from services.wrappers.base_wrapper import BaseWrapper


class TestinfraWrapper(BaseWrapper):
    """testinfra (pytest-testinfra) wrapper for VM validation."""

    @property
    def tool_name(self) -> str:
        return "pytest"

    def run_tests(
        self,
        hosts: List[str],
        test_dir: str = "tests/",
        ssh_key: Optional[str] = None,
        sudo: bool = True
    ) -> bool:
        """
        Run testinfra tests against one or more hosts.

        Args:
            hosts: List of host specifications (e.g., ['ansible@10.10.10.50'])
            test_dir: Directory containing testinfra tests
            ssh_key: Optional SSH private key file
            sudo: Whether to use sudo for tests

        Returns:
            True if all tests passed, False otherwise
        """
        cmd = ["pytest", test_dir, "-v"]

        hosts_str = " ".join(hosts)
        cmd.append(f"--hosts={hosts_str}")

        if ssh_key:
            ssh_extra = f"-o IdentityFile={ssh_key} -o StrictHostKeyChecking=no"
            cmd.append(f"--ssh-extra-args={ssh_extra}")

        if sudo:
            cmd.append("--sudo")

        result = self._run_command(cmd)
        return result.returncode == 0
