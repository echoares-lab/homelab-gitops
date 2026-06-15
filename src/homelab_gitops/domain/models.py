from datetime import datetime
from typing import Optional, Dict, Any, Generic, TypeVar
from pydantic import BaseModel, Field, field_validator

T = TypeVar("T")

class NodeProfile(BaseModel):
    """Represents a profile YAML loaded and validated."""
    name: str
    vcenter: Dict[str, Any]  # datacenter, cluster, datastore, network
    vm_specs: Dict[str, Any]  # cpu, memory, disk
    deployment: Dict[str, Any]  # tags, roles, playbooks
    networking: Dict[str, Any] = Field(default_factory=dict)  # vlan, firewall_rules


    @field_validator("vcenter")
    @classmethod
    def validate_vcenter(cls, v: Dict[str, Any]) -> Dict[str, Any]:
        required_vcenter = ["datacenter", "cluster", "datastore", "network"]
        for key in required_vcenter:
            if key not in v:
                raise ValueError(f"vcenter missing required key: {key}")
        return v

    @field_validator("vm_specs")
    @classmethod
    def validate_vm_specs(cls, v: Dict[str, Any]) -> Dict[str, Any]:
        required_vm = ["cpu", "memory", "disk"]
        for key in required_vm:
            if key not in v:
                raise ValueError(f"vm_specs missing required key: {key}")
        return v

class DeploymentState(BaseModel):
    """Tracks a node through its lifecycle."""
    profile_name: str
    index: str
    vm_name: str
    state: str = "planned"  # planned, deployed, configured, tested, failed
    vm_ip: Optional[str] = None
    workspace_id: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.now)
    error: Optional[str] = None


class Task(BaseModel):
    """A unit of work for a driver to execute."""
    type: str  # build, provision, configure, test, destroy
    profile: Optional[NodeProfile] = None
    target: Optional[str] = None  # VM IP or name
    overrides: Dict[str, Any] = Field(default_factory=dict)


class TaskResult(BaseModel, Generic[T]):
    """Result of task execution."""
    success: bool
    task_type: str
    output: T
    duration: float
    error: Optional[str] = None
    vm_ip: Optional[str] = None  # Returned from deploy task

