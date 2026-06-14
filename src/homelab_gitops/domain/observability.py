from typing import Dict, Any
from homelab_gitops.domain.models import NodeProfile, Task, TaskResult

class ObservabilityService:
    """Service to manage observability stack."""

    def __init__(self):
        from homelab_gitops.drivers.ansible_driver import AnsibleDriver
        self.ansible = AnsibleDriver()

    def deploy_monitoring(self, profile: NodeProfile) -> TaskResult:
        """Deploy monitoring stack to a node."""
        task = Task(
            type="config",
            profile=profile,
            target=profile.name,
            overrides={
                "tags": "alloy,docker_metrics"
            }
        )
        return self.ansible.execute(task)

    def get_metrics(self, profile: NodeProfile) -> Dict[str, Any]:
        """Get metrics for a node."""
        return {"status": "ok", "metrics": {}}
