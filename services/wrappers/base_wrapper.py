"""Abstract base class for all tool wrappers."""

from abc import ABC, abstractmethod
import subprocess
import shutil
from typing import List
from rich.console import Console

console = Console()


class BaseWrapper(ABC):
    """Abstract base for all tool wrappers.

    Each tool wrapper:
    1. Validates tool is installed at init (fail fast)
    2. Builds commands as pure functions
    3. Executes via subprocess
    4. Returns success/failure boolean
    """

    @property
    @abstractmethod
    def tool_name(self) -> str:
        """Tool name (e.g., 'tofu', 'ansible-playbook')."""
        pass

    def __init__(self):
        """Initialize wrapper and validate tool is installed."""
        self._validate_tool_installed()

    def _validate_tool_installed(self) -> None:
        """Check if tool exists in PATH. Raise RuntimeError if missing."""
        if not shutil.which(self.tool_name):
            raise RuntimeError(
                f"{self.tool_name} not found in PATH. "
                f"Please install {self.tool_name} and ensure it's in your PATH."
            )

    def _run_command(self, cmd: List[str], cwd: str = None) -> subprocess.CompletedProcess:
        """
        Execute a command and return the result.

        Args:
            cmd: Command as list of arguments (e.g., ['tofu', 'apply'])
            cwd: Optional working directory

        Returns:
            subprocess.CompletedProcess with returncode, stdout, stderr

        Raises:
            RuntimeError: If command execution fails
        """
        try:
            console.print(f"[dim]Running: {' '.join(cmd)}[/dim]")
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                cwd=cwd,
                check=False
            )

            if result.returncode != 0:
                console.print(f"[yellow]Command stderr: {result.stderr}[/yellow]")

            return result
        except Exception as e:
            raise RuntimeError(f"Failed to execute {self.tool_name}: {e}")
