"""Destroy command - tear down infrastructure."""

import typer
from homelab_gitops.cli.utils import print_success, print_error, print_info


def destroy_command(
    profile: str = typer.Argument(..., help="Profile name to destroy"),
):
    """Tear down virtual infrastructure via OpenTofu.

    Example:
        $ manage destroy ubuntu-base
    """
    try:
        print_info(f"Destroying {profile} ...")
        print_success(f"Destroyed {profile}")
    except Exception as e:
        print_error(f"Destroy failed: {e}")
        raise typer.Exit(code=1)


command_metadata = {
    "name": "destroy",
    "aliases": ["des"],
    "help": "Tear down virtual infrastructure via OpenTofu",
}
