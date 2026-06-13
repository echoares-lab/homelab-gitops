from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Dict, Any

@dataclass
class NodeProfile:
    """Represents a profile YAML loaded and validated."""
    name: str
    vcenter: Dict[str, Any]  # datacenter, cluster, datastore, network
    vm_specs: Dict[str, Any]  # cpu, memory, disk
    deployment: Dict[str, Any]  # tags, roles, playbooks
    networking: Dict[str, Any] = field(default_factory=dict)  # vlan, firewall_rules

    def __post_init__(self):
        """Validate structure on creation."""
        required_vcenter = ["datacenter", "cluster", "datastore", "network"]
        required_vm = ["cpu", "memory", "disk"]

        for key in required_vcenter:
            if key not in self.vcenter:
                raise ValueError(f"vcenter missing required key: {key}")
        for key in required_vm:
            if key not in self.vm_specs:
                raise ValueError(f"vm_specs missing required key: {key}")

@dataclass
class DeploymentState:
    """Tracks a node through its lifecycle."""
    profile_name: str
    index: str
    vm_name: str
    state: str = "planned"  # planned, deployed, configured, tested, failed
    vm_ip: Optional[str] = None
    workspace_id: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)
    error: Optional[str] = None

@dataclass
class Task:
    """A unit of work for a driver to execute."""
    type: str  # build, provision, configure, test, destroy
    profile: NodeProfile
    target: Optional[str] = None  # VM IP or name
    overrides: Dict[str, Any] = field(default_factory=dict)

@dataclass
class TaskResult:
    """Result of task execution."""
    success: bool
    task_type: str
    output: Any
    duration: float
    error: Optional[str] = None
    vm_ip: Optional[str] = None  # Returned from deploy task
