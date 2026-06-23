"""Base transpiler class."""
import abc
from homelab_gitops.domain.models import NodeProfile

class Transpiler(abc.ABC):
    @abc.abstractmethod
    def transpile(self, profile: NodeProfile) -> str:
        """Convert a profile to the immutable OS's native configuration string."""
        pass
