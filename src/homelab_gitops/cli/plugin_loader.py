"""Dynamic plugin loader for CLI commands."""

import importlib
from pathlib import Path
from typing import List, Dict


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
        except Exception:
            return plugins

        # Discover .py files in package
        for py_file in package_dir.glob("*.py"):
            if py_file.name.startswith("_"):
                continue

            module_name = py_file.stem
            try:
                module = importlib.import_module(f"{self.package_path}.{module_name}")
            except Exception:
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
