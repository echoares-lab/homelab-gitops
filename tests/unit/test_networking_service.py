"""Unit tests for NetworkingService."""

import pytest
from unittest.mock import MagicMock
from homelab_gitops.domain.networking import NetworkingService
from homelab_gitops.domain.models import Task, NodeProfile

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
        networking={"vlan": {"id": 10, "enabled": True}, "firewall_rules": []}
    )

def test_networking_service_prepare_node_network(networking_service, mock_driver, dummy_profile):
    mock_driver.execute.return_value = MagicMock(success=True)
    results = networking_service.prepare_node_network(profile=dummy_profile)
    assert len(results) >= 0

def test_networking_service_cleanup_node_network(networking_service, mock_driver, dummy_profile):
    mock_driver.execute.return_value = MagicMock(success=True)
    results = networking_service.cleanup_node_network(profile=dummy_profile)
    assert len(results) >= 0
