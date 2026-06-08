"""CLI application and entry point."""

import typer
from .plugin_loader import PluginLoader
from .utils import print_error
from .exceptions import CLIError


def create_app() -> typer.Typer:
    """Create and configure the Typer CLI app.

    Returns:
        Typer app with all command plugins registered
    """
    app = typer.Typer(
        help="HomeLab GitOps Orchestrator",
        add_completion=False,
        rich_markup_mode="rich",
    )

    # Load core commands
    loader = PluginLoader("homelab_gitops.cli.core_commands")
    plugins = loader.load_plugins()

    for plugin in plugins:
        app.command(
            name=plugin["name"],
            help=plugin["help"],
        )(plugin["callable"])

    return app


def main():
    """Entry point."""
    app = create_app()
    try:
        app()
    except CLIError as e:
        print_error(str(e))
        exit(1)
    except Exception as e:
        print_error(f"Unexpected error: {e}")
        exit(1)


if __name__ == "__main__":
    main()
