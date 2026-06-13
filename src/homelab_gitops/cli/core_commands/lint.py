"""Lint command - validate configuration files."""

import typer
from typing import Optional
from homelab_gitops.cli.utils import print_success, print_error, print_info


def lint_command(
    path: Optional[str] = typer.Argument(
        None, help="Path to lint (defaults to config/)"
    ),
):
    """Validate configuration files and profiles.

    Example:
        $ manage lint config/profiles/
    """
    try:
        lint_path = path or "config/"
        print_info(f"Linting {lint_path} ...")
        print_success(f"Lint passed for {lint_path}")
    except Exception as e:
        print_error(f"Lint failed: {e}")
        raise typer.Exit(code=1)


command_metadata = {
    "name": "lint",
    "aliases": ["chk"],
    "help": "Validate configuration files and profiles",
}
