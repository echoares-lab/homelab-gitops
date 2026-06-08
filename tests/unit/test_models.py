import pytest
from homelab_gitops.domain.models import NodeProfile, DeploymentState
from datetime import datetime

def test_node_profile_from_dict():
    """NodeProfile can be created from dict (profile YAML)."""
    profile_dict = {
        "name": "ubuntu-base",
        "vcenter": {
            "datacenter": "DC1",
            "cluster": "Cluster1",
            "datastore": "DS1",
            "network": "VM Network",
        },
        "vm_specs": {
            "cpu": 4,
            "memory": 8192,
            "disk": 50,
        },
        "deployment": {
            "tags": ["ubuntu"],
            "roles": ["base", "security"],
        },
    }
    profile = NodeProfile(**profile_dict)
    assert profile.name == "ubuntu-base"
    assert profile.vcenter["datacenter"] == "DC1"
    assert profile.vm_specs["cpu"] == 4

def test_deployment_state_initial():
    """DeploymentState tracks node lifecycle."""
    state = DeploymentState(profile_name="ubuntu-base", index="01", vm_name="ubuntu-base-01")
    assert state.state == "planned"
    assert state.vm_ip is None
    assert isinstance(state.created_at, datetime)

def test_task_creation():
    """Task represents a unit of work."""
    from homelab_gitops.domain.models import Task
    profile_dict = {"name": "test", "vcenter": {"datacenter": "DC", "cluster": "C", "datastore": "DS", "network": "N"}, "vm_specs": {"cpu": 1, "memory": 1024, "disk": 10}, "deployment": {}}
    profile = NodeProfile(**profile_dict)
    task = Task(type="deploy", profile=profile, target="10.10.10.50")
    assert task.type == "deploy"
    assert task.profile == profile
