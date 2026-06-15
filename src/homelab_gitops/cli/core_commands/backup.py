"""Backup management CLI plugin."""

import typer
from rich.console import Console
from rich.table import Table
from homelab_gitops.domain.backup import BackupService

console = Console()
app = typer.Typer(help="Manage infrastructure backups")


def backup_command():
    """Entry point for the backup command group."""
    return app


@app.command(name="run")
def run_backup():
    """Run backup for all supported services and store in 1Password."""
    service = BackupService()
    console.print("[bold blue]Starting infrastructure backup...[/bold blue]")

    with console.status("[bold green]Backing up services...[/bold green]"):
        results = service.run_backup()

    table = Table(title="Backup Results")
    table.add_column("Service", style="cyan")
    table.add_column("Status", style="bold")
    table.add_column("File / Error", style="magenta")

    for res in results:
        status = "[green]SUCCESS[/green]" if res["status"] == "success" else "[red]FAILED[/red]"
        detail = res.get("file") or res.get("error", "Unknown error")
        table.add_row(
            res["service"],
            status,
            detail
        )
    
    console.print(table)
    
    success_count = sum(1 for r in results if r["status"] == "success")
    if success_count == len(results):
        console.print("\n[bold green]All backups completed successfully and stored in 1Password![/bold green]")
    else:
        console.print(f"\n[bold yellow]Backup completed with {len(results) - success_count} failures.[/bold yellow]")


command_metadata = {
    "name": "backup",
    "help": "Manage infrastructure backups",
    "is_app": True
}
