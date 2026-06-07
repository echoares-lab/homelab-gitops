import pytest
from homelab_gitops.cli.app import create_app
from homelab_gitops.cli.plugin_loader import PluginLoader


def test_app_creation():
    """CLI app is created successfully."""
    app = create_app()
    assert app is not None
    assert hasattr(app, "command")


def test_plugin_loader_discovers_commands():
    """PluginLoader discovers command plugins."""
    loader = PluginLoader("homelab_gitops.cli.core_commands")
    plugins = loader.load_plugins()
    # Should discover at least deploy and config
    assert len(plugins) > 0
    names = [p["name"] for p in plugins]
    assert "deploy" in names
