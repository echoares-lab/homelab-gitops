"""DNS management CLI plugin."""

import typer
from typing import Optional, List
from rich.console import Console
from rich.table import Table
from homelab_gitops.domain.dns import DNSService
from homelab_gitops.domain.models import TaskResult

console = Console()
app = typer.Typer(help="Manage Technitium DNS records")


def dns_command():
    """Entry point for the dns command group."""
    return app


@app.command(name="list")
def list_records(
    zone: str = typer.Argument(
        ..., help="DNS Zone to list (e.g. mgmt.plexplease.com)"
    )
):
    """List all records in a zone."""
    service = DNSService()
    records = service.list_records(zone)

    if not records:
        console.print(f"[yellow]No records found in zone {zone}[/yellow]")
        return

    table = Table(title=f"DNS Records: {zone}")
    table.add_column("Name", style="cyan")
    table.add_column("Type", style="magenta")
    table.add_column("Value", style="green")
    table.add_column("TTL", style="yellow")

    for r in records:
        table.add_row(
            r.get("name", ""),
            r.get("type", ""),
            r.get("value", ""),
            str(r.get("ttl", ""))
        )
    console.print(table)


@app.command(name="create")
def create_record(
    name: str = typer.Argument(..., help="Record name (hostname portion)"),
    ip: str = typer.Argument(..., help="IP Address (for A record)"),
    zone: Optional[str] = typer.Option(None, help="DNS Zone")
):
    """Create A and PTR records for a host."""
    if not zone:
        zone = typer.prompt("DNS Zone", default="mgmt.plexplease.com")

    service = DNSService()
    console.print(
        f"[bold blue]Creating DNS records for {name}.{zone} -> {ip}..."
        "[/bold blue]"
    )

    try:
        results = service.provision_manual(name, ip, zone)
        _display_results(results, f"DNS Creation: {name}.{zone}")
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {str(e)}")


@app.command(name="delete")
def delete_record(
    name: str = typer.Argument(..., help="Record name (hostname portion)"),
    ip: Optional[str] = typer.Option(
        None, help="IP Address (for PTR record cleanup)"
    ),
    zone: Optional[str] = typer.Option(None, help="DNS Zone")
):
    """Delete A and PTR records for a host."""
    if not zone:
        zone = typer.prompt("DNS Zone", default="mgmt.plexplease.com")

    service = DNSService()
    console.print(
        f"[bold blue]Deleting DNS records for {name}.{zone}...[/bold blue]"
    )

    try:
        results = service.deprovision_manual(name, ip, zone)
        _display_results(results, f"DNS Deletion: {name}.{zone}")
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {str(e)}")


def _display_results(results: List[TaskResult], title: str):
    """Display task results in a Rich table."""
    table = Table(title=title)
    table.add_column("Task Type", style="cyan")
    table.add_column("Status", style="bold")
    table.add_column("Duration", style="yellow")
    table.add_column("Details", style="magenta")

    for res in results:
        status = (
            "[green]SUCCESS[/green]" if res.success else "[red]FAILED[/red]"
        )
        details = (
            res.error if not res.success else "Operation completed successfully"
        )
        table.add_row(
            res.task_type,
            status,
            f"{res.duration:.2f}s",
            details
        )
    console.print(table)


command_metadata = {
    "name": "dns",
    "help": "Manage Technitium DNS records",
    "is_app": True
}
