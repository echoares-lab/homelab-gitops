"""Secrets driver for 1Password and environment variables."""

import os
import subprocess
import time
import shutil
import json
from typing import Optional, Dict, Any
from homelab_gitops.drivers.base import Driver
from homelab_gitops.drivers.exceptions import PrerequisiteError, ExecutionError
from homelab_gitops.domain.models import Task, TaskResult


class SecretsDriver(Driver):
    """Driver for resolving secrets from 1Password and Environment."""

    def __init__(self, default_vault: Optional[str] = None):
        """Initialize SecretsDriver.

        Args:
            default_vault: Default 1Password vault to use if not specified in URI.
        """
        self.op_path = shutil.which("op")
        self.default_vault = default_vault or os.getenv("OP_VAULT", "homelab-gitops")

    def validate(self) -> bool:
        """Validate 1Password CLI is available and authenticated if needed."""
        # If op is missing, we can only use environment variables
        if not self.op_path:
            # We don't fail here because some secrets might be in ENV already.
            # But if a task requires op, it will fail during execute.
            return True

        try:
            # Check if authenticated - 'op whoami' is the standard way
            result = subprocess.run(
                [self.op_path, "whoami"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode != 0:
                # If OP_SERVICE_ACCOUNT_TOKEN is set, op whoami should work.
                # If not set, user might need 'op signin'
                raise PrerequisiteError(
                    "1Password CLI not authenticated. Run 'op signin' or set OP_SERVICE_ACCOUNT_TOKEN."
                )
        except subprocess.TimeoutExpired:
            raise PrerequisiteError("1Password CLI 'whoami' timed out")
        except Exception as e:
            if isinstance(e, PrerequisiteError):
                raise
            raise PrerequisiteError(f"Failed to validate 1Password CLI: {str(e)}")

        return True

    def execute(self, task: Task) -> TaskResult:
        """Execute secret resolution task.

        Supported task types:
            get: Fetch a single secret. Target should be env var name or op:// URI.
            resolve_file: Resolve all op:// references in a file. Target is file path.

        Returns:
            TaskResult with secret value (for 'get') or JSON-encoded dict (for 'resolve_file').
        """
        start = time.time()

        try:
            if task.type == "get":
                output = self._get_secret(task.target, task.overrides)
            elif task.type in ("resolve_file", "bootstrap"):
                output = self._resolve_file(task.target)
            else:
                raise ExecutionError(f"Unsupported task type: {task.type}")

            duration = time.time() - start
            return TaskResult(
                success=True,
                task_type=task.type,
                output=output,
                duration=duration
            )
        except Exception as e:
            if isinstance(e, ExecutionError):
                raise
            raise ExecutionError(f"Secrets operation failed: {str(e)}")

    def store_secret(self, item_name: str, value: str, vault: Optional[str] = None) -> None:
        """Store a secret in 1Password.

        Args:
            item_name: Name of the item to create/update.
            value: Secret value (stored in 'password' field by default).
            vault: Vault to store in.
        """
        if not self.op_path:
            raise ExecutionError("'op' CLI required for storing secrets")

        vault = vault or self.default_vault

        try:
            # Check if item exists
            result = subprocess.run(
                [self.op_path, "item", "get", item_name, "--vault", vault, "--format", "json"],
                capture_output=True,
                text=True
            )

            if result.returncode == 0:
                # Update existing item
                subprocess.run(
                    [self.op_path, "item", "edit", item_name, f"password={value}", "--vault", vault],
                    check=True,
                    capture_output=True
                )
            else:
                # Create new item
                subprocess.run(
                    [self.op_path, "item", "create", "--category", "login", "--title", item_name, f"password={value}", "--vault", vault],
                    check=True,
                    capture_output=True
                )
        except subprocess.CalledProcessError as e:
            raise ExecutionError(f"Failed to store secret in 1Password: {e.stderr}")

    def _get_secret(self, secret_ref: Optional[str], overrides: Optional[Dict[str, Any]] = None) -> str:
        """Fetch a single secret."""
        if not secret_ref:
            raise ExecutionError("No secret reference provided")

        overrides = overrides or {}

        # 1. Check environment variables first (only if not a URI)
        if not secret_ref.startswith("op://"):
            val = os.getenv(secret_ref)
            if val:
                return val

        # 2. Try 1Password
        if not self.op_path:
            raise ExecutionError(
                f"Secret '{secret_ref}' not found in environment and 'op' CLI is missing"
            )

        try:
            # If it's not a URI, try to construct one using default vault
            # Use 'op read op://vault/item/field' pattern
            op_uri = secret_ref
            explicit_field = overrides.get("field")

            if not op_uri.startswith("op://"):
                field_name = explicit_field or "password"
                op_uri = f"op://{self.default_vault}/{secret_ref}/{field_name}"

            result = subprocess.run(
                [self.op_path, "read", op_uri, "-n"],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode == 0:
                return result.stdout.strip()

            # If it failed and we constructed the URI without an explicit field, try 'credential' field?
            if not secret_ref.startswith("op://") and not explicit_field and "password" in op_uri:
                op_uri_alt = f"op://{self.default_vault}/{secret_ref}/credential"
                result_alt = subprocess.run(
                    [self.op_path, "read", op_uri_alt, "-n"],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                if result_alt.returncode == 0:
                    return result_alt.stdout.strip()

            # Final failure
            if secret_ref.startswith("op://"):
                raise ExecutionError(f"1Password read failed for {op_uri}: {result.stderr}")
            else:
                msg = f"Secret '{secret_ref}' not found in environment or 1Password (tried {op_uri})"
                if not explicit_field:
                    msg += " and fallback 'credential' field"
                raise ExecutionError(msg)

        except subprocess.TimeoutExpired:
            raise ExecutionError(f"1Password read timed out for {secret_ref}")
        except subprocess.SubprocessError as e:
            raise ExecutionError(f"1Password execution failed: {str(e)}")

    def _resolve_file(self, file_path: Optional[str]) -> str:
        """Resolve all op:// references in a file."""
        # Use default if not provided
        if not file_path:
            file_path = "config/secrets.env"

        if not os.path.exists(file_path):
            raise ExecutionError(f"Env file not found: {file_path}")

        if not self.op_path:
            raise ExecutionError("'op' CLI required for resolving files")

        try:
            # 'op inject' resolves op:// references in the file
            result = subprocess.run(
                [self.op_path, "inject", "-i", file_path],
                capture_output=True,
                text=True,
                timeout=20
            )
            if result.returncode != 0:
                raise ExecutionError(f"1Password inject failed: {result.stderr}")

            # Parse the resolved content into a dict
            resolved_secrets = {}
            for line in result.stdout.splitlines():
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" in line:
                    key, value = line.split("=", 1)
                    # Strip quotes if present
                    value = value.strip().strip('"').strip("'")
                    resolved_secrets[key.strip()] = value

            return json.dumps(resolved_secrets)

        except subprocess.TimeoutExpired:
            raise ExecutionError(f"1Password inject timed out for {file_path}")
        except subprocess.SubprocessError as e:
            raise ExecutionError(f"1Password inject failed: {str(e)}")
