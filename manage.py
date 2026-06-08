#!/usr/bin/env python3
"""
Unified HomeLab GitOps Orchestrator CLI.

Thin wrapper around services layer using Typer + Rich.
All business logic is in services/; this file is pure CLI presentation.
"""

import sys
import os
import typer
from typing import Optional
from rich.console import Console
from rich.table import Table

from services.secrets import SecretsService
from services.config import ConfigService
from services.infrastructure import InfrastructureService
from services.orchestrate import OrchestrateService
from services.dns import DNSService

try:
    from opnsense.modules.firewall import FirewallClient
    from opnsense.modules.network import NetworkClient
    from opnsense.exceptions import OPNsenseError
except ImportError:
    # OPNsense module not installed; define placeholders
    FirewallClient = None
    NetworkClient = None
    OPNsenseError = None

# Initialize Typer app and Rich console
app = typer.Typer(
    help="Unified HomeLab GitOps Orchestrator",
    add_completion=False,
    rich_markup_mode="rich"
)
console = Console()

# Initialize services
_secrets = SecretsService()
_config = ConfigService()
_infrastructure = InfrastructureService()
_orchestrate = OrchestrateService(_infrastructure, _config)
_dns = DNSService()


def opnsense_prepare(profile_config: dict, console: Console) -> bool:
    """Pre-deploy: Setup OPNsense for new host

    Creates VLANs and firewall rules from profile config.
    Returns True on success, False on error.
    """
    if 'opnsense' not in profile_config:
        # No OPNsense config in profile, skip
        return True

    if OPNsenseError is None:
        console.print("[yellow]⊘ OPNsense module not installed, skipping[/yellow]")
        return True

    opnsense_cfg = profile_config['opnsense']

    try:
        fw = FirewallClient(
            api_key=os.getenv('OPNSENSE_KEY'),
            api_secret=os.getenv('OPNSENSE_SECRET'),
            url=os.getenv('OPNSENSE_URL')
        )

        net = NetworkClient(
            api_key=os.getenv('OPNSENSE_KEY'),
            api_secret=os.getenv('OPNSENSE_SECRET'),
            url=os.getenv('OPNSENSE_URL')
        )

        console.print("[bold cyan]Preparing OPNsense...[/bold cyan]")

        # Create VLAN if configured
        if 'vlan' in opnsense_cfg:
            vlan_cfg = opnsense_cfg['vlan']
            console.print(f"Creating VLAN {vlan_cfg['id']}... ", end="")
            net.create_vlan(
                interface=vlan_cfg['interface'],
                vlan_id=vlan_cfg['id'],
                description=vlan_cfg['name'],
                enabled=vlan_cfg.get('enabled', True)
            )
            console.print("[green]✓[/green]")

        # Create firewall rules if configured
        if 'firewall_rules' in opnsense_cfg:
            for rule in opnsense_cfg['firewall_rules']:
                console.print(f"Creating rule '{rule['name']}'... ", end="")
                fw.create_firewall_rule(**rule)
                console.print("[green]✓[/green]")

        console.print("[bold green]OPNsense preparation complete[/bold green]")
        return True

    except OPNsenseError as e:
        console.print(f"[red]✗ OPNsense error: {e}[/red]")
        return False
    except Exception as e:
        console.print(f"[red]✗ Unexpected error: {e}[/red]")
        return False


# --- ORCHESTRATION COMMANDS ---

@app.command()
def build(target: str = typer.Argument("photon-docker", help="Build target: ubuntu-2404, ubuntu-2604, photon-docker")):
    """Build golden image (ubuntu-2404, ubuntu-2604, photon-docker)."""
    if _orchestrate.build(target):
        console.print("[green]✓ Build completed[/green]")
    else:
        raise typer.Exit(1)

@app.command()
def lint(profile: str = typer.Argument("photon-docker", help="Profile to lint"),
         index: str = typer.Argument("01", help="Instance ID (Optional)")):
    """Validate profile and vCenter infrastructure."""
    if _orchestrate.lint(profile, index):
        console.print("[green]✓ Lint passed[/green]")
    else:
        raise typer.Exit(1)

@app.command()
def deploy(
    profile: str = typer.Argument("photon-docker", help="Profile to deploy"),
    index: str = typer.Argument("01", help="Instance ID"),
    host: str = typer.Option("esxi-01.mgmt.plexplease.com", help="ESXi host FQDN"),
    mac: Optional[str] = typer.Option(None, help="MAC address for DHCP reservation")
):
    """Provision VM via OpenTofu."""
    profile_config = _config.load_profile(profile)
    if not opnsense_prepare(profile_config, console):
        console.print("[red]OPNsense preparation failed, aborting deploy[/red]")
        raise typer.Exit(1)
    if _orchestrate.deploy(profile, index, host=host, mac=mac):
        console.print("[green]✓ Deploy completed[/green]")
    else:
        raise typer.Exit(1)

@app.command()
def config(profile: str = typer.Argument("photon-docker", help="Profile to configure"),
           index: str = typer.Argument("01", help="Instance ID")):
    """Apply Ansible configuration."""
    if _orchestrate.config(profile, index):
        console.print("[green]✓ Config completed[/green]")
    else:
        raise typer.Exit(1)

@app.command()
def test(profile: str = typer.Argument("photon-docker", help="Profile to test"),
         index: str = typer.Argument("01", help="Instance ID")):
    """Run testinfra validation."""
    if _orchestrate.test(profile, index):
        console.print("[green]✓ Tests passed[/green]")
    else:
        raise typer.Exit(1)

@app.command()
def destroy(identifier: str = typer.Argument(help="VM Name, IP, or MAC")):
    """Destroy VM by name, IP, or MAC."""
    confirm = typer.confirm(f"Destroy {identifier}?")
    if not confirm:
        console.print("[yellow]Aborted[/yellow]")
        raise typer.Exit(0)

    if _orchestrate.destroy(identifier):
        console.print("[green]✓ Destroy completed[/green]")
    else:
        raise typer.Exit(1)

@app.command()
def status():
    """Report fleet health and status."""
    rows = _orchestrate.status()

    if not rows:
        console.print("[yellow]No VMs found[/yellow]")
        return

    table = Table(title="Fleet Status")
    table.add_column("Name", style="cyan")
    table.add_column("Power", style="magenta")
    table.add_column("IP", style="green")
    table.add_column("Tags", style="yellow")

    for row in rows:
        table.add_row(
            row.get("name", "Unknown"),
            row.get("power", "Unknown"),
            row.get("ip", "Unknown"),
            ", ".join(row.get("tags", []))
        )

    console.print(table)

@app.command()
def all(
    profile: str = typer.Argument("photon-docker", help="Profile to deploy"),
    index: str = typer.Argument("01", help="Instance ID"),
    host: str = typer.Option("esxi-01.mgmt.plexplease.com", help="ESXi host FQDN")
):
    """Run complete pipeline: lint → deploy → config → test."""
    if _orchestrate.all(profile, index, host):
        console.print("[green]✓ Complete pipeline succeeded[/green]")
    else:
        raise typer.Exit(1)

# --- ALIASES ---
app.command(name="bu", help="Alias for build")(build)
app.command(name="li", help="Alias for lint")(lint)
app.command(name="dep", help="Alias for deploy")(deploy)
app.command(name="cfg", help="Alias for config")(config)
app.command(name="ts", help="Alias for test")(test)
app.command(name="rm", help="Alias for destroy")(destroy)
app.command(name="st", help="Alias for status")(status)
app.command(name="a", help="Alias for all")(all)

# --- CONFIGURATION COMMANDS ---

@app.command(name="create-profile")
def create_profile():
    """Interactive profile creation."""
    name = typer.prompt("Profile name (e.g., ubuntu-2404-base)")
    cpu = typer.prompt("CPU cores", type=int)
    memory = typer.prompt("Memory (GB)", type=int)
    disk = typer.prompt("Disk (GB)", type=int)
    tags_str = typer.prompt("Tags (comma-separated)")
    tags = [t.strip() for t in tags_str.split(",")]

    spec = {"cpu": cpu, "memory": memory, "disk": disk}
    try:
        if _config.create_profile(name, spec, tags):
            console.print(f"[green]✓ Created profile {name}[/green]")
        else:
            raise typer.Exit(1)
    except FileExistsError as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)

@app.command(name="create-role")
def create_role():
    """Interactive Ansible role creation."""
    name = typer.prompt("Role name (e.g., harden_os)")

    try:
        if _config.create_role(name):
            console.print(f"[green]✓ Created role {name}[/green]")
        else:
            raise typer.Exit(1)
    except FileExistsError as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)

# --- DNS COMMANDS ---

@app.command(name="dns-list")
def dns_list():
    """List all DNS records."""
    records = _dns.list_records()

    if not records:
        console.print("[yellow]No DNS records found[/yellow]")
        return

    table = Table(title="DNS Records")
    table.add_column("Name", style="cyan")
    table.add_column("Type", style="magenta")
    table.add_column("Value", style="green")
    table.add_column("TTL", style="yellow")

    for record in records:
        table.add_row(
            record.get("name", ""),
            record.get("type", ""),
            record.get("value", ""),
            str(record.get("ttl", ""))
        )

    console.print(table)

@app.command(name="dns-create")
def dns_create(name: str, ip: str):
    """Create DNS record."""
    if _dns.create_record(name, ip):
        console.print(f"[green]✓ Created DNS record {name}[/green]")
    else:
        raise typer.Exit(1)

# --- OPNSENSE COMMANDS ---

@app.command()
def opnsense(
    action: str = typer.Argument(..., help="Action: list-rules, create-rule, list-vlans, create-vlan"),
):
    """Manage OPNsense firewall rules and VLANs"""

    if OPNsenseError is None:
        console.print("[red]Error: OPNsense module not installed[/red]")
        raise typer.Exit(1)

    try:
        fw = FirewallClient(
            api_key=os.getenv('OPNSENSE_KEY'),
            api_secret=os.getenv('OPNSENSE_SECRET'),
            url=os.getenv('OPNSENSE_URL')
        )

        net = NetworkClient(
            api_key=os.getenv('OPNSENSE_KEY'),
            api_secret=os.getenv('OPNSENSE_SECRET'),
            url=os.getenv('OPNSENSE_URL')
        )

        if action == "list-rules":
            rules = fw.list_firewall_rules()
            table = Table(title="Firewall Rules")
            table.add_column("ID", style="cyan")
            table.add_column("Name", style="green")
            table.add_column("Action", style="yellow")
            for rule in rules:
                table.add_row(rule.get('uuid', ''), rule.get('name', ''), rule.get('action', ''))
            console.print(table)

        elif action == "list-vlans":
            vlans = net.list_vlans()
            table = Table(title="VLANs")
            table.add_column("ID", style="cyan")
            table.add_column("VLAN ID", style="green")
            table.add_column("Description", style="yellow")
            for vlan in vlans:
                table.add_row(vlan.get('uuid', ''), str(vlan.get('vlan_id', '')), vlan.get('description', ''))
            console.print(table)

        else:
            console.print("[red]Invalid action[/red]")
            raise typer.Exit(1)

    except OPNsenseError as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)

# --- MAIN ---

if __name__ == "__main__":
    # Bootstrap secrets if this command needs them
    if _secrets.should_bootstrap(sys.argv):
        _secrets.bootstrap_secrets()

    # Set VMWARE environment vars from vault
    os.environ["VMWARE_HOST"] = os.environ.get("VCENTER_SERVER", "")
    os.environ["VMWARE_USER"] = os.environ.get("VCENTER_USERNAME", "")
    os.environ["VMWARE_PASSWORD"] = os.environ.get("VCENTER_PASSWORD", "")
    os.environ["VMWARE_VALIDATE_CERTS"] = "no"

    app()
