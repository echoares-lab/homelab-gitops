"""Dynamic plugin loader for CLI commands."""

import importlib
import sys
from pathlib import Path
from typing import List, Dict
import typer


class PluginLoader:
    """Dynamically load command plugins from a package."""

    def __init__(self, package_path: str):
        """Initialize loader for a package.

        Args:
            package_path: e.g., "homelab_gitops.cli.core_commands"
        """
        self.package_path = package_path

    def load_plugins(self) -> List[Dict]:
        """Load all command plugins from the package.

        Returns:
            List of plugin dicts with keys: name, aliases, help, callable
        """
        plugins = []

        try:
            package = importlib.import_module(self.package_path)
            package_dir = Path(package.__file__).parent
        except Exception as e:
            typer.secho(f"Error loading plugin package {self.package_path}: {e}", fg=typer.colors.RED, err=True)
            return plugins

        # Discover .py files in package
        for py_file in package_dir.glob("*.py"):
            if py_file.name.startswith("_"):
                continue

            module_name = py_file.stem
            try:
                module = importlib.import_module(f"{self.package_path}.{module_name}")
            except SyntaxError:
                typer.secho(f"Syntax error in plugin {module_name}:", fg=typer.colors.RED, err=True)
                raise
            except Exception as e:
                typer.secho(f"Failed to load plugin {module_name}: {e}", fg=typer.colors.YELLOW, err=True)
                continue

            # Extract metadata
            if hasattr(module, "command_metadata") and hasattr(
                module, f"{module_name}_command"
            ):
                metadata = module.command_metadata
                command_func = getattr(module, f"{module_name}_command")

                plugins.append(
                    {
                        "name": metadata.get("name", module_name),
                        "aliases": metadata.get("aliases", []),
                        "help": metadata.get("help", ""),
                        "callable": command_func,
                        "metadata": metadata,
                    }
                )

        return plugins
