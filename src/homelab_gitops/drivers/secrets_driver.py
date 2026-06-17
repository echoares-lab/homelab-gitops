"""Secrets driver for 1Password and environment variables."""

import os
import subprocess
import time
import shutil
import json
import re
import urllib.request
import urllib.error
from typing import Optional, Dict, Any
from homelab_gitops.drivers.base import Driver
from homelab_gitops.drivers.exceptions import PrerequisiteError, ExecutionError
from homelab_gitops.domain.models import Task, TaskResult


class ConnectClient:
    """A minimal 1Password Connect API client."""
    def __init__(self, host: str, token: str):
        self.host = host.rstrip('/')
        self.token = token
        self._vaults_cache = {}
        self._items_cache = {}
        self._item_details_cache = {}

    def _request(self, path: str, method="GET", data=None):
        url = f"{self.host}{path}"
        req = urllib.request.Request(url, method=method)
        req.add_header("Authorization", f"Bearer {self.token}")
        if data:
            req.add_header("Content-Type", "application/json")
            req.data = json.dumps(data).encode("utf-8")
        try:
            with urllib.request.urlopen(req, timeout=10) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.URLError as e:
            raise ExecutionError(f"Connect Server API error: {e}")

    def get_vault_id(self, vault_name: str) -> str:
        if vault_name in self._vaults_cache:
            return self._vaults_cache[vault_name]
        
        vaults = self._request("/v1/vaults")
        for v in vaults:
            self._vaults_cache[v["name"]] = v["id"]
            
        if vault_name not in self._vaults_cache:
            raise ExecutionError(f"Vault '{vault_name}' not found")
        return self._vaults_cache[vault_name]

    def get_item_id(self, vault_id: str, item_name: str) -> str:
        cache_key = f"{vault_id}:{item_name}"
        if cache_key in self._items_cache:
            return self._items_cache[cache_key]

        # Fetch all items in vault and cache them to avoid multiple calls per vault
        items = self._request(f"/v1/vaults/{vault_id}/items")
        for item in items:
            key = f"{vault_id}:{item['title']}"
            self._items_cache[key] = item["id"]
                
        if cache_key not in self._items_cache:
            raise ExecutionError(f"Item '{item_name}' not found in vault")
            
        return self._items_cache[cache_key]

    def get_item_field(self, vault_name: str, item_name: str, field_name: str) -> str:
        vault_id = self.get_vault_id(vault_name)
        item_id = self.get_item_id(vault_id, item_name)
        
        if item_id not in self._item_details_cache:
            self._item_details_cache[item_id] = self._request(f"/v1/vaults/{vault_id}/items/{item_id}")
            
        item = self._item_details_cache[item_id]
        
        # Look for field by label or id
        for field in item.get("fields", []):
            if field.get("label") == field_name or field.get("id") == field_name:
                return field.get("value", "")
                
        # Fallback to credential
        for field in item.get("fields", []):
            if field.get("label") == "credential":
                return field.get("value", "")
                
        raise ExecutionError(f"Field '{field_name}' not found on item '{item_name}'")


class SecretsDriver(Driver):
    """Driver for resolving secrets from 1Password and Environment."""

    def __init__(self, default_vault: Optional[str] = None):
        """Initialize SecretsDriver."""
        self.op_path = shutil.which("op")
        self.default_vault = default_vault or os.getenv("OP_VAULT", "homelab-gitops")
        
        self.connect_host = os.getenv("OP_CONNECT_HOST")
        self.connect_token = os.getenv("OP_CONNECT_TOKEN")
        self.connect_client = None
        
        if self.connect_host and self.connect_token:
            self.connect_client = ConnectClient(self.connect_host, self.connect_token)

    def validate(self) -> bool:
        """Validate 1Password CLI or Connect is available."""
        if self.connect_client:
            return True
            
        if not self.op_path:
            return True

        try:
            result = subprocess.run(
                [self.op_path, "whoami"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode != 0:
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
        """Execute secret resolution task."""
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
        """Store a secret in 1Password."""
        if not self.op_path:
            raise ExecutionError("'op' CLI required for storing secrets")

        vault = vault or self.default_vault

        try:
            result = subprocess.run(
                [self.op_path, "item", "get", item_name, "--vault", vault, "--format", "json"],
                capture_output=True,
                text=True
            )

            if result.returncode == 0:
                subprocess.run(
                    [self.op_path, "item", "edit", item_name, f"password={value}", "--vault", vault],
                    check=True,
                    capture_output=True
                )
            else:
                subprocess.run(
                    [self.op_path, "item", "create", "--category", "login", "--title", item_name, f"password={value}", "--vault", vault],
                    check=True,
                    capture_output=True
                )
        except subprocess.CalledProcessError as e:
            raise ExecutionError(f"Failed to store secret in 1Password: {e.stderr}")

    def store_document(self, title: str, file_path: str, vault: Optional[str] = None) -> None:
        """Store a document in 1Password."""
        if not self.op_path:
            raise ExecutionError("'op' CLI required for storing documents")

        vault = vault or self.default_vault

        try:
            result = subprocess.run(
                [self.op_path, "item", "get", title, "--vault", vault, "--format", "json"],
                capture_output=True,
                text=True
            )

            if result.returncode == 0:
                subprocess.run(
                    [self.op_path, "item", "delete", title, "--vault", vault],
                    check=True,
                    capture_output=True
                )

            subprocess.run(
                [self.op_path, "document", "create", file_path, "--title", title, "--vault", vault],
                check=True,
                capture_output=True
            )
        except subprocess.CalledProcessError as e:
            raise ExecutionError(f"Failed to store document in 1Password: {e.stderr}")

    def _get_secret(self, secret_ref: Optional[str], overrides: Optional[Dict[str, Any]] = None) -> str:
        """Fetch a single secret."""
        if not secret_ref:
            raise ExecutionError("No secret reference provided")

        overrides = overrides or {}

        if not secret_ref.startswith("op://"):
            val = os.getenv(secret_ref)
            if val:
                return val

        explicit_field = overrides.get("field")
        op_uri = secret_ref

        if not op_uri.startswith("op://"):
            field_name = explicit_field or "password"
            op_uri = f"op://{self.default_vault}/{secret_ref}/{field_name}"

        # Try Connect Server if configured
        if self.connect_client:
            m = re.match(r"op://([^/]+)/([^/]+)/([^/]+)", op_uri)
            if not m:
                raise ExecutionError(f"Invalid op:// URI format: {op_uri}")
            vault_name, item_name, field_name = m.groups()
            return self.connect_client.get_item_field(vault_name, item_name, field_name)

        if not self.op_path:
            raise ExecutionError(
                f"Secret '{secret_ref}' not found in environment and Connect Server/op CLI missing"
            )

        try:
            result = subprocess.run(
                [self.op_path, "read", op_uri, "-n"],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode == 0:
                return result.stdout.strip()

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
        if not file_path:
            file_path = "config/secrets.env"

        if not os.path.exists(file_path):
            raise ExecutionError(f"Env file not found: {file_path}")
            
        # Try Connect Server if configured
        if self.connect_client:
            resolved_secrets = {}
            with open(file_path, "r") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue
                    if "=" in line:
                        key, value = line.split("=", 1)
                        value = value.strip().strip('"').strip("'")
                        
                        if value.startswith("op://"):
                            m = re.match(r"op://([^/]+)/([^/]+)/([^/]+)", value)
                            if m:
                                vault_name, item_name, field_name = m.groups()
                                try:
                                    value = self.connect_client.get_item_field(vault_name, item_name, field_name)
                                except Exception as e:
                                    raise ExecutionError(f"Failed resolving {value} via Connect: {e}")
                            else:
                                raise ExecutionError(f"Invalid op:// URI format: {value}")
                        
                        resolved_secrets[key.strip()] = value
            return json.dumps(resolved_secrets)

        if not self.op_path:
            raise ExecutionError("'op' CLI required for resolving files when Connect Server is not used")

        try:
            result = subprocess.run(
                [self.op_path, "inject", "-i", file_path],
                capture_output=True,
                text=True,
                timeout=20
            )
            if result.returncode != 0:
                raise ExecutionError(f"1Password inject failed: {result.stderr}")

            resolved_secrets = {}
            for line in result.stdout.splitlines():
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" in line:
                    key, value = line.split("=", 1)
                    value = value.strip().strip('"').strip("'")
                    resolved_secrets[key.strip()] = value

            return json.dumps(resolved_secrets)

        except subprocess.TimeoutExpired:
            raise ExecutionError(f"1Password inject timed out for {file_path}")
        except subprocess.SubprocessError as e:
            raise ExecutionError(f"1Password inject failed: {str(e)}")
