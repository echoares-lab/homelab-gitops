"""DHCP Migration CLI plugin."""

import typer
from rich.console import Console
from rich.table import Table
from homelab_gitops.domain.migration import MigrationService

console = Console()
app = typer.Typer(help="Migrate DHCP from OPNsense to Technitium")


def migrate_command():
    """Entry point for the migrate command group."""
    return app


@app.command(name="dhcp-migrate")
def dhcp_migrate():
    """Interactive DHCP migration wizard."""
    service = MigrationService()

    console.rule("[bold cyan]Step 1 — Discovery[/bold cyan]")
    discovery = service.discover()

    iface_table = Table(title="OPNsense DHCP Interfaces")
    iface_table.add_column("Interface", style="cyan")
    for iface in discovery["opnsense_interfaces"]:
        iface_table.add_row(iface["interface"])
    console.print(iface_table)

    scope_table = Table(title="Technitium DHCP Scopes")
    scope_table.add_column("Name", style="cyan")
    for scope in discovery["technitium_scopes"]:
        scope_table.add_row(scope["name"])
    console.print(scope_table)

    console.rule("[bold cyan]Step 2 — Mapping[/bold cyan]")
    source = typer.prompt("Source interface (OPNsense)")
    target = typer.prompt("Target scope (Technitium)")

    if typer.confirm(f"Proceed with migration: {source} -> {target}?"):
        try:
            res = service.migrate_dhcp(source, target)
            console.print(
                f"[green]✓ Migration successful: {res['status']}[/green]"
            )
        except Exception as e:
            console.print(f"[red]✗ Migration failed: {e}[/red]")


@app.command(name="dhcp-rollback")
def dhcp_rollback():
    """Roll back previous DHCP migrations."""
    service = MigrationService()
    if typer.confirm("Roll back all migrated scopes?"):
        res = service.rollback()
        console.print(
            f"[green]✓ Rollback complete: {res.get('status')}[/green]"
        )


command_metadata = {
    "name": "migrate",
    "help": "Migrate DHCP services",
    "is_app": True
}
