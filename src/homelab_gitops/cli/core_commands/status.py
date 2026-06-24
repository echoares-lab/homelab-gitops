"""Status command - check deployment status."""

import os
import typer
import yaml
from typing import Optional, List
from rich.console import Console
from rich.table import Table
from homelab_gitops.domain.models import NodeProfile
from homelab_gitops.providers.read_only import ReadOnlyProviderFactory
from homelab_gitops.cli.utils import print_success, print_error, print_info


def status_command(
    profile_name: Optional[str] = typer.Argument(None, help="Profile name to check (optional)"),
):
    """Check deployment status and resource utilization.

    Example:
        $ manage status ubuntu-base
    """
    try:
        profiles: List[NodeProfile] = []
        profile_dir = "config/profiles"
        
        if profile_name:
            paths = [os.path.join(profile_dir, f"{profile_name}.yml")]
        else:
            paths = [os.path.join(profile_dir, f) for f in os.listdir(profile_dir) if f.endswith(".yml")]

        for path in paths:
            if not os.path.exists(path):
                if profile_name:
                     raise FileNotFoundError(f"Profile not found: {path}")
                continue
                
            with open(path) as f:
                p_dict = yaml.safe_load(f)
            
            p_dict["name"] = os.path.basename(path).replace(".yml", "")
            profiles.append(NodeProfile(**p_dict))

        if not profiles:
            print_info("No profiles found.")
            return

        # Setup service
        service = ReadOnlyProviderFactory().status_service()

        print_info("Fetching fleet status ...")
        fleet_status = service.get_fleet_status(profiles)

        # Render table
        console = Console()
        table = Table(title="Homelab Fleet Status")
        
        table.add_column("Profile", style="cyan")
        table.add_column("Provisioned", style="green")
        table.add_column("Power", style="yellow")
        table.add_column("IP Address", style="magenta")
        table.add_column("Drift", style="red")

        for s in fleet_status:
            table.add_row(
                s["name"],
                s["provisioned"],
                s["power"],
                s["ip"],
                s["drift"]
            )

        console.print(table)

    except Exception as e:
        print_error(f"Status check failed: {e}")
        raise typer.Exit(code=1)


command_metadata = {
    "name": "status",
    "aliases": ["st"],
    "help": "Check deployment status and resource utilization",
}
