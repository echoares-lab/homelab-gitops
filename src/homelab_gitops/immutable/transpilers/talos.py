import shutil
from homelab_gitops.domain.models import NodeProfile
from homelab_gitops.immutable.transpilers.base import Transpiler
from homelab_gitops.drivers.exceptions import ExecutionError

class TalosTranspiler(Transpiler):
    def transpile(self, profile: NodeProfile) -> str:
        talosctl_path = shutil.which("talosctl")
        if not talosctl_path:
            raise ExecutionError("talosctl not found in PATH")
            
        # Simplified proof-of-concept. Normally we run talosctl gen config.
        # But we return a stub YAML matching what Tofu expects to inject into GuestInfo.
        return "version: v1alpha1\nmachine:\n  network:\n    hostname: " + profile.name
