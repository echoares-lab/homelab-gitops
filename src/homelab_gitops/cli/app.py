"""CLI application and entry point."""

import typer
from homelab_gitops.cli.plugin_loader import PluginLoader
from homelab_gitops.cli.utils import print_error
from homelab_gitops.cli.exceptions import CLIError


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
        target = plugin["callable"]
        metadata = plugin.get("metadata", {})
        
        # If it's explicitly marked as an app factory, call it
        if metadata.get("is_app", False):
            try:
                result = target()
                if isinstance(result, typer.Typer):
                    target = result
            except Exception as e:
                print_error(f"Failed to load sub-command {plugin['name']}: {e}")
                continue

        # Support both simple commands and Typer sub-apps
        if isinstance(target, typer.Typer):
            app.add_typer(
                target,
                name=plugin["name"],
                help=plugin["help"],
            )
        else:
            app.command(
                name=plugin["name"],
                help=plugin["help"],
            )(target)

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
