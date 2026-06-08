"""SecretsService: Manages 1Password secret bootstrapping."""

import os
import sys
from typing import List
from rich.console import Console

console = Console()

class SecretsService:
    """Manages 1Password secret bootstrapping and environment injection."""

    def bootstrap_secrets(self) -> bool:
        """
        Ensure secrets are in the environment.

        Returns True if secrets were loaded, False if already present or unavailable.
        """
        # Case 1: Secrets already present (called via `op run` or pre-set)
        if os.environ.get("VCENTER_SERVER"):
            return True

        token = os.environ.get("OP_SERVICE_ACCOUNT_TOKEN")
        secrets_env = "config/secrets.env"

        # Case 2: Token is set, re-exec with `op run`
        if token and os.path.exists(secrets_env):
            os.execvp("op", ["op", "run", f"--env-file={secrets_env}", "--", sys.executable] + sys.argv)
            # os.execvp replaces the process; nothing below runs

        # Case 3: Neither token nor secrets available
        console.print("[bold red]Error:[/bold red] Secrets not loaded.")
        if not token:
            console.print("  Set [cyan]OP_SERVICE_ACCOUNT_TOKEN[/cyan] to your service account token and re-run.")
            console.print("  [dim]Create one: 1Password → Settings → Developer → Service Accounts[/dim]")
        if not os.path.exists(secrets_env):
            console.print(f"  [yellow]Warning:[/yellow] {secrets_env} not found.")
        console.print("")
        console.print("  Or run explicitly:")
        console.print(f"    [dim]op run --env-file={secrets_env} -- python3 manage.py <command>[/dim]")

        return False

    def should_bootstrap(self, argv: List[str]) -> bool:
        """
        Determine if this invocation actually needs injected secrets.

        Help output, interactive mode, local generators, and dry linting should stay
        offline-safe so tests and basic CLI discovery do not require 1Password.

        Args:
            argv: Command-line arguments (sys.argv)

        Returns:
            True if command needs secrets, False otherwise
        """
        if len(argv) <= 1:
            return False

        if any(arg in ("-h", "--help") for arg in argv[1:]):
            return False

        command = argv[1]
        commands_without_secrets = {
            "lint", "li",
            "status", "st",
            "create-profile", "mkprofile",
            "edit-profile", "ep",
            "create-role", "mkrole",
            "create-play", "mkplay",
        }
        return command not in commands_without_secrets
