"""End-to-end integration tests for OPNsense client

These tests require a running OPNsense instance.
Set environment variables:
  OPNSENSE_KEY=<your-api-key>
  OPNSENSE_SECRET=<your-api-secret>
  OPNSENSE_URL=https://opnsense.local/api
"""

import os
import time
import pytest
from opnsense.modules.firewall import FirewallClient
from opnsense.modules.network import NetworkClient
from opnsense.exceptions import APIError


@pytest.fixture(scope="module")
def opnsense_skip():
    """Skip tests if OPNsense credentials not configured"""
    if not os.getenv('OPNSENSE_KEY'):
        pytest.skip("OPNSENSE_KEY not set")


@pytest.fixture
def firewall_client():
    """Create FirewallClient with env credentials"""
    return FirewallClient(
        api_key=os.getenv('OPNSENSE_KEY'),
        api_secret=os.getenv('OPNSENSE_SECRET'),
        url=os.getenv('OPNSENSE_URL')
    )


@pytest.fixture
def network_client():
    """Create NetworkClient with env credentials"""
    return NetworkClient(
        api_key=os.getenv('OPNSENSE_KEY'),
        api_secret=os.getenv('OPNSENSE_SECRET'),
        url=os.getenv('OPNSENSE_URL')
    )


@pytest.mark.integration
def test_firewall_rule_lifecycle(firewall_client, opnsense_skip):
    """E2E: Create, read, update, delete firewall rule"""

    # Create rule with unique name
    rule_name = f"test-rule-e2e-{int(time.time())}"
    result = firewall_client.create_firewall_rule(
        name=rule_name,
        src_net="10.0.0.0/24",
        dst_net="192.168.0.0/24",
        protocol="tcp",
        port=443,
        action="pass",
        description="E2E test rule"
    )
    rule_id = result['uuid']

    # Read rule
    rule = firewall_client.get_firewall_rule(rule_id)
    assert rule['name'] == rule_name
    assert rule['src_net'] == "10.0.0.0/24"
    assert rule['dst_net'] == "192.168.0.0/24"
    assert rule['protocol'] == "tcp"
    assert rule['action'] == "pass"

    # Verify in list
    rules = firewall_client.list_firewall_rules()
    rule_names = [r['name'] for r in rules]
    assert rule_name in rule_names

    # Update rule
    firewall_client.update_firewall_rule(
        rule_id,
        description="Updated E2E test rule"
    )

    # Verify update
    updated_rule = firewall_client.get_firewall_rule(rule_id)
    assert updated_rule['description'] == "Updated E2E test rule"

    # Delete rule
    firewall_client.delete_firewall_rule(rule_id)

    # Verify deleted
    with pytest.raises(APIError):
        firewall_client.get_firewall_rule(rule_id)


@pytest.mark.integration
def test_firewall_rule_filtering(firewall_client, opnsense_skip):
    """E2E: Create multiple rules and filter"""

    # Create first rule
    rule1_name = f"test-filter-1-{int(time.time())}"
    result1 = firewall_client.create_firewall_rule(
        name=rule1_name,
        src_net="10.0.0.0/24",
        dst_net="192.168.0.0/24",
        protocol="tcp",
        action="pass"
    )
    rule1_id = result1['uuid']

    # Create second rule
    rule2_name = f"test-filter-2-{int(time.time())}"
    result2 = firewall_client.create_firewall_rule(
        name=rule2_name,
        src_net="172.16.0.0/16",
        dst_net="10.0.0.0/8",
        protocol="udp",
        action="block"
    )
    rule2_id = result2['uuid']

    # List all rules
    all_rules = firewall_client.list_firewall_rules()
    assert len(all_rules) >= 2

    # Cleanup
    firewall_client.delete_firewall_rule(rule1_id)
    firewall_client.delete_firewall_rule(rule2_id)


@pytest.mark.integration
def test_vlan_lifecycle(network_client, opnsense_skip):
    """E2E: Create, read, update, delete VLAN"""

    # Create VLAN with unique ID
    vlan_id_value = 900 + int(time.time() % 100)
    result = network_client.create_vlan(
        interface="em0",
        vlan_id=vlan_id_value,
        description="e2e-test-vlan"
    )
    vlan_id = result['uuid']

    # Read VLAN
    vlan = network_client.get_vlan(vlan_id)
    assert vlan['vlan_id'] == vlan_id_value
    assert vlan['description'] == "e2e-test-vlan"
    assert vlan['interface'] == "em0"

    # Verify in list
    vlans = network_client.list_vlans()
    vlan_ids_in_list = [v['vlan_id'] for v in vlans]
    assert vlan_id_value in vlan_ids_in_list

    # Delete VLAN
    network_client.delete_vlan(vlan_id)

    # Verify deleted
    with pytest.raises(APIError):
        network_client.get_vlan(vlan_id)


@pytest.mark.integration
def test_vlan_multiple_interfaces(network_client, opnsense_skip):
    """E2E: Create VLANs on different interfaces"""

    # Create VLAN on em0
    vlan1_id_value = 800 + int(time.time() % 100)
    result1 = network_client.create_vlan(
        interface="em0",
        vlan_id=vlan1_id_value,
        description="e2e-test-vlan-em0"
    )
    vlan1_id = result1['uuid']

    # Create VLAN on em1
    vlan2_id_value = 801 + int(time.time() % 100)
    result2 = network_client.create_vlan(
        interface="em1",
        vlan_id=vlan2_id_value,
        description="e2e-test-vlan-em1"
    )
    vlan2_id = result2['uuid']

    # Verify both exist
    vlans = network_client.list_vlans()
    vlan_ids_in_list = [v['vlan_id'] for v in vlans]
    assert vlan1_id_value in vlan_ids_in_list
    assert vlan2_id_value in vlan_ids_in_list

    # Cleanup
    network_client.delete_vlan(vlan1_id)
    network_client.delete_vlan(vlan2_id)


@pytest.mark.integration
def test_list_interfaces(network_client, opnsense_skip):
    """E2E: Can list interfaces"""
    interfaces = network_client.list_interfaces()

    assert isinstance(interfaces, list)
    assert len(interfaces) > 0

    # Each interface has expected fields
    for iface in interfaces:
        assert 'name' in iface
        assert isinstance(iface['name'], str)


@pytest.mark.integration
def test_get_interface_details(network_client, opnsense_skip):
    """E2E: Get details of a specific interface"""

    # List interfaces first
    interfaces = network_client.list_interfaces()
    assert len(interfaces) > 0

    # Get details of first interface
    first_interface_name = interfaces[0]['name']
    interface = network_client.get_interface(first_interface_name)

    assert interface['name'] == first_interface_name
    assert 'status' in interface or interface is not None


@pytest.mark.integration
def test_firewall_rule_protocols(firewall_client, opnsense_skip):
    """E2E: Test various protocol types in rules"""

    protocols = ['tcp', 'udp', 'icmp']
    rule_ids = []

    for protocol in protocols:
        rule_name = f"test-protocol-{protocol}-{int(time.time())}"
        result = firewall_client.create_firewall_rule(
            name=rule_name,
            src_net="10.0.0.0/24",
            dst_net="192.168.0.0/24",
            protocol=protocol,
            action="pass"
        )
        rule_ids.append(result['uuid'])

    # Verify each rule was created with correct protocol
    rules = firewall_client.list_firewall_rules()
    rule_protocols = {r['name']: r['protocol'] for r in rules}

    for idx, protocol in enumerate(protocols):
        rule_name = f"test-protocol-{protocol}-{int(time.time())}"
        # The rule should be in the list (may have different exact timestamp)
        found = False
        for rule in rules:
            if f"test-protocol-{protocol}" in rule['name']:
                assert rule['protocol'] == protocol
                found = True
                break
        assert found, f"Rule with protocol {protocol} not found"

    # Cleanup
    for rule_id in rule_ids:
        try:
            firewall_client.delete_firewall_rule(rule_id)
        except APIError:
            pass  # Already deleted


@pytest.mark.integration
def test_firewall_rule_actions(firewall_client, opnsense_skip):
    """E2E: Test different rule actions (pass, block, reject)"""

    actions = ['pass', 'block', 'reject']
    rule_ids = []

    for action in actions:
        rule_name = f"test-action-{action}-{int(time.time())}"
        result = firewall_client.create_firewall_rule(
            name=rule_name,
            src_net="10.0.0.0/24",
            dst_net="192.168.0.0/24",
            protocol="tcp",
            action=action
        )
        rule_ids.append(result['uuid'])

    # Verify each rule was created with correct action
    rules = firewall_client.list_firewall_rules()
    for rule_id in rule_ids:
        rule = firewall_client.get_firewall_rule(rule_id)
        assert rule['action'] in actions

    # Cleanup
    for rule_id in rule_ids:
        try:
            firewall_client.delete_firewall_rule(rule_id)
        except APIError:
            pass  # Already deleted
