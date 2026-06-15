"""Unit tests for CLI core components."""

import pytest
from unittest.mock import MagicMock, patch, PropertyMock
from pathlib import Path
import typer
from homelab_gitops.cli.utils import print_success, print_error, print_info
from homelab_gitops.cli.plugin_loader import PluginLoader
from homelab_gitops.cli.app import create_app, main
from homelab_gitops.cli.exceptions import CLIError

# --- Utils Tests ---

@patch("homelab_gitops.cli.utils.console")
def test_print_success(mock_console):
    print_success("Success message")
    mock_console.print.assert_called_once_with("[green]✓[/green] Success message")

@patch("homelab_gitops.cli.utils.console")
def test_print_error(mock_console):
    print_error("Error message")
    mock_console.print.assert_called_once_with("[red]✗[/red] Error message")

@patch("homelab_gitops.cli.utils.console")
def test_print_info(mock_console):
    print_info("Info message")
    mock_console.print.assert_called_once_with("[blue]ℹ[/blue] Info message")

# --- PluginLoader Tests ---

def test_plugin_loader_init():
    loader = PluginLoader("test.package")
    assert loader.package_path == "test.package"

@patch("importlib.import_module")
@patch("typer.secho")
def test_plugin_loader_package_not_found(mock_secho, mock_import):
    mock_import.side_effect = ImportError("No module named 'test.package'")
    loader = PluginLoader("test.package")
    plugins = loader.load_plugins()
    assert plugins == []
    mock_secho.assert_called_once()
    assert "Error loading plugin package" in mock_secho.call_args[0][0]

@patch("importlib.import_module")
@patch("homelab_gitops.cli.plugin_loader.Path")
def test_plugin_loader_skips_private_and_non_py(mock_path, mock_import):
    mock_package = MagicMock()
    mock_package.__file__ = "/path/to/package/__init__.py"
    mock_import.return_value = mock_package
    
    mock_dir = MagicMock()
    mock_path.return_value.parent = mock_dir
    
    # Mock glob to return some files
    file1 = MagicMock(spec=Path)
    file1.name = "_private.py"
    file1.stem = "_private"
    
    file2 = MagicMock(spec=Path)
    file2.name = "public.py"
    file2.stem = "public"
    
    mock_dir.glob.return_value = [file1, file2]
    
    # Mock second import_module for the plugin itself
    mock_module = MagicMock()
    mock_module.command_metadata = {"name": "public"}
    mock_module.public_command = lambda: None
    mock_import.side_effect = [mock_package, mock_module]
    
    loader = PluginLoader("test.package")
    plugins = loader.load_plugins()
    
    assert len(plugins) == 1
    assert plugins[0]["name"] == "public"
    # Ensure _private was skipped (only 2 calls to import_module: package and public)
    assert mock_import.call_count == 2

@patch("importlib.import_module")
@patch("homelab_gitops.cli.plugin_loader.Path")
@patch("typer.secho")
def test_plugin_loader_syntax_error(mock_secho, mock_path, mock_import):
    mock_package = MagicMock()
    mock_package.__file__ = "/path/to/package/__init__.py"
    mock_import.side_effect = [mock_package, SyntaxError("Invalid syntax")]
    
    mock_dir = MagicMock()
    mock_path.return_value.parent = mock_dir
    file1 = MagicMock(spec=Path)
    file1.name = "bad.py"
    file1.stem = "bad"
    mock_dir.glob.return_value = [file1]
    
    loader = PluginLoader("test.package")
    with pytest.raises(SyntaxError):
        loader.load_plugins()
    
    mock_secho.assert_called_once()
    assert "Syntax error in plugin bad" in mock_secho.call_args[0][0]

@patch("importlib.import_module")
@patch("homelab_gitops.cli.plugin_loader.Path")
@patch("typer.secho")
def test_plugin_loader_load_exception(mock_secho, mock_path, mock_import):
    mock_package = MagicMock()
    mock_package.__file__ = "/path/to/package/__init__.py"
    mock_import.side_effect = [mock_package, Exception("Generic error")]
    
    mock_dir = MagicMock()
    mock_path.return_value.parent = mock_dir
    file1 = MagicMock(spec=Path)
    file1.name = "fail.py"
    file1.stem = "fail"
    mock_dir.glob.return_value = [file1]
    
    loader = PluginLoader("test.package")
    plugins = loader.load_plugins()
    
    assert plugins == []
    mock_secho.assert_called_once()
    assert "Failed to load plugin fail" in mock_secho.call_args[0][0]

# --- App Tests ---

@patch("homelab_gitops.cli.app.PluginLoader")
def test_create_app_with_sub_app(mock_loader_cls):
    mock_loader = mock_loader_cls.return_value
    sub_app = typer.Typer()
    mock_loader.load_plugins.return_value = [
        {
            "name": "sub",
            "help": "Sub app help",
            "callable": sub_app,
            "metadata": {}
        }
    ]
    
    app = create_app()
    # Typer doesn't expose a clean way to check registered sub-apps easily without internal access
    # but we can check if it's a Typer instance
    assert isinstance(app, typer.Typer)

@patch("homelab_gitops.cli.app.PluginLoader")
def test_create_app_with_simple_command(mock_loader_cls):
    mock_loader = mock_loader_cls.return_value
    def my_cmd(): pass
    mock_loader.load_plugins.return_value = [
        {
            "name": "cmd",
            "help": "Cmd help",
            "callable": my_cmd,
            "metadata": {}
        }
    ]
    
    app = create_app()
    assert isinstance(app, typer.Typer)

@patch("homelab_gitops.cli.app.PluginLoader")
@patch("homelab_gitops.cli.app.print_error")
def test_create_app_factory_success(mock_print, mock_loader_cls):
    mock_loader = mock_loader_cls.return_value
    sub_app = typer.Typer()
    def factory(): return sub_app
    
    mock_loader.load_plugins.return_value = [
        {
            "name": "fact",
            "help": "Factory help",
            "callable": factory,
            "metadata": {"is_app": True}
        }
    ]
    
    app = create_app()
    assert isinstance(app, typer.Typer)
    mock_print.assert_not_called()

@patch("homelab_gitops.cli.app.PluginLoader")
@patch("homelab_gitops.cli.app.print_error")
def test_create_app_factory_failure(mock_print, mock_loader_cls):
    mock_loader = mock_loader_cls.return_value
    def factory(): raise Exception("Factory failed")
    
    mock_loader.load_plugins.return_value = [
        {
            "name": "fact",
            "help": "Factory help",
            "callable": factory,
            "metadata": {"is_app": True}
        }
    ]
    
    app = create_app()
    assert isinstance(app, typer.Typer)
    mock_print.assert_called_once()
    assert "Failed to load sub-command fact" in mock_print.call_args[0][0]

@patch("homelab_gitops.cli.app.PluginLoader")
def test_create_app_factory_returns_non_typer(mock_loader_cls):
    mock_loader = mock_loader_cls.return_value
    def factory(): return "not a typer app"
    
    mock_loader.load_plugins.return_value = [
        {
            "name": "fact",
            "help": "Factory help",
            "callable": factory,
            "metadata": {"is_app": True}
        }
    ]
    
    app = create_app()
    assert isinstance(app, typer.Typer)

@patch("homelab_gitops.cli.app.create_app")
@patch("homelab_gitops.cli.app.print_error")
def test_main_cli_error(mock_print, mock_create_app):
    mock_app = mock_create_app.return_value
    mock_app.side_effect = CLIError("CLI Error")
    
    with pytest.raises(SystemExit) as excinfo:
        main()
    
    assert excinfo.value.code == 1
    mock_print.assert_called_once_with("CLI Error")

@patch("homelab_gitops.cli.app.create_app")
@patch("homelab_gitops.cli.app.print_error")
def test_main_unexpected_error(mock_print, mock_create_app):
    mock_app = mock_create_app.return_value
    mock_app.side_effect = Exception("Unexpected")
    
    with pytest.raises(SystemExit) as excinfo:
        main()
    
    assert excinfo.value.code == 1
    mock_print.assert_called_once_with("Unexpected error: Unexpected")

@patch("homelab_gitops.cli.app.create_app")
def test_main_success(mock_create_app):
    mock_app = mock_create_app.return_value
    main()
    mock_app.assert_called_once()

def test_app_module_main_execution():
    import runpy
    with patch("sys.argv", ["homelab-gitops"]), \
         patch("sys.exit"), \
         patch("homelab_gitops.cli.app.PluginLoader") as mock_loader:
        mock_loader.return_value.load_plugins.return_value = []
        runpy.run_module("homelab_gitops.cli.app", run_name="__main__")
