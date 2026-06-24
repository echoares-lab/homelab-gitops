"""Doctor command - run system diagnostics."""

import typer
from rich.console import Console
from rich.table import Table
from homelab_gitops.providers.read_only import ReadOnlyProviderFactory
from homelab_gitops.cli.utils import print_success, print_error, print_info

def doctor_command():
    """Run system diagnostics."""
    console = Console()
    print_info("Running system diagnostics...")
    
    try:
        service = ReadOnlyProviderFactory().doctor_service()
        results = service.run_diagnostics()
        
        table = Table(title="System Diagnostics")
        table.add_column("Component", style="cyan")
        table.add_column("Status", style="bold")
        table.add_column("Details", style="magenta")
        
        for component, data in results.items():
            status_val = data.get("status", "unknown")
            if status_val == "pass":
                status_str = "[green]PASS[/green]"
                latency = data.get("latency", 0)
                details = f"Latency: {latency:.3f}s"
            else:
                status_str = "[red]FAIL[/red]"
                details = data.get("error", "Unknown error")
                
            table.add_row(component.capitalize(), status_str, details)
            
        console.print(table)
        
    except Exception as e:
        print_error(f"Diagnostics failed: {e}")
        raise typer.Exit(code=1)

command_metadata = {
    "name": "doctor",
    "aliases": ["doc"],
    "help": "Run system diagnostics"
}
