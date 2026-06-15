import os
import json
import tempfile
from datetime import datetime
from typing import Dict, Any, List
from homelab_gitops.drivers.opnsense_driver import OPNsenseDriver
from homelab_gitops.drivers.technitium_driver import TechnitiumDriver
from homelab_gitops.drivers.secrets_driver import SecretsDriver
from homelab_gitops.domain.models import Task, NodeProfile

class BackupService:
    """Service for managing infrastructure backups."""

    def __init__(self, opnsense_driver=None, technitium_driver=None, secrets_driver=None):
        self.opnsense = opnsense_driver or OPNsenseDriver()
        self.technitium = technitium_driver or TechnitiumDriver()
        self.secrets = secrets_driver or SecretsDriver()

    def run_backup(self) -> List[Dict[str, Any]]:
        """Run backup for all supported services."""
        results = []
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")

        # 1. OPNsense Backup
        try:
            opnsense_task = Task(
                type="backup",
                profile=self._get_dummy_profile("opnsense"),
                overrides={"resource": "backup", "action": "export"}
            )
            res = self.opnsense.execute(opnsense_task)
            if res.success:
                content = res.output["content"]
                filename = f"opnsense-config-{timestamp}.xml"
                self._store_in_1password(filename, content)
                results.append({"service": "OPNsense", "status": "success", "file": filename})
            else:
                results.append({"service": "OPNsense", "status": "failed", "error": res.error})
        except Exception as e:
            results.append({"service": "OPNsense", "status": "failed", "error": str(e)})

        # 2. Technitium Backup
        try:
            technitium_task = Task(
                type="backup",
                profile=self._get_dummy_profile("technitium"),
                overrides={"resource": "backup", "action": "export"}
            )
            res = self.technitium.execute(technitium_task)
            if res.success:
                content = json.dumps(res.output["zones"], indent=2)
                filename = f"technitium-zones-{timestamp}.json"
                self._store_in_1password(filename, content)
                results.append({"service": "Technitium", "status": "success", "file": filename})
            else:
                results.append({"service": "Technitium", "status": "failed", "error": res.error})
        except Exception as e:
            results.append({"service": "Technitium", "status": "failed", "error": str(e)})

        return results

    def _store_in_1password(self, filename: str, content: str):
        """Store content in 1Password as a document."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as tmp:
            tmp.write(content)
            tmp_path = tmp.name
        
        try:
            self.secrets.store_document(title=filename, file_path=tmp_path)
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    def _get_dummy_profile(self, name: str) -> NodeProfile:
        """Create a dummy profile for tasks that don't really need one."""
        return NodeProfile(
            name=name,
            vcenter={"datacenter": "dc", "cluster": "cl", "datastore": "ds", "network": "nw"},
            vm_specs={"cpu": 1, "memory": 1024, "disk": 10},
            deployment={"tags": [], "roles": [], "playbooks": []}
        )
