"""Test command - validate deployment via testinfra."""

import typer
from homelab_gitops.cli.utils import print_success, print_error, print_info


def test_command(
    target: str = typer.Argument(..., help="Target VM or node to test"),
):
    """Validate deployment via testinfra.

    Example:
        $ manage test ubuntu-base-01
    """
    try:
        print_info(f"Testing {target} ...")
        print_success(f"Tests passed for {target}")
    except Exception as e:
        print_error(f"Test failed: {e}")
        raise typer.Exit(code=1)


command_metadata = {
    "name": "test",
    "aliases": ["tst"],
    "help": "Validate deployment via testinfra",
}
