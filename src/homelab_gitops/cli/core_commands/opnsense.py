"""OPNsense command - networking orchestration."""

import typer
from rich.table import Table
from homelab_gitops.domain.networking import NetworkingService
from homelab_gitops.domain.models import NodeProfile, Task
from homelab_gitops.cli.utils import print_error, print_info, console

# Define the sub-app
# Using a Typer object directly as the plugin callable
opnsense_command = typer.Typer(help="OPNsense networking management")


@opnsense_command.command("list-rules")
def list_rules():
    """List firewall rules on OPNsense."""
    try:
        service = NetworkingService()
        # Use a generic task to list rules
        task = Task(
            type="firewall",
            profile=NodeProfile(name="cli"),
            overrides={"resource": "firewall", "action": "list"}
        )
        result = service.driver.execute(task)
        rules = result.output.get("rules", [])

        if not rules:
            print_info("No firewall rules found.")
            return

        table = Table(title="OPNsense Firewall Rules")
        table.add_column("Description", style="cyan")
        table.add_column("Action", style="green")
        table.add_column("Protocol", style="magenta")
        table.add_column("Source")
        table.add_column("Destination")

        for rule in rules:
            table.add_row(
                rule.get("description", "N/A"),
                rule.get("action", "N/A"),
                rule.get("protocol", "N/A"),
                rule.get("src_net", "N/A"),
                rule.get("dst_net", "N/A")
            )
        console.print(table)
    except Exception as e:
        print_error(f"Failed to list rules: {e}")
        raise typer.Exit(1)


@opnsense_command.command("list-vlans")
def list_vlans():
    """List VLANs on OPNsense."""
    try:
        service = NetworkingService()
        task = Task(
            type="vlan",
            profile=NodeProfile(name="cli"),
            overrides={"resource": "vlan", "action": "list"}
        )
        result = service.driver.execute(task)
        vlans = result.output.get("vlans", [])

        if not vlans:
            print_info("No VLANs found.")
            return

        table = Table(title="OPNsense VLANs")
        table.add_column("Tag", style="cyan")
        table.add_column("Interface", style="green")
        table.add_column("Description", style="magenta")

        for vlan in vlans:
            table.add_row(
                str(vlan.get("tag", "N/A")),
                vlan.get("if", "N/A"),
                vlan.get("descr", "N/A")
            )
        console.print(table)
    except Exception as e:
        print_error(f"Failed to list VLANs: {e}")
        raise typer.Exit(1)


# Plugin metadata
command_metadata = {
    "name": "opnsense",
    "help": "OPNsense networking management",
}
