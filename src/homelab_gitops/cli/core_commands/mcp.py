"""MCP command - run the Model Context Protocol server."""

import typer

from homelab_gitops.cli.utils import print_error
from homelab_gitops.mcp_server import mcp


def mcp_command():
    """Run the Model Context Protocol (MCP) Server.

    Example:
        $ manage mcp
    """
    try:
        mcp.run()
    except Exception as e:
        print_error(f"MCP server failed: {e}")
        raise typer.Exit(code=1)


command_metadata = {
    "name": "mcp",
    "aliases": [],
    "help": "Run the Model Context Protocol (MCP) Server.",
}
