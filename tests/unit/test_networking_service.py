"""Unit tests for NetworkingService."""

import pytest
from unittest.mock import MagicMock
from homelab_gitops.domain.networking import NetworkingService
from homelab_gitops.domain.models import Task, NodeProfile, TaskResult

@pytest.fixture
def mock_driver():
    return MagicMock()

@pytest.fixture
def networking_service(mock_driver):
    return NetworkingService(driver=mock_driver)

@pytest.fixture
def dummy_profile():
    return NodeProfile(
        name="test-profile",
        vcenter={"datacenter": "D", "cluster": "C", "datastore": "S", "network": "N"},
        vm_specs={"cpu": 1, "memory": 1, "disk": 1},
        deployment={"tags": [], "roles": [], "playbooks": []},
        networking={
            "vlan": {"id": 10, "interface": "em0", "enabled": True, "name": "TestVLAN"},
            "firewall_rules": [
                {
                    "name": "Allow HTTP",
                    "src_net": "any",
                    "dst_net": "any",
                    "protocol": "tcp",
                    "port": 80,
                    "action": "pass",
                    "enabled": True
                },
                {
                    "name": "Disabled Rule",
                    "enabled": False
                }
            ]
        }
    )

def test_prepare_node_network_no_config(networking_service):
    profile = NodeProfile(
        name="no-net",
        vcenter={"datacenter": "D", "cluster": "C", "datastore": "S", "network": "N"},
        vm_specs={"cpu": 1, "memory": 1, "disk": 1},
        deployment={"tags": [], "roles": [], "playbooks": []},
        networking={}
    )
    results = networking_service.prepare_node_network(profile)
    assert results == []

def test_prepare_node_network_vlan_exists(networking_service, mock_driver, dummy_profile):
    # Mock VLAN list to show it already exists
    mock_driver.execute.side_effect = [
        TaskResult(success=True, task_type="vlan", output={"vlans": [{"tag": "10", "if": "em0"}]}, duration=0.1),
        TaskResult(success=True, task_type="firewall", output={"rules": []}, duration=0.1),
        TaskResult(success=True, task_type="firewall", output={"status": "created"}, duration=0.1),
    ]
    
    results = networking_service.prepare_node_network(dummy_profile)
    
    assert len(results) == 2 # 1 skipped VLAN, 1 created Firewall rule
    assert results[0].output["status"] == "skipped"
    assert results[0].output["reason"] == "already_exists"
    assert results[1].task_type == "firewall"

def test_prepare_node_network_vlan_create(networking_service, mock_driver, dummy_profile):
    # Mock VLAN list to show it doesn't exist
    mock_driver.execute.side_effect = [
        TaskResult(success=True, task_type="vlan", output={"vlans": []}, duration=0.1),
        TaskResult(success=True, task_type="vlan", output={"status": "created"}, duration=0.1),
        TaskResult(success=True, task_type="firewall", output={"rules": []}, duration=0.1),
        TaskResult(success=True, task_type="firewall", output={"status": "created"}, duration=0.1),
    ]
    
    results = networking_service.prepare_node_network(dummy_profile)
    
    assert len(results) == 2
    assert results[0].task_type == "vlan"
    assert results[1].task_type == "firewall"

def test_prepare_node_network_firewall_exists(networking_service, mock_driver, dummy_profile):
    # Mock VLAN list and Firewall list
    mock_driver.execute.side_effect = [
        TaskResult(success=True, task_type="vlan", output={"vlans": [{"tag": "10", "if": "em0"}]}, duration=0.1),
        TaskResult(success=True, task_type="firewall", output={"rules": [{"description": "Allow HTTP"}]}, duration=0.1),
    ]
    
    results = networking_service.prepare_node_network(dummy_profile)
    
    assert len(results) == 2
    assert results[0].output["reason"] == "already_exists"
    assert results[1].output["reason"] == "already_exists"

def test_cleanup_node_network_no_config(networking_service):
    profile = NodeProfile(
        name="no-net",
        vcenter={"datacenter": "D", "cluster": "C", "datastore": "S", "network": "N"},
        vm_specs={"cpu": 1, "memory": 1, "disk": 1},
        deployment={"tags": [], "roles": [], "playbooks": []},
        networking={}
    )
    results = networking_service.cleanup_node_network(profile)
    assert results == []

def test_cleanup_node_network_full(networking_service, mock_driver, dummy_profile):
    # Mock Firewall list and VLAN list
    mock_driver.execute.side_effect = [
        TaskResult(success=True, task_type="firewall", output={"rules": [{"description": "Allow HTTP", "uuid": "rule-uuid"}]}, duration=0.1),
        TaskResult(success=True, task_type="firewall", output={"status": "deleted"}, duration=0.1),
        TaskResult(success=True, task_type="vlan", output={"vlans": [{"tag": "10", "if": "em0", "uuid": "vlan-uuid"}]}, duration=0.1),
        TaskResult(success=True, task_type="vlan", output={"status": "deleted"}, duration=0.1),
    ]
    
    results = networking_service.cleanup_node_network(dummy_profile)
    
    assert len(results) == 2
    assert results[0].task_type == "firewall"
    assert results[1].task_type == "vlan"

def test_cleanup_node_network_not_found(networking_service, mock_driver, dummy_profile):
    # Mock Firewall list and VLAN list to be empty
    mock_driver.execute.side_effect = [
        TaskResult(success=True, task_type="firewall", output={"rules": []}, duration=0.1),
        TaskResult(success=True, task_type="vlan", output={"vlans": []}, duration=0.1),
    ]
    
    results = networking_service.cleanup_node_network(dummy_profile)
    
    assert len(results) == 0
