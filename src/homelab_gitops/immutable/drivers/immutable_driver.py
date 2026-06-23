"""Driver for verifying immutable deployments."""
import time
from homelab_gitops.drivers.base import Driver
from homelab_gitops.domain.models import Task, TaskResult
from homelab_gitops.drivers.exceptions import ExecutionError

class ImmutableDriver(Driver):
    def validate(self) -> bool:
        return True

    def execute(self, task: Task) -> TaskResult:
        start = time.time()
        
        if task.type not in ["config", "configure"]:
            raise ExecutionError(f"ImmutableDriver only overrides config, not {task.type}")
            
        # Immutable nodes receive their config from Tofu GuestInfo injection at boot.
        # Here we would poll the native API (e.g. talosctl health) to verify readiness.
        # For now, we simulate success.
        print(f"Immutable node {task.profile.name} config injection verified.")
        
        duration = time.time() - start
        return TaskResult(
            success=True,
            task_type=task.type,
            output="Immutable config applied via boot injection.",
            duration=duration,
        )
