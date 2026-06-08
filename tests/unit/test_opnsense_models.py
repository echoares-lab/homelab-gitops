from opnsense.models import FirewallRule, VLAN, Interface

def test_firewall_rule_creation():
    """FirewallRule can be created with required fields"""
    rule = FirewallRule(
        id="abc123",
        name="Allow SSH",
        description="SSH from mgmt",
        enabled=True,
        action="pass",
        protocol="tcp",
        src_net="10.0.0.0/24",
        dst_net="0.0.0.0/0",
        port=22,
        log=True
    )

    assert rule.id == "abc123"
    assert rule.name == "Allow SSH"
    assert rule.enabled is True
    assert rule.action == "pass"

def test_firewall_rule_conversion_to_dict():
    """FirewallRule can be converted to dict"""
    rule = FirewallRule(
        id="abc123",
        name="test",
        description="",
        enabled=True,
        action="pass",
        protocol="tcp",
        src_net="10.0.0.0/24",
        dst_net="0.0.0.0/0",
        port=22,
        log=False
    )

    rule_dict = rule.__dict__
    assert rule_dict['name'] == "test"
    assert rule_dict['id'] == "abc123"

def test_vlan_creation():
    """VLAN can be created with required fields"""
    vlan = VLAN(
        id="vlan-100",
        interface="em0",
        vlan_id=100,
        description="web-tier",
        enabled=True
    )

    assert vlan.id == "vlan-100"
    assert vlan.vlan_id == 100
    assert vlan.interface == "em0"

def test_interface_creation():
    """Interface can be created with fields"""
    interface = Interface(
        name="em0",
        ip_address="192.168.1.1",
        gateway="192.168.1.254",
        dns_servers=["8.8.8.8"],
        mtu=1500
    )

    assert interface.name == "em0"
    assert interface.ip_address == "192.168.1.1"
    assert interface.mtu == 1500
