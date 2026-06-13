"""Unit tests for CLI command discovery and imports."""

import pytest
import importlib
import pkgutil
from pathlib import Path
import homelab_gitops.cli.core_commands as core_commands
from homelab_gitops.cli.plugin_loader import PluginLoader

def test_import_all_core_commands():
    """Verify all core commands can be imported without error."""
    package = core_commands
    prefix = package.__name__ + "."
    for _, name, _ in pkgutil.iter_modules(package.__path__, prefix):
        # Skip __init__ or other non-command files if any
        module = importlib.import_module(name)
        assert module is not None
        # Check for standard command attributes
        assert hasattr(module, "command_metadata") or hasattr(module, "app")

def test_plugin_loader_discovery():
    """Test PluginLoader discovery logic."""
    # Find the absolute path to core_commands
    package_path = "homelab_gitops.cli.core_commands"
    loader = PluginLoader(package_path=package_path)
    plugins = loader.load_plugins()
    # Should find at least one plugin
    assert len(plugins) > 0
    # verify 'dns' or 'cert' exists
    names = [p["name"] for p in plugins]
    assert "dns" in names or "cert" in names
