"""InfrastructureService: vCenter, OpenTofu, and Ansible integration."""

import subprocess
import shutil
from typing import List, Dict, Optional
from rich.console import Console
from services.utils import run_cmd

console = Console()

class InfrastructureService:
    """
    Manages vCenter, OpenTofu, and Ansible infrastructure operations.

    This is a shared service used by orchestration commands to interact
    with infrastructure (VMs, networks, configuration).
    """

    def __init__(self):
        """Initialize infrastructure service."""
        self.govc_path = shutil.which("govc") or "./build/govc"

    def ensure_tags_exist(self, tags: List[str]) -> bool:
        """
        Check and create vSphere tags using govc if they don't exist.

        Args:
            tags: List of tag names to ensure exist

        Returns:
            True if all tags exist or were created
        """
        if not tags:
            return True

        try:
            with console.status("[bold blue]Ensuring vCenter tags exist..."):
                # Check if tag category exists
                rc, out, err = run_cmd([self.govc_path, "tags.category.ls"], capture=True)

                if "Provisioning" not in out:
                    console.print("[yellow]Creating tag category 'Provisioning'...[/yellow]")
                    run_cmd([self.govc_path, "tags.category.create", "Provisioning"])

                # Check and create tags
                rc, out, err = run_cmd(
                    [self.govc_path, "tags.ls", "-c", "Provisioning"],
                    capture=True
                )

                for tag in tags:
                    if tag not in out:
                        console.print(f"[yellow]Creating vCenter tag '{tag}'...[/yellow]")
                        run_cmd([self.govc_path, "tags.create", "-c", "Provisioning", tag])

            return True
        except Exception as e:
            console.print(f"[yellow]Warning: Could not ensure tags: {e}[/yellow]")
            return False

    def get_host_info(self, hostname: str) -> Dict[str, str]:
        """
        Get information about an ESXi host.

        Args:
            hostname: ESXi hostname or IP

        Returns:
            Dictionary with host info (cpu, memory, etc.)
        """
        # Placeholder: would query vCenter via govc
        return {
            "name": hostname,
            "cpu": "Unknown",
            "memory": "Unknown"
        }

    def list_cluster_hosts(self) -> List[str]:
        """
        List all ESXi hosts in the cluster.

        Returns:
            List of host names
        """
        # Placeholder: would query vCenter
        return []

    def get_vm_status(self, vm_name: str) -> Dict[str, str]:
        """
        Get the current status of a VM (power state, IP, tags, etc.).

        Args:
            vm_name: Name of the VM

        Returns:
            Dictionary with VM status
        """
        # Placeholder: would query vCenter
        return {
            "name": vm_name,
            "power": "Unknown",
            "ip": "Unknown",
            "tags": []
        }

    def collect_fleet_status(self) -> List[Dict]:
        """
        Collect status of all managed VMs from vCenter and OpenTofu.

        Returns:
            List of VM status dictionaries
        """
        console.print("[dim]Querying OpenTofu workspaces...[/dim]")
        # 1. Get workspaces
        rc, out, err = run_cmd(["tofu", "-chdir=tofu/", "workspace", "list"], capture=True)
        if rc != 0:
            console.print(f"[red]Error listing workspaces: {err}[/red]")
            return []

        workspaces = []
        for line in out.splitlines():
            line = line.replace("*", "").strip()
            if line and line != "default":
                workspaces.append(line)

        if not workspaces:
            return []

        # 2. Get VM info from vCenter
        # Map VCENTER env vars to GOVC env vars for the command
        import os
        govc_env = os.environ.copy()
        govc_env["GOVC_URL"] = os.getenv("VCENTER_SERVER", "")
        govc_env["GOVC_USERNAME"] = os.getenv("VCENTER_USERNAME", "")
        govc_env["GOVC_PASSWORD"] = os.getenv("VCENTER_PASSWORD", "")
        govc_env["GOVC_INSECURE"] = "1"

        console.print(f"[dim]Querying vCenter for {len(workspaces)} VMs...[/dim]")
        rows = []
        for ws in workspaces:
            # Workspace name is the VM name
            vm_name = ws
            
            # Use govc to get power state and IP
            # We use 'find' first to ensure it exists
            rc, out, err = run_cmd(
                [self.govc_path, "find", "/", "-type", "m", "-name", vm_name],
                capture=True,
                env=govc_env
            )
            
            if rc != 0 or not out.strip():
                rows.append({
                    "name": vm_name,
                    "power": "[red]Missing[/red]",
                    "ip": "N/A",
                    "tags": ["[dim]no-vcenter-obj[/dim]"]
                })
                continue

            vm_path = out.strip()
            
            # Get detailed info
            rc, out, err = run_cmd(
                [self.govc_path, "vm.info", "-json", vm_path],
                capture=True,
                env=govc_env
            )
            
            import json
            try:
                info = json.loads(out)
                vm_data = info.get("VirtualMachines", [{}])[0]
                runtime = vm_data.get("Runtime", {})
                guest = vm_data.get("Guest", {})
                
                # Get tags
                rc, out, err = run_cmd(
                    [self.govc_path, "tags.attached.ls", vm_path],
                    capture=True,
                    env=govc_env
                )
                tags = out.splitlines() if rc == 0 else []

                rows.append({
                    "name": vm_name,
                    "power": runtime.get("PowerState", "Unknown"),
                    "ip": guest.get("IpAddress", "Unknown"),
                    "tags": tags
                })
            except (json.JSONDecodeError, IndexError):
                rows.append({
                    "name": vm_name,
                    "power": "Unknown",
                    "ip": "Unknown",
                    "tags": []
                })

        return rows

    def run_ansible_playbook(
        self,
        playbook: str,
        inventory: str,
        extra_vars: Optional[Dict] = None,
        check_mode: bool = False
    ) -> bool:
        """
        Execute an Ansible playbook.

        Args:
            playbook: Path to playbook file
            inventory: Inventory (hosts file or comma-separated IPs)
            extra_vars: Optional dictionary of extra variables
            check_mode: If True, run in --check (dry-run) mode

        Returns:
            True if playbook succeeded, False otherwise
        """
        cmd = ["ansible-playbook"]

        # Add inventory
        cmd.extend(["-i", inventory])

        # Add extra vars if provided
        if extra_vars:
            for key, value in extra_vars.items():
                cmd.extend(["-e", f"{key}={value}"])

        # Add check mode if requested
        if check_mode:
            cmd.append("--check")

        # Add playbook
        cmd.append(playbook)

        rc, out, err = run_cmd(cmd, capture=True)
        return rc == 0

    def validate_ansible_syntax(self, playbook: str) -> bool:
        """
        Validate Ansible playbook syntax.

        Args:
            playbook: Path to playbook file

        Returns:
            True if syntax is valid
        """
        rc, out, err = run_cmd(
            ["ansible-playbook", "--syntax-check", playbook],
            capture=True
        )
        return rc == 0
