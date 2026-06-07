"""CLI output utilities."""

from rich.console import Console

console = Console()


def print_success(message: str):
    """Print success message."""
    console.print(f"[green]✓[/green] {message}")


def print_error(message: str):
    """Print error message."""
    console.print(f"[red]✗[/red] {message}")


def print_info(message: str):
    """Print info message."""
    console.print(f"[blue]ℹ[/blue] {message}")
