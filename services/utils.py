"""Shared utility functions for services."""

import re
import time
import subprocess
from typing import Optional
from rich.console import Console

console = Console()

def validate_mac(mac: Optional[str]):
    """Ensures MAC address follows the xx:xx:xx:xx:xx:xx format."""
    if mac and not re.match(r"^([0-9a-fA-F]{2}:){5}[0-9a-fA-F]{2}$", mac):
        console.print(f"[bold red]Error:[/bold red] Invalid MAC address format ({mac}).")
        raise ValueError(f"Invalid MAC address: {mac}")

def track_time(start_time: float, task_name: str):
    """Calculates and prints the duration of a task."""
    duration = int(time.time() - start_time)
    console.print(f"[bold green]Task [{task_name}][/bold green] completed in {duration // 60}m {duration % 60}s")

def run_cmd(cmd, cwd=None, capture=False, env=None):
    """
    Execute a shell command.

    Args:
        cmd: Command string or list
        cwd: Working directory
        capture: If True, return stdout; if False, stream to console
        env: Environment variables dict

    Returns:
        Tuple of (returncode, stdout, stderr) if capture=True, else (returncode, "", "")
    """
    if isinstance(cmd, str):
        cmd = cmd.split()

    if capture:
        result = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, env=env)
        return result.returncode, result.stdout, result.stderr
    else:
        result = subprocess.run(cmd, cwd=cwd, env=env)
        return result.returncode, "", ""
