#!/usr/bin/env python3
"""HomeLab GitOps Orchestrator - modular entry point.

This is the new entrypoint for the unified GitOps pipeline.
It replaces the monolithic manage.py with a plugin-based CLI system.

Usage:
    python3 manage.py deploy ubuntu-base 01
    python3 manage.py config ubuntu-base
    python3 manage.py status

All commands are auto-discovered via the plugin system.
See src/homelab_gitops/cli/core_commands/ for available commands.
"""

import sys


def main():
    """Main entry point for the CLI application."""
    # Import the CLI app factory
    from src.homelab_gitops.cli import main as cli_main

    # Run the CLI
    cli_main()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nCancelled by user", file=sys.stderr)
        sys.exit(0)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
