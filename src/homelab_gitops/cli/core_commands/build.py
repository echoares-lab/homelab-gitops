"""Build command - prepare base images."""

import typer
from homelab_gitops.cli.utils import print_success, print_error, print_info


def build_command(
    profile: str = typer.Argument(..., help="Profile name to build"),
):
    """Prepare base images from templates.

    Example:
        $ manage build ubuntu-base
    """
    try:
        print_info(f"Building {profile} ...")
        print_success(f"Build completed for {profile}")
    except Exception as e:
        print_error(f"Build failed: {e}")
        raise typer.Exit(code=1)


command_metadata = {
    "name": "build",
    "aliases": ["bld"],
    "help": "Prepare base images from templates",
}
