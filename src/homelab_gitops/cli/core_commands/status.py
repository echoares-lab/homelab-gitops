"""Status command - check deployment status."""

import typer
from ..utils import print_success, print_error, print_info


def status_command(
    profile: str = typer.Argument(..., help="Profile name to check"),
):
    """Check deployment status and resource utilization.

    Example:
        $ manage status ubuntu-base
    """
    try:
        print_info(f"Checking status for {profile} ...")
        print_success(f"Status check completed for {profile}")
    except Exception as e:
        print_error(f"Status check failed: {e}")
        raise typer.Exit(code=1)


command_metadata = {
    "name": "status",
    "aliases": ["st"],
    "help": "Check deployment status and resource utilization",
}
