"""Stateful migration driver for DHCP cutovers."""

import json
import os
import time
from datetime import datetime
from typing import List, Dict, Any, Optional
from homelab_gitops.drivers.base import Driver
from homelab_gitops.drivers.exceptions import ExecutionError
from homelab_gitops.drivers.opnsense_driver import OPNsenseDriver
from homelab_gitops.drivers.technitium_driver import TechnitiumDriver
from homelab_gitops.domain.models import Task, TaskResult, NodeProfile


class MigrationDriver(Driver):
    """Driver for managing stateful migrations with rollback support."""

    def __init__(self, state_file: str = ".dhcp-migration-state.json",
                 opnsense_driver: Optional[OPNsenseDriver] = None,
                 technitium_driver: Optional[TechnitiumDriver] = None):
        """Initialize with state file and sub-drivers."""
        self.state_file = state_file
        self.opnsense_driver = opnsense_driver or OPNsenseDriver()
        self.technitium_driver = technitium_driver or TechnitiumDriver()

    def validate(self) -> bool:
        """Validate state file accessibility and sub-drivers."""
        # Ensure directory for state file is writable
        state_dir = os.path.dirname(os.path.abspath(self.state_file))
        if not os.access(state_dir, os.W_OK):
            return False
            
        return self.opnsense_driver.validate() and self.technitium_driver.validate()

    def execute(self, task: Task) -> TaskResult:
        """Execute migration-related state tasks."""
        start = time.time()
        action = task.overrides.get("action")
        
        try:
            if action == "save_state":
                migrated = task.overrides.get("migrated", [])
                output = self.save_state(migrated)
            elif action == "load_state":
                output = {"migrated": self.load_state()}
            elif action == "rollback":
                output = self.rollback(task.profile)
            elif action == "clear_state":
                if os.path.exists(self.state_file):
                    os.remove(self.state_file)
                output = {"status": "cleared"}
            else:
                raise ExecutionError(f"Unsupported migration action: {action}")

            return TaskResult(
                success=True,
                task_type=task.type,
                output=output,
                duration=time.time() - start
            )
        except Exception as e:
            if isinstance(e, ExecutionError):
                raise
            raise ExecutionError(f"Migration state operation failed: {str(e)}")

    def save_state(self, migrated: List[Dict[str, str]]) -> Dict[str, Any]:
        """Save migration state to JSON file."""
        state = {
            'migrated': migrated,
            'timestamp': datetime.now().isoformat()
        }
        with open(self.state_file, 'w') as f:
            json.dump(state, f, indent=2)
        return {"status": "saved", "path": self.state_file}

    def load_state(self) -> List[Dict[str, str]]:
        """Load migration state from JSON file."""
        if not os.path.exists(self.state_file):
            return []
        try:
            with open(self.state_file, 'r') as f:
                data = json.load(f)
                return data.get('migrated', [])
        except (json.JSONDecodeError, IOError):
            return []

    def rollback(self, profile: NodeProfile) -> Dict[str, Any]:
        """Roll back migration based on saved state."""
        migrated = self.load_state()
        if not migrated:
            return {"status": "skipped", "reason": "no_state"}

        results = []
        failed = []
        
        for m in migrated:
            iface = m.get('opnsense_interface')
            scope = m.get('technitium_scope')
            
            if not iface or not scope:
                continue
                
            try:
                # Re-enable OPNsense
                self.opnsense_driver.execute(Task(
                    type="dhcp",
                    profile=profile,
                    overrides={"resource": "dhcp", "action": "enable", "interface": iface}
                ))
                
                # Disable Technitium
                self.technitium_driver.execute(Task(
                    type="dhcp",
                    profile=profile,
                    overrides={"resource": "dhcp", "action": "disable", "name": scope}
                ))
                
                results.append({"interface": iface, "scope": scope, "status": "rolled_back"})
            except Exception as e:
                failed.append({"interface": iface, "error": str(e)})

        if not failed:
            if os.path.exists(self.state_file):
                os.remove(self.state_file)
            return {"status": "success", "results": results}
        else:
            return {"status": "partial_failure", "results": results, "failed": failed}
