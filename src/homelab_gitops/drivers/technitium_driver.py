"""Technitium DNS Server driver."""

import os
import time
import requests
from typing import Dict, Any, Optional
from homelab_gitops.drivers.base import Driver
from homelab_gitops.drivers.exceptions import PrerequisiteError, ExecutionError
from homelab_gitops.domain.models import Task, TaskResult


class TechnitiumDriver(Driver):
    """Driver for Technitium DNS and DHCP operations."""

    def __init__(self, host: Optional[str] = None, token: Optional[str] = None):
        """Initialize TechnitiumDriver with host and token."""
        self.host = (host or os.getenv("TECHNITIUM_HOST", "")).rstrip("/")
        self.token = token or os.getenv("TECHNITIUM_TOKEN")
        self.timeout = 10

    def validate(self) -> bool:
        """Validate Technitium credentials and connectivity."""
        if not self.host or not self.token:
            raise PrerequisiteError(
                "TECHNITIUM_HOST and TECHNITIUM_TOKEN must be set"
            )

        try:
            # Check connectivity by listing zones
            response = requests.get(
                f"{self.host}/api/zones/list",
                params={"token": self.token},
                timeout=self.timeout
            )
            if response.status_code == 401:
                raise PrerequisiteError("Invalid Technitium API token")
            
            data = response.json()
            if data.get("status") == "error":
                raise PrerequisiteError(
                    f"Technitium API error: {data.get('errorMessage')}"
                )
            return True
        except requests.exceptions.RequestException as e:
            raise PrerequisiteError(f"Technitium unreachable: {str(e)}")

    def execute(self, task: Task) -> TaskResult:
        """Execute Technitium DNS operations."""
        start = time.time()
        
        # Determine resource and action from task
        resource = task.overrides.get("resource", "record")
        # Map task type to action if not explicitly provided in overrides
        action = task.overrides.get("action")
        if not action:
            if task.type == "provision":
                action = "create"
            elif task.type == "destroy":
                action = "delete"
            else:
                action = task.type

        try:
            if resource == "record":
                output = self._handle_record(action, task)
            elif resource == "zone":
                output = self._handle_zone(action, task)
            elif resource == "dhcp":
                output = self._handle_dhcp(action, task)
            elif resource == "backup":
                output = self._handle_backup(action, task)
            else:
                raise ExecutionError(f"Unsupported resource type: {resource}")

            duration = time.time() - start
            return TaskResult(
                success=True,
                task_type=task.type,
                output=output,
                duration=duration,
            )
        except Exception as e:
            if isinstance(e, ExecutionError):
                raise
            raise ExecutionError(f"Technitium operation failed: {str(e)}")

    def _handle_dhcp(self, action: str, task: Task) -> Dict[str, Any]:
        """Handle DHCP scope operations."""
        params = task.overrides.copy()
        
        if action == "list":
            return self._api_call("dhcp/scopes/list", params)
        elif action == "enable":
            return self._api_call("dhcp/scopes/enable", params)
        elif action == "disable":
            return self._api_call("dhcp/scopes/disable", params)
        else:
            raise ExecutionError(f"Unsupported DHCP action: {action}")

    def _handle_backup(self, action: str, task: Task) -> Dict[str, Any]:
        """Handle Backup operations."""
        if action == "export":
            # 1. List all zones
            zones_data = self._api_call("zones/list", {})
            zones = zones_data.get("zones", [])

            backups = {}
            for zone in zones:
                zone_name = zone.get("name")
                if zone_name:
                    # 2. Export each zone
                    export_data = self._api_call("zones/export", {"zone": zone_name})
                    backups[zone_name] = export_data.get("zoneFileContent")
            
            return {
                "zones": backups,
                "filename": "technitium-zones.json"
            }
        else:
            raise ExecutionError(f"Unsupported backup action: {action}")

    def _handle_record(self, action: str, task: Task) -> Dict[str, Any]:
        """Handle DNS record operations."""
        params = task.overrides.copy()
        
        # If it's a provision task and record info is missing, try to infer from profile
        if action == "create" and "domain" not in params:
             # Assume profile.name is the hostname if domain is missing
             params.setdefault("zone", "homelab.internal") # Default zone
             params.setdefault("domain", f"{task.profile.name}.homelab.internal")
             if task.target:
                 params.setdefault("ipAddress", task.target)
             params.setdefault("type", "A")

        if action in ("create", "add"):
            return self._api_call("zones/records/add", params)
        elif action == "delete":
            return self._api_call("zones/records/delete", params)
        elif action in ("list", "get"):
            return self._api_call("zones/records/get", params)
        else:
            raise ExecutionError(f"Unsupported record action: {action}")

    def _handle_zone(self, action: str, task: Task) -> Dict[str, Any]:
        """Handle DNS zone operations."""
        params = task.overrides.copy()
        
        if action in ("create", "add"):
            return self._api_call("zones/create", params)
        elif action == "delete":
            return self._api_call("zones/delete", params)
        elif action == "list":
            return self._api_call("zones/list", params)
        else:
            raise ExecutionError(f"Unsupported zone action: {action}")

    def _api_call(self, endpoint: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Perform Technitium API call."""
        url = f"{self.host}/api/{endpoint}"
        query_params = {"token": self.token}
        
        # Map some common params to Technitium API names if they differ
        api_params = params.copy()
        
        # Mapping common names to API names
        mappings = {
            "ip_address": "ipAddress",
            "ip": "ipAddress",
            "record_type": "type",
            "ttl": "ttl",
            "ptr": "ptrName"
        }
        for k, v in mappings.items():
            if k in api_params:
                api_params.setdefault(v, api_params.pop(k))

        # Filter out driver internal params
        api_params.pop("resource", None)
        api_params.pop("action", None)

        query_params.update(api_params)

        try:
            response = requests.get(url, params=query_params, timeout=self.timeout)
            if response.status_code != 200:
                raise ExecutionError(
                    f"Technitium API error ({response.status_code}): {response.text}"
                )
            
            data = response.json()
            if data.get("status") == "error":
                raise ExecutionError(
                    f"Technitium Error: {data.get('errorMessage')}"
                )
            
            return data.get("response", data)
        except requests.exceptions.RequestException as e:
            raise ExecutionError(f"Technitium request failed: {str(e)}")
