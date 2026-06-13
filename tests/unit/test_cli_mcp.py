import pytest
from unittest.mock import patch
import typer
from typer.testing import CliRunner

from homelab_gitops.cli.core_commands.mcp import mcp_command
from homelab_gitops.cli.app import create_app

runner = CliRunner()

def test_mcp_command_success():
    with patch("homelab_gitops.cli.core_commands.mcp.mcp.run") as mock_run:
        mcp_command()
        mock_run.assert_called_once()

def test_mcp_command_exception():
    with patch("homelab_gitops.cli.core_commands.mcp.mcp.run") as mock_run:
        mock_run.side_effect = Exception("MCP error")
        with pytest.raises(typer.Exit) as exc_info:
            mcp_command()
        assert exc_info.value.exit_code == 1

def test_mcp_cli_integration():
    app = create_app()
    with patch("homelab_gitops.cli.core_commands.mcp.mcp.run") as mock_run:
        result = runner.invoke(app, ["mcp"])
        assert result.exit_code == 0
        mock_run.assert_called_once()
